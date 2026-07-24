/**
 * contentFilter — 前端违禁词审核
 * ================================
 * 阻止用户输入和 AI 输出包含辱骂、不雅内容及违反国家法律法规的内容。
 *
 * 用法：
 *   import { validateInput, filterOutput } from '@/utils/contentFilter.js'
 *   const { valid, reason } = validateInput(userText)
 *   const safeText = filterOutput(aiText)
 */

/* ================================================================
   违禁词库
   ================================================================ */

/**
 * 严重违规 — 政治敏感、分裂言论、违法内容
 * 命中后直接拒绝发送
 */
const SEVERE_WORDS = [
  // 分裂言论
  '台独', '藏独', '疆独', '港独', '两个中国', '一中一台',
  '台湾独立', '西藏独立', '新疆独立', '香港独立',
  '光复香港', '时代革命',
  // 邪教 / 非法组织
  '法轮功', '法轮大法', '全能神', '门徒会',
  // 毒品
  '冰毒', '海洛因', '可卡因', '大麻', '麻古', '摇头丸',
  '吸毒', '贩毒', '制毒', '溜冰',
  // 赌博
  '赌博网站', '博彩平台', '六合彩', '赌球', '网赌',
  // 色情
  '色情', '淫秽', '嫖娼', '卖淫', '招嫖',
  // 暴力恐怖
  '恐怖主义', '恐怖分子', '圣战', '爆炸袭击',
  // 诈骗
  '电信诈骗', '网络诈骗', '传销',
]

/**
 * 辱骂不雅 — 脏话、人身攻击、歧视性言论
 * 命中后阻止发送并提示文明用语
 */
const ABUSIVE_WORDS = [
  // 中文脏话
  'sb', '傻逼', '傻b', '煞笔', '傻叉',
  'cnm', '操你妈', '草泥马', '草你妈', '艹你妈', '去你妈',
  'nmsl', '你妈死了',
  'tmd', '他妈的', '特么',
  'mlgb', '妈了个逼',
  '卧槽', '我操', '我艹', '我草',
  'jb', '鸡巴', '几把',
  '龟儿子', '狗日的', '日你', '干你',
  '杂种', '狗杂种', '王八蛋', '畜生',
  '混蛋', '废物', '蠢货', '白痴', '脑残', '智障',
  // 英文脏话
  'fuck', 'fck', 'shit', 'bitch', 'asshole', 'dick',
  'penis', 'vagina', 'pussy', 'bastard', 'motherfucker',
  // 歧视性言论
  '黑鬼', 'nigger', 'nigga',
  '支那', 'chinazi',
  '东亚病夫',
  '小日本', '日本鬼子', '高丽棒子', '阿三',
]

/**
 * 输出过滤词 — 不适合展示但不需要完全拒绝
 * 命中后替换为 ***
 */
const OUTPUT_FILTER_WORDS = [
  ...SEVERE_WORDS,
  ...ABUSIVE_WORDS,
  // 领导人负面称呼
  '维尼', '小熊维尼', '包子', '庆丰',
  // 敏感历史
  '六四', '天安门事件', '天安门广场',
  // 更多脏话变体
  '叼', '屌', '逼', '艹', '草泥',
  // 枪械
  '枪支', '买枪', '手枪', '步枪',
  'gun', 'pistol', 'rifle', 'firearm',
  // 自残/自杀
  '自杀', '自残', '割腕', '跳楼', '上吊',
  'suicide', 'kill myself',
]

/* ================================================================
   工具函数
   ================================================================ */

/**
 * 构建正则，匹配词列表中的任意一项。
 * 对英文词使用单词边界 \\b，中文直接匹配子串。
 */
function buildRegex(wordList) {
  const enWords = []
  const cnWords = []
  for (const w of wordList) {
    if (/[a-zA-Z]/.test(w)) {
      enWords.push(w.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'))
    } else {
      cnWords.push(w.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'))
    }
  }
  const parts = []
  if (enWords.length) parts.push('\\b(?:' + enWords.join('|') + ')\\b')
  if (cnWords.length) parts.push('(?:' + cnWords.join('|') + ')')
  return parts.length ? new RegExp(parts.join('|'), 'i') : null
}

const severeRe = buildRegex(SEVERE_WORDS)
const abusiveRe = buildRegex(ABUSIVE_WORDS)
const outputRe = buildRegex(OUTPUT_FILTER_WORDS)

/**
 * 校验用户输入是否合规。
 *
 * @param {string} text 用户输入的文本
 * @returns {{ valid: boolean, reason?: string }}
 *   - valid: true 表示可以通过
 *   - reason: 不通过时的原因描述
 */
export function validateInput(text) {
  if (!text || typeof text !== 'string') return { valid: true }

  if (severeRe && severeRe.test(text)) {
    return { valid: false, reason: '输入内容包含违规信息，请修改后重试' }
  }

  if (abusiveRe && abusiveRe.test(text)) {
    return { valid: false, reason: '请注意文明用语，请修改后重试' }
  }

  return { valid: true }
}

/**
 * 过滤输出文本中的敏感词，替换为 ***。
 *
 * @param {string} text 待过滤的文本
 * @returns {string} 过滤后的文本
 */
export function filterOutput(text) {
  if (!text || typeof text !== 'string') return text || ''

  if (!outputRe) return text
  return text.replace(outputRe, '***')
}
