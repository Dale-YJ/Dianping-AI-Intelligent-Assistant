/**
 * parseAIReply — 将 buildResponseText() 生成的纯文本解析为结构化对象
 *
 * 输入：AI 回复文本（包含 emoji 标题、奖牌排名、粗体、星级、地址、类别等）
 * 输出：结构化对象，供 AIReplyContent 组件进行富文本渲染
 *
 * 用法：
 *   import { parseAIReply } from '../utils/parseAIReply.js'
 *   const parsed = parseAIReply(msg.intro)
 */

/* ─── 辅助判断函数 ─── */

/**
 * 检查字符串是否以 emoji 开头（匹配 surrogate pair 编码的 emoji 字符）
 * JS 内部使用 UTF-16，补充平面字符（含大多数 emoji）由一对 surrogate 表示：
 *   高代理项 \uD800-\uDBFF + 低代理项 \uDC00-\uDFFF
 * 某些 emoji 后可能跟变体选择器 U+FE0F（️）
 */
function startsWithEmoji(str) {
  // 先去除可能的前导空格
  const s = str.trimStart()
  if (s.length < 2) return false
  const c0 = s.charCodeAt(0)
  // 基本多文种平面内的 emoji（如 ⭐ ★ 等符号）
  if (c0 >= 0x2600 && c0 <= 0x27BF) return true  // 杂项符号
  if (c0 >= 0x1F300 && c0 <= 0x1F9FF) return true // 直接在 BMP 内? 不会 — 但逻辑上明确范围
  // 检查 surrogate pair
  if (c0 >= 0xD800 && c0 <= 0xDBFF) return true // 高代理项开头即认为是 emoji 区域
  // 检查常见 emoji 字面量（🔍 💡 📍 🏷️ 😅 🍲 🍜 等）
  if (/^[🔍💡📍🏷️😅🍲🍜🍣🥩🥢🍝🍛🦞🍰🍸🍽️🥗🍔🍗🍴]/.test(s)) return true
  return false
}

const MEDALS = ['🥇', '🥈', '🥉']

function isHeaderLine(line) {
  // 匹配：<emoji> 找到啦！...
  return startsWithEmoji(line) && /找到啦/.test(line)
}

function isFallbackLine(line) {
  return /^😅/.test(line) || /抱歉/.test(line) || /没有找到/.test(line)
}

function isFallbackHint(line) {
  return /^💡/.test(line) || /试试/.test(line)
}

function isRankedLine(line) {
  return /^[🥇🥈🥉]/.test(line)
}

function isLocationLine(line) {
  return /^\s*📍/.test(line)
}

function isTeaserLine(line) {
  return /还有.*也不错|往下滑/.test(line)
}

function isCategoryLine(line) {
  return /^\s*🏷️/.test(line)
}

/* ─── 提取函数 ─── */

function extractCount(text) {
  const m = text.match(/(\d+)\s*家/)
  return m ? parseInt(m[1], 10) : 0
}

/**
 * 提取行首的 emoji（支持 surrogate pair + 可选的变体选择器 U+FE0F）
 */
function extractHeaderEmoji(text) {
  const s = text.trimStart()
  if (s.length === 0) return ''
  let i = 0
  const c0 = s.charCodeAt(0)
  // surrogate pair → emoji 占 2 个 UTF-16 码元
  if (c0 >= 0xD800 && c0 <= 0xDBFF && s.length > 1) {
    i = 2
  } else {
    i = 1
  }
  // 检查是否跟变体选择器
  if (i < s.length && s.charCodeAt(i) === 0xFE0F) {
    i++
  }
  return s.slice(0, i)
}

/**
 * 解析单行排名条目
 * 格式：🥇 **店名**  ⭐⭐⭐⭐ 4.3  258 条评价
 */
function extractRankedItem(line) {
  const medal = line.charAt(0) + (line.charAt(1) === '️' ? '️' : '')

  // 提取 **粗体** 中的名称
  const nameMatch = line.match(/\*\*(.+?)\*\*/)
  const name = nameMatch ? nameMatch[1] : ''

  // 移除 medal 和名称后的剩余部分
  let rest = line
  if (nameMatch) {
    rest = line.slice(nameMatch.index + nameMatch[0].length)
  } else {
    rest = line.slice(2) // 跳过 medal
  }

  // 统计 ⭐ 数量
  const starMatch = rest.match(/⭐+/)
  const stars = starMatch ? starMatch[0].length : 0

  // 提取评分数字
  const ratingMatch = rest.match(/(\d+\.?\d*)/)
  const rating = ratingMatch ? parseFloat(ratingMatch[1]) : 0

  // 提取评价数
  const reviewMatch = rest.match(/(\d+)\s*条评价/)
  const reviewCount = reviewMatch ? parseInt(reviewMatch[1], 10) : 0
  const reviews = reviewCount ? `${reviewCount} 条评价` : ''

  return {
    medal: medal || '',
    name,
    stars,
    rating,
    reviews,
    location: '',
  }
}

/* ─── 主解析函数 ─── */

export function parseAIReply(text) {
  if (!text || typeof text !== 'string' || !text.trim()) {
    return {
      mode: 'structured',
      header: null,
      items: [],
      teaser: '',
      categories: '',
      isFallback: false,
      fallbackText: '',
      fallbackHint: '',
      conversationalText: '',
    }
  }

  const lines = text.split('\n').filter(l => l !== '\r')
  const result = {
    mode: 'structured',
    header: null,
    items: [],
    teaser: '',
    categories: '',
    isFallback: false,
    fallbackText: '',
    fallbackHint: '',
    conversationalText: '',
  }

  let currentItem = null
  let fallbackLines = []
  let hintLines = []

  for (const rawLine of lines) {
    const line = rawLine.trim()

    if (!line) continue

    // 检测 fallback
    if (isFallbackLine(line)) {
      result.isFallback = true
      fallbackLines.push(line)
      continue
    }

    if (result.isFallback && isFallbackHint(line)) {
      hintLines.push(line)
      continue
    }

    if (result.isFallback) {
      fallbackLines.push(line)
      continue
    }

    // 标题行
    if (isHeaderLine(line)) {
      result.header = {
        emoji: extractHeaderEmoji(line),
        text: line.replace(extractHeaderEmoji(line), '').trim(),
        totalCount: extractCount(line),
      }
      continue
    }

    // 排名条目
    if (isRankedLine(line)) {
      // 保存上一个 item
      if (currentItem) {
        result.items.push(currentItem)
      }
      currentItem = extractRankedItem(line)
      continue
    }

    // 位置行（附加到当前 item）
    if (isLocationLine(line) && currentItem) {
      currentItem.location = line.replace(/^\s*📍\s*/, '').trim()
      continue
    }

    // teaser 行
    if (isTeaserLine(line)) {
      result.teaser = line
      continue
    }

    // 类别行
    if (isCategoryLine(line)) {
      result.categories = line.replace(/^\s*🏷️\s*/, '').trim()
      continue
    }
  }

  // 保存最后一个 item
  if (currentItem) {
    result.items.push(currentItem)
  }

  // 组装 fallback 文本
  if (result.isFallback) {
    result.fallbackText = fallbackLines.join('\n')
    result.fallbackHint = hintLines.join('\n')
  }

  // 判断回复模式
  if (!result.header && !result.items.length && !result.isFallback) {
    // 对话式回复（非结构化模板）—— 保留原始文本供富文本渲染
    result.mode = 'conversational'
    result.conversationalText = text
  } else {
    result.mode = 'structured'
  }

  return result
}

export default parseAIReply
