/**
 * useChat — 聊天会话管理
 * ========================
 * 封装 HomePage 的对话逻辑：消息列表、发送消息、思考状态、session 持久化。
 *
 * 用法：
 *   const { messages, isThinking, sendMessage, clearChat, latestRecs } = useChat()
 *   await sendMessage('附近有什么好吃的川菜？')
 *
 * 兜底处理：
 *   code 1001 → 展示兜底文案 + alternatives
 *   网络错误  → 展示错误提示
 */

import { ref } from 'vue'
import { postRecommend } from '../api/modules/chat.js'
import { ApiError } from '../api/client.js'

const SESSION_KEY = 'dp_ai_session_id'

/* ─── helpers ─── */
function now() {
  return new Date().toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
}

function loadSession() {
  return sessionStorage.getItem(SESSION_KEY) || null
}

function saveSession(id) {
  if (id) sessionStorage.setItem(SESSION_KEY, id)
}

function clearSession() {
  sessionStorage.removeItem(SESSION_KEY)
}

/* ─── composable ─── */
export function useChat() {
  const messages = ref([])
  const isThinking = ref(false)
  const sessionId = ref(loadSession())

  /**
   * 发送消息并获取 AI 回复
   */
  async function sendMessage(text) {
    if (!text.trim() || isThinking.value) return

    const time = now()

    // 1. 用户消息
    messages.value.push({ role: 'user', text: text.trim(), time })

    // 2. 思考中
    isThinking.value = true
    messages.value.push({ role: 'thinking', time: '' })

    try {
      const data = await postRecommend({
        query: text.trim(),
        sessionId: sessionId.value,
        topK: 5,
      })

      // 持久化 session
      if (data.session_id) {
        sessionId.value = data.session_id
        saveSession(data.session_id)
      }

      // 3. AI 回复
      messages.value.pop() // 移除 thinking
      messages.value.push({
        role: 'ai',
        intro: data.answer,
        recommendations: data.recommendations || [],
        fallback: data.recommendations?.length === 0 ? data.answer : '',
        time: now(),
      })
    } catch (err) {
      messages.value.pop() // 移除 thinking

      // 兜底处理: code 1001 返回了 alternatives
      if (err instanceof ApiError && err.code === 1001 && err.data) {
        messages.value.push({
          role: 'ai',
          intro: '',
          recommendations: [],
          fallback: err.data.answer || err.message,
          alternatives: err.data.alternatives || [],
          time: now(),
        })
      } else {
        // 网络或其他错误
        messages.value.push({
          role: 'ai',
          intro: '',
          recommendations: [],
          fallback: err.message || '抱歉，发生了未知错误，请稍后再试',
          time: now(),
        })
      }
    } finally {
      isThinking.value = false
    }
  }

  /**
   * 清空对话
   */
  function clearChat() {
    messages.value = []
    // 注意: 不清除 session_id，保留服务端对话上下文
  }

  /**
   * 从消息历史中提取最新的推荐结果（PC 端右侧面板使用）
   */
  function latestRecs() {
    for (let i = messages.value.length - 1; i >= 0; i--) {
      const m = messages.value[i]
      if (m.role === 'ai' && m.recommendations && m.recommendations.length) {
        return m.recommendations
      }
    }
    return []
  }

  return {
    messages,
    isThinking,
    sessionId,
    sendMessage,
    clearChat,
    latestRecs,
    clearSession,
  }
}
