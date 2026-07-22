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
      <!-- Write Review Button -->
      <div class="review-tab-header stagger-3">
        <button class="btn-write-review-dash" @click="openWriteReview">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 5v14M5 12h14"/></svg>
          写评价
        </button>
      </div>

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
          :class="{ 'is-user-review': r.source === 'user_review' }"
          :style="{ animationDelay: (0.3 + i * 0.05) + 's' }"
        >
          <div class="review-top">
            <div class="review-user-row">
              <span class="review-user">{{ r.user }}</span>
              <span class="review-source-badge" v-if="r.source === 'user_review'">我的评价</span>
            </div>
            <SentimentBadge :sentiment="r.sentiment" :confidence="r.confidence" />
          </div>
          <div class="review-stars">{{ '★'.repeat(r.stars) }}{{ '☆'.repeat(5 - r.stars) }}</div>
          <p class="review-text">{{ r.text }}</p>
          <div class="review-bottom">
            <span class="review-date">{{ r.date }}</span>
            <span class="review-votes" v-if="r.useful">👍 {{ r.useful }}</span>
            <template v-if="r.source === 'user_review' && r.review_id">
              <button class="review-action-btn" title="编辑" @click="handleEditReview(r)">
                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/></svg>
              </button>
              <button class="review-action-btn" title="删除" @click="handleDeleteReview(r)">
                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/></svg>
              </button>
            </template>
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
      <!-- AI Summary -->
      <div class="analysis-section stagger-3" v-if="aiSummary">
        <div class="section-card summary-card">
          <h3 class="section-card-title">🤖 AI 口碑总结</h3>
          <div class="summary-body">
            <div class="highlight-group" v-for="group in aiSummaryParsed" :key="group.title">
              <h4 class="highlight-title">{{ group.title }}</h4>
              <div class="highlight-item" v-for="(item, idx) in group.items" :key="idx" @click="item._open = !item._open">
                <div class="highlight-point">
                  <span class="point-dot"></span>
                  <span class="point-text">{{ item.point }}</span>
                  <span class="point-count">{{ item.mention_count }}人提到</span>
                  <svg class="point-chevron" :class="{ open: item._open }" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="6 9 12 15 18 9"/></svg>
                </div>
                <div class="point-sources" v-if="item._open">
                  <div class="source-quote" v-for="(s, si) in item.sources.slice(0, 3)" :key="si">
                    <span class="quote-mark">"</span>{{ s.snippet }}<span class="quote-mark">"</span>
                    <span class="quote-meta"> — {{ s.user_name }} · {{ '★'.repeat(s.rating) }}</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

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
          <div class="suggestion-list">
            <div v-for="(s, i) in autoSuggestions" :key="i" class="suggestion-item">
              <span class="suggestion-num" :class="'severity-' + (s.severity || 'medium')">{{ s.index }}</span>
              <div class="suggestion-content">
                <strong class="suggestion-title">{{ s.title }}</strong>
                <p class="suggestion-detail">{{ s.detail }}</p>
              </div>
            </div>
          </div>
        </div>
      </div>
      </template>
    </div>
    </template>

    <!-- Review Form Modal -->
    <ReviewForm
      :businessId="businessId()"
      :visible="showReviewForm"
      :initialReview="editingReview"
      @close="closeReviewForm"
      @saved="handleReviewSaved"
      @deleted="handleReviewDeleted"
    />
  </div>
</template>

<script>
import { ref, computed, onMounted, watch } from 'vue'
import { useRoute } from 'vue-router'
import TopNav from '../components/TopNav.vue'
import SentimentBadge from '../components/SentimentBadge.vue'
import FeatureTagCloud from '../components/FeatureTagCloud.vue'
import ReviewForm from '../components/ReviewForm.vue'
import { getBusinessDetail } from '../api/modules/business.js'
import {
  getBusinessReviews, getBusinessSummary, getSentimentStats,
  getKeywords, getNegativeAttribution, getSuggestions, deleteReview,
} from '../api/modules/reviews.js'
import { sharedStore } from '../stores/sharedData.js'

const ATTRIBUTION_COLORS = ['#EF4444', '#F97316', '#F59E0B', '#EAB308', '#F97316']

export default {
  name: 'BusinessDashboard',
  components: { TopNav, SentimentBadge, FeatureTagCloud, ReviewForm },
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

    /* ─── Review Form ─── */
    const showReviewForm = ref(false)
    const editingReview = ref(null)

    /* ─── Sentiment ─── */
    const sentimentStats = ref(null)

    /* ─── Analysis ─── */
    const featureGroups = ref([])
    const complaintGroups = ref([])
    const suggestions = ref([])
    const aiSummary = ref(null)
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

    // 解析 AI 总结 JSON（可能是字符串）
    const aiSummaryParsed = computed(() => {
      const groups = []
      const fields = [
        { key: 'highlights', label: '👍 好评亮点' },
        { key: 'lowlights', label: '👎 差评槽点' },
        { key: 'recent', label: '📊 近期动态' },
      ]
      for (const f of fields) {
        const raw = aiSummary.value?.[f.key]
        if (!raw) continue
        let data = raw
        if (typeof raw === 'string') {
          try { data = JSON.parse(raw) } catch { continue }
        }
        if (data && data.items?.length) {
          groups.push({ title: f.label, items: data.items.map(i => ({ ...i, _open: false })) })
        } else if (data && data.title) {
          groups.push({ title: data.title, items: (data.items || []).map(i => ({ ...i, _open: false })) })
        }
      }
      return groups
    })

    // 从关键词+情感数据自动生成经营建议
    const autoSuggestions = computed(() => {
      const list = []
      const pos = sentimentPercent.value
      const negCount = sentimentCounts.value.negative || 0
      const flatTags = featureGroups.value.flatMap(g =>
        (g.tags || []).map(t => ({ ...t, dim: g.name }))
      )

      if (pos.positive >= 80) {
        list.push({ title: '口碑良好，继续保持', detail: `好评率 ${pos.positive}%，核心优势明显，建议持续维护招牌菜品品质并鼓励满意顾客留下评价。`, severity: 'low' })
      }
      if (negCount > 0 && pos.negative >= 10) {
        list.push({ title: `关注差评反馈（${negCount}条）`, detail: '建议逐条回复差评、了解具体原因，针对性改进后邀请顾客再次体验。', severity: 'high' })
      }
      // 从关键词中找出负面标签
      const negTags = flatTags.filter(t => t.sentiment === 'negative' || t.text?.includes('差') || t.text?.includes('慢') || t.text?.includes('贵'))
      if (negTags.length) {
        const topNeg = negTags.slice(0, 3).map(t => t.text).join('、')
        list.push({ title: '改进重点：' + topNeg, detail: `这些方面在评价中被反复提及，优先改进可显著提升顾客满意度。`, severity: 'high' })
      }
      const posTags = flatTags.filter(t => t.sentiment === 'positive').sort((a, b) => b.count - a.count)
      if (posTags.length) {
        const top3 = posTags.slice(0, 3).map(t => t.text).join('、')
        list.push({ title: '核心卖点：' + top3, detail: '这些是顾客最认可的亮点，建议在宣传和菜单中突出展示。', severity: 'low' })
      }
      if (!list.length) {
        list.push({ title: '数据积累中', detail: '评价数据还不够充分，建议鼓励顾客多留下真实反馈，积累到一定量后系统将自动生成经营建议。', severity: 'medium' })
      }
      return list.map((s, i) => ({ ...s, index: i + 1 }))
    })

    /* ─── 数据加载 ─── */
    function loadFromStore() {
      const biz = sharedStore.currentBusiness
      if (!biz || !biz.name) return false
      const storePhotos = Array.isArray(biz.photos) ? biz.photos : []
      const storePhoto = storePhotos[0] || null
      shop.value = {
        name: biz.name,
        rating: Math.round((biz.rating || 0) * 10) / 10,
        reviewCount: biz.review_count || 0,
        tags: (biz.categories || []).slice(0, 5),
        imgBg: storePhoto
          ? `url(${storePhoto}) center/cover no-repeat`
          : (biz.imgBg || 'linear-gradient(135deg, #C0392B, #E74C3C)'),
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
          source: r.source || 'yelp',
          review_id: r.review_id || null,
        }))
        reviewTotal.value = biz.sources.length
      }
      return true
    }

    async function loadShopFromApi(bizId) {
      try {
        const biz = await getBusinessDetail(bizId)
        if (!biz || !biz.name) return false
        const apiPhotos = Array.isArray(biz.photos) ? biz.photos : []
        const apiPhoto = apiPhotos[0] || null
        shop.value = {
          name: biz.name,
          rating: Math.round((biz.rating || 0) * 10) / 10,
          reviewCount: biz.review_count || 0,
          tags: (biz.categories || []).slice(0, 5),
          imgBg: apiPhoto
            ? `url(${apiPhoto}) center/cover no-repeat`
            : 'linear-gradient(135deg, #C0392B, #E74C3C)',
        }
        return true
      } catch { return false }
    }

    async function fetchReviews(bizId) {
      reviewsLoading.value = true
      try {
        const result = await getBusinessReviews(bizId, {
          page: reviewPage.value,
          pageSize: reviewPageSize,
          sortBy: 'date',
        })
        reviews.value = (result.items || []).map(r => ({
          user: r.user_name || '匿名用户',
          stars: Math.round(r.rating || 0),
          text: r.text || '',
          date: r.date || '',
          sentiment: r.sentiment?.label || (r.rating >= 4 ? 'positive' : r.rating <= 2 ? 'negative' : 'neutral'),
          confidence: r.sentiment ? Math.round((r.sentiment.confidence || 0) * 100) : 85,
          useful: r.useful || 0,
          source: r.source || 'yelp',
          review_id: r.review_id || null,
        }))
        reviewTotal.value = result.total || 0
      } catch { /* keep existing */ }
      finally { reviewsLoading.value = false }
    }

    async function fetchStats(bizId) {
      try {
        const data = await getSentimentStats(bizId)
        if (data?.sentiment_stats) {
          sentimentStats.value = {
            total_reviews: data.total_reviews,
            positive: { count: data.sentiment_stats.positive_count, percentage: Math.round(data.sentiment_stats.positive_ratio * 100) },
            neutral: { count: data.sentiment_stats.neutral_count, percentage: Math.round(data.sentiment_stats.neutral_ratio * 100) },
            negative: { count: data.sentiment_stats.negative_count, percentage: Math.round(data.sentiment_stats.negative_ratio * 100) },
          }
        }
        // 同时用情感接口带回的评价列表更新 review
        if (data?.reviews?.length && (!reviews.value.length || activeFilter.value === 'all')) {
          reviews.value = data.reviews.map(r => ({
            user: r.user_name || '匿名用户',
            stars: Math.round(r.rating || 0),
            text: r.text || '',
            date: r.date || '',
            sentiment: r.sentiment?.label || 'neutral',
            confidence: r.sentiment ? Math.round((r.sentiment.confidence || 0) * 100) : 0,
            useful: r.useful || 0,
            source: r.source || 'yelp',
            review_id: r.review_id || null,
          }))
          reviewTotal.value = data.total_reviews || reviews.value.length
        }
      } catch {}
    }

    async function fetchAnalysis(bizId) {
      if (analysisLoaded.value || !bizId) return
      analysisLoading.value = true
      try {
        const [kw, att, sug, sum] = await Promise.allSettled([
          getKeywords(bizId, 15),
          getNegativeAttribution(bizId),
          getSuggestions(bizId),
          getBusinessSummary(bizId),
        ])

        if (kw.status === 'fulfilled' && kw.value?.keyword_groups) {
          featureGroups.value = kw.value.keyword_groups.map(g => ({
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

        if (sum.status === 'fulfilled' && sum.value) {
          aiSummary.value = {
            highlights: sum.value.highlights || '',
            lowlights: sum.value.lowlights || '',
            recent: sum.value.recent_news || '',
          }
        }
        analysisLoaded.value = true
      } catch {} finally { analysisLoading.value = false }
    }

    function goToReviewPage(p) { reviewPage.value = p; fetchReviews(businessId()) }

    /* ─── Review Form Handlers ─── */
    function openWriteReview() {
      editingReview.value = null
      showReviewForm.value = true
    }

    function handleEditReview(r) {
      editingReview.value = {
        review_id: r.review_id,
        rating: r.stars,
        text: r.text,
      }
      showReviewForm.value = true
    }

    async function handleDeleteReview(r) {
      if (!r.review_id) return
      if (!confirm('确定要删除这条评价吗？此操作不可撤销。')) return
      try {
        await deleteReview(r.review_id)
        reviews.value = reviews.value.filter(rv => rv.review_id !== r.review_id)
        reviewTotal.value = Math.max(0, reviewTotal.value - 1)
      } catch (err) {
        alert(err.message || '删除失败，请稍后重试')
      }
    }

    function closeReviewForm() {
      showReviewForm.value = false
      editingReview.value = null
    }

    function handleReviewSaved() {
      const bizId = businessId()
      if (bizId) fetchReviews(bizId)
    }

    function handleReviewDeleted() {
      if (editingReview.value?.review_id) {
        reviews.value = reviews.value.filter(r => r.review_id !== editingReview.value.review_id)
        reviewTotal.value = Math.max(0, reviewTotal.value - 1)
      }
      editingReview.value = null
    }

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
      featureGroups, complaintGroups, aiSummary, aiSummaryParsed, autoSuggestions,
      totalNegativeReviews, analysisLoading, maxComplaint,
      initData, goToReviewPage, businessId,
      showReviewForm, editingReview,
      openWriteReview, handleEditReview, handleDeleteReview,
      closeReviewForm, handleReviewSaved, handleReviewDeleted,
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
  background-size: cover;
  background-position: center;
  background-repeat: no-repeat;
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

/* ── Write Review Button ── */
.review-tab-header {
  display: flex;
  justify-content: flex-end;
  margin-bottom: var(--space-3);
}
.btn-write-review-dash {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: var(--space-2) var(--space-4);
  background: var(--coral);
  color: #fff;
  border-radius: var(--radius-full);
  font-size: var(--text-sm);
  font-weight: 600;
  transition: background var(--duration-fast);
}
.btn-write-review-dash:hover { background: var(--coral-deep); }

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
.review-user-row {
  display: flex; align-items: center; gap: var(--space-2);
}
.review-source-badge {
  font-size: 0.625rem;
  padding: 1px 6px;
  background: var(--coral);
  color: #fff;
  border-radius: var(--radius-full);
  font-weight: 600;
}
.review-stars { color: var(--amber); font-size: var(--text-sm); margin-bottom: var(--space-1); }
.review-text { font-size: var(--text-sm); color: var(--ink-light); line-height: var(--leading-relaxed); margin-bottom: var(--space-2); }
.review-bottom { display: flex; align-items: center; gap: var(--space-3); font-size: var(--text-xs); color: var(--ink-muted); }
.review-action-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 22px;
  height: 22px;
  border-radius: 50%;
  color: var(--ink-muted);
  transition: all var(--duration-fast);
}
.review-action-btn:hover {
  background: var(--coral-pale);
  color: var(--coral);
}

/* ── User Review Highlight ── */
.review-item.is-user-review {
  border-left: 3px solid var(--coral);
  background: var(--coral-pale);
}

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

/* ── AI Summary ── */
.summary-card { border-left: 3px solid var(--coral); }
.summary-body { display: flex; flex-direction: column; gap: var(--space-4); }
.highlight-group { }
.highlight-title { font-size: var(--text-sm); font-weight: 700; color: var(--ink); margin-bottom: var(--space-2); }
.highlight-item {
  border-radius: var(--radius-sm);
  transition: background var(--duration-fast);
  cursor: pointer;
}
.highlight-item:hover { background: var(--warm-bg); }
.highlight-point {
  display: flex; align-items: center; gap: var(--space-2);
  padding: var(--space-1) 0;
  font-size: var(--text-sm);
}
.point-dot {
  width: 6px; height: 6px; border-radius: 50%;
  background: var(--coral); flex-shrink: 0;
}
.point-text { flex: 1; color: var(--ink-light); }
.point-count { font-size: var(--text-xs); color: var(--coral); font-weight: 600; white-space: nowrap; }
.point-chevron { flex-shrink: 0; color: var(--ink-muted); transition: transform 0.2s ease; }
.point-chevron.open { transform: rotate(180deg); }
.point-sources { padding: var(--space-2) var(--space-2) var(--space-2) var(--space-6); }
.source-quote {
  font-size: var(--text-xs); color: var(--ink-muted);
  line-height: 1.6; padding: var(--space-1) 0;
  border-bottom: 1px solid var(--border);
}
.source-quote:last-child { border-bottom: none; }
.quote-mark { color: var(--amber); }
.quote-meta { color: var(--ink-muted); font-size: 0.625rem; white-space: nowrap; }

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
