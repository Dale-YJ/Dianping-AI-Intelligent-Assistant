/**
 * 模块 B：商家信息
 * ==================
 * 对应接口文档 三、模块 B
 * - GET /businesses            商家列表（分页 + 筛选）
 * - GET /businesses/{id}       商家详情
 *
 * 响应格式: { code: 0, message: "success", data: {...} }
 */

import { get } from '../client.js'

/**
 * B.1 商家列表
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
  }).then(res => res.data || res)
}

/**
 * B.2 商家详情
 */
export function getBusinessDetail(businessId) {
  return get(`/businesses/${encodeURIComponent(businessId)}`)
    .then(res => res.data || res)
}
