// H5 只使用预置可见聊天文本模拟端侧 OCR 的结果。
// Android 真机版将由“玩家主动截一帧 → 裁剪聊天区 → 本地 OCR”提供相同的 text 输入。

const SIGNAL_RULES = [
  {
    id: 'enemy_mid_missing',
    patterns: [/中路.*(不见|消失|miss)/i, /中单.*(不见|消失)/i],
    priority: 'high',
    title: '敌方中路消失',
    detail: '压线前先看中路河道和附近草丛，避免被法师游走夹击。',
  },
  {
    id: 'enemy_jungle_path',
    patterns: [/(打野|对面野).*(红开|蓝开)/i, /(红开|蓝开).*(打野|对面野)/i],
    priority: 'medium',
    title: '敌方打野路径',
    detail: '结合已知开局路线预判下一波可能的抓人方向。',
  },
  {
    id: 'team_calls_objective',
    patterns: [/(来|集合|开).*(龙|龙坑|暴君|主宰)/i, /(龙坑|暴君|主宰).*(来|集合|开)/i],
    priority: 'high',
    title: '队友请求资源集合',
    detail: '优先确认人数、关键技能和兵线，再决定是否靠近龙坑。',
  },
  {
    id: 'ally_ultimate_unavailable',
    patterns: [/(没大|大招.*(没|cd|CD)|大招.*还)/i],
    priority: 'medium',
    title: '我方关键大招未就绪',
    detail: '暂缓强开团，优先拉扯、清线或等关键技能恢复。',
  },
  {
    id: 'enemy_flash_down',
    patterns: [/(闪现).*(没|交了|用掉|已交)/i, /(没|交了|用掉).*(闪现)/i],
    priority: 'medium',
    title: '敌方闪现可能已交',
    detail: '可在视野充分时提高追击和先手的优先级。',
  },
  {
    id: 'team_retreat',
    patterns: [/(撤退|别打|撤|后撤)/i],
    priority: 'high',
    title: '队友发出撤退信号',
    detail: '优先脱离高风险区域，避免在人数或技能劣势下接团。',
  },
]

export function extractTacticalSignals(lines) {
  const normalizedLines = lines.map((line) => String(line || '').trim()).filter(Boolean)
  const signals = SIGNAL_RULES.filter((rule) => normalizedLines.some((line) => rule.patterns.some((pattern) => pattern.test(line))))
  return { lines: normalizedLines, signals }
}

export function summarizeTacticalSignals(signals) {
  if (!signals.length) return '未发现可执行战术信息，保持常规视野与出装节奏。'
  const high = signals.filter((signal) => signal.priority === 'high')
  const primary = high[0] || signals[0]
  return primary.detail
}
