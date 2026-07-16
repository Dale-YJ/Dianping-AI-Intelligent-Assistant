/**
 * useChat — 聊天会话管理
 * ========================
 * 封装 HomePage 的对话逻辑：消息列表、发送消息、思考状态、会话持久化。
 * 内置中文→英文翻译层，解决 embedding 模型仅支持英文的问题。
 *
 * 用法：
 *   const { messages, isThinking, sendMessage, clearChat, latestRecs } = useChat()
 *   await sendMessage('附近有什么好吃的川菜？')
 */

import { ref } from 'vue'
import { postChatSend } from '../api/modules/chat.js'
import { useTranslate } from './useTranslate.js'

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
  const { translate, isTranslating } = useTranslate()

  /**
   * 发送消息并获取 AI 回复。
   *
   * 流程：
   * 1. 检测中文 → 翻译为英文（解决 embedding 仅支持英文的问题）
   * 2. 发送英文查询到 RAG 链路
   * 3. 接收 AI 回复（系统提示词为中文，LLM 回复中文）
   */
  async function sendMessage(text) {
    if (!text.trim() || isThinking.value) return

    const time = now()
    const rawText = text.trim()

    // 1. 用户消息
    messages.value.push({ role: 'user', text: rawText, time })

    // 2. 翻译 + 发送
    isThinking.value = true

    try {
      // 翻译中文 → 英文（不含中文则直接返回原文）
      const enQuery = await translate(rawText)

      // 如果发生了翻译，在 AI 回复中添加提示
      const wasTranslated = enQuery !== rawText

      // 发送英文查询到 RAG 链路
      const data = await postChatSend(enQuery, conversationId.value)

      // 持久化 conversation
      if (data.conversation_id) {
        conversationId.value = data.conversation_id
        saveConversation(data.conversation_id)
      }

      // 3. AI 回复
      const aiMsg = {
        role: 'ai',
        intro: data.is_fallback ? '' : data.text,
        recommendations: data.recommendations || [],
        fallback: data.is_fallback ? data.text : '',
        translated: wasTranslated,
        enQuery: wasTranslated ? enQuery : undefined,
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
    isTranslating,
    conversationId,
    sendMessage,
    clearChat,
    latestRecs,
  }
}
