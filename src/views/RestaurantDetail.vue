<template>
  <div class="page-detail">
    <!-- Loading -->
    <div v-if="loading" class="detail-loading">
      <div class="loading-spinner"></div>
      <p>正在加载商家信息...</p>
    </div>

    <!-- Error -->
    <div v-else-if="error" class="detail-error">
      <div class="error-icon">😵</div>
      <h3>加载失败</h3>
      <p>{{ error }}</p>
      <button class="error-retry" @click="$router.back()">返回</button>
    </div>

    <!-- Content -->
    <template v-else>
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
          <span>{{ restaurant.reviewCount }}条评论</span>
          <span class="meta-sep">·</span>
          <span class="status-open">营业中</span>
        </div>
      </div>
    </div>

    <!-- Info Pills -->
    <div class="info-pills stagger-1">
      <div class="info-pill"><span>🍽️</span> {{ restaurant.cuisine }}</div>
      <div class="info-pill"><span>📍</span> {{ restaurant.location }}</div>
      <div class="info-pill"><span>💰</span> {{ restaurant.price }} / 人</div>
      <div class="info-pill"><span>⭐</span> {{ restaurant.badge }}</div>
    </div>

    <!-- Photos -->
    <div class="detail-section">
      <div class="detail-section-title">餐厅环境</div>
      <PhotoStrip :photos="photos" />
    </div>

    <!-- Recommended Dishes -->
    <div class="detail-section">
      <div class="detail-section-title">👍 招牌推荐菜</div>
      <DishGrid :dishes="dishes" />
    </div>

    <!-- Reviews -->
    <div class="detail-section">
      <div class="section-header">
        <div class="detail-section-title" style="margin-bottom:0;">💬 精选评价</div>
        <a class="section-more" href="#" @click.prevent="$router.push('/profile')">全部 {{ restaurant.reviewCount }} 条 →</a>
      </div>

      <ReviewCard
        v-for="r in reviews"
        :key="r.user"
        v-bind="r"
      />
    </div>

    <!-- Bottom Action Bar -->
    <div class="detail-actions">
      <button class="btn-icon" @click="toggleHeart">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="action-heart" :class="{ filled: heartActive }">
          <path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z"/>
        </svg>
      </button>
      <button class="btn-icon">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 2C8.13 2 5 5.13 5 9c0 5.25 7 13 7 13s7-7.75 7-13c0-3.87-3.13-7-7-7z"/><circle cx="12" cy="9" r="2.5"/></svg>
      </button>
      <button class="btn-primary">立即订座</button>
    </div>
  </div>
    </template>
  </div>
</template>

<script>
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import PhotoStrip from '../components/PhotoStrip.vue'
import DishGrid from '../components/DishGrid.vue'
import ReviewCard from '../components/ReviewCard.vue'
import { getBusinessDetail } from '../api/modules/business.js'
import { getBusinessSummary, getBusinessReviews } from '../api/modules/reviews.js'

export default {
  name: 'RestaurantDetail',
  components: { PhotoStrip, DishGrid, ReviewCard },
  setup() {
    const route = useRoute()
    const router = useRouter()

    /* ─── 状态 ─── */
    const heartActive = ref(false)
    const loading = ref(true)
    const error = ref(null)

    const restaurant = ref({
      name: '加载中...', rating: 0, reviewCount: 0,
      cuisine: '', location: '', price: '--', badge: '',
    })
    const photos = ref([])
    const dishes = ref([])
    const reviews = ref([])
    const heroBg = ref('linear-gradient(135deg,#2D1B1B,#3D2E2E,#4D2A2A)')

    /* ─── 加载数据 ─── */
    async function fetchData(businessId) {
      loading.value = true
      error.value = null
      try {
        const [biz, revData] = await Promise.all([
          getBusinessDetail(businessId),
          getBusinessReviews(businessId, { pageSize: 5, sortBy: 'date' }),
        ])

        // 商家详情 → 组件数据
        restaurant.value = {
          name: biz.name || '未知商家',
          rating: Math.round(biz.rating * 10) / 10,
          reviewCount: biz.review_count || 0,
          cuisine: (biz.categories || []).join(' · '),
          location: [biz.city, biz.state].filter(Boolean).join(' · '),
          price: '--',
          badge: biz.attributes ? (Object.keys(biz.attributes)[0] || '') : '',
        }

        // 照片
        photos.value = (biz.photos || []).map(url => ({
          bg: `url(${url})`, w: '160px', h: '110px',
        }))

        // 评价列表 → ReviewCard props
        reviews.value = (revData.items || []).map(r => ({
          avatar: (r.user_name || '?')[0],
          user: r.user_name,
          rating: r.rating,
          text: r.text,
          date: r.date,
          likes: r.useful || 0,
          replies: 0,
          photoCount: 0,
          photoBg: [],
        }))
      } catch (err) {
        error.value = err.message || '加载失败'
      } finally {
        loading.value = false
      }
    }

    /* ─── 方法 ─── */
    function toggleHeart() {
      heartActive.value = !heartActive.value
      if (heartActive.value) setTimeout(() => { heartActive.value = false }, 600)
    }

    /* ─── 初始化 ─── */
    onMounted(() => {
      const id = route.params.id
      if (id) {
        fetchData(id)
      } else {
        error.value = '未指定商家 ID'
        loading.value = false
      }
    })

    return {
      heartActive, loading, error,
      restaurant, photos, dishes, reviews, heroBg,
      toggleHeart,
    }
  },
}
</script>

<style scoped>
.detail-hero {
  position: relative;
  width: 100%; height: 260px;
  overflow: hidden;
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
  color: #fff;
  display: flex; align-items: center; gap: var(--space-1);
  font-size: var(--text-sm);
  transition: opacity var(--duration-fast);
}
.back-btn-white:hover { opacity: 0.7; }
.back-btn-white svg { width: 18px; height: 18px; }

.icon-btn-glass {
  width: 36px; height: 36px;
  border-radius: 50%;
  display: flex; align-items: center; justify-content: center;
  background: rgba(255,255,255,0.15);
  border: 1px solid rgba(255,255,255,0.2);
  color: #fff;
}
.icon-btn-glass svg { width: 18px; height: 18px; }

.detail-hero-info {
  position: absolute; bottom: 0; left: 0; right: 0;
  padding: var(--space-6);
  color: #fff;
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
  padding: var(--space-4);
  flex-wrap: wrap;
}
.info-pill {
  display: flex; align-items: center; gap: var(--space-1);
  font-size: var(--text-xs); color: var(--ink-light);
  padding: var(--space-1) var(--space-3);
  border-radius: var(--radius-full);
  background: #F5F3F0;
}

.detail-section {
  padding: var(--space-3) var(--space-4) var(--space-5);
  border-bottom: 1px solid var(--border);
}
.detail-section:last-child { border-bottom: none; }

.detail-section-title {
  font-family: var(--font-display);
  font-size: var(--text-lg);
  font-weight: 700;
  margin-bottom: var(--space-3);
  color: var(--ink);
}

.section-header {
  display: flex; align-items: flex-end; justify-content: space-between;
  margin-bottom: 0;
}
.section-more { font-size: var(--text-xs); color: var(--ink-muted); }

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
  width: 44px; height: 44px;
  border-radius: 50%;
  display: flex; align-items: center; justify-content: center;
  border: 1px solid var(--border);
  flex-shrink: 0;
  transition: background var(--duration-fast);
}
.btn-icon:hover { background: var(--card-warm); }
.btn-icon svg { width: 20px; height: 20px; }
.action-heart.filled { color: var(--coral); }

.btn-primary {
  flex: 1;
  background: var(--coral);
  color: #fff;
  border-radius: var(--radius-full);
  font-size: var(--text-md);
  font-weight: 600;
  padding: var(--space-3);
  transition: background var(--duration-fast);
}
.btn-primary:hover { background: var(--coral-deep); }
.btn-primary:active { transform: scale(0.97); }

.heart-icon { width: 18px; height: 18px; }

/* ── Loading & Error States ── */
.detail-loading { text-align: center; padding: var(--space-16) var(--space-4); }
.detail-loading p { margin-top: var(--space-4); color: var(--ink-muted); font-size: var(--text-sm); }
.detail-error { text-align: center; padding: var(--space-16) var(--space-4); }
</style>
