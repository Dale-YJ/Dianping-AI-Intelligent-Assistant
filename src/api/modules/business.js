/**
 * 模块 B：商家信息
 * ==================
 * 对应接口文档 三、模块 B
 * - GET /businesses          商家列表（分页 + 筛选）
 * - GET /businesses/{id}     商家详情
 */

import { get } from '../client.js'

/**
 * B.1 商家列表
 *
 * 分页查询商家列表，支持多条件筛选。
 *
 * @param {object}  [params]
 * @param {number}  [params.page=1]        - 页码
 * @param {number}  [params.pageSize=10]   - 每页数量，最大 50
 * @param {string}  [params.category]      - 菜系/类型筛选，如"川菜"
 * @param {number}  [params.minRating]     - 最低评分筛选，如 4.0
 * @param {string}  [params.keyword]       - 名称/标签模糊搜索
 * @param {string}  [params.sortBy]        - 排序：rating / review_count / distance
 * @returns {Promise<{
 *   total: number, page: number, page_size: number,
 *   items: Array<{
 *     business_id: string, name: string, address: string,
 *     city: string, state: string, latitude: number, longitude: number,
 *     rating: number, review_count: number, categories: string[],
 *     hours: object, attributes: object, thumbnail: string
 *   }>
 * }>}
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
 * B.2 商家详情
 *
 * 获取商家完整信息（含营业时间、环境特征、照片）。
 *
 * @param {string} businessId - 商家唯一 ID
 * @returns {Promise<{
 *   business_id: string, name: string, address: string,
 *   latitude: number, longitude: number, rating: number,
 *   review_count: number, categories: string[],
 *   hours: object, attributes: object, photos: string[],
 *   created_at: string
 * }>}
 */
export function getBusinessDetail(businessId) {
  return get(`/businesses/${businessId}`)
}
