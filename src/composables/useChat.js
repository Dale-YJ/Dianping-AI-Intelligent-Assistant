/**
 * useChat — 聊天会话管理
 * ========================
 * 封装对话逻辑：消息列表、发送消息、思考状态、会话持久化。
 * 使用商家搜索 API（GET /api/v1/businesses?keyword=...）代替 RAG 对话链路。
 *
 * 用法：
 *   const { messages, isThinking, sendMessage, clearChat, latestRecs } = useChat()
 *   await sendMessage('附近有什么好吃的川菜？')
 */

import { ref } from 'vue'
import { postChatSend } from '../api/modules/chat.js'

const SESSION_KEY = 'dp_ai_conversation_id'

/* ─── helpers ─── */
function now() {
  return new Date().toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
}

function loadConversation() {
  return sessionStorage.getItem(SESSION_KEY) || null
}

function saveConversation(id) {
  if (id) sessionStorage.setItem(SESSION_KEY, id)
}

export function clearConversation() {
  sessionStorage.removeItem(SESSION_KEY)
}

/* ─── composable ─── */
export function useChat() {
  const messages = ref([])
  const isThinking = ref(false)
  const conversationId = ref(loadConversation())

  /**
   * 发送消息并获取搜索结果。
   *
   * 流程：
   * 1. 发送查询到商家搜索 API（原生支持中文关键词）
   * 2. 接收搜索结果并展示为推荐卡片
   */
  async function sendMessage(text) {
    if (!text.trim() || isThinking.value) return

    const time = now()
    const rawText = text.trim()

    // 1. 用户消息
    messages.value.push({ role: 'user', text: rawText, time })

    // 2. 发送查询
    isThinking.value = true

    try {
      const data = await postChatSend(rawText, conversationId.value)

      // 持久化 conversation
      if (data.conversation_id) {
        conversationId.value = data.conversation_id
        saveConversation(data.conversation_id)
      }

      // 3. 搜索结果
      const aiMsg = {
        role: 'ai',
        intro: data.is_fallback ? '' : data.text,
        recommendations: data.recommendations || [],
        fallback: data.is_fallback ? data.text : '',
        time: now(),
      }
      messages.value.push(aiMsg)
    } catch (err) {
      messages.value.push({
        role: 'ai',
        intro: '',
        recommendations: [],
        fallback: err.message || '抱歉，发生了未知错误，请稍后再试',
        time: now(),
      })
    } finally {
      isThinking.value = false
    }
  }

  /**
   * 清空对话
   */
  function clearChat() {
    messages.value = []
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
    conversationId,
    sendMessage,
    clearChat,
    latestRecs,
  }
}
