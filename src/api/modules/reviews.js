/**
 * 模块 C：评价智能理解
 * ======================
 * 对应接口文档 四、模块 C
 * - GET /businesses/{id}/summary              C.1 评价智能总结
 * - GET /businesses/{id}/reviews              C.2 评价列表（含情感筛选）
 * - GET /reviews/{id}                         C.3 单条评价详情
 * - GET /businesses/{id}/sentiment-stats      C.4 情感统计
 * - GET /businesses/{id}/keywords             C.5 关键特征词
 * - GET /businesses/{id}/negative-attribution C.6 差评归因分析
 * - GET /businesses/{id}/suggestions          C.7 经营建议
 *
 * 响应格式: { code: 0, message: "success", data: {...} }
 */

import { get } from '../client.js'

/* ───────── C.1 评价智能总结 ───────── */
export function getBusinessSummary(businessId) {
  return get(`/businesses/${encodeURIComponent(businessId)}/summary`)
    .then(res => res.data || res)
}

/* ───────── C.2 评价列表 ───────── */
export function getBusinessReviews(businessId, {
  page = 1,
  pageSize = 10,
  sentiment,
  minRating,
  sortBy,
} = {}) {
  return get(`/businesses/${encodeURIComponent(businessId)}/reviews`, {
    page,
    page_size: pageSize,
    sentiment,
    min_rating: minRating,
    sort_by: sortBy,
  }).then(res => res.data || res)
}

/* ───────── C.3 单条评价详情 ───────── */
export function getReviewDetail(reviewId) {
  return get(`/reviews/${encodeURIComponent(reviewId)}`)
    .then(res => res.data || res)
}

/* ───────── C.4 情感统计 ───────── */
export function getSentimentStats(businessId) {
  return get(`/businesses/${encodeURIComponent(businessId)}/sentiment-stats`)
    .then(res => res.data || res)
}

/* ───────── C.5 关键特征词 ───────── */
export function getKeywords(businessId, topN = 10) {
  return get(`/businesses/${encodeURIComponent(businessId)}/keywords`, { top_n: topN })
    .then(res => res.data || res)
}

/* ───────── C.6 差评归因分析 ───────── */
export function getNegativeAttribution(businessId) {
  return get(`/businesses/${encodeURIComponent(businessId)}/negative-attribution`)
    .then(res => res.data || res)
}

/* ───────── C.7 经营建议 ───────── */
export function getSuggestions(businessId) {
  return get(`/businesses/${encodeURIComponent(businessId)}/suggestions`)
    .then(res => res.data || res)
}
