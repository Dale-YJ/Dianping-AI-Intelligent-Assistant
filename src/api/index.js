/**
 * API 统一导出入口
 * =================
 * 用法：
 *   import { chatApi, businessApi, reviewsApi } from '@/api'
 *   const result = await chatApi.postChatSend('川菜')
 */

export * as chatApi from './modules/chat.js'
export * as businessApi from './modules/business.js'
export * as reviewsApi from './modules/reviews.js'

/* 按需单独导入 */
export { postChatSend, postChatStream, getChatHistory, deleteChatHistory } from './modules/chat.js'
export { getBusinesses, getBusinessDetail } from './modules/business.js'
export {
  getBusinessSummary,
  getBusinessReviews,
  getReviewDetail,
  getSentimentStats,
  getKeywords,
  getNegativeAttribution,
  getSuggestions,
} from './modules/reviews.js'

/* 基础客户端 */
export { request, get, post, del } from './client.js'
