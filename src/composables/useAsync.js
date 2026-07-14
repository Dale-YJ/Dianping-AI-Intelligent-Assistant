/**
 * useAsync — 通用异步状态管理
 * =============================
 * 为任何异步操作提供统一的 loading / error / data 三态管理。
 *
 * 用法：
 *   const { data, loading, error, execute } = useAsync(() => getBusinesses(params))
 *   await execute()
 *
 *   // 模板中:
 *   // v-if="loading"     → 骨架屏
 *   // v-else-if="error"  → 错误提示 + 重试
 *   // v-else             → 正常渲染 data
 */

import { ref } from 'vue'

/**
 * @param {Function} asyncFn          - 异步函数，返回 Promise
 * @param {object}   [options]
 * @param {boolean}  [options.immediate=false] - 是否创建后立即执行
 * @returns {{ data: Ref, error: Ref<string|null>, loading: Ref<boolean>, execute: Function }}
 */
export function useAsync(asyncFn, { immediate = false } = {}) {
  const data = ref(null)
  const error = ref(null)
  const loading = ref(false)

  async function execute() {
    loading.value = true
    error.value = null
    try {
      data.value = await asyncFn()
    } catch (err) {
      error.value = err.message || '未知错误'
      data.value = null
    } finally {
      loading.value = false
    }
  }

  if (immediate) {
    execute()
  }

  return { data, error, loading, execute }
}
