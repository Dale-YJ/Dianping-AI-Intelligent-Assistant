/**
 * 模块 A：AI 对话与探店推荐
 * ============================
 * 对应后端 FastAPI /api/chat/ 路由
 * - POST /chat/stream      SSE 流式 RAG 对话
 * - POST /chat/send        非流式 RAG 对话（一次性返回）
 * - GET  /chat/history/{id} 获取会话历史
 * - DELETE /chat/history/{id} 清除会话历史
 */

import { post, get, del } from '../client.js'

/**
 * A.1 非流式对话推荐
 *
 * 发送自然语言咨询，后端执行 RAG 检索 + LLM 生成，一次性返回完整结果。
 *
 * @param {string}  message          - 用户自然语言输入，1-2000 字符
 * @param {string}  [conversationId] - 会话 ID，用于多轮对话，不传则新建
 * @returns {Promise<{
 *   conversation_id: string,
 *   text: string,
 *   recommendations: Array<{
 *     business_id: string, name: string, rating: number,
 *     review_count: number, categories: string[],
 *     address: string, city: string,
 *     reason: string,
 *     sources: Array<{
 *       user_name: string, rating: number, date: string,
 *       text: string, business_name: string
 *     }>,
 *     score: number
 *   }>,
 *   is_fallback: boolean
 * }>}
 */
export function postChatSend(message, conversationId) {
  return post('/chat/send', {
    message,
    conversation_id: conversationId || null,
  })
}

/**
 * A.2 SSE 流式对话推荐
 *
 * 通过 Server-Sent Events 流式返回 AI 生成内容。
 * 事件类型：start、delta、recommendations、done。
 *
 * @param {string}  message          - 用户自然语言输入
 * @param {string}  [conversationId] - 会话 ID
 * @param {object}  callbacks        - 事件回调
 * @param {function} [callbacks.onStart]           - 收到 start 事件
 * @param {function} [callbacks.onDelta]           - 收到 delta 事件（token 增量）
 * @param {function} [callbacks.onRecommendations] - 收到 recommendations 事件
 * @param {function} [callbacks.onDone]            - 收到 done 事件
 * @param {function} [callbacks.onError]           - 发生错误
 * @returns {Promise<void>}
 */
export async function postChatStream(message, conversationId, callbacks = {}) {
  const { onStart, onDelta, onRecommendations, onDone, onError } = callbacks

  try {
    const response = await fetch('/api/chat/stream', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        message,
        conversation_id: conversationId || null,
      }),
    })

    if (!response.ok) {
      const err = await response.json().catch(() => ({}))
      throw new Error(err.detail || `HTTP ${response.status}`)
    }

    const reader = response.body.getReader()
    const decoder = new TextDecoder()
    let buffer = ''

    while (true) {
      const { done, value } = await reader.read()
      if (done) break

      buffer += decoder.decode(value, { stream: true })

      // Parse SSE events from buffer
      const lines = buffer.split('\n')
      buffer = lines.pop() || '' // keep incomplete line in buffer

      for (const line of lines) {
        if (!line.startsWith('data: ')) continue
        const jsonStr = line.slice(6) // remove "data: " prefix
        try {
          const event = JSON.parse(jsonStr)
          switch (event.type) {
            case 'start':
              onStart?.(event)
              break
            case 'delta':
              onDelta?.(event)
              break
            case 'recommendations':
              onRecommendations?.(event)
              break
            case 'done':
              onDone?.(event)
              break
          }
        } catch {
          // skip malformed JSON lines
        }
      }
    }
  } catch (err) {
    onError?.(err)
    throw err
  }
}

/**
 * A.3 获取会话历史
 *
 * @param {string} conversationId
 * @returns {Promise<{ conversation_id: string, messages: Array<{role: string, content: string}> }>}
 */
export function getChatHistory(conversationId) {
  return get(`/chat/history/${conversationId}`)
}

/**
 * A.4 清除会话历史
 *
 * @param {string} conversationId
 * @returns {Promise<{ status: string, message: string }>}
 */
export function deleteChatHistory(conversationId) {
  return del(`/chat/history/${conversationId}`)
}
