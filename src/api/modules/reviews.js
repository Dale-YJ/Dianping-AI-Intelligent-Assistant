/**
 * 模块 C：评价智能理解
 * ======================
 * 对应接口文档 四、模块 C
 * - GET /businesses/{id}/summary              评价智能总结
 * - GET /businesses/{id}/reviews              评价列表（含情感筛选）
 * - GET /reviews/{id}                         单条评价详情
 * - GET /businesses/{id}/sentiment-stats      情感统计
 * - GET /businesses/{id}/keywords             关键特征词
 * - GET /businesses/{id}/negative-attribution 差评归因分析
 * - GET /businesses/{id}/suggestions          经营建议
 */

import { get } from '../client.js'

/* ───────── C.1 评价智能总结 ───────── */

/**
 * 获取某商家的 AI 口碑摘要（好评亮点 + 差评槽点 + 近期动态）。
 *
 * @param {string} businessId
 * @returns {Promise<{
 *   business_id: string, business_name: string, generated_at: string,
 *   review_count_used: number,
 *   highlights: { title: string, items: Array<{point:string, mention_count:number, sources:Source[]}> },
 *   concerns:   { title: string, items: Array<{point:string, mention_count:number, sources:Source[]}> },
 *   recent_trend: { title: string, summary: string, period: string, sources: Source[] },
 *   elapsed_ms: number
 * }>}
 */
export function getBusinessSummary(businessId) {
  return get(`/businesses/${businessId}/summary`)
}

/* ───────── C.2 评价列表 ───────── */

/**
 * 获取某商家的评价列表，每条含情感标签，支持按情感筛选。
 *
 * @param {string}  businessId
 * @param {object}  [params]
 * @param {number}  [params.page=1]        - 页码
 * @param {number}  [params.pageSize=10]   - 每页数量，最大 50
 * @param {string}  [params.sentiment]     - 情感筛选：positive / neutral / negative
 * @param {number}  [params.minRating]     - 最低星级筛选，1-5
 * @param {string}  [params.sortBy]        - 排序：date / rating / useful
 * @returns {Promise<{
 *   business_id: string, total: number, page: number, page_size: number,
 *   filter_sentiment: string|null,
 *   items: Array<{
 *     review_id: string, user_name: string, rating: number,
 *     text: string, date: string, useful: number, funny: number, cool: number,
 *     sentiment: { label: string, label_cn: string, icon: string, confidence: number }
 *   }>
 * }>}
 */
export function getBusinessReviews(businessId, {
  page = 1,
  pageSize = 10,
  sentiment,
  minRating,
  sortBy,
} = {}) {
  return get(`/businesses/${businessId}/reviews`, {
    page,
    page_size: pageSize,
    sentiment,
    min_rating: minRating,
    sort_by: sortBy,
  })
}

/* ───────── C.3 单条评价详情 ───────── */

/**
 * 获取单条评价的完整信息（用于溯源弹窗）。
 *
 * @param {string} reviewId
 * @returns {Promise<{
 *   review_id: string, business_id: string, business_name: string,
 *   user_name: string, rating: number, text: string, date: string,
 *   useful: number, funny: number, cool: number,
 *   sentiment: { label: string, label_cn: string, icon: string, confidence: number }
 * }>}
 */
export function getReviewDetail(reviewId) {
  return get(`/reviews/${reviewId}`)
}

/* ───────── C.4 情感统计 ───────── */

/**
 * 获取某商家评价的正/中/负面占比统计。
 *
 * @param {string} businessId
 * @returns {Promise<{
 *   business_id: string, total_reviews: number,
 *   positive: { count: number, percentage: number },
 *   neutral:  { count: number, percentage: number },
 *   negative: { count: number, percentage: number }
 * }>}
 */
export function getSentimentStats(businessId) {
  return get(`/businesses/${businessId}/sentiment-stats`)
}

/* ───────── C.5 关键特征词 ───────── */

/**
 * 获取从评价中提取的特征词标签，按四维度分类。
 *
 * @param {string}  businessId
 * @param {number}  [topN=10] - 每维度返回前 N 个标签
 * @returns {Promise<{
 *   business_id: string, business_name: string, generated_at: string,
 *   total_keywords_extracted: number,
 *   groups: Array<{
 *     dimension: string, label: string, icon: string,
 *     tags: Array<{ keyword: string, count: number, score: number }>
 *   }>
 * }>}
 */
export function getKeywords(businessId, topN = 10) {
  return get(`/businesses/${businessId}/keywords`, { top_n: topN })
}

/* ───────── C.6 差评归因分析 ───────── */

/**
 * 获取差评中的问题归因，按维度聚合。
 *
 * @param {string} businessId
 * @returns {Promise<{
 *   business_id: string, total_negative: number,
 *   attributions: Array<{
 *     dimension: string, label: string, count: number, percentage: number
 *   }>
 * }>}
 */
export function getNegativeAttribution(businessId) {
  return get(`/businesses/${businessId}/negative-attribution`)
}

/* ───────── C.7 经营建议 ───────── */

/**
 * 获取基于评价数据生成的经营改善建议。
 *
 * @param {string} businessId
 * @returns {Promise<{
 *   business_id: string, generated_at: string,
 *   suggestions: Array<{
 *     index: number, title: string, detail: string,
 *     related_tags: string[], severity: 'high' | 'medium' | 'low'
 *   }>
 * }>}
 */
export function getSuggestions(businessId) {
  return get(`/businesses/${businessId}/suggestions`)
}
