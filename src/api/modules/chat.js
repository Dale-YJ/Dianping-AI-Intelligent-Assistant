/**
 * 模块 A：AI 对话与探店推荐
 * ============================
 * 对应接口文档 二、模块 A
 * - POST /chat/recommend   对话式探店推荐（RAG + LLM）
 * - GET  /chat/quick-tags  获取快捷提问标签
 */

import { post, get } from '../client.js'

/**
 * A.1 对话式探店推荐
 *
 * 发送自然语言咨询，系统执行 RAG 检索 + LLM 生成，返回推荐商家及理由。
 *
 * @param {object}  params
 * @param {string}  params.query       - 用户自然语言输入，最大 500 字符
 * @param {string}  [params.sessionId] - 会话 ID，用于多轮对话，不传则新建
 * @param {number}  [params.topK=3]    - 返回推荐数量，最大 10
 * @param {string}  [params.mode]      - recommend（推荐）/ search（搜店）
 * @returns {Promise<{
 *   session_id: string,
 *   query: string,
 *   answer: string,
 *   recommendations: Array<{
 *     business_id: string, name: string, rating: number,
 *     categories: string[], reason: string, tags: string[],
 *     sources: Array<{review_id:string, user_name:string, date:string, snippet:string, rating:number}>
 *   }>,
 *   retrieval_count: number,
 *   elapsed_ms: number
 * }>}
 *
 * 兜底场景：code === 1001 时返回 alternatives 替代建议
 */
export function postRecommend({ query, sessionId, topK = 3, mode = 'recommend' }) {
  return post('/chat/recommend', {
    query,
    session_id: sessionId,
    top_k: topK,
    mode,
  })
}

/**
 * A.2 获取快捷提问标签
 *
 * 获取欢迎页展示的快捷提问标签列表。
 *
 * @returns {Promise<{
 *   tags: Array<{ id: string, text: string, icon: string }>
 * }>}
 */
export function getQuickTags() {
  return get('/chat/quick-tags')
}
