<template>
  <div class="biz-dashboard">
    <TopNav>
      <template #left>
        <button class="back-btn" @click="$router.back()">
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="15 18 9 12 15 6"/></svg>
        </button>
      </template>
      <template #center><span class="nav-title">商家后台</span></template>
    </TopNav>

    <!-- Loading -->
    <div class="state-container" v-if="shopLoading">
      <div class="loading-spinner"></div>
      <p>正在加载商家数据...</p>
    </div>

    <!-- Error -->
    <div class="state-container" v-else-if="shopError && !shop.name">
      <div class="state-icon">🚧</div>
      <h2 class="state-title">暂时无法加载</h2>
      <p class="state-desc">{{ shopError }}</p>
      <button class="state-btn" @click="initData">重试</button>
      <button class="state-btn secondary" @click="$router.push('/')">前往 AI 助手</button>
    </div>

    <template v-else>
    <!-- Shop Header -->
    <div class="biz-header stagger-1">
      <div class="biz-avatar" :style="{ background: shop.imgBg }">{{ (shop.name || '?')[0] }}</div>
      <div class="biz-info">
        <h1 class="biz-name">{{ shop.name }}</h1>
        <div class="biz-rating">
          <span class="stars">{{ '★'.repeat(Math.floor(shop.rating)) }}</span>
          <span>{{ shop.rating }}</span>
          <span class="review-count">({{ shop.reviewCount }} 条评价)</span>
        </div>
        <div class="biz-tags"><span v-for="t in shop.tags" :key="t" class="biz-tag">{{ t }}</span></div>
      </div>
    </div>

    <!-- Tab Switch -->
    <div class="tab-switch stagger-2">
      <button
        v-for="tab in tabs" :key="tab.key"
        class="tab-btn" :class="{ active: activeTab === tab.key }"
        @click="activeTab = tab.key"
      >{{ tab.label }}</button>
    </div>

    <!-- ═══ 评价管理 Tab ═══ -->
    <div class="tab-content" v-if="activeTab === 'reviews'">
      <!-- Sentiment Stats Cards -->
      <div class="sentiment-stats stagger-3">
        <div class="stat-card positive">
          <span class="stat-num">{{ sentimentCounts.positive }}</span>
          <span class="stat-label">😊 好评</span>
        </div>
        <div class="stat-card neutral">
          <span class="stat-num">{{ sentimentCounts.neutral }}</span>
          <span class="stat-label">😐 中评</span>
        </div>
        <div class="stat-card negative">
          <span class="stat-num">{{ sentimentCounts.negative }}</span>
          <span class="stat-label">😞 差评</span>
        </div>
      </div>

      <!-- Filter Chips -->
      <div class="review-filters stagger-3">
        <button
          v-for="f in filters" :key="f.key"
          class="filter-chip" :class="{ active: activeFilter === f.key }"
          @click="activeFilter = f.key"
        >{{ f.label }}</button>
      </div>

      <!-- Review Loading -->
      <div class="review-loading" v-if="reviewsLoading">
        <span class="typing-dot"></span><span class="typing-dot"></span><span class="typing-dot"></span>
        <span class="loading-text">加载评价中...</span>
      </div>

      <!-- Review List -->
      <div class="review-list" v-else>
        <div class="review-empty" v-if="filteredReviews.length === 0">
          <p>暂无{{ activeFilter === 'all' ? '' : filterLabel }}评价</p>
        </div>
        <div
          v-for="(r, i) in filteredReviews" :key="i"
          class="review-item stagger-3"
          :style="{ animationDelay: (0.3 + i * 0.05) + 's' }"
        >
          <div class="review-top">
            <span class="review-user">{{ r.user }}</span>
            <SentimentBadge :sentiment="r.sentiment" :confidence="r.confidence" />
          </div>
          <div class="review-stars">{{ '★'.repeat(r.stars) }}{{ '☆'.repeat(5 - r.stars) }}</div>
          <p class="review-text">{{ r.text }}</p>
          <div class="review-bottom">
            <span class="review-date">{{ r.date }}</span>
            <span class="review-votes" v-if="r.useful">👍 {{ r.useful }}</span>
          </div>
        </div>
      </div>

      <!-- Pagination -->
      <div class="pagination" v-if="reviewTotalPages > 1">
        <button class="page-btn" :disabled="reviewPage <= 1" @click="goToReviewPage(reviewPage - 1)">上一页</button>
        <span class="page-info">{{ reviewPage }} / {{ reviewTotalPages }}</span>
        <button class="page-btn" :disabled="reviewPage >= reviewTotalPages" @click="goToReviewPage(reviewPage + 1)">下一页</button>
      </div>
    </div>

    <!-- ═══ 口碑分析 Tab ═══ -->
    <div class="tab-content" v-if="activeTab === 'analysis'">
      <div class="analysis-loading" v-if="analysisLoading">
        <div class="loading-spinner"></div>
        <p>正在分析口碑数据...</p>
      </div>

      <template v-else>
      <!-- Sentiment Distribution -->
      <div class="analysis-section stagger-3">
        <div class="section-card">
          <h3 class="section-card-title">📈 情感分布</h3>
          <div class="sentiment-bar-chart">
            <div class="bar-row">
              <span class="bar-label">好评</span>
              <div class="bar-track"><div class="bar-fill positive" :style="{ width: sentimentPercent.positive + '%' }"></div></div>
              <span class="bar-val">{{ sentimentPercent.positive }}%</span>
            </div>
            <div class="bar-row">
              <span class="bar-label">中评</span>
              <div class="bar-track"><div class="bar-fill neutral" :style="{ width: sentimentPercent.neutral + '%' }"></div></div>
              <span class="bar-val">{{ sentimentPercent.neutral }}%</span>
            </div>
            <div class="bar-row">
              <span class="bar-label">差评</span>
              <div class="bar-track"><div class="bar-fill negative" :style="{ width: sentimentPercent.negative + '%' }"></div></div>
              <span class="bar-val">{{ sentimentPercent.negative }}%</span>
            </div>
          </div>
        </div>
      </div>

      <!-- Feature Keywords -->
      <div class="analysis-section stagger-3">
        <div class="section-card">
          <h3 class="section-card-title">🏷️ 特征关键词</h3>
          <FeatureTagCloud :groups="featureGroups" />
          <div class="card-empty" v-if="!featureGroups.length">
            <p>评价数据不足，暂无法提取关键词</p>
          </div>
        </div>
      </div>

      <!-- Negative Attribution -->
      <div class="analysis-section stagger-3" v-if="complaintGroups.length">
        <div class="section-card">
          <h3 class="section-card-title">⚠️ 差评归因</h3>
          <p class="section-card-desc">共 {{ totalNegativeReviews }} 条差评，主要投诉集中在以下方面</p>
          <div class="complaint-list">
            <div v-for="(c, i) in complaintGroups" :key="i" class="complaint-item">
              <span class="complaint-dim">{{ c.dimension }}</span>
              <div class="complaint-bar-track">
                <span class="complaint-bar" :style="{ width: (c.count / maxComplaint * 100) + '%', background: c.barColor }"></span>
              </div>
              <span class="complaint-count">{{ c.count }}条</span>
            </div>
          </div>
        </div>
      </div>

      <!-- Suggestions -->
      <div class="analysis-section stagger-3">
        <div class="section-card">
          <h3 class="section-card-title">💡 经营建议</h3>
          <div class="suggestion-list" v-if="suggestions.length">
            <div v-for="(s, i) in suggestions" :key="i" class="suggestion-item">
              <span class="suggestion-num" :class="'severity-' + (s.severity || 'medium')">{{ s.index || i + 1 }}</span>
              <div class="suggestion-content">
                <strong class="suggestion-title">{{ s.title }}</strong>
                <p class="suggestion-detail">{{ s.detail }}</p>
              </div>
            </div>
          </div>
          <div class="card-empty" v-else>
            <p>暂无经营建议，请从首页 AI 推荐进入以获取完整数据</p>
          </div>
        </div>
      </div>
      </template>
    </div>
    </template>
  </div>
</template>

<script>
import { ref, computed, onMounted, watch } from 'vue'
import { useRoute } from 'vue-router'
import TopNav from '../components/TopNav.vue'
import SentimentBadge from '../components/SentimentBadge.vue'
import FeatureTagCloud from '../components/FeatureTagCloud.vue'
import { getBusinessDetail } from '../api/modules/business.js'
import {
  getBusinessReviews, getSentimentStats, getKeywords,
  getNegativeAttribution, getSuggestions,
} from '../api/modules/reviews.js'
import { sharedStore } from '../stores/sharedData.js'

const ATTRIBUTION_COLORS = ['#EF4444', '#F97316', '#F59E0B', '#EAB308', '#F97316']

export default {
  name: 'BusinessDashboard',
  components: { TopNav, SentimentBadge, FeatureTagCloud },
  setup() {
    const route = useRoute()

    /* ─── Tab & Filter ─── */
    const activeTab = ref('reviews')
    const activeFilter = ref('all')
    const tabs = [
      { key: 'reviews', label: '评价管理' },
      { key: 'analysis', label: '口碑分析' },
    ]
    const filters = [
      { key: 'all', label: '全部' },
      { key: 'positive', label: '😊 好评' },
      { key: 'neutral', label: '😐 中评' },
      { key: 'negative', label: '😞 差评' },
    ]

    /* ─── Shop ─── */
    const shop = ref({ name: '', rating: 0, reviewCount: 0, tags: [], imgBg: '' })
    const shopLoading = ref(true)
    const shopError = ref(null)

    /* ─── Reviews ─── */
    const reviews = ref([])
    const reviewsLoading = ref(false)
    const reviewPage = ref(1)
    const reviewTotal = ref(0)
    const reviewPageSize = 10

    /* ─── Sentiment ─── */
    const sentimentStats = ref(null)

    /* ─── Analysis ─── */
    const featureGroups = ref([])
    const complaintGroups = ref([])
    const suggestions = ref([])
    const totalNegativeReviews = ref(0)
    const analysisLoading = ref(false)
    const analysisLoaded = ref(false)

    /* ─── Computed ─── */
    const filterLabel = computed(() => filters.find(f => f.key === activeFilter.value)?.label || '')

    const sentimentCounts = computed(() => {
      if (sentimentStats.value) {
        return {
          positive: sentimentStats.value.positive?.count || 0,
          neutral: sentimentStats.value.neutral?.count || 0,
          negative: sentimentStats.value.negative?.count || 0,
        }
      }
      const c = { positive: 0, neutral: 0, negative: 0 }
      reviews.value.forEach(r => { if (c[r.sentiment] !== undefined) c[r.sentiment]++ })
      return c
    })

    const sentimentPercent = computed(() => {
      const total = sentimentStats.value?.total_reviews || reviews.value.length || 1
      return {
        positive: Math.round(sentimentCounts.value.positive / total * 100),
        neutral: Math.round(sentimentCounts.value.neutral / total * 100),
        negative: Math.round(sentimentCounts.value.negative / total * 100),
      }
    })

    const filteredReviews = computed(() =>
      activeFilter.value === 'all'
        ? reviews.value
        : reviews.value.filter(r => r.sentiment === activeFilter.value)
    )

    const reviewTotalPages = computed(() => Math.max(1, Math.ceil(reviewTotal.value / reviewPageSize)))
    const maxComplaint = computed(() => Math.max(...complaintGroups.value.map(c => c.count), 1))

    /* ─── 数据加载 ─── */
    function loadFromStore() {
      const biz = sharedStore.currentBusiness
      if (!biz || !biz.name) return false
      shop.value = {
        name: biz.name,
        rating: Math.round((biz.rating || 0) * 10) / 10,
        reviewCount: biz.review_count || 0,
        tags: (biz.categories || []).slice(0, 5),
        imgBg: biz.imgBg || 'linear-gradient(135deg, #C0392B, #E74C3C)',
      }
      // Sources → reviews
      if (biz.sources && biz.sources.length) {
        reviews.value = biz.sources.map(r => ({
          user: r.user_name || '匿名用户',
          stars: Math.round(r.rating || 0),
          text: r.text || r.snippet || '',
          date: r.date || '',
          sentiment: r.rating >= 4 ? 'positive' : r.rating <= 2 ? 'negative' : 'neutral',
          confidence: 85,
          useful: r.useful || 0,
        }))
        reviewTotal.value = biz.sources.length
      }
      return true
    }

    async function loadShopFromApi(bizId) {
      try {
        const biz = await getBusinessDetail(bizId)
        if (!biz || !biz.name) return false
        shop.value = {
          name: biz.name,
          rating: Math.round((biz.rating || 0) * 10) / 10,
          reviewCount: biz.review_count || 0,
          tags: (biz.categories || []).slice(0, 5),
          imgBg: 'linear-gradient(135deg, #C0392B, #E74C3C)',
        }
        return true
      } catch { return false }
    }

    async function fetchReviews(bizId) {
      reviewsLoading.value = true
      try {
        const sent = { all: undefined, positive: 'positive', neutral: 'neutral', negative: 'negative' }
        const result = await getBusinessReviews(bizId, {
          page: reviewPage.value,
          pageSize: reviewPageSize,
          sentiment: sent[activeFilter.value],
          sortBy: 'date',
        })
        reviews.value = (result.items || []).map(r => ({
          user: r.user_name || '匿名用户',
          stars: Math.round(r.rating || 0),
          text: r.text || '',
          date: r.date || '',
          sentiment: r.sentiment?.label || 'neutral',
          confidence: r.sentiment ? Math.round((r.sentiment.confidence || 0) * 100) : 0,
          useful: r.useful || 0,
        }))
        reviewTotal.value = result.total || 0
      } catch { /* keep existing */ }
      finally { reviewsLoading.value = false }
    }

    async function fetchStats(bizId) {
      try { sentimentStats.value = await getSentimentStats(bizId) } catch {}
    }

    async function fetchAnalysis(bizId) {
      if (analysisLoaded.value || !bizId) return
      analysisLoading.value = true
      try {
        const [kw, att, sug] = await Promise.allSettled([
          getKeywords(bizId, 15),
          getNegativeAttribution(bizId),
          getSuggestions(bizId),
        ])

        if (kw.status === 'fulfilled' && kw.value?.groups) {
          featureGroups.value = kw.value.groups.map(g => ({
            name: g.label || g.dimension,
            icon: g.icon || '🏷️',
            tags: (g.tags || []).map(t => ({ text: t.keyword, count: t.count })),
            max: Math.max(...(g.tags || []).map(t => t.count), 1),
          }))
        }

        if (att.status === 'fulfilled' && att.value) {
          totalNegativeReviews.value = att.value.total_negative || 0
          complaintGroups.value = (att.value.attributions || []).map((a, i) => ({
            dimension: a.label || a.dimension,
            count: a.count,
            barColor: ATTRIBUTION_COLORS[i % ATTRIBUTION_COLORS.length],
          }))
        }

        if (sug.status === 'fulfilled' && sug.value?.suggestions) {
          suggestions.value = sug.value.suggestions
        }
        analysisLoaded.value = true
      } catch {} finally { analysisLoading.value = false }
    }

    function goToReviewPage(p) { reviewPage.value = p; fetchReviews(businessId()) }

    function businessId() { return route.params.id || sharedStore.currentBusiness?.business_id || '' }

    async function initData() {
      const bizId = businessId()
      shopLoading.value = true
      shopError.value = null

      // 1. Try sharedStore
      const fromStore = loadFromStore()

      // 2. Try API for more data
      if (bizId) {
        if (!fromStore) await loadShopFromApi(bizId)
        await fetchReviews(bizId)
        await fetchStats(bizId)
      }

      if (!shop.value.name) {
        shopError.value = bizId
          ? '商家数据接口尚未就绪，请从首页 AI 推荐结果进入'
          : '未指定商家 ID，请从推荐结果或商家详情页进入'
      }

      shopLoading.value = false
    }

    onMounted(() => initData())
    watch(activeFilter, () => { reviewPage.value = 1; fetchReviews(businessId()) })
    watch(activeTab, tab => { if (tab === 'analysis') fetchAnalysis(businessId()) })
    watch(() => route.params.id, () => { analysisLoaded.value = false; initData() })

    return {
      activeTab, activeFilter, tabs, filters, filterLabel,
      shop, shopLoading, shopError,
      reviews, reviewsLoading, reviewPage, reviewTotal, reviewTotalPages,
      sentimentCounts, sentimentPercent, filteredReviews,
      featureGroups, complaintGroups, suggestions,
      totalNegativeReviews, analysisLoading, maxComplaint,
      initData, goToReviewPage,
    }
  },
}
</script>

<style scoped>
.biz-dashboard { padding-bottom: calc(var(--tab-height) + var(--space-8)); }
.back-btn { padding: var(--space-2); color: var(--ink); }
.nav-title { font-family: var(--font-display); font-weight: 700; font-size: var(--text-md); }

/* ── States ── */
.state-container { text-align: center; padding: var(--space-16) var(--space-4); animation: fadeIn 0.5s ease; }
.state-icon { font-size: 3rem; margin-bottom: var(--space-4); }
.state-title { font-family: var(--font-display); font-size: var(--text-xl); font-weight: 700; margin-bottom: var(--space-2); color: var(--ink); }
.state-desc { font-size: var(--text-sm); color: var(--ink-muted); margin-bottom: var(--space-6); }
.state-btn {
  padding: var(--space-2) var(--space-6); background: var(--coral); color: #fff;
  border-radius: var(--radius-full); font-size: var(--text-sm); font-weight: 600;
  margin: 0 var(--space-2); transition: background var(--duration-fast);
}
.state-btn:hover { background: var(--coral-deep); }
.state-btn.secondary { background: var(--warm-bg); color: var(--ink-light); border: 1px solid var(--border); }
.state-btn.secondary:hover { background: var(--border); }

.loading-spinner {
  width: 36px; height: 36px; border: 3px solid var(--border); border-top-color: var(--coral);
  border-radius: 50%; margin: 0 auto var(--space-4); animation: spin 0.8s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }

/* ── Header ── */
.biz-header { display: flex; gap: var(--space-4); padding: var(--space-4); align-items: center; }
.biz-avatar {
  width: 64px; height: 64px; border-radius: var(--radius-lg);
  display: flex; align-items: center; justify-content: center;
  font-family: var(--font-display); font-size: var(--text-xl); font-weight: 700;
  color: #fff; flex-shrink: 0;
}
.biz-info { flex: 1; min-width: 0; }
.biz-name { font-family: var(--font-display); font-size: var(--text-xl); font-weight: 700; margin-bottom: var(--space-1); }
.biz-rating { font-size: var(--text-sm); color: var(--amber); margin-bottom: var(--space-1); }
.review-count { color: var(--ink-muted); font-size: var(--text-xs); }
.biz-tags { display: flex; gap: var(--space-1); flex-wrap: wrap; }
.biz-tag { font-size: var(--text-xs); padding: 2px var(--space-2); background: var(--warm-bg); border-radius: var(--radius-full); color: var(--ink-muted); }

/* ── Tabs ── */
.tab-switch { display: flex; margin: var(--space-3) var(--space-4); background: var(--warm-bg); border-radius: var(--radius-full); padding: 3px; }
.tab-btn {
  flex: 1; padding: var(--space-2) var(--space-4); border-radius: var(--radius-full);
  font-size: var(--text-sm); font-weight: 600; color: var(--ink-muted);
  transition: all var(--duration-fast); text-align: center;
}
.tab-btn.active { background: var(--card-bg); color: var(--coral); box-shadow: var(--shadow-sm); }
.tab-content { padding: 0 var(--space-4); }

/* ── Stats Cards ── */
.sentiment-stats { display: grid; grid-template-columns: repeat(3, 1fr); gap: var(--space-2); margin-bottom: var(--space-4); }
.stat-card { text-align: center; padding: var(--space-3); border-radius: var(--radius-md); }
.stat-card.positive { background: var(--sentiment-positive-bg); }
.stat-card.neutral { background: var(--sentiment-neutral-bg); }
.stat-card.negative { background: var(--sentiment-negative-bg); }
.stat-num { display: block; font-family: var(--font-display); font-size: var(--text-xl); font-weight: 700; }
.stat-card.positive .stat-num { color: var(--sentiment-positive); }
.stat-card.neutral .stat-num { color: #92400E; }
.stat-card.negative .stat-num { color: var(--sentiment-negative); }
.stat-label { font-size: var(--text-xs); color: var(--ink-muted); }

/* ── Filter Chips ── */
.review-filters { display: flex; gap: var(--space-2); margin-bottom: var(--space-4); overflow-x: auto; }
.filter-chip {
  flex-shrink: 0; padding: var(--space-1) var(--space-3); border-radius: var(--radius-full);
  font-size: var(--text-sm); background: var(--warm-bg); color: var(--ink-muted);
  transition: all var(--duration-fast);
}
.filter-chip.active { background: var(--coral); color: #fff; }

/* ── Reviews ── */
.review-loading { display: flex; align-items: center; gap: var(--space-1); padding: var(--space-6); justify-content: center; }
.loading-text { font-size: var(--text-sm); color: var(--ink-muted); margin-left: var(--space-2); }
.review-list { display: flex; flex-direction: column; gap: var(--space-3); }
.review-empty { text-align: center; padding: var(--space-6); color: var(--ink-muted); font-size: var(--text-sm); }
.review-item {
  background: var(--card-bg); border: 1px solid var(--border);
  border-radius: var(--radius-md); padding: var(--space-3);
  animation: slideInUp 0.35s var(--ease-out) both;
}
.review-top { display: flex; align-items: center; justify-content: space-between; margin-bottom: var(--space-1); }
.review-user { font-weight: 600; font-size: var(--text-sm); }
.review-stars { color: var(--amber); font-size: var(--text-sm); margin-bottom: var(--space-1); }
.review-text { font-size: var(--text-sm); color: var(--ink-light); line-height: var(--leading-relaxed); margin-bottom: var(--space-2); }
.review-bottom { display: flex; gap: var(--space-3); font-size: var(--text-xs); color: var(--ink-muted); }

.typing-dot {
  width: 6px; height: 6px; background: var(--ink-muted); border-radius: 50%;
  animation: bounce 1.4s ease-in-out infinite both;
}
.typing-dot:nth-child(1) { animation-delay: 0s; }
.typing-dot:nth-child(2) { animation-delay: 0.16s; }
.typing-dot:nth-child(3) { animation-delay: 0.32s; }
@keyframes bounce { 0%,80%,100%{transform:scale(.6);opacity:.4} 40%{transform:scale(1);opacity:1} }

/* ── Pagination ── */
.pagination { display: flex; align-items: center; justify-content: center; gap: var(--space-4); padding: var(--space-4) 0; }
.page-btn {
  padding: var(--space-2) var(--space-4); border: 1px solid var(--border);
  border-radius: var(--radius-full); font-size: var(--text-sm); color: var(--ink-light);
  transition: all var(--duration-fast);
}
.page-btn:hover:not(:disabled) { border-color: var(--coral); color: var(--coral); }
.page-btn:disabled { opacity: 0.4; cursor: not-allowed; }
.page-info { font-size: var(--text-sm); color: var(--ink-muted); }

/* ── Analysis ── */
.analysis-loading { text-align: center; padding: var(--space-12) var(--space-4); }
.analysis-loading p { margin-top: var(--space-4); color: var(--ink-muted); font-size: var(--text-sm); }
.analysis-section { margin-bottom: var(--space-4); }
.section-card { background: var(--card-bg); border: 1px solid var(--border); border-radius: var(--radius-lg); padding: var(--space-4); }
.section-card-title { font-family: var(--font-display); font-size: var(--text-md); font-weight: 700; margin-bottom: var(--space-4); }
.section-card-desc { font-size: var(--text-xs); color: var(--ink-muted); margin-bottom: var(--space-3); }
.card-empty { text-align: center; padding: var(--space-3); color: var(--ink-muted); font-size: var(--text-sm); }

.sentiment-bar-chart { display: flex; flex-direction: column; gap: var(--space-3); }
.bar-row { display: flex; align-items: center; gap: var(--space-2); }
.bar-label { width: 3em; font-size: var(--text-sm); color: var(--ink-light); flex-shrink: 0; }
.bar-track { flex: 1; height: 8px; background: var(--warm-bg); border-radius: var(--radius-full); overflow: hidden; }
.bar-fill { height: 100%; border-radius: var(--radius-full); transition: width 0.6s var(--ease-out); }
.bar-fill.positive { background: var(--sentiment-positive); }
.bar-fill.neutral { background: var(--sentiment-neutral); }
.bar-fill.negative { background: var(--sentiment-negative); }
.bar-val { width: 3em; font-size: var(--text-sm); font-weight: 600; color: var(--ink); text-align: right; flex-shrink: 0; }

.complaint-list { display: flex; flex-direction: column; gap: var(--space-3); }
.complaint-item { display: flex; align-items: center; gap: var(--space-2); }
.complaint-dim { width: 5em; font-size: var(--text-sm); color: var(--ink-light); flex-shrink: 0; }
.complaint-bar-track { flex: 1; height: 6px; background: var(--warm-bg); border-radius: var(--radius-full); overflow: hidden; }
.complaint-bar { display: block; height: 100%; border-radius: var(--radius-full); transition: width 0.6s var(--ease-out); min-width: 4px; }
.complaint-count { font-size: var(--text-xs); color: var(--ink-muted); flex-shrink: 0; }

.suggestion-list { display: flex; flex-direction: column; gap: var(--space-4); }
.suggestion-item { display: flex; gap: var(--space-3); align-items: flex-start; }
.suggestion-num {
  flex-shrink: 0; width: 28px; height: 28px; border-radius: 50%;
  display: flex; align-items: center; justify-content: center;
  font-size: var(--text-xs); font-weight: 700; margin-top: 1px;
  background: var(--coral-pale); color: var(--coral);
}
.suggestion-num.severity-high { background: #FEE2E2; color: #DC2626; }
.suggestion-num.severity-low { background: #D1FAE5; color: #059669; }
.suggestion-content { flex: 1; }
.suggestion-title { font-size: var(--text-sm); color: var(--ink); display: block; margin-bottom: 2px; }
.suggestion-detail { font-size: var(--text-sm); color: var(--ink-light); line-height: var(--leading-relaxed); margin: 0; }

@media (min-width: 768px) {
  .biz-header { padding: var(--space-6); }
  .biz-avatar { width: 80px; height: 80px; }
  .tab-content { padding: 0 var(--space-6); }
}
@media (min-width: 1024px) {
  .biz-dashboard { max-width: 900px; margin: 0 auto; }
}
</style>
