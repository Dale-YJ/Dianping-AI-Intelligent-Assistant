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

    <div class="biz-header stagger-1">
      <div class="biz-avatar" :style="{ background: shop.imgBg }">{{ shop.name[0] }}</div>
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

    <div class="tab-switch stagger-2">
      <button
        v-for="tab in tabs"
        :key="tab.key"
        class="tab-btn"
        :class="{ active: activeTab === tab.key }"
        @click="activeTab = tab.key"
      >{{ tab.label }}</button>
    </div>

    <!-- Reviews Tab -->
    <div class="tab-content" v-if="activeTab === 'reviews'">
      <div class="sentiment-stats stagger-3">
        <div class="stat-card positive">
          <span class="stat-num">{{ sentimentCounts.positive }}</span>
          <span class="stat-label">好评</span>
        </div>
        <div class="stat-card neutral">
          <span class="stat-num">{{ sentimentCounts.neutral }}</span>
          <span class="stat-label">中评</span>
        </div>
        <div class="stat-card negative">
          <span class="stat-num">{{ sentimentCounts.negative }}</span>
          <span class="stat-label">差评</span>
        </div>
      </div>

      <div class="review-filters stagger-3">
        <button
          v-for="f in filters"
          :key="f.key"
          class="filter-chip"
          :class="{ active: activeFilter === f.key }"
          @click="activeFilter = f.key"
        >{{ f.label }}</button>
      </div>

      <div class="review-list">
        <div
          v-for="(r, i) in filteredReviews"
          :key="i"
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
    </div>

    <!-- Analysis Tab -->
    <div class="tab-content" v-if="activeTab === 'analysis'">
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

      <div class="analysis-section stagger-3">
        <div class="section-card">
          <h3 class="section-card-title">🏷️ 特征关键词</h3>
          <FeatureTagCloud :groups="featureGroups" />
        </div>
      </div>

      <div class="analysis-section stagger-3" v-if="complaintGroups.length">
        <div class="section-card">
          <h3 class="section-card-title">⚠️ 差评归因</h3>
          <div class="complaint-list">
            <div v-for="c in complaintGroups" :key="c.dimension" class="complaint-item">
              <span class="complaint-dim">{{ c.dimension }}</span>
              <span class="complaint-bar" :style="{ width: (c.count / maxComplaint * 100) + '%', background: c.barColor }"></span>
              <span class="complaint-count">{{ c.count }}条</span>
            </div>
          </div>
        </div>
      </div>

      <div class="analysis-section stagger-3">
        <div class="section-card">
          <h3 class="section-card-title">💡 经营建议</h3>
          <div class="suggestion-list">
            <div v-for="(s, i) in suggestions" :key="i" class="suggestion-item">
              <span class="suggestion-num">{{ i + 1 }}</span>
              <p>{{ s }}</p>
            </div>
          </div>
        </div>
      </div>
    </div>
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

/* ─── 情感标签颜色（用于差评归因条形图） ─── */
const ATTRIBUTION_COLORS = ['#EF4444', '#F97316', '#F59E0B', '#EAB308', '#F97316']

export default {
  name: 'BusinessDashboard',
  components: { TopNav, SentimentBadge, FeatureTagCloud },
  setup() {
    const route = useRoute()

    /* ─── Tab & Filter 状态 ─── */
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

    /* ─── 商家基础信息 ─── */
    const shop = ref({
      name: '加载中...', rating: 0, reviewCount: 0,
      tags: [], imgBg: 'linear-gradient(135deg, #C0392B, #E74C3C)',
    })
    const shopLoading = ref(true)
    const shopError = ref(null)

    /* ─── 评价数据 ─── */
    const reviews = ref([])
    const reviewsLoading = ref(false)
    const sentimentStats = ref(null)

    /* ─── 口碑分析数据 ─── */
    const featureGroups = ref([])
    const complaintGroups = ref([])
    const suggestions = ref([])
    const analysisLoading = ref(false)
    const analysisLoaded = ref(false)

    /* ─── 计算属性 ─── */
    const sentimentCounts = computed(() => {
      if (sentimentStats.value) {
        return {
          positive: sentimentStats.value.positive?.count || 0,
          neutral: sentimentStats.value.neutral?.count || 0,
          negative: sentimentStats.value.negative?.count || 0,
        }
      }
      // fallback: 从评价列表计算
      const c = { positive: 0, neutral: 0, negative: 0 }
      reviews.value.forEach(r => { if (c[r.sentiment] !== undefined) c[r.sentiment]++ })
      return c
    })

    const sentimentPercent = computed(() => {
      const total = (sentimentStats.value?.total_reviews || reviews.value.length) || 1
      return {
        positive: Math.round(sentimentCounts.value.positive / total * 100),
        neutral: Math.round(sentimentCounts.value.neutral / total * 100),
        negative: Math.round(sentimentCounts.value.negative / total * 100),
      }
    })

    const filteredReviews = computed(() => {
      if (activeFilter.value === 'all') return reviews.value
      return reviews.value.filter(r => r.sentiment === activeFilter.value)
    })

    const maxComplaint = computed(() =>
      Math.max(...complaintGroups.value.map(c => c.count), 1)
    )

    /* ─── 方法 ─── */

    /** 加载商家信息 */
    async function fetchShop(businessId) {
      shopLoading.value = true
      shopError.value = null
      try {
        const biz = await getBusinessDetail(businessId)
        shop.value = {
          name: biz.name,
          rating: Math.round(biz.rating * 10) / 10,
          reviewCount: biz.review_count || 0,
          tags: biz.categories || [],
          imgBg: 'linear-gradient(135deg, #C0392B, #E74C3C)',
        }
      } catch (e) {
        shopError.value = e.message
      } finally {
        shopLoading.value = false
      }
    }

    /** 加载评价列表 + 情感统计 */
    async function fetchReviews(businessId, params = {}) {
      reviewsLoading.value = true
      try {
        const sent = { all: undefined, positive: 'positive', neutral: 'neutral', negative: 'negative' }
        const result = await getBusinessReviews(businessId, {
          ...params,
          sentiment: sent[activeFilter.value],
        })
        reviews.value = (result.items || []).map(r => ({
          user: r.user_name,
          stars: r.rating,
          text: r.text,
          date: r.date,
          sentiment: r.sentiment?.label || 'neutral',
          confidence: r.sentiment ? Math.round(r.sentiment.confidence * 100) : 0,
          useful: r.useful || 0,
        }))
      } finally {
        reviewsLoading.value = false
      }
    }

    /** 加载情感统计 */
    async function fetchStats(businessId) {
      try {
        sentimentStats.value = await getSentimentStats(businessId)
      } catch { /* 静默失败 */ }
    }

    /** 懒加载口碑分析数据 */
    async function fetchAnalysis(businessId) {
      if (analysisLoaded.value) return
      analysisLoading.value = true
      try {
        const [kw, att, sug] = await Promise.allSettled([
          getKeywords(businessId),
          getNegativeAttribution(businessId),
          getSuggestions(businessId),
        ])

        if (kw.status === 'fulfilled') {
          featureGroups.value = (kw.value.groups || []).map(g => ({
            name: g.label || g.dimension,
            icon: g.icon || '🏷️',
            tags: (g.tags || []).map(t => ({ text: t.keyword, count: t.count })),
            max: Math.max(...(g.tags || []).map(t => t.count), 1),
          }))
        }

        if (att.status === 'fulfilled') {
          complaintGroups.value = (att.value.attributions || []).map((a, i) => ({
            dimension: a.label || a.dimension,
            count: a.count,
            barColor: ATTRIBUTION_COLORS[i % ATTRIBUTION_COLORS.length],
          }))
        }

        if (sug.status === 'fulfilled') {
          suggestions.value = (sug.value.suggestions || []).map(s =>
            `${s.title}\n${s.detail}`
          )
        }

        analysisLoaded.value = true
      } finally {
        analysisLoading.value = false
      }
    }

    /* ─── 路由监听 ─── */
    const businessId = route.params.id || 'biz_001'

    onMounted(() => {
      fetchShop(businessId)
      fetchReviews(businessId)
      fetchStats(businessId)
    })

    // 切换筛选时重新请求
    watch(activeFilter, () => fetchReviews(businessId))
    // 切换到分析 Tab 时懒加载
    watch(activeTab, (tab) => {
      if (tab === 'analysis') fetchAnalysis(businessId)
    })

    return {
      activeTab, activeFilter, tabs, filters,
      shop, shopLoading, shopError,
      reviews, reviewsLoading,
      sentimentCounts, sentimentPercent, filteredReviews,
      featureGroups, complaintGroups, suggestions,
      analysisLoading, analysisLoaded, maxComplaint,
    }
  },
}
</script>

<style scoped>
.biz-dashboard { padding-bottom: calc(var(--tab-height) + var(--space-8)); }
.back-btn { padding: var(--space-2); color: var(--ink); }
.nav-title { font-family: var(--font-display); font-weight: 700; font-size: var(--text-md); }

.biz-header {
  display: flex;
  gap: var(--space-4);
  padding: var(--space-4);
  align-items: center;
}
.biz-avatar {
  width: 64px;
  height: 64px;
  border-radius: var(--radius-lg);
  display: flex;
  align-items: center;
  justify-content: center;
  font-family: var(--font-display);
  font-size: var(--text-xl);
  font-weight: 700;
  color: #fff;
  flex-shrink: 0;
}
.biz-info { flex: 1; min-width: 0; }
.biz-name {
  font-family: var(--font-display);
  font-size: var(--text-xl);
  font-weight: 700;
  margin-bottom: var(--space-1);
}
.biz-rating { font-size: var(--text-sm); color: var(--amber); margin-bottom: var(--space-1); }
.biz-rating span { margin-right: var(--space-1); }
.review-count { color: var(--ink-muted); font-size: var(--text-xs); }
.biz-tags { display: flex; gap: var(--space-1); flex-wrap: wrap; }
.biz-tag {
  font-size: var(--text-xs);
  padding: 2px var(--space-2);
  background: var(--warm-bg);
  border-radius: var(--radius-full);
  color: var(--ink-muted);
}

.tab-switch {
  display: flex;
  margin: var(--space-3) var(--space-4);
  background: var(--warm-bg);
  border-radius: var(--radius-full);
  padding: 3px;
}
.tab-btn {
  flex: 1;
  padding: var(--space-2) var(--space-4);
  border-radius: var(--radius-full);
  font-size: var(--text-sm);
  font-weight: 600;
  color: var(--ink-muted);
  transition: all var(--duration-fast);
  text-align: center;
}
.tab-btn.active { background: var(--card-bg); color: var(--coral); box-shadow: var(--shadow-sm); }
.tab-content { padding: 0 var(--space-4); }

/* Sentiment Stats */
.sentiment-stats {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: var(--space-2);
  margin-bottom: var(--space-4);
}
.stat-card {
  text-align: center;
  padding: var(--space-3);
  border-radius: var(--radius-md);
}
.stat-card.positive { background: var(--sentiment-positive-bg); }
.stat-card.neutral { background: var(--sentiment-neutral-bg); }
.stat-card.negative { background: var(--sentiment-negative-bg); }
.stat-num {
  display: block;
  font-family: var(--font-display);
  font-size: var(--text-xl);
  font-weight: 700;
}
.stat-card.positive .stat-num { color: var(--sentiment-positive); }
.stat-card.neutral .stat-num { color: #92400E; }
.stat-card.negative .stat-num { color: var(--sentiment-negative); }
.stat-label { font-size: var(--text-xs); color: var(--ink-muted); }

/* Filters */
.review-filters {
  display: flex;
  gap: var(--space-2);
  margin-bottom: var(--space-4);
  overflow-x: auto;
}
.filter-chip {
  flex-shrink: 0;
  padding: var(--space-1) var(--space-3);
  border-radius: var(--radius-full);
  font-size: var(--text-sm);
  background: var(--warm-bg);
  color: var(--ink-muted);
  transition: all var(--duration-fast);
}
.filter-chip.active { background: var(--coral); color: #fff; }

/* Review List */
.review-list { display: flex; flex-direction: column; gap: var(--space-3); }
.review-item {
  background: var(--card-bg);
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
  padding: var(--space-3);
  animation: slideInUp 0.35s var(--ease-out) both;
}
.review-top { display: flex; align-items: center; justify-content: space-between; margin-bottom: var(--space-1); }
.review-user { font-weight: 600; font-size: var(--text-sm); }
.review-stars { color: var(--amber); font-size: var(--text-sm); margin-bottom: var(--space-1); }
.review-text { font-size: var(--text-sm); color: var(--ink-light); line-height: var(--leading-relaxed); margin-bottom: var(--space-2); }
.review-bottom { display: flex; gap: var(--space-3); font-size: var(--text-xs); color: var(--ink-muted); }

/* Analysis Sections */
.analysis-section { margin-bottom: var(--space-4); }
.section-card {
  background: var(--card-bg);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  padding: var(--space-4);
}
.section-card-title {
  font-family: var(--font-display);
  font-size: var(--text-md);
  font-weight: 700;
  margin-bottom: var(--space-4);
}

/* Bar Chart */
.sentiment-bar-chart { display: flex; flex-direction: column; gap: var(--space-3); }
.bar-row { display: flex; align-items: center; gap: var(--space-2); }
.bar-label { width: 3em; font-size: var(--text-sm); color: var(--ink-light); flex-shrink: 0; }
.bar-track { flex: 1; height: 8px; background: var(--warm-bg); border-radius: var(--radius-full); overflow: hidden; }
.bar-fill { height: 100%; border-radius: var(--radius-full); transition: width 0.6s var(--ease-out); }
.bar-fill.positive { background: var(--sentiment-positive); }
.bar-fill.neutral { background: var(--sentiment-neutral); }
.bar-fill.negative { background: var(--sentiment-negative); }
.bar-val { width: 3em; font-size: var(--text-sm); font-weight: 600; color: var(--ink); text-align: right; flex-shrink: 0; }

/* Complaint */
.complaint-list { display: flex; flex-direction: column; gap: var(--space-3); }
.complaint-item { display: flex; align-items: center; gap: var(--space-2); }
.complaint-dim { width: 5em; font-size: var(--text-sm); color: var(--ink-light); flex-shrink: 0; }
.complaint-bar { height: 6px; border-radius: var(--radius-full); transition: width 0.6s var(--ease-out); min-width: 4px; }
.complaint-count { font-size: var(--text-xs); color: var(--ink-muted); flex-shrink: 0; }

/* Suggestions */
.suggestion-list { display: flex; flex-direction: column; gap: var(--space-3); }
.suggestion-item { display: flex; gap: var(--space-3); align-items: flex-start; }
.suggestion-num {
  flex-shrink: 0;
  width: 24px;
  height: 24px;
  border-radius: 50%;
  background: var(--coral-pale);
  color: var(--coral);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: var(--text-xs);
  font-weight: 700;
  margin-top: 1px;
}
.suggestion-item p { font-size: var(--text-sm); color: var(--ink-light); line-height: var(--leading-relaxed); }

@media (min-width: 768px) {
  .biz-header { padding: var(--space-6); }
  .biz-avatar { width: 80px; height: 80px; }
  .tab-content { padding: 0 var(--space-6); }
}
@media (min-width: 1024px) {
  .biz-dashboard { max-width: 900px; margin: 0 auto; }
  .sentiment-stats { grid-template-columns: repeat(3, 1fr); gap: var(--space-4); }
}
</style>
