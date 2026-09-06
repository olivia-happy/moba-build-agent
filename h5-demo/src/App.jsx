import { useEffect, useMemo, useRef, useState } from 'react'
import { analyzeFrame, fetchHeroes, fetchPortraitIndex, isOffline, requestDecision } from './api.js'
import { extractTacticalSignals, summarizeTacticalSignals } from './chatSignals.js'
import { DEFAULT_SCENARIO_ID, SCENARIOS, getScenario } from './scenarios.js'
import { DEFAULT_THEME_ID, THEMES } from './themes.js'

const NEED_LABELS = {
  magic_resist: '法术防御',
  tenacity: '韧性',
  physical_defense: '物理防御',
  anti_heal: '减疗',
  anti_sustain: '对抗续航',
  magic_burst: '法术爆发',
  physical_burst: '物理爆发',
  survival: '生存保命',
  physical_sustain: '物理续航',
  true_damage: '真实伤害',
}

const FUNCTION_LABELS = {
  invulnerability: '金身无敌',
  revive: '复活',
  death_avoid: '免死',
  shield: '护盾',
  damage_reduction: '减伤',
  magic_resist: '法术防御',
  tenacity: '韧性',
  physical_defense: '物理防御',
  anti_heal: '减疗',
  health: '生命值',
  sustain: '续航',
  magic_shield: '法术护盾',
  boots: '鞋子',
  haste: '冷却缩减',
  physical_attack: '物理攻击',
  crit: '暴击',
  attack_speed: '攻速',
}

const STATUS_LABELS = {
  idle: '等待抓取',
  capturing: '正在抓取一帧',
  recognizing: '本地识别中',
  recognized: '识别完成',
  deciding: '生成出装方案',
  ready: '建议已生成',
  error: '需要重试',
}

function labelOf(value) {
  return NEED_LABELS[value] || FUNCTION_LABELS[value] || value
}

function portraitSrc(heroId) {
  return `portraits/${heroId}.jpg`
}

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms))
}

function HeroPortrait({ hero, tone = 'enemy', confidence, active = false, onClick }) {
  if (!hero) return null
  const content = (
    <>
      <div className="portrait-frame">
        <img src={portraitSrc(hero.id)} alt={hero.name} />
        {active && <span className="active-mark">你</span>}
      </div>
      <span className="portrait-name">{hero.name}</span>
      {confidence !== undefined && <span className="confidence">{Math.round(confidence * 100)}%</span>}
    </>
  )
  return onClick ? (
    <button className={`portrait ${tone} ${active ? 'active' : ''}`} onClick={onClick} title="切换我方英雄">
      {content}
    </button>
  ) : (
    <div className={`portrait ${tone} ${active ? 'active' : ''}`}>{content}</div>
  )
}

function StepRail({ status }) {
  const steps = [
    ['capture', '抓取一帧'],
    ['recognize', '本地识别'],
    ['decide', '出装建议'],
  ]
  const stage = status === 'capturing' ? 0 : ['recognizing', 'recognized'].includes(status) ? 1 : status === 'idle' || status === 'error' ? -1 : 2
  return (
    <div className="step-rail" aria-label="处理流程">
      {steps.map(([id, name], index) => (
        <div className={`step ${index <= stage ? 'done' : ''} ${index === stage ? 'current' : ''}`} key={id}>
          <span className="step-dot">{index < stage ? '✓' : index + 1}</span>
          <span>{name}</span>
          {index < steps.length - 1 && <i />}
        </div>
      ))}
    </div>
  )
}

function CaptureTimeline({ status, recognition, captureVersion, onRetry }) {
  const identified = recognition?.slots?.filter((slot) => slot.candidates?.[0]).length || 0
  const entries = [
    { key: 'capture', label: '主动抓取一帧', detail: '仅保留本次对局瞬间', done: ['recognizing', 'recognized', 'deciding', 'ready'].includes(status) },
    { key: 'recognize', label: '本地识别敌我信息', detail: recognition ? `敌方 ${identified}/5 · Top-1 置信度已返回` : '16×16 亮度网格比对中', done: ['recognized', 'deciding', 'ready'].includes(status) },
    { key: 'decide', label: '生成可执行建议', detail: status === 'ready' ? '已结合经济、格子和定位' : '等待识别结果', done: status === 'ready' },
  ]
  const activeIndex = status === 'capturing' ? 0 : ['recognizing', 'recognized'].includes(status) ? 1 : status === 'idle' || status === 'error' ? -1 : 2
  return (
    <div className="capture-timeline">
      <div className="timeline-head"><div><span className="eyebrow">CAPTURE PIPELINE</span><h3>自动抓取进度</h3></div><span className="capture-counter">第 {captureVersion || 1} 次</span></div>
      {entries.map((entry, index) => (
        <div className={`timeline-entry ${entry.done ? 'done' : ''} ${index === activeIndex ? 'active' : ''}`} key={entry.key}>
          <span className="timeline-dot">{entry.done ? '✓' : index + 1}</span><div><b>{entry.label}</b><small>{entry.detail}</small></div>
        </div>
      ))}
      {status === 'error' && <button className="retry-button" onClick={onRetry}>↻ 重新抓取</button>}
    </div>
  )
}

function StatusPill({ status, detail }) {
  const isLive = ['capturing', 'recognizing', 'deciding'].includes(status)
  return (
    <div className={`status-pill ${isLive ? 'live' : ''} ${status === 'error' ? 'failed' : ''}`}>
      {isLive && <span className="pulse" />}
      <span>{STATUS_LABELS[status]}</span>
      {detail && <small>{detail}</small>}
    </div>
  )
}

function ScenarioSwitcher({ activeId, onChange }) {
  return (
    <div className="scenario-nav">
      <div className="control-kicker">演示场景 · 自动抓取</div>
      <div className="scenario-tabs">
        {SCENARIOS.map((scenario, index) => (
          <button key={scenario.id} className={scenario.id === activeId ? 'selected' : ''} onClick={() => onChange(scenario.id)}>
            <span className="tab-index">0{index + 1}</span>
            <span>{scenario.title}</span>
          </button>
        ))}
      </div>
    </div>
  )
}

const ITEM_NAMES = { 1411: '神速之靴', 1313: '抗魔披风', 1333: '不祥征兆', 1113: '搏击拳套', 1325: '守护者之铠' }

function SceneState({ scenario }) {
  const heldNames = scenario.ownedItemIds.length ? scenario.ownedItemIds.map((id) => ITEM_NAMES[id] || `装备 ${id}`).join(' · ') : '暂无已购装备'
  return (
    <div className="scene-state">
      <div className="state-line"><span>◈</span><span>{scenario.captureLabel}</span><b>LIVE</b></div>
      <div className="state-grid">
        <div><small>当前金币</small><strong>{scenario.gold.toLocaleString()}</strong></div>
        <div><small>装备栏</small><strong>{scenario.ownedItemIds.length}<em>/{scenario.slotCapacity}</em></strong></div>
        <div><small>复活甲</small><strong>{scenario.reviveUsesUsed}<em>/2 次</em></strong></div>
      </div>
      <div className="held-items"><span>已持有</span>{heldNames}</div>
    </div>
  )
}

function CaptureData({ scenario, status, recognition, heroes }) {
  const identified = recognition?.slots?.filter((slot) => slot.candidates?.[0]).length || 0
  const stateLabel = status === 'ready' ? '已抓取' : status === 'error' ? '抓取失败' : '读取中'
  return (
    <div className="capture-data">
      <div className="capture-data-head"><span>自动抓取的数据</span><b className={status === 'error' ? 'failed' : ''}>{stateLabel}</b></div>
      <div className="capture-data-grid">
        <div><small>敌方阵容</small><strong>{status === 'ready' ? `${identified}/5 人` : '识别中…'}</strong></div>
        <div><small>我方阵容</small><strong>{heroes.length ? '5 人' : '读取中…'}</strong></div>
        <div><small>经济状态</small><strong>{status === 'ready' ? '已同步' : '读取中…'}</strong></div>
      </div>
      <div className="capture-proof"><span>来源</span>场景 fixture · 16×16 亮度网格 · 索引 {recognition?.index_hash?.slice(0, 8) || '等待返回'}</div>
      <div className="capture-proof"><span>边界</span>仅发送微型网格；不读取游戏进程，不上传原始画面</div>
    </div>
  )
}

function RecommendationPanel({ decision, chat, chatOpen, chatCaptured, onCaptureChat, onCloseChat }) {
  if (!decision) return <div className="recommendation-empty">等待识别完成，助手会把建议放在这里。</div>
  const first = decision.recommendations?.[0]
  return (
    <div className="recommendation-panel">
      <div className="recommendation-header">
        <div><span className="eyebrow">BUILD ADVISOR · NOW</span><h2>现在该怎么出</h2></div>
        <span className="local-badge">本地规则</span>
      </div>
      {first && (
        <div className="primary-recommendation">
          <div className="recommendation-main">
            <span className="priority-mark">优先购买</span>
            <h3>{first.item_name}</h3>
            <strong className="price">{first.item_price}<small>金币</small></strong>
          </div>
          <div className="recommendation-tags">
            {(first.covered_needs || []).map((item) => <span key={item}>{labelOf(item)}</span>)}
            <span>{first.purchase_status === 'buy_now' ? '当前可购买' : first.purchase_status === 'buy_component' ? '先买组件' : first.purchase_status}</span>
          </div>
          {first.component_path?.length > 0 && <p className="component-line">合成路径：{first.component_path.map((item) => item.name).join('  →  ')}</p>}
          <p className="why-now"><b>为什么现在：</b>{first.why_now || first.evidence}</p>
        </div>
      )}
      <div className="decision-details">
        <div className="detail-title">我方定位调整</div>
        {decision.own_hero_adjustments?.length > 0 ? decision.own_hero_adjustments.map((item) => (
          <div className="adjustment" key={item.code}><span>✦</span><div><b>{item.label}</b><p>{item.reason}</p></div></div>
        )) : <p className="muted">本局由敌方威胁主导推荐。</p>}
      </div>
      {decision.recommendations?.length > 1 && (
        <div className="alternatives"><div className="detail-title">备选方案</div>{decision.recommendations.slice(1).map((item) => <span key={item.item_id}>{item.item_name} · {item.item_price}g</span>)}</div>
      )}
      {decision.emergency_swap?.suggestions?.length > 0 && (
        <div className="emergency"><div className="detail-title"><span>⚠</span> 紧急秒换提醒</div><p>{decision.emergency_swap.suggestions[0].target_item_name}：{decision.emergency_swap.suggestions[0].why_now}</p></div>
      )}
      <div className="evidence-line">▣ 建议依据：官方装备文本 + 敌方机制标签 + 当前经济约束</div>
      <div className="chat-action-row"><button className="chat-capture-button" onClick={onCaptureChat}>▣ {chatOpen ? (chatCaptured ? '再次抓取聊天' : '正在抓取…') : '抓取局内聊天'}</button>{chatOpen && <button className="chat-close-button" onClick={onCloseChat}>收起</button>}</div>
      {chatOpen && chatCaptured && <ChatBrief chat={chat} />}
    </div>
  )
}

function ChatBrief({ chat }) {
  return (
    <div className="chat-brief">
      <div className="chat-brief-head"><span>局内速读 · 本次聊天抓取</span><b>LOCAL OCR</b></div>
      <div className="chat-lines">{chat.lines.map((line, index) => <div key={`${line}-${index}`}><span className="chat-time">19:{41 + index}</span>{line}</div>)}</div>
      <div className="chat-signal-summary"><span>✦</span>{summarizeTacticalSignals(chat.signals)}</div>
      <div className="chat-signal-list">{chat.signals.map((signal) => <span className={signal.priority === 'high' ? 'high' : ''} key={signal.id}>{signal.title}</span>)}</div>
    </div>
  )
}

export default function App() {
  const [heroes, setHeroes] = useState([])
  const [portraitIndex, setPortraitIndex] = useState(null)
  const [scenarioId, setScenarioId] = useState(DEFAULT_SCENARIO_ID)
  const [ownHeroOverride, setOwnHeroOverride] = useState(null)
  const [status, setStatus] = useState('idle')
  const [recognition, setRecognition] = useState(null)
  const [decision, setDecision] = useState(null)
  const [captureVersion, setCaptureVersion] = useState(0)
  const [chatOpen, setChatOpen] = useState(false)
  const [chatCaptured, setChatCaptured] = useState(false)
  const [error, setError] = useState('')
  const runIdRef = useRef(0)
  const [overlayOpacity, setOverlayOpacity] = useState(90)
  const [themeId, setThemeId] = useState(DEFAULT_THEME_ID)
  const [settingsOpen, setSettingsOpen] = useState(false)
  const [backendMode, setBackendMode] = useState('checking') // checking | live | offline

  const scenario = getScenario(scenarioId)
  const theme = THEMES[themeId]
  const heroById = useMemo(() => new Map(heroes.map((hero) => [hero.id, hero])), [heroes])
  const ownHeroId = ownHeroOverride || scenario.ownHero
  const ownHero = heroById.get(ownHeroId)
  const enemyHeroes = scenario.enemyTeam.map((id) => heroById.get(id)).filter(Boolean)
  const ownTeam = scenario.ownTeam.map((id) => heroById.get(id)).filter(Boolean)
  const selectedEnemyIds = recognition?.slots?.map((slot) => slot.candidates?.[0]?.hero_id).filter(Boolean) || scenario.enemyTeam
  const captureVersionLabel = captureVersion || 1
  const chat = useMemo(() => extractTacticalSignals(scenario.chatLines || []), [scenario.chatLines])

  useEffect(() => {
    Promise.all([fetchHeroes(), fetchPortraitIndex()]).then(([heroData, index]) => {
      setHeroes(heroData)
      setPortraitIndex(index)
    }).catch((e) => setError(String(e)))
  }, [])

  const runCapture = async (nextScenarioId = scenarioId, nextOwnHeroId = null) => {
    const nextScenario = getScenario(nextScenarioId)
    if (!portraitIndex) return
    setError('')
    setDecision(null)
    setRecognition(null)
    setCaptureVersion((version) => version + 1)
    const runId = ++runIdRef.current
    setStatus('capturing')
    await sleep(420)
    if (runId !== runIdRef.current) return
    setStatus('recognizing')
    try {
      const analysis = await analyzeFrame(portraitIndex, nextScenario.capturePortraitIds, nextScenario.id)
      if (runId !== runIdRef.current) return
      setRecognition(analysis)
      await sleep(420)
      if (runId !== runIdRef.current) return
      setStatus('recognized')
      await sleep(380)
      if (runId !== runIdRef.current) return
      setStatus('deciding')
      const ownId = nextOwnHeroId || ownHeroOverride || nextScenario.ownHero
      const result = await requestDecision(
        {
          enemyHeroIds: analysis.slots.map((slot) => slot.candidates[0]?.hero_id).filter(Boolean),
          ownHeroId: ownId,
          gold: nextScenario.gold,
          ownedItemIds: nextScenario.ownedItemIds,
          reviveUsesUsed: nextScenario.reviveUsesUsed,
          slotCapacity: nextScenario.slotCapacity,
          needsTenacity: nextScenario.needsTenacity,
        },
        nextScenario.id,
      )
      if (runId !== runIdRef.current) return
      setDecision(result)
      setStatus('ready')
      setBackendMode(isOffline() ? 'offline' : 'live')
    } catch (e) {
      if (runId !== runIdRef.current) return
      setError(String(e))
      setStatus('error')
      setBackendMode(isOffline() ? 'offline' : 'live')
    }
  }

  useEffect(() => {
    if (!portraitIndex || !heroes.length) return
    const timer = setTimeout(() => runCapture(), 0)
    return () => clearTimeout(timer)
    // Initial load only; explicit scenario/hero changes invoke runCapture directly.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [portraitIndex, heroes.length])

  const switchScenario = (nextId) => {
    const nextScenario = getScenario(nextId)
    setScenarioId(nextId)
    setOwnHeroOverride(null)
    setChatCaptured(false)
    setChatOpen(false)
    // 传入新场景的默认英雄，避免异步 state 更新前沿用旧场景的切换选择。
    runCapture(nextId, nextScenario.ownHero)
  }

  const switchOwnHero = (heroId) => {
    setOwnHeroOverride(heroId)
    runCapture(scenarioId, heroId)
  }

  const captureChat = async () => {
    setChatOpen(true)
    setChatCaptured(false)
    await sleep(480)
    setChatCaptured(true)
  }

  const cssVars = { ...theme.tokens, '--overlay-opacity': overlayOpacity / 100 }

  return (
    <div className="app-shell" style={cssVars}>
      <div className="studio-bar">
        <div className="studio-brand"><span className="brand-glyph">◇</span><div><b>LOCAL BUILD AGENT</b><small>产品演示工作台</small></div></div>
        <div className="studio-actions">
          <span className={`connection-dot ${backendMode}`} />
          {backendMode === 'offline' ? '离线演示 · 内置快照' : backendMode === 'live' ? '本地规则引擎 · 已连接' : '检测服务中…'}
          <button title="切换皮肤" onClick={() => setSettingsOpen((open) => !open)}>{theme.label}⌄</button>
        </div>
      </div>
      {settingsOpen && <div className="skin-popover"><div className="control-kicker">选择前端皮肤</div><div className="skin-options">{Object.values(THEMES).map((candidate) => <button key={candidate.id} className={candidate.id === themeId ? 'selected' : ''} onClick={() => { setThemeId(candidate.id); setSettingsOpen(false) }}><span className="skin-swatch" style={{ background: candidate.tokens['--app-bg'], borderColor: candidate.tokens['--gold'] }} /><span><b>{candidate.label}</b><small>{candidate.description}</small></span></button>)}</div></div>}
      <div className="demo-layout">
        <aside className="control-panel">
          <div className="panel-heading"><span>DEMO CONTROL</span><h1>对局场景</h1><p>模拟“主动抓取一帧”后的助手响应。所有状态由场景自动带入。</p></div>
          <ScenarioSwitcher activeId={scenarioId} onChange={switchScenario} />
          <div className="control-block"><div className="control-kicker">我方英雄 · 可切换</div><div className="own-selector">{ownTeam.map((hero) => <HeroPortrait key={hero.id} hero={hero} tone="ally" active={hero.id === ownHeroId} onClick={() => switchOwnHero(hero.id)} />)}</div><p className="control-note">点击我方英雄，观察同一敌方阵容下的推荐变化。</p></div>
          <div className="control-block opacity-control"><div className="control-kicker"><span>悬浮窗透明度</span><strong>{overlayOpacity}%</strong></div><input type="range" min="65" max="100" value={overlayOpacity} onChange={(e) => setOverlayOpacity(Number(e.target.value))} /></div>
          <div className="privacy-note"><span>◈</span><div><b>隐私边界</b><p>Demo 使用本地预置指纹走真实识别接口。Android 真机版才会请求系统截屏；原始画面不上传。</p></div></div>
        </aside>

        <main className="phone-wrap">
          <div className="phone-stage">
            <div className="notch" />
            <div className="game-topbar"><span>19:42</span><div className="top-icons"><span>⌁</span><span>▣</span><span>⚙</span></div></div>
            <div className="game-title"><span>排位赛 · 巅峰对决</span><b>12 : 09</b><span>王者峡谷</span></div>
            <div className="scene-banner"><div><span className="eyebrow">{scenario.id.toUpperCase()} · MATCH MOMENT</span><h2>{scenario.title}</h2><p>{scenario.subtitle}</p></div><StatusPill status={status} detail={status === 'ready' ? '已就绪' : ''} /></div>
            <StepRail status={status} />
            <CaptureTimeline status={status} recognition={recognition} captureVersion={captureVersionLabel} onRetry={() => runCapture()} />

            <section className="battlefield">
              <div className="team-row enemy-row"><div className="team-label enemy-label"><i />敌方阵容 <small>ENEMY</small></div><div className="portraits-row">{enemyHeroes.map((hero, index) => <HeroPortrait key={hero.id} hero={hero} tone="enemy" confidence={recognition?.slots?.[index]?.candidates?.[0]?.confidence} />)}</div></div>
              <div className="versus"><span>VS</span><i /><small>已抓取对局画面</small><i /></div>
              <div className="team-row ally-row"><div className="team-label ally-label"><i />我方阵容 <small>ALLY</small></div><div className="portraits-row">{ownTeam.map((hero) => <HeroPortrait key={hero.id} hero={hero} tone="ally" active={hero.id === ownHeroId} onClick={() => switchOwnHero(hero.id)} />)}</div></div>
            </section>

            <SceneState scenario={scenario} />
            <CaptureData scenario={scenario} status={status} recognition={recognition} heroes={ownTeam} />

            <button className="assistant-float" onClick={() => document.querySelector('.assistant-overlay')?.scrollIntoView({ behavior: 'smooth', block: 'center' })} title="查看出装建议"><div className="float-orbit" /><span className="float-icon">✦</span><small>助手</small></button>
            <div className="assistant-overlay"><div className="overlay-head"><span className="assistant-avatar">✦</span><div><b>局内出装助手</b><small>{ownHero ? `正在为 ${ownHero.name} 计算` : '本地规则引擎'}</small></div><span className="overlay-state">{status === 'ready' ? '已就绪' : '分析中'}</span><span className="drag-handle">⠿</span></div><RecommendationPanel decision={decision} chat={chat} chatOpen={chatOpen} chatCaptured={chatCaptured} onCaptureChat={captureChat} onCloseChat={() => setChatOpen(false)} /></div>
            <div className="phone-home" />
          </div>
          <div className="phone-caption"><span>PHONE PREVIEW · 390 × 844</span><span>Skin / {theme.label}</span></div>
        </main>
      </div>
      <footer className="source-footer"><span>DATA PROVENANCE</span><a href="https://pvp.qq.com/web201605/js/herolist.json" target="_blank" rel="noreferrer">英雄目录 · 官方公开资源 ↗</a><a href="https://pvp.qq.com/web201605/js/item.json" target="_blank" rel="noreferrer">装备目录 · 官方公开资源 ↗</a><span>识别索引 {portraitIndex?.content_hash?.slice(0, 12) || '加载中…'}</span></footer>
    </div>
  )
}
