/**
 * 模块 D：数据管理
 * ==================
 * ⚠️ 后端尚未实现管理接口，当前返回占位数据。
 * 对应接口文档 五、模块 D
 */

function warn(name) {
  console.warn(`[API] ${name} 后端尚未实现`)
}

/* ───────── D.1 数据导入 ───────── */
export function postDataImport({
  datasetPath,
  city,
  categoriesFilter,
  minReviewsPerBusiness,
} = {}) {
  warn('postDataImport')
  return Promise.resolve({ task_id: 'stub_import', status: 'pending' })
}

/* ───────── D.2 数据处理（向量化） ───────── */
export function postDataProcess({
  chunkSize = 512,
  chunkOverlap = 64,
  embeddingModel,
  indexNames,
} = {}) {
  warn('postDataProcess')
  return Promise.resolve({ task_id: 'stub_process', status: 'pending' })
}

/* ───────── D.3 任务状态查询 ───────── */
export function getTaskStatus(taskId) {
  warn('getTaskStatus')
  return Promise.resolve({
    task_id: taskId,
    type: 'unknown',
    status: 'pending',
    progress: { phase: '', current: 0, total: 0, percentage: 0 },
    result: null,
    created_at: '',
    updated_at: '',
  })
}

/* ───────── D.4 数据统计总览 ───────── */
export function getAdminStats() {
  warn('getAdminStats')
  return Promise.resolve({
    total_businesses: 0,
    total_reviews: 0,
    total_chunks: 0,
    avg_review_length: 0,
    last_import_at: '',
    last_process_at: '',
    index_status: 'not_initialized',
  })
}
