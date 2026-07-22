/**
 * 模块 B：商家信息
 * ==================
 * 对应 ANALYSIS_API_DOCS.md 第 2 节
 * - GET /businesses            商家列表（分页 + 筛选）
 * - GET /businesses/{id}       商家详情
 *
 * 响应由 client.js 自动解包 { code, message, data } → data
 */

import { get } from '../client.js'

/**
 * B.1 商家列表
 *
 * @param {object}  [params]
 * @param {number}  [params.page=1]       页码（从1开始）
 * @param {number}  [params.pageSize=10]  每页数量（最大50）
 * @param {string}  [params.keyword]      关键词搜索（商家名称、地址）
 * @param {string}  [params.category]     分类筛选（如"Restaurant"）
 * @param {number}  [params.minRating]    最低评分（0-5）
 * @param {string}  [params.sortBy]       排序字段（rating / review_count）
 * @returns {Promise<{ total: number, page: number, page_size: number, items: object[] }>}
 */
export function getBusinesses({
  page = 1,
  pageSize = 10,
  category,
  minRating,
  keyword,
  sortBy,
} = {}) {
  return get('/businesses', {
    page,
    page_size: pageSize,
    category,
    min_rating: minRating,
    keyword,
    sort_by: sortBy,
  })
}

/**
 * B.2 商家列表（含评价，高效率）
 *
 * 相比 B.1，此端点直接打包评价数据，page_size 上限 10000，
 * 一次请求即可拉取全量餐厅，避免 N+1 查询。
 */
export function getBusinessesWithReviews({
  page = 1,
  pageSize = 20,
  category,
  minRating,
  minReviews,
  keyword,
  sortBy,
} = {}) {
  return get('/businesses/with-reviews', {
    page,
    page_size: pageSize,
    category,
    min_rating: minRating,
    min_reviews: minReviews,
    keyword,
    sort_by: sortBy,
  })
}

/**
 * B.3 商家详情
 *
 * @param {string} businessId - 商家唯一标识
 * @returns {Promise<{
 *   business_id: string, name: string, address: string,
 *   latitude: number, longitude: number, rating: number,
 *   review_count: number, categories: string[],
 *   hours?: object, attributes?: object
 * }>}
 */
export function getBusinessDetail(businessId) {
  return get(`/businesses/${encodeURIComponent(businessId)}`)
}
