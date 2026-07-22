/**
 * useChatHistory — 对话持久化管理
 * ====================================
 * 后端 Redis 优先 + localStorage 降级。
 *
 * - saveConversation  → localStorage（后端无独立保存接口）
 * - loadConversation  → 后端 API 优先，失败时回退 localStorage
 * - loadConversations → localStorage 索引（后端暂缺列表接口）
 * - deleteConversation → 后端 API + localStorage 双删
 *
 * localStorage 结构（对话索引 + 离线缓存）：
 *   dp_chat_conversations → [{ id, title, messages[], createdAt, updatedAt }, ...]
 *   dp_chat_current_id    → 当前活跃会话 ID
 *
 * 限制：最多 50 条对话，每条最多 100 条消息
 *
 * 用法：
 *   const { loadConversations, loadConversation, saveConversation,
 *           deleteConversation, getCurrentId, setCurrentId,
 *           generateId, generateTitle } = useChatHistory()
 */

import { fetchChatHistory, deleteChatHistoryApi } from '../api/modules/chat.js'

const STORAGE_KEY = 'dp_chat_conversations'
const CURRENT_KEY = 'dp_chat_current_id'
const MAX_CONVERSATIONS = 50
const MAX_MESSAGES = 100

/* ─── 安全读写 localStorage ─── */

function safeGet(key) {
  try {
    const raw = localStorage.getItem(key)
    return raw ? JSON.parse(raw) : null
  } catch {
    return null
  }
}

function safeSet(key, value) {
  try {
    localStorage.setItem(key, JSON.stringify(value))
    return true
  } catch {
    return false
  }
}

function safeRemove(key) {
  try {
    localStorage.removeItem(key)
  } catch {}
}

/* ─── 后端消息格式 → 前端渲染格式 ─── */
/**
 * 后端 Redis 存储的消息格式：
 *   { role: 'user', content: '...' }
 *   { role: 'assistant', content: '...' }
 *
 * 前端渲染期望的格式：
 *   { role: 'user', text: '...', time: '...' }
 *   { role: 'ai', intro: '...', recs: [], fallback: false, time: '...' }
 */
function normalizeMessages(messages) {
  if (!Array.isArray(messages)) return []

  return messages.map((m, i) => {
    // Already in frontend format — pass through
    if (m.text !== undefined || m.intro !== undefined || (m.role === 'ai' && !m.content)) {
      return m
    }

    const time = m.time || m.timestamp || ''

    if (m.role === 'user') {
      return {
        role: 'user',
        text: m.content || m.text || '',
        time,
      }
    }

    if (m.role === 'assistant') {
      return {
        role: 'ai',
        intro: m.content || m.intro || '',
        recs: m.recs || [],
        fallback: m.fallback || false,
        time,
      }
    }

    // Unknown role — return as-is with text fallback
    return {
      ...m,
      text: m.text || m.content || '',
      time,
    }
  })
}

/* ─── 更新 localStorage 缓存中的单条对话 ─── */

function updateLocalCache(id, messages) {
  const data = safeGet(STORAGE_KEY)
  if (!Array.isArray(data)) return
  const conv = data.find(c => c.id === id)
  if (conv) {
    conv.messages = messages
    safeSet(STORAGE_KEY, data)
  }
}

/* ─── composable ─── */

export function useChatHistory() {
  /* ── 当前会话 ID ── */
  function getCurrentId() {
    try { return localStorage.getItem(CURRENT_KEY) || null } catch { return null }
  }

  function setCurrentId(id) {
    if (id) safeSet(CURRENT_KEY, id)
  }

  /* ── 生成 ID 和标题 ── */
  function generateId() {
    return `conv_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`
  }

  function generateTitle(messages) {
    if (!messages || !messages.length) return '新对话'
    const firstUser = messages.find(m => m.role === 'user')
    if (!firstUser) return '新对话'
    const t = (firstUser.text || firstUser.content || '').trim()
    return t.length > 20 ? t.slice(0, 20) + '…' : t || '新对话'
  }

  /* ── 加载对话列表（不含完整消息，用于面板展示） ── */
  function loadConversations() {
    const data = safeGet(STORAGE_KEY)
    if (!Array.isArray(data)) return []

    return data.map(c => ({
      id: c.id,
      title: c.title || '新对话',
      messageCount: Array.isArray(c.messages) ? c.messages.length : 0,
      createdAt: c.createdAt || '',
      updatedAt: c.updatedAt || '',
    }))
  }

  /* ── 加载单条对话（localStorage 优先 → 后端 Redis 降级） ── */
  /**
   * localStorage 存储了完整的前端格式数据（含推荐结果 recs、来源 sources 等），
   * 后端 Redis 只存储简化的 {role, content} 文本记录。
   * 因此优先使用 localStorage 的富数据，Redis 仅作为跨设备/清缓存后的降级源。
   */
  async function loadConversation(id) {
    // 1. 优先 localStorage —— 包含完整结构化数据（recs, sources 等）
    const data = safeGet(STORAGE_KEY)
    if (Array.isArray(data)) {
      const local = data.find(c => c.id === id)
      if (local && local.messages && local.messages.length) {
        return {
          id: local.id,
          title: local.title || generateTitle(local.messages),
          messages: local.messages,
        }
      }
    }

    // 2. localStorage 无数据 → 降级到后端 Redis
    try {
      const backend = await fetchChatHistory(id)
      if (backend && backend.messages && backend.messages.length) {
        // 将后端格式转为前端渲染格式（recs 为空，仅展示文本）
        const normalized = normalizeMessages(backend.messages)
        // 写入 localStorage 缓存，后续访问走 localStorage 快速路径
        saveConversation(id, normalized)
        return {
          id: backend.conversation_id || id,
          title: generateTitle(normalized),
          messages: normalized,
        }
      }
    } catch {
      // 后端不可用，忽略
    }

    return null
  }

  /* ── 保存/更新对话（localStorage，后端无独立保存接口） ── */
  function saveConversation(id, messages) {
    if (!id || !Array.isArray(messages)) return false

    const data = safeGet(STORAGE_KEY) || []
    const existing = data.find(c => c.id === id)
    const now = new Date().toISOString()

    const trimmed = messages.slice(-MAX_MESSAGES)
    const title = generateTitle(trimmed)

    if (existing) {
      existing.messages = trimmed
      existing.title = title
      existing.updatedAt = now
    } else {
      data.unshift({
        id,
        title,
        messages: trimmed,
        createdAt: now,
        updatedAt: now,
      })
    }

    if (data.length > MAX_CONVERSATIONS) {
      data.length = MAX_CONVERSATIONS
    }

    return safeSet(STORAGE_KEY, data)
  }

  /* ── 删除对话（后端 Redis + localStorage 双删） ── */
  async function deleteConversation(id) {
    // 1. 删后端 Redis
    try {
      await deleteChatHistoryApi(id)
    } catch {
      // 后端不可用时忽略
    }

    // 2. 删 localStorage 索引
    const data = safeGet(STORAGE_KEY)
    if (!Array.isArray(data)) return false

    const filtered = data.filter(c => c.id !== id)
    safeSet(STORAGE_KEY, filtered)

    if (getCurrentId() === id) {
      safeRemove(CURRENT_KEY)
    }

    return true
  }

  return {
    loadConversations,
    loadConversation,
    saveConversation,
    deleteConversation,
    getCurrentId,
    setCurrentId,
    generateId,
    generateTitle,
  }
}

export default useChatHistory
