/**
 * 模块 A：AI 对话与探店推荐
 * ============================
 * 使用商家关键词搜索 API（GET /api/v1/businesses?keyword=...），
 * 配合 useTranslate 将中文查询翻译为英文关键词，
 * 匹配 Yelp 英文数据集中的商家名称。
 *
 * - postChatSend    → 调用 GET /api/v1/businesses?keyword=...（关键词搜索）
 * - postChatStream  → 不可用
 * - getChatHistory  → 基于 sessionStorage 的本地实现
 * - deleteChatHistory → 清除 sessionStorage
 */

import { get, del, request } from '../client.js'

/* ─── sessionStorage 会话管理 ─── */
const CLIENT_SESSION_KEY = 'dp_ai_conversation_id'
const BIZ_SESSION_KEY = 'dp_ai_conversation_id_biz'
const HISTORY_PREFIX = 'dp_ai_history_'

function genConversationId() {
  return `conv_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`
}

function loadConversationId(isBiz = false) {
  try { return sessionStorage.getItem(isBiz ? BIZ_SESSION_KEY : CLIENT_SESSION_KEY) || null } catch { return null }
}

function saveConversationId(id, isBiz = false) {
  try { sessionStorage.setItem(isBiz ? BIZ_SESSION_KEY : CLIENT_SESSION_KEY, id) } catch {}
}

function loadHistory(convId) {
  try {
    const raw = sessionStorage.getItem(HISTORY_PREFIX + convId)
    return raw ? JSON.parse(raw) : []
  } catch { return [] }
}

function saveHistory(convId, messages) {
  try {
    sessionStorage.setItem(HISTORY_PREFIX + convId, JSON.stringify(messages.slice(-20)))
  } catch {}
}

/**
 * 将商家搜索结果映射为推荐格式（兼容 ChatResponse.recommendations）
 */
function mapBusinessToRec(biz) {
  return {
    business_id: biz.business_id || '',
    name: biz.name || '未知商家',
    rating: typeof biz.rating === 'number' ? biz.rating : 0,
    review_count: biz.review_count || 0,
    categories: Array.isArray(biz.categories) ? biz.categories : [],
    address: biz.address || '',
    city: biz.city || '',
    state: biz.state || '',
    latitude: biz.latitude,
    longitude: biz.longitude,
    reason: '',
    sources: [],
    score: biz.rating || 0,
    // 商家照片（招牌/环境），透传给前端组件展示
    photos: Array.isArray(biz.photos) ? biz.photos : [],
    photo_url: biz.photo_url || (Array.isArray(biz.photos) ? biz.photos[0] : null),
  }
}

/* ─── 非餐饮类目黑名单正则 ─── */
const NON_FOOD_CATEGORY_RE = /pet|groomer|veterinar|doctor|hospital|dentist|pharmacy|clinic|gas\s?station|laundry|dry\s?clean|auto\s?repair|storage|shipping|postal|bank|insurance|real\s?estate|lawyer|attorney|plumber|electric|hardware|jewelry|shoe\s?store|tailor|tobacco|vape|cannabis|liquor\s?store|cleaner|carpet|glass|roofing|mover|moving|internet|telecom|isp\b|salon|barber|beauty|nail\s?salon|spa|nonprofit|charity|school|tutor|college|gym|yoga|fitness|church|religious|funeral|cremation|gun|firearm|pawn|payday|loan|taxi|limousine|towing|car\s?wash|oil\s?change|pest\s?control|landscap|gardener|contractor|painter|handyman|locksmith|appliance/i

/**
 * 判断商家是否为餐饮/食品相关类目。
 * 使用黑名单过滤明显非餐饮的类目（搬家公司、美发店、诊所等）。
 */
function isFoodBusiness(biz) {
  const cats = Array.isArray(biz.categories) ? biz.categories : []
  if (cats.length === 0) return true // 无类目信息时不过滤，避免误杀
  // 只要有一个类目不匹配非餐饮黑名单，就认为是餐饮相关
  return cats.some(c => !NON_FOOD_CATEGORY_RE.test(c))
}

/* ─── 根据关键词推断相关 emoji ─── */
function guessEmoji(keyword) {
  const kw = keyword.toLowerCase()
  if (/hot\s?pot|火锅|涮锅/.test(kw)) return '🍲'
  if (/sichuan|川|麻|辣/.test(kw)) return '🌶️'
  if (/japanese|sushi|ramen|日料|寿司|拉面|居酒屋/.test(kw)) return '🍣'
  if (/korean|bbq|韩|烤肉|烧烤/.test(kw)) return '🥩'
  if (/chinese|中餐|中餐馆|dim\s?sum|点心/.test(kw)) return '🥢'
  if (/italian|pasta|pizza|意|披萨/.test(kw)) return '🍝'
  if (/thai|vietnamese|pho|泰|越南|河粉/.test(kw)) return '🍜'
  if (/indian|curry|印度|咖喱/.test(kw)) return '🍛'
  if (/seafood|海鲜/.test(kw)) return '🦞'
  if (/dessert|ice\s?cream|coffee|cafe|bubble\s?tea|甜品|咖啡|奶茶|蛋糕/.test(kw)) return '🍰'
  if (/bar|pub|beer|wine|cocktail|酒吧|精酿/.test(kw)) return '🍸'
  if (/breakfast|brunch|lunch|dinner|早餐|午餐|晚餐|夜宵/.test(kw)) return '🍽️'
  if (/buffet|自助/.test(kw)) return '🥗'
  if (/steak|牛排/.test(kw)) return '🥩'
  if (/burger|汉堡/.test(kw)) return '🍔'
  if (/chicken|fried|炸鸡/.test(kw)) return '🍗'
  return '🍴'
}

/* ─── 将搜索结果组装为自然语言回复 ─── */
function buildResponseText(message, items) {
  if (!items || items.length === 0) {
    return `😅 抱歉，没有找到与「${message}」相关的商家。\n\n💡 试试换个更具体的关键词，比如具体的菜系名（川菜、日料、火锅…）或场景描述（约会、聚餐…）`
  }

  const emoji = guessEmoji(message)
  const top = items.slice(0, 3)

  // 收集所有类别
  const allCats = new Set()
  for (const biz of items) {
    for (const c of (biz.categories || [])) allCats.add(c)
  }
  const foodCats = [...allCats].filter(c =>
    !/pet|service|groomer|doctor|hospital|dentist|pharmacy|gas|laundry|dry\s*clean|auto|repair|storage|shipping|bank|insurance|real\s*estate|lawyer|plumber|electric|hardware|jewelry|shoe|tailor|tobacco|vape|cannabis|liquor|cleaner|carpet|glass|roofing/i.test(c)
  ).slice(0, 5).join('、')

  const parts = []
  parts.push(`${emoji} 找到啦！为你精选了 ${items.length} 家好店：`)

  for (let i = 0; i < top.length; i++) {
    const b = top[i]
    const medal = ['🥇', '🥈', '🥉'][i]
    const stars = '⭐'.repeat(Math.round(b.rating || 0))
    const reviews = b.review_count ? `${b.review_count} 条评价` : ''
    parts.push(`${medal} **${b.name}**  ${stars} ${b.rating}  ${reviews}`)
    if (b.city) parts.push(`   📍 ${b.city}${b.address ? ' · ' + b.address.split(',')[0] : ''}`)
  }

  if (items.length > 3) {
    parts.push(`\n还有 ${items.length - 3} 家也不错，往下滑看看～`)
  }

  if (foodCats) {
    parts.push(`\n🏷️ 涵盖类别：${foodCats}`)
  }

  return parts.join('\n')
}

/**
 * A.1 对话推荐（AI 对话接口）
 *
 * 直接调用后端 AI 对话接口，发送自然语言消息（中文/英文均可），
 * 后端 LLM 理解意图后在 Yelp 数据集中搜索并返回推荐结果。
 * 同时后端自动将对话存入 Redis。
 *
 * @param {string}  message          - 用户原始查询（中文/英文，无需翻译）
 * @param {string}  [conversationId] - 会话 ID，不传则新建
 * @param {string}  [city]           - 从查询中提取的中国城市英文名，用于后端地理过滤
 * @returns {Promise<{
 *   conversation_id: string,
 *   text: string,
 *   recommendations: object[],
 *   is_fallback: boolean
 * }>}
 */
export async function postChatSend(message, conversationId, city, businessId) {
  const isBiz = !!businessId
  const convId = conversationId || loadConversationId(isBiz) || genConversationId()
  saveConversationId(convId, isBiz)

  // 本地缓存一份用户消息
  const history = loadHistory(convId)
  history.push({ role: 'user', content: message })

  try {
    const url = '/api/chat/send'
    const body = {
      message: message,
      conversation_id: convId,
    }
    if (city) body.city = city
    if (businessId) body.business_id = businessId

    const resp = await fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    })

    if (!resp.ok) {
      throw new Error(`AI 服务返回错误 (HTTP ${resp.status})`)
    }

    const json = await resp.json()

    // 统一响应解包：{ code, message, data }
    let data = json
    if (json && typeof json.code === 'number') {
      if (json.code !== 0) {
        throw new Error(json.message || `AI 服务错误 (code=${json.code})`)
      }
      data = json.data !== undefined ? json.data : json
    }

    const recommendations = (data.recommendations || [])
      .map(mapBusinessToRec)
      .filter(isFoodBusiness)
    const isFallback = !data.text || recommendations.length === 0

    // 本地缓存 AI 回复
    history.push({ role: 'assistant', content: data.text || '' })
    saveHistory(convId, history)

    return {
      conversation_id: data.conversation_id || convId,
      text: data.text || '',
      recommendations,
      is_fallback: isFallback,
    }
  } catch (err) {
    history.push({ role: 'assistant', content: `[错误] ${err.message}` })
    saveHistory(convId, history)

    return {
      conversation_id: convId,
      text: '',
      recommendations: [],
      is_fallback: true,
    }
  }
}

/**
 * A.2 SSE 流式对话推荐 — 不可用
 *
 * 分析 API 不支持 SSE 流式响应。
 * 调用此函数将立即触发 onError 回调。
 */
export async function postChatStream(message, conversationId, callbacks = {}) {
  const { onError } = callbacks
  const err = new Error('SSE 流式对话接口不可用，请使用普通搜索')
  onError?.(err)
  throw err
}

/**
 * A.3 获取会话历史（本地实现）
 *
 * @param {string} conversationId
 * @returns {Promise<{ conversation_id: string, messages: Array<{role: string, content: string}> }>}
 */
export function getChatHistory(conversationId) {
  console.warn('[API] getChatHistory — 使用本地 sessionStorage 实现')
  return Promise.resolve({
    conversation_id: conversationId,
    messages: loadHistory(conversationId),
  })
}

/**
 * A.4 清除会话历史（本地实现）
 *
 * @param {string} conversationId
 * @returns {Promise<{ status: string, message: string }>}
 */
export function deleteChatHistory(conversationId) {
  try {
    sessionStorage.removeItem(HISTORY_PREFIX + conversationId)
  } catch {}
  return Promise.resolve({ status: 'ok', message: 'Conversation cleared' })
}

/* ─── A.5 对话历史（后端 Redis） ─── */

/**
 * 从后端 Redis 获取对话历史
 *
 * @param {string} conversationId
 * @returns {Promise<{ conversation_id: string, messages: Array }>}
 */
export async function fetchChatHistory(conversationId) {
  const url = `/api/chat/history/${encodeURIComponent(conversationId)}`
  const resp = await fetch(url)
  if (!resp.ok) {
    throw new Error(`获取对话历史失败 (HTTP ${resp.status})`)
  }
  const json = await resp.json()
  // 统一响应解包
  if (json && typeof json.code === 'number') {
    if (json.code !== 0) throw new Error(json.message || '获取对话历史失败')
    return json.data !== undefined ? json.data : json
  }
  return json
}

/**
 * 从后端 Redis 删除对话历史
 *
 * @param {string} conversationId
 * @returns {Promise<{ status: string }>}
 */
export async function deleteChatHistoryApi(conversationId) {
  const url = `/api/chat/history/${encodeURIComponent(conversationId)}`
  const resp = await fetch(url, { method: 'DELETE' })
  if (!resp.ok) {
    throw new Error(`删除对话失败 (HTTP ${resp.status})`)
  }
  const json = await resp.json()
  if (json && typeof json.code === 'number') {
    if (json.code !== 0) throw new Error(json.message || '删除对话失败')
    return json.data !== undefined ? json.data : json
  }
  return json
}

/* ─── A.2 快捷提问标签 ─── */

/**
 * 获取欢迎页快捷提问标签列表
 *
 * @returns {Promise<{ tags: Array<{ id: string, text: string, icon: string }> }>}
 */
export async function getQuickTags() {
  const url = '/api/chat/quick-tags'
  const resp = await fetch(url)
  if (!resp.ok) throw new Error(`获取快捷标签失败 (HTTP ${resp.status})`)
  const json = await resp.json()
  if (json && typeof json.code === 'number') {
    if (json.code !== 0) throw new Error(json.message || '获取快捷标签失败')
    return json.data !== undefined ? json.data : json
  }
  return json
}
