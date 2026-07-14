/**
 * useBusiness — 商家数据聚合管理
 * ================================
 * 为商家详情页和商家后台页提供一站式数据获取。
 * 每个数据块有独立的 loading/error 状态，可独立展示骨架屏。
 *
 * 用法：
 *   const dash = useBusiness(businessId)
 *   await dash.fetchAll()       // 加载评价管理 Tab 所需数据
 *   await dash.fetchAnalysis()  // 加载口碑分析 Tab 所需数据（懒加载）
 */

import { ref } from 'vue'
import { getBusinessDetail } from '../api/modules/business.js'
import {
  getBusinessSummary,
  getBusinessReviews,
  getSentimentStats,
  getKeywords,
  getNegativeAttribution,
  getSuggestions,
} from '../api/modules/reviews.js'

export function useBusiness(businessId) {
  /* ─── 商家基础信息 ─── */
  const shop = ref(null)
  const shopLoading = ref(false)
  const shopError = ref(null)

  /* ─── 评价管理 Tab ─── */
  const reviews = ref([])
  const reviewsTotal = ref(0)
  const reviewsLoading = ref(false)
  const reviewsError = ref(null)

  const sentimentStats = ref(null)
  const statsLoading = ref(false)

  /* ─── 口碑分析 Tab ─── */
  const summary = ref(null)
  const summaryLoading = ref(false)

  const keywords = ref(null)
  const keywordsLoading = ref(false)

  const attributions = ref([])
  const attribLoading = ref(false)

  const suggestions = ref([])
  const suggLoading = ref(false)

  /* ─── 方法 ─── */

  async function fetchShop() {
    shopLoading.value = true
    shopError.value = null
    try {
      shop.value = await getBusinessDetail(businessId)
    } catch (e) {
      shopError.value = e.message
    } finally {
      shopLoading.value = false
    }
  }

  async function fetchReviews(params = {}) {
    reviewsLoading.value = true
    reviewsError.value = null
    try {
      const result = await getBusinessReviews(businessId, params)
      reviews.value = result.items || []
      reviewsTotal.value = result.total || 0
    } catch (e) {
      reviewsError.value = e.message
    } finally {
      reviewsLoading.value = false
    }
  }

  async function fetchSentimentStats() {
    statsLoading.value = true
    try {
      sentimentStats.value = await getSentimentStats(businessId)
    } finally {
      statsLoading.value = false
    }
  }

  async function fetchSummary() {
    summaryLoading.value = true
    try {
      summary.value = await getBusinessSummary(businessId)
    } finally {
      summaryLoading.value = false
    }
  }

  async function fetchKeywords() {
    keywordsLoading.value = true
    try {
      keywords.value = await getKeywords(businessId)
    } finally {
      keywordsLoading.value = false
    }
  }

  async function fetchAttribution() {
    attribLoading.value = true
    try {
      const result = await getNegativeAttribution(businessId)
      attributions.value = result.attributions || []
    } finally {
      attribLoading.value = false
    }
  }

  async function fetchSuggestions() {
    suggLoading.value = true
    try {
      const result = await getSuggestions(businessId)
      suggestions.value = result.suggestions || []
    } finally {
      suggLoading.value = false
    }
  }

  /**
   * 加载评价管理 Tab 全部数据
   */
  async function fetchAll() {
    await Promise.allSettled([
      fetchShop(),
      fetchReviews(),
      fetchSentimentStats(),
    ])
  }

  /**
   * 加载口碑分析 Tab 全部数据（懒加载，切换到 Tab 时调用）
   */
  async function fetchAnalysis() {
    await Promise.allSettled([
      fetchSummary(),
      fetchKeywords(),
      fetchAttribution(),
      fetchSuggestions(),
    ])
  }

  return {
    // 状态
    shop, shopLoading, shopError,
    reviews, reviewsTotal, reviewsLoading, reviewsError,
    sentimentStats, statsLoading,
    summary, summaryLoading,
    keywords, keywordsLoading,
    attributions, attribLoading,
    suggestions, suggLoading,
    // 方法
    fetchAll, fetchAnalysis,
    fetchShop, fetchReviews, fetchSentimentStats,
    fetchSummary, fetchKeywords, fetchAttribution, fetchSuggestions,
  }
}
