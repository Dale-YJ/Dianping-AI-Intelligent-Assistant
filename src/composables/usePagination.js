/**
 * usePagination — 分页状态管理
 * ==============================
 * 为列表页提供统一的分页加载能力。
 *
 * 用法：
 *   const { items, total, loading, hasMore, loadPage, loadMore, reset } = usePagination(
 *     (params) => getBusinesses(params)
 *   )
 *   await loadPage(1)        // 加载第 1 页
 *   await loadMore()         // 加载下一页（追加）
 */

import { ref, computed } from 'vue'

/**
 * @param {Function} fetchFn        - 分页请求函数，签名为 ({ page, pageSize }) => Promise<{total, items[]}>
 * @param {number}   [defaultPageSize=10]
 * @returns {{
 *   page: Ref<number>, pageSize: Ref<number>,
 *   total: Ref<number>, items: Ref<Array>,
 *   loading: Ref<boolean>, hasMore: computed<boolean>,
 *   loadPage: Function, loadMore: Function, reset: Function
 * }}
 */
export function usePagination(fetchFn, defaultPageSize = 10) {
  const page = ref(1)
  const pageSize = ref(defaultPageSize)
  const total = ref(0)
  const items = ref([])
  const loading = ref(false)

  const hasMore = computed(() => items.value.length < total.value)

  /**
   * 加载指定页码（替换当前列表）
   */
  async function loadPage(p) {
    page.value = p
    loading.value = true
    try {
      const result = await fetchFn({ page: page.value, pageSize: pageSize.value })
      items.value = result.items || []
      total.value = result.total || 0
    } finally {
      loading.value = false
    }
  }

  /**
   * 加载下一页（追加到当前列表）
   */
  async function loadMore() {
    if (!hasMore.value || loading.value) return
    page.value++
    loading.value = true
    try {
      const result = await fetchFn({ page: page.value, pageSize: pageSize.value })
      items.value.push(...(result.items || []))
      total.value = result.total || total.value
    } finally {
      loading.value = false
    }
  }

  /**
   * 重置分页状态
   */
  function reset() {
    page.value = 1
    items.value = []
    total.value = 0
  }

  return { page, pageSize, total, items, loading, hasMore, loadPage, loadMore, reset }
}
