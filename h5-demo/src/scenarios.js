export const SCENARIOS = [
  {
    id: 'magic-burst',
    title: '高地前的法爆团战',
    subtitle: '敌方中野爆发已成型，后排需要先保证生存窗口。',
    ownHero: 169,
    ownTeam: [169, 133, 107, 118, 105],
    enemyTeam: [142, 152, 156, 141, 109],
    gold: 2140,
    ownedItemIds: [1411, 1313],
    reviveUsesUsed: 0,
    slotCapacity: 6,
    needsTenacity: true,
    captureLabel: '刚刚抓取 · 敌方 5 人 + 我方 5 人 + 对局状态',
    capturePortraitIds: [142, 152, 156, 141, 109],
    chatLines: ['[队友] 中路不见了，注意草丛', '[队友] 来龙坑，先集合', '[队友] 我没大招，等一下'],
  },
  {
    id: 'assassin-dive',
    title: '河道遭遇战',
    subtitle: '对面刺客绕后频繁，射手需要把被秒风险压到最低。',
    ownHero: 112,
    ownTeam: [112, 106, 167, 105, 118],
    enemyTeam: [153, 167, 107, 144, 133],
    gold: 2860,
    ownedItemIds: [1411, 1333, 1113],
    reviveUsesUsed: 1,
    slotCapacity: 6,
    needsTenacity: false,
    captureLabel: '刚刚抓取 · 敌方 5 人 + 我方 5 人 + 对局状态',
    capturePortraitIds: [153, 167, 107, 144, 133],
    chatLines: ['[队友] 兰陵王闪现交了', '[队友] 对面打野红开，注意下半区', '[队友] 别压太深，先后撤'],
  },
  {
    id: 'sustain-control',
    title: '龙坑拉扯',
    subtitle: '敌方回复与控制同时成型，先做减疗与韧性，再考虑保命。',
    ownHero: 105,
    ownTeam: [105, 107, 142, 112, 184],
    enemyTeam: [144, 118, 184, 156, 108],
    gold: 1650,
    ownedItemIds: [1411, 1325],
    reviveUsesUsed: 0,
    slotCapacity: 6,
    needsTenacity: true,
    captureLabel: '刚刚抓取 · 敌方 5 人 + 我方 5 人 + 对局状态',
    capturePortraitIds: [144, 118, 184, 156, 108],
    chatLines: ['[队友] 对面程咬金回血太多', '[队友] 张良没大，先拉扯', '[队友] 龙坑集合，别急着开'],
  },
]

export const DEFAULT_SCENARIO_ID = SCENARIOS[0].id

export function getScenario(id) {
  return SCENARIOS.find((scenario) => scenario.id === id) || SCENARIOS[0]
}
