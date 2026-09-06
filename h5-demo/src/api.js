// 与后端交互；后端不可用时自动回退到离线快照（offline-snapshots.json，
// 由 backend/scripts/generate_h5_offline_snapshots.py 用真实引擎生成）。
// H5 Demo 只提交预置场景生成的头像指纹网格；不会读取浏览器或游戏进程。
// 所有路径使用相对路径 + base './'，构建产物可部署到 GitHub Pages 子路径。

import snapshots from './offline-snapshots.json'

const GRID_SIZE = 16
const MAX_LUMINANCE = 255
const FETCH_TIMEOUT_MS = 1500

let offlineMode = null // null=未知 true=离线 false=在线

export function isOffline() {
  return offlineMode === true
}

function pickScenarioSnapshot(scenarioId) {
  return snapshots?.scenarios?.[scenarioId] || snapshots?.scenarios?.[Object.keys(snapshots?.scenarios || {})[0]]
}

async function fetchWithTimeout(url, options = {}) {
  const controller = new AbortController()
  const timer = setTimeout(() => controller.abort(), FETCH_TIMEOUT_MS)
  try {
    return await fetch(url, { ...options, signal: controller.signal })
  } finally {
    clearTimeout(timer)
  }
}

export async function fetchHeroes() {
  const res = await fetch('heroes.json')
  if (!res.ok) throw new Error(`加载英雄清单失败 HTTP ${res.status}`)
  const data = await res.json()
  return data.heroes
}

export async function fetchPortraitIndex() {
  const res = await fetch('portrait_index.json')
  if (!res.ok) throw new Error(`加载头像索引失败 HTTP ${res.status}`)
  return res.json()
}

/**
 * 为演示场景构造与 Android 同格式的 16x16 亮度网格。
 * 场景使用官方头像的已缓存网格，真实请求仍经过 /api/frames/analyze。
 */
export function buildCaptureSlots(index, heroIds) {
  const byId = new Map((index?.entries || []).map((entry) => [entry.hero_id, entry]))
  return heroIds.map((heroId, slotIndex) => {
    const entry = byId.get(heroId)
    if (!entry || !Array.isArray(entry.grid) || entry.grid.length !== GRID_SIZE * GRID_SIZE) {
      throw new Error(`场景缺少英雄 ${heroId} 的 16×16 指纹`)
    }
    return { slot_index: slotIndex, grid: entry.grid.map((value) => Math.max(0, Math.min(MAX_LUMINANCE, Number(value)))) }
  })
}

function offlineAnalyze(snapshot) {
  if (!snapshot?.analyze) throw new Error('离线识别数据缺失')
  return snapshot.analyze
}

export async function analyzeFrame(index, heroIds, scenarioId) {
  // 后端不可用时直接返回离线快照，保持流程状态机不变。
  if (offlineMode === true) return offlineAnalyze(pickScenarioSnapshot(scenarioId))

  const payload = {
    input_source: 'player_tapped_capture',
    layout_version: 'draft-layout-1080x2400-v1',
    slots: buildCaptureSlots(index, heroIds),
  }
  try {
    const res = await fetchWithTimeout('api/frames/analyze', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    })
    if (!res.ok) throw new Error(`识别接口返回 HTTP ${res.status}`)
    const body = await res.json()
    offlineMode = false
    return body
  } catch (err) {
    offlineMode = true
    return offlineAnalyze(pickScenarioSnapshot(scenarioId))
  }
}

function offlineDecision(snapshot, ownHeroId) {
  const ownKey = String(ownHeroId)
  const decision = snapshot?.decisions?.[ownKey] || Object.values(snapshot?.decisions || {})[0]
  if (!decision) throw new Error('离线建议数据缺失')
  return decision
}

export async function requestDecision(state, scenarioId) {
  if (offlineMode === true) return offlineDecision(pickScenarioSnapshot(scenarioId), state.ownHeroId)

  const payload = {
    input_source: 'player_confirmed_screen',
    enemy_hero_ids: state.enemyHeroIds,
    own_hero_id: state.ownHeroId,
    gold: state.gold,
    owned_item_ids: state.ownedItemIds,
    revive_uses_used: state.reviveUsesUsed,
    slot_capacity: state.slotCapacity,
    needs_tenacity: state.needsTenacity,
  }
  try {
    const res = await fetchWithTimeout('api/decisions', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    })
    if (!res.ok) throw new Error(`建议接口返回 HTTP ${res.status}`)
    const body = await res.json()
    offlineMode = false
    return body
  } catch (err) {
    offlineMode = true
    return offlineDecision(pickScenarioSnapshot(scenarioId), state.ownHeroId)
  }
}
