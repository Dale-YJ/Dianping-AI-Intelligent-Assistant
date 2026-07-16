<template>
  <div class="page-detail">
    <!-- Loading -->
    <div v-if="loading" class="detail-loading">
      <div class="loading-spinner"></div>
      <p>正在加载商家信息...</p>
    </div>

    <!-- Error -->
    <div v-else-if="error" class="detail-error">
      <div class="error-icon">🚧</div>
      <h3>暂时无法加载</h3>
      <p>{{ error }}</p>
      <button class="error-retry" @click="loadData">重试</button>
      <button class="error-retry secondary" @click="$router.push('/')">返回首页</button>
    </div>

    <!-- Content -->
    <template v-else-if="restaurant.name">
    <!-- Hero -->
    <div class="detail-hero">
      <div class="detail-hero-img" :style="{ background: heroBg }"></div>
      <div class="detail-hero-overlay"></div>

      <div class="hero-actions">
        <button class="back-btn-white" @click="$router.back()">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M19 12H5M12 19l-7-7 7-7"/></svg>
        </button>
        <div class="hero-actions-right">
          <button class="icon-btn-glass" @click="toggleHeart">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="heart-icon" :class="{ 'heart-beat': heartActive }">
              <path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z"/>
            </svg>
          </button>
          <button class="icon-btn-glass">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="18" cy="5" r="3"/><circle cx="6" cy="12" r="3"/><circle cx="18" cy="19" r="3"/><path d="M8.59 13.51l6.83 3.98M15.41 6.51l-6.82 3.98"/></svg>
          </button>
        </div>
      </div>

      <div class="detail-hero-info">
        <div class="detail-name">{{ restaurant.name }}</div>
        <div class="detail-meta-row">
          <div class="detail-rating-big">
            <span class="score">{{ restaurant.rating }}</span>
            <span class="unit">/5</span>
          </div>
          <span class="meta-sep">·</span>
          <span>{{ restaurant.reviewCount }} 条评价</span>
          <span class="meta-sep">·</span>
          <span class="status-open">营业中</span>
        </div>
      </div>
    </div>

    <!-- Info Pills -->
    <div class="info-pills stagger-1">
      <div class="info-pill" v-if="restaurant.cuisine"><span>🍽️</span> {{ restaurant.cuisine }}</div>
      <div class="info-pill" v-if="restaurant.location"><span>📍</span> {{ restaurant.location }}</div>
      <div class="info-pill" v-if="restaurant.price"><span>💰</span> {{ restaurant.price }}</div>
      <div class="info-pill" v-if="restaurant.badge"><span>⭐</span> {{ restaurant.badge }}</div>
      <div class="info-pill" @click="goToDashboard" style="cursor:pointer;">
        <span>📊</span> 商家后台
      </div>
    </div>

    <!-- Photos -->
    <div class="detail-section" v-if="photos.length">
      <div class="detail-section-title">🖼️ 餐厅环境</div>
      <PhotoStrip :photos="photos" />
    </div>

    <!-- Recommended Dishes -->
    <div class="detail-section" v-if="dishes.length">
      <div class="detail-section-title">👍 招牌推荐菜</div>
      <DishGrid :dishes="dishes" />
    </div>

    <!-- Reviews -->
    <div class="detail-section">
      <div class="section-header">
        <div class="detail-section-title" style="margin-bottom:0;">💬 精选评价</div>
        <a class="section-more" href="#" @click.prevent="goToDashboard">全部 {{ restaurant.reviewCount }} 条 →</a>
      </div>

      <!-- Review loading -->
      <div class="review-loading" v-if="reviewsLoading">
        <span class="typing-dot"></span><span class="typing-dot"></span><span class="typing-dot"></span>
      </div>

      <!-- Review list -->
      <template v-else>
        <div class="review-empty" v-if="reviews.length === 0 && !reviewsLoading">
          <p>暂无评价数据</p>
        </div>
        <ReviewCard
          v-for="r in reviews"
          :key="r.user + r.date"
          v-bind="r"
        />
      </template>
    </div>

    <!-- Bottom Action Bar -->
    <div class="detail-actions">
      <button class="btn-icon" @click="toggleHeart">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="action-heart" :class="{ filled: heartActive }">
          <path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z"/>
        </svg>
      </button>
      <button class="btn-icon" @click="goToDashboard">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="3" width="18" height="18" rx="2"/><path d="M3 9h18M9 21V9"/></svg>
      </button>
      <button class="btn-primary" @click="goToDashboard">查看口碑分析</button>
    </div>
    </template>

    <!-- No data -->
    <div class="detail-error" v-else-if="!loading">
      <div class="error-icon">🍜</div>
      <h3>未找到商家信息</h3>
      <p>请从首页 AI 推荐结果进入商家详情页</p>
      <button class="error-retry" @click="$router.push('/')">前往 AI 助手</button>
    </div>

    <!-- Source Modal -->
    <Teleport to="body">
      <div class="modal-overlay" v-if="selectedSource" @click.self="selectedSource = null">
        <div class="modal-content">
          <div class="modal-header">
            <h3>📎 原始评价</h3>
            <button class="modal-close" @click="selectedSource = null">✕</button>
          </div>
          <div class="modal-body">
            <div class="source-user-info">
              <span class="source-avatar">{{ (selectedSource.user_name || selectedSource.user || '?')[0] }}</span>
              <div>
                <strong>{{ selectedSource.user_name || selectedSource.user || '匿名用户' }}</strong>
                <span class="source-date">{{ selectedSource.date }}</span>
              </div>
            </div>
            <div class="source-stars">
              <span v-for="i in 5" :key="i" class="star" :class="sourceStarClass(i)">{{ sourceStarChar(i) }}</span>
            </div>
            <p class="source-full-text">{{ selectedSource.text || selectedSource.snippet }}</p>
          </div>
        </div>
      </div>
    </Teleport>
  </div>
</template>

<script>
import { ref, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import PhotoStrip from '../components/PhotoStrip.vue'
import DishGrid from '../components/DishGrid.vue'
import ReviewCard from '../components/ReviewCard.vue'
import { getBusinessDetail } from '../api/modules/business.js'
import { getBusinessReviews } from '../api/modules/reviews.js'
import { sharedStore } from '../stores/sharedData.js'

const IMG_GRADIENTS = [
  'linear-gradient(135deg, #C0392B, #E74C3C)',
  'linear-gradient(135deg, #8B0000, #DC143C)',
  'linear-gradient(135deg, #5D4037, #8D6E63)',
  'linear-gradient(135deg, #2D1B2E, #3D2E3E)',
  'linear-gradient(135deg, #1A3A2A, #2A4A3A)',
  'linear-gradient(135deg, #3D2E1A, #5D4E3A)',
  'linear-gradient(135deg, #2D1A1A, #4D2A2A)',
  'linear-gradient(135deg, #1A2D3D, #2A3D4D)',
]
function hashGradient(str) {
  let hash = 0
  for (let i = 0; i < str.length; i++) hash = str.charCodeAt(i) + ((hash << 5) - hash)
  return IMG_GRADIENTS[Math.abs(hash) % IMG_GRADIENTS.length]
}

export default {
  name: 'RestaurantDetail',
  components: { PhotoStrip, DishGrid, ReviewCard },
  setup() {
    const route = useRoute()
    const router = useRouter()

    const heartActive = ref(false)
    const loading = ref(true)
    const error = ref(null)

    const restaurant = ref({
      name: '', rating: 0, reviewCount: 0,
      cuisine: '', location: '', price: '--', badge: '',
    })
    const heroBg = ref('linear-gradient(135deg,#2D1B1B,#3D2E2E,#4D2A2A)')
    const photos = ref([])
    const dishes = ref([])
    const reviews = ref([])
    const reviewsLoading = ref(false)
    const selectedSource = ref(null)

    /** 从 sharedStore 加载数据（来自首页推荐卡片点击） */
    function loadFromStore() {
      const biz = sharedStore.currentBusiness
      if (!biz || !biz.name) return false

      heroBg.value = biz.imgBg || hashGradient(biz.business_id || biz.name || '')

      restaurant.value = {
        name: biz.name,
        rating: Math.round((biz.rating || 0) * 10) / 10,
        reviewCount: biz.review_count || 0,
        cuisine: (biz.categories || []).join(' · '),
        location: [biz.city, biz.state].filter(Boolean).join(' · ') || biz.address || '',
        price: biz.attributes?.RestaurantsPriceRange2
          ? '$'.repeat(Number(biz.attributes.RestaurantsPriceRange2)) + ' · /人'
          : (biz.price || '--'),
        badge: biz.attributes
          ? Object.keys(biz.attributes).filter(k => !k.startsWith('Restaurants'))[0] || ''
          : '',
      }

      photos.value = (biz.photos || []).map(url => ({ bg: `url(${url})`, w: '160px', h: '110px' }))

      // Sources from recommendation → review cards
      reviews.value = (biz.sources || []).map(r => ({
        avatar: (r.user_name || '?')[0],
        user: r.user_name || '匿名用户',
        rating: r.rating || 0,
        text: r.text || r.snippet || '',
        date: r.date || '',
        likes: r.useful || 0,
        replies: 0, photoCount: 0, photoBg: [],
      }))

      return true
    }

    /** 从后端 API 加载（B.2 + C.2） */
    async function loadFromApi(businessId) {
      try {
        const biz = await getBusinessDetail(businessId)
        if (!biz || !biz.name) return false

        heroBg.value = hashGradient(biz.business_id || biz.name || '')
        restaurant.value = {
          name: biz.name,
          rating: Math.round((biz.rating || 0) * 10) / 10,
          reviewCount: biz.review_count || 0,
          cuisine: (biz.categories || []).join(' · '),
          location: [biz.city, biz.state].filter(Boolean).join(' · '),
          price: biz.attributes?.RestaurantsPriceRange2
            ? '$'.repeat(Number(biz.attributes.RestaurantsPriceRange2)) + ' · /人'
            : '--',
          badge: biz.attributes
            ? Object.keys(biz.attributes).filter(k => !k.startsWith('Restaurants'))[0] || ''
            : '',
        }
        photos.value = (biz.photos || []).map(url => ({ bg: `url(${url})`, w: '160px', h: '110px' }))

        // Load reviews
        reviewsLoading.value = true
        try {
          const revData = await getBusinessReviews(businessId, { pageSize: 5, sortBy: 'date' })
          reviews.value = (revData.items || []).map(r => ({
            avatar: (r.user_name || '?')[0],
            user: r.user_name || '匿名用户',
            rating: r.rating || 0,
            text: r.text || '',
            date: r.date || '',
            likes: r.useful || 0,
            replies: 0, photoCount: 0, photoBg: [],
          }))
        } catch { /* keep existing reviews */ }
        finally { reviewsLoading.value = false }

        return true
      } catch {
        return false
      }
    }

    async function loadData() {
      loading.value = true
      error.value = null

      const businessId = route.params.id

      // 1. Try sharedStore first (from HomePage recommendation click)
      if (loadFromStore()) {
        loading.value = false
        // Also try to load more reviews from API
        if (businessId) {
          reviewsLoading.value = true
          try {
            const revData = await getBusinessReviews(businessId, { pageSize: 10, sortBy: 'date' })
            if (revData.items && revData.items.length) {
              reviews.value = revData.items.map(r => ({
                avatar: (r.user_name || '?')[0],
                user: r.user_name || '匿名用户',
                rating: r.rating || 0,
                text: r.text || '',
                date: r.date || '',
                likes: r.useful || 0,
                replies: 0, photoCount: 0, photoBg: [],
              }))
            }
          } catch { /* keep store data */ }
          finally { reviewsLoading.value = false }
        }
        return
      }

      // 2. Try API
      if (businessId) {
        const ok = await loadFromApi(businessId)
        if (ok) { loading.value = false; return }
      }

      // 3. No data available
      error.value = businessId
        ? '商家详情接口尚未就绪，请从首页 AI 推荐结果进入'
        : '未指定商家 ID'
      loading.value = false
    }

    function toggleHeart() {
      heartActive.value = !heartActive.value
      if (heartActive.value) setTimeout(() => { heartActive.value = false }, 600)
    }

    function goToDashboard() {
      const id = route.params.id
      if (id) router.push(`/business/${encodeURIComponent(id)}`)
    }

    function sourceStarClass(i) {
      const stars = selectedSource.value?.rating || 0
      const full = Math.floor(stars)
      if (i <= full) return 'star-full'
      if (i === full + 1 && stars % 1 >= 0.5) return 'star-half'
      return 'star-empty'
    }
    function sourceStarChar(i) {
      const stars = selectedSource.value?.rating || 0
      return i <= Math.floor(stars) ? '★' : '☆'
    }

    onMounted(() => loadData())
    watch(() => route.params.id, () => loadData())

    return {
      heartActive, loading, error,
      restaurant, photos, dishes, reviews, reviewsLoading,
      heroBg, selectedSource,
      toggleHeart, goToDashboard, loadData,
      sourceStarClass, sourceStarChar,
    }
  },
}
</script>

<style scoped>
.detail-hero {
  position: relative; width: 100%; height: 260px; overflow: hidden;
  background: linear-gradient(135deg, #1A1A2E, #3D2E3A);
}
.detail-hero-img { width: 100%; height: 100%; opacity: 0.85; }
.detail-hero-overlay {
  position: absolute; inset: 0;
  background: linear-gradient(to top, rgba(26,26,46,0.9) 0%, rgba(26,26,46,0.05) 55%, transparent 100%);
}

.hero-actions {
  position: absolute; top: 0; left: 0; right: 0;
  padding: var(--space-3) var(--space-4);
  display: flex; justify-content: space-between; align-items: center;
  z-index: 10;
}
.hero-actions-right { display: flex; gap: var(--space-2); }

.back-btn-white {
  color: #fff; display: flex; align-items: center; gap: var(--space-1);
  font-size: var(--text-sm); transition: opacity var(--duration-fast);
}
.back-btn-white:hover { opacity: 0.7; }
.back-btn-white svg { width: 18px; height: 18px; }

.icon-btn-glass {
  width: 36px; height: 36px; border-radius: 50%;
  display: flex; align-items: center; justify-content: center;
  background: rgba(255,255,255,0.15);
  border: 1px solid rgba(255,255,255,0.2);
  color: #fff;
}
.icon-btn-glass svg { width: 18px; height: 18px; }

.detail-hero-info {
  position: absolute; bottom: 0; left: 0; right: 0;
  padding: var(--space-6); color: #fff;
}
.detail-name { font-family: var(--font-display); font-size: var(--text-2xl); font-weight: 700; margin-bottom: var(--space-2); }
.detail-meta-row { display: flex; align-items: center; gap: var(--space-3); font-size: var(--text-sm); }
.meta-sep { color: rgba(255,255,255,0.5); }
.detail-rating-big { display: flex; align-items: baseline; gap: 2px; font-weight: 700; }
.detail-rating-big .score { font-size: var(--text-xl); color: var(--amber); }
.detail-rating-big .unit { font-size: var(--text-xs); color: rgba(255,255,255,0.7); }
.status-open { color: var(--emerald); font-weight: 600; }

.info-pills {
  display: flex; gap: var(--space-2);
  padding: var(--space-4); flex-wrap: wrap;
}
.info-pill {
  display: flex; align-items: center; gap: var(--space-1);
  font-size: var(--text-xs); color: var(--ink-light);
  padding: var(--space-1) var(--space-3);
  border-radius: var(--radius-full);
  background: #F5F3F0;
  transition: background var(--duration-fast);
}
.info-pill:hover { background: var(--coral-pale); }

.detail-section {
  padding: var(--space-3) var(--space-4) var(--space-5);
  border-bottom: 1px solid var(--border);
}
.detail-section-title {
  font-family: var(--font-display); font-size: var(--text-lg);
  font-weight: 700; margin-bottom: var(--space-3); color: var(--ink);
}

.section-header {
  display: flex; align-items: flex-end; justify-content: space-between;
  margin-bottom: 0;
}
.section-more { font-size: var(--text-xs); color: var(--ink-muted); }
.section-more:hover { color: var(--coral); }

.review-loading {
  display: flex; align-items: center; gap: var(--space-1);
  padding: var(--space-4); justify-content: center;
}
.review-empty { text-align: center; padding: var(--space-4); color: var(--ink-muted); font-size: var(--text-sm); }

.typing-dot {
  width: 6px; height: 6px; background: var(--ink-muted);
  border-radius: 50%; animation: bounce 1.4s ease-in-out infinite both;
}
.typing-dot:nth-child(1) { animation-delay: 0s; }
.typing-dot:nth-child(2) { animation-delay: 0.16s; }
.typing-dot:nth-child(3) { animation-delay: 0.32s; }
@keyframes bounce {
  0%, 80%, 100% { transform: scale(0.6); opacity: 0.4; }
  40% { transform: scale(1); opacity: 1; }
}

.detail-actions {
  position: fixed; bottom: 0; left: 50%; transform: translateX(-50%);
  width: 100%; max-width: var(--max-width);
  display: flex; gap: var(--space-3);
  padding: var(--space-3) var(--space-4);
  padding-bottom: calc(var(--space-3) + env(safe-area-inset-bottom, 0));
  background: rgba(255,255,255,0.95);
  backdrop-filter: blur(20px);
  border-top: 1px solid var(--border);
  z-index: 100;
}
.btn-icon {
  width: 44px; height: 44px; border-radius: 50%;
  display: flex; align-items: center; justify-content: center;
  border: 1px solid var(--border); flex-shrink: 0;
  transition: background var(--duration-fast);
}
.btn-icon:hover { background: var(--card-warm); }
.btn-icon svg { width: 20px; height: 20px; }
.action-heart.filled { color: var(--coral); }

.btn-primary {
  flex: 1; background: var(--coral); color: #fff;
  border-radius: var(--radius-full); font-size: var(--text-md);
  font-weight: 600; padding: var(--space-3);
  transition: background var(--duration-fast);
}
.btn-primary:hover { background: var(--coral-deep); }
.btn-primary:active { transform: scale(0.97); }

.heart-icon { width: 18px; height: 18px; }

/* ── Loading & Error ── */
.detail-loading { text-align: center; padding: var(--space-16) var(--space-4); }
.detail-loading p { margin-top: var(--space-4); color: var(--ink-muted); font-size: var(--text-sm); }
.loading-spinner {
  width: 36px; height: 36px;
  border: 3px solid var(--border); border-top-color: var(--coral);
  border-radius: 50%; margin: 0 auto;
  animation: spin 0.8s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }

.detail-error { text-align: center; padding: var(--space-16) var(--space-4); }
.error-icon { font-size: 3rem; margin-bottom: var(--space-4); }
.detail-error h3 {
  font-family: var(--font-display); font-size: var(--text-xl);
  font-weight: 700; margin-bottom: var(--space-2);
}
.detail-error p { font-size: var(--text-sm); color: var(--ink-muted); margin-bottom: var(--space-6); }
.error-retry {
  padding: var(--space-2) var(--space-6);
  background: var(--coral); color: #fff;
  border-radius: var(--radius-full); font-size: var(--text-sm);
  font-weight: 600; margin: 0 var(--space-2);
  transition: background var(--duration-fast);
}
.error-retry:hover { background: var(--coral-deep); }
.error-retry.secondary {
  background: var(--warm-bg); color: var(--ink-light);
  border: 1px solid var(--border);
}
.error-retry.secondary:hover { background: var(--border); }

/* ── Modal ── */
.modal-overlay {
  position: fixed; inset: 0;
  background: rgba(26, 26, 46, 0.5);
  backdrop-filter: blur(4px);
  display: flex; align-items: center; justify-content: center;
  z-index: 200; padding: var(--space-4);
  animation: fadeIn 0.2s ease;
}
.modal-content {
  background: var(--card-bg); border-radius: var(--radius-xl);
  max-width: 480px; width: 100%; max-height: 80vh; overflow-y: auto;
  box-shadow: var(--shadow-xl);
  animation: scaleIn 0.3s var(--ease-spring);
}
.modal-header {
  display: flex; align-items: center; justify-content: space-between;
  padding: var(--space-4); border-bottom: 1px solid var(--border);
  position: sticky; top: 0; background: var(--card-bg); z-index: 1;
}
.modal-header h3 { font-family: var(--font-display); font-size: var(--text-md); }
.modal-close {
  width: 2rem; height: 2rem; border-radius: 50%;
  display: flex; align-items: center; justify-content: center;
  background: var(--warm-bg); font-size: var(--text-sm);
}
.modal-body { padding: var(--space-4); }
.source-user-info { display: flex; gap: var(--space-3); align-items: center; margin-bottom: var(--space-3); }
.source-avatar {
  width: 40px; height: 40px; border-radius: 50%;
  background: var(--coral-pale); color: var(--coral);
  display: flex; align-items: center; justify-content: center;
  font-weight: 700; font-size: var(--text-md);
}
.source-date { display: block; font-size: var(--text-xs); color: var(--ink-muted); }
.source-stars { color: var(--amber); font-size: var(--text-sm); margin-bottom: var(--space-3); }
.source-stars .star { display: inline-block; position: relative; }
.source-stars .star-full { color: var(--amber); }
.source-stars .star-empty { color: #DDD; }
.source-stars .star-half { color: #DDD; }
.source-stars .star-half::after {
  content: '★'; position: absolute; left: 0; top: 0;
  width: 50%; overflow: hidden; color: var(--amber); pointer-events: none;
}
.source-full-text { font-size: var(--text-base); line-height: var(--leading-relaxed); color: var(--ink-light); }

@media (min-width: 768px) { .detail-hero { height: 320px; } }
@media (min-width: 1024px) { .page-detail { max-width: 900px; margin: 0 auto; } }
</style>
