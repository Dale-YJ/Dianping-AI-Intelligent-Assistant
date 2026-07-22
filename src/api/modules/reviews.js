/**
 * 模块 C：评价智能理解 + 用户评价 CRUD
 * =====================================
 * - GET    /businesses/{id}/reviews              评价列表（合并索引，支持 source 筛选）
 * - GET    /businesses/{id}/summary              AI 评价总结
 * - GET    /businesses/{id}/keywords             关键特征词提取
 * - GET    /businesses/{id}/sentiment            评价情感分析
 * - GET    /reviews/{id}                         单条评价详情（优先查 user_review）
 * - POST   /businesses/{id}/reviews              创建用户评价（需评分+文字）
 * - PUT    /reviews/{id}                         部分更新用户评价（仅改传入字段）
 * - DELETE /reviews/{id}                         删除用户评价
 */

import { get, post, put, del } from '../client.js'

/* ───────── AI 评价总结 ───────── */
export function getBusinessSummary(businessId) {
  return get(`/businesses/${encodeURIComponent(businessId)}/summary`, undefined, 120000)
}

/* ───────── 评价列表（合并索引，支持 source 筛选） ───────── */
export function getBusinessReviews(businessId, {
  page = 1,
  pageSize = 10,
  sentiment,
  minRating,
  sortBy,
  source,        // 'user_review' | 'yelp' | undefined（合并全部）
} = {}) {
  return get(`/businesses/${encodeURIComponent(businessId)}/reviews`, {
    page,
    page_size: pageSize,
    sentiment,
    min_rating: minRating,
    sort_by: sortBy,
    source,
  })
}

/* ───────── 单条评价详情（优先查 user_review） ───────── */
export function getReviewDetail(reviewId) {
  return get(`/reviews/${encodeURIComponent(reviewId)}`)
}

/* ───────── 创建用户评价 ───────── */
/**
 * POST /businesses/{id}/reviews
 *
 * @param {string} businessId - 商家 ID
 * @param {{ rating: number, text: string }} body - 评分(1-5) + 评价文字
 * @returns {Promise<object>} 创建的评价对象
 * @throws {Error} 商家不存在时 404
 */
export function createReview(businessId, { user_name, rating, text }) {
  return post(`/businesses/${encodeURIComponent(businessId)}/reviews`, {
    user_name,
    rating,
    text,
  })
}

/* ───────── 部分更新用户评价（仅改传入字段） ───────── */
/**
 * PUT /reviews/{id}
 *
 * 仅更新请求体中传入的字段，未传入的字段保持不变。
 * 仅允许更新 user_review 类型的评价。
 *
 * @param {string} reviewId - 评价 ID
 * @param {{ rating?: number, text?: string }} fields - 要更新的字段
 * @returns {Promise<object>} 更新后的评价对象
 */
export function updateReview(reviewId, fields) {
  return put(`/reviews/${encodeURIComponent(reviewId)}`, fields)
}

/* ───────── 删除用户评价 ───────── */
/**
 * DELETE /reviews/{id}
 *
 * 仅允许删除 user_review 类型的评价。
 *
 * @param {string} reviewId - 评价 ID
 * @returns {Promise<object>} 删除确认
 */
export function deleteReview(reviewId) {
  return del(`/reviews/${encodeURIComponent(reviewId)}`)
}

/* ───────── 情感分析 (LLM) ───────── */
export function getSentimentStats(businessId) {
  return get(`/businesses/${encodeURIComponent(businessId)}/sentiment`, undefined, 120000)
}

/* ───────── 关键特征词 (LLM) ───────── */
export function getKeywords(businessId, topN = 15) {
  return get(`/businesses/${encodeURIComponent(businessId)}/keywords`, undefined, 120000)
}

/* ───────── 差评归因 — 暂无独立后端，从情感+关键词衍生 ───────── */
export function getNegativeAttribution(businessId) {
  return Promise.resolve({ total_negative: 0, attributions: [] })
}

/* ───────── 经营建议 — 暂无后端 ───────── */
export function getSuggestions(businessId) {
  return Promise.resolve({ suggestions: [] })
}
