/**
 * 模块 D：数据管理
 * ==================
 * 对应接口文档 五、模块 D
 * - POST /admin/data/import   数据导入（异步）
 * - POST /admin/data/process  数据处理/向量化（异步）
 * - GET  /admin/tasks/{id}    异步任务状态查询
 * - GET  /admin/stats         数据统计总览
 */

import { post, get } from '../client.js'

/* ───────── D.1 数据导入 ───────── */

/**
 * 从 Yelp Dataset 筛选并导入数据到系统。
 *
 * @param {object}   params
 * @param {string}   params.datasetPath             - Yelp Dataset 解压后的目录路径
 * @param {string}   params.city                    - 目标城市
 * @param {string[]} [params.categoriesFilter]      - 类型筛选，默认 ["Restaurants", "Food"]
 * @param {number}   [params.minReviewsPerBusiness] - 商家最少评价数，默认 1
 * @returns {Promise<{ task_id: string, status: string, created_at: string }>}
 */
export function postDataImport({
  datasetPath,
  city,
  categoriesFilter,
  minReviewsPerBusiness,
}) {
  return post('/admin/data/import', {
    dataset_path: datasetPath,
    city,
    categories_filter: categoriesFilter,
    min_reviews_per_business: minReviewsPerBusiness,
  })
}

/* ───────── D.2 数据处理（向量化） ───────── */

/**
 * 启动内容处理 Pipeline：清洗 → 语义切分 → 向量化 → 入库 OpenSearch。
 *
 * @param {object} [params]
 * @param {number} [params.chunkSize=512]       - Chunk 大小（tokens）
 * @param {number} [params.chunkOverlap=64]      - Chunk 重叠（tokens）
 * @param {string} [params.embeddingModel]       - 向量化模型，默认 deepseek
 * @param {object} [params.indexNames]           - OpenSearch 索引名配置
 * @returns {Promise<{ task_id: string, status: string, created_at: string }>}
 */
export function postDataProcess({
  chunkSize = 512,
  chunkOverlap = 64,
  embeddingModel,
  indexNames,
} = {}) {
  return post('/admin/data/process', {
    chunk_size: chunkSize,
    chunk_overlap: chunkOverlap,
    embedding_model: embeddingModel,
    index_names: indexNames,
  })
}

/* ───────── D.3 任务状态查询 ───────── */

/**
 * 查询异步任务（数据导入 / 处理）的进度和结果。
 *
 * @param {string} taskId
 * @returns {Promise<{
 *   task_id: string, type: string,
 *   status: 'pending' | 'processing' | 'completed' | 'failed',
 *   progress: { phase: string, current: number, total: number, percentage: number },
 *   result: object|null,
 *   created_at: string, updated_at: string
 * }>}
 */
export function getTaskStatus(taskId) {
  return get(`/admin/tasks/${taskId}`)
}

/* ───────── D.4 数据统计总览 ───────── */

/**
 * 获取系统知识库的整体统计信息。
 *
 * @returns {Promise<{
 *   total_businesses: number, total_reviews: number, total_chunks: number,
 *   avg_review_length: number,
 *   last_import_at: string, last_process_at: string, index_status: string
 * }>}
 */
export function getAdminStats() {
  return get('/admin/stats')
}
