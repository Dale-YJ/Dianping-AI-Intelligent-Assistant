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
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="heart-icon" :class="{ 'heart-beat': heartActive }"><path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z"/></svg>
            </button>
            <button class="icon-btn-glass">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="18" cy="5" r="3"/><circle cx="6" cy="12" r="3"/><circle cx="18" cy="19" r="3"/><path d="M8.59 13.51l6.83 3.98M15.41 6.51l-6.82 3.98"/></svg>
            </button>
          </div>
        </div>
        <div class="detail-hero-info">
          <div class="detail-name">{{ restaurant.name }}</div>
        </div>
      </div>

      <!-- Rating & Quick Info Card -->
      <div class="rating-card">
        <div class="rating-main">
          <span class="rating-big">{{ restaurant.rating }}</span>
          <div class="rating-right">
            <div class="rating-stars">
              <span v-for="i in 5" :key="i" class="rstar" :class="i <= starFloor ? 'full' : (i === starHalf ? 'half' : 'empty')">★</span>
            </div>
            <span class="rating-sub">{{ restaurant.reviewCount }} 条评价</span>
          </div>
        </div>
        <div class="rating-bar-wrap">
          <div class="rating-bar-fill" :style="{ width: ratingPct + '%' }"></div>
        </div>
      </div>

      <!-- Address & Info -->
      <div class="info-section">
        <div class="info-row" v-if="restaurant.location">
          <span class="info-icon">📍</span>
          <div class="info-content">
            <span class="info-label">地址</span>
            <span class="info-value">{{ restaurant.location }}</span>
          </div>
        </div>
        <div class="info-row" v-if="restaurant.cuisine">
          <span class="info-icon">🍽️</span>
          <div class="info-content">
            <span class="info-label">菜系</span>
            <span class="info-value">{{ restaurant.cuisine }}</span>
          </div>
        </div>
        <div class="info-row" v-if="restaurant.price && restaurant.price !== '--'">
          <span class="info-icon">💰</span>
          <div class="info-content">
            <span class="info-label">人均</span>
            <span class="info-value">{{ restaurant.price }}</span>
          </div>
        </div>
        <div class="info-row" v-if="restaurant.badge">
          <span class="info-icon">🏷️</span>
          <div class="info-content">
            <span class="info-label">特色</span>
            <span class="info-value">{{ restaurant.badge }}</span>
          </div>
        </div>
      </div>

      <!-- Photos -->
      <div class="detail-section" v-if="photos.length">
        <div class="detail-section-title">📷 餐厅环境</div>
        <PhotoStrip :photos="photos" />
      </div>

      <!-- Dishes -->
      <div class="detail-section" v-if="dishes.length">
        <div class="detail-section-title">🍳 招牌菜品</div>
        <DishGrid :dishes="dishes" />
      </div>

      <!-- AI Summary -->
      <div class="detail-section" v-if="businessId">
        <AISummary :business-id="businessId" />
      </div>

      <!-- Reviews -->
      <div class="detail-section">
        <div class="detail-section-title">
          顾客评价
          <span class="title-count" v-if="restaurant.reviewCount">{{ restaurant.reviewCount }} 条</span>
          <button class="btn-write-review" @click="openWriteReview">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 5v14M5 12h14"/></svg>
            写评价
          </button>
        </div>

        <div class="review-loading" v-if="reviewsLoading">
          <span class="typing-dot"></span><span class="typing-dot"></span><span class="typing-dot"></span>
        </div>

        <template v-else>
          <div class="review-empty" v-if="reviews.length === 0">
            <p>暂无评价数据</p>
          </div>
          <div class="review-list" v-else>
            <div
              v-for="(r, i) in reviews"
              :key="i"
              class="review-card-detail"
              :class="{ 'is-user-review': r.source === 'user_review' || r.source === 'user' }"
            >
              <div class="rv-avatar">{{ r.avatar || (r.user || '?')[0] }}</div>
              <div class="rv-body">
                <div class="rv-header">
                  <div class="rv-user-row">
                    <span class="rv-user">{{ r.user }}</span>
                    <span class="rv-source-badge" v-if="r.source === 'user_review' || r.source === 'user'">我的评价</span>
                  </div>
                  <div class="rv-stars">
                    <span v-for="s in 5" :key="s" class="rv-star" :class="s <= r.rating ? 'on' : 'off'">★</span>
                  </div>
                </div>
                <p class="rv-text">{{ r.text }}</p>
                <div class="rv-footer">
                  <span class="rv-date">{{ r.date }}</span>
                  <span class="rv-likes" v-if="r.likes">👍 {{ r.likes }}</span>
                  <template v-if="(r.source === 'user_review' || r.source === 'user') && r.review_id">
                    <button class="rv-action-btn" title="编辑" @click="handleEditReview(r)">
                      <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/></svg>
                    </button>
                    <button class="rv-action-btn" title="删除" @click="handleDeleteReview(r)">
                      <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/></svg>
                    </button>
                  </template>
                </div>
              </div>
            </div>
          </div>
        </template>
      </div>

      <!-- Spacer for bottom bar -->
      <div class="detail-bottom-spacer"></div>

      <!-- Bottom Action Bar -->
      <div class="detail-actions">
        <button class="btn-icon" @click="toggleHeart">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="action-heart" :class="{ filled: heartActive }"><path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z"/></svg>
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
            <div class="source-loading" v-if="sourceDetailLoading">
              <span class="typing-dot"></span><span class="typing-dot"></span><span class="typing-dot"></span>
            </div>
            <p class="source-full-text" v-else>{{ selectedSource.text || selectedSource.snippet }}</p>
          </div>
        </div>
      </div>
    </Teleport>

    <!-- Review Form Modal -->
    <ReviewForm
      :businessId="route.params.id || ''"
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
import { useRoute, useRouter } from 'vue-router'
import PhotoStrip from '../components/PhotoStrip.vue'
import DishGrid from '../components/DishGrid.vue'
import ReviewForm from '../components/ReviewForm.vue'
import AISummary from '../components/AISummary.vue'
import { getBusinessDetail } from '../api/modules/business.js'
import { getBusinessReviews, getReviewDetail, deleteReview } from '../api/modules/reviews.js'
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
  components: { PhotoStrip, DishGrid, ReviewForm, AISummary },
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
    const sourceDetailLoading = ref(false)

    async function openSourceDetail(source) {
      selectedSource.value = { ...source }
      // 如果有 review_id，从后端获取完整评价
      if (source.review_id && (!source.text || source.text.length < 100)) {
        sourceDetailLoading.value = true
        try {
          const detail = await getReviewDetail(source.review_id)
          if (detail) {
            selectedSource.value = {
              ...selectedSource.value,
              text: detail.text || selectedSource.value.text,
              rating: detail.rating || selectedSource.value.rating,
              user_name: detail.user_name || selectedSource.value.user_name,
              date: detail.date || selectedSource.value.date,
            }
          }
        } catch {
          // 获取失败时使用已有片段
        } finally {
          sourceDetailLoading.value = false
        }
      }
    }
    const showReviewForm = ref(false)
    const editingReview = ref(null)

    const businessId = computed(() => route.params.id || '')

    const starFloor = computed(() => Math.floor(restaurant.value.rating || 0))
    const starHalf = computed(() => (restaurant.value.rating || 0) % 1 >= 0.5 ? starFloor.value + 1 : 0)
    const ratingPct = computed(() => Math.round(((restaurant.value.rating || 0) / 5) * 100))

    function loadFromStore() {
      const biz = sharedStore.currentBusiness
      if (!biz || !biz.name) return false

      const storePhotos = Array.isArray(biz.photos) ? biz.photos : []
      const firstPhoto = storePhotos[0] || null
      heroBg.value = firstPhoto
        ? `url(${firstPhoto}) center/cover no-repeat`
        : (biz.imgBg || hashGradient(biz.business_id || biz.name || ''))

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

      photos.value = storePhotos.map(url => ({ bg: `url(${url})`, w: '160px', h: '110px' }))
      dishes.value = (biz.dishes || []).slice(0, 8)
      reviews.value = (biz.sources || []).map(r => ({
        avatar: (r.user_name || r.user || '?')[0],
        user: r.user_name || r.user || '匿名用户',
        rating: r.rating || r.stars || 0,
        text: r.text || r.snippet || '',
        date: r.date || '',
        likes: r.useful || 0,
        replies: 0, photoCount: 0, photoBg: [],
        source: r.source || 'ingested',
        review_id: r.review_id || null,
      }))

      return true
    }

    async function loadFromApi(businessId) {
      try {
        const biz = await getBusinessDetail(businessId)
        if (!biz || !biz.name) return false

        const apiPhotos = Array.isArray(biz.photos) ? biz.photos : []
        const firstPhoto = apiPhotos[0] || null
        heroBg.value = firstPhoto
          ? `url(${firstPhoto}) center/cover no-repeat`
          : hashGradient(biz.business_id || biz.name || '')

        restaurant.value = {
          name: biz.name,
          rating: Math.round((biz.rating || 0) * 10) / 10,
          reviewCount: biz.review_count || 0,
          cuisine: (biz.categories || []).join(' · '),
          location: [biz.city, biz.state, biz.address].filter(Boolean).join(' · '),
          price: biz.attributes?.RestaurantsPriceRange2
            ? '$'.repeat(Number(biz.attributes.RestaurantsPriceRange2)) + ' · /人'
            : '--',
          badge: biz.attributes
            ? Object.keys(biz.attributes).filter(k => !k.startsWith('Restaurants'))[0] || ''
            : '',
        }

        photos.value = apiPhotos.map(url => ({ bg: `url(${url})`, w: '160px', h: '110px' }))
        dishes.value = (biz.dishes || []).slice(0, 8)

        reviewsLoading.value = true
        try {
          const revData = await getBusinessReviews(businessId, { pageSize: 10, sortBy: 'date' })
          reviews.value = (revData.items || []).map(r => ({
            avatar: (r.user_name || r.user || '?')[0],
            user: r.user_name || r.user || '匿名用户',
            rating: r.rating || 0,
            text: r.text || '',
            date: r.date || '',
            likes: r.useful || 0,
            source: r.source || 'ingested',
            review_id: r.review_id || null,
          }))
        } catch { /* keep empty */ }
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

      if (loadFromStore()) {
        loading.value = false
        if (businessId) {
          reviewsLoading.value = true
          try {
            const revData = await getBusinessReviews(businessId, { pageSize: 10, sortBy: 'date' })
            if (revData.items && revData.items.length) {
              reviews.value = revData.items.map(r => ({
                avatar: (r.user_name || r.user || '?')[0],
                user: r.user_name || r.user || '匿名用户',
                rating: r.rating || 0,
                text: r.text || '',
                date: r.date || '',
                likes: r.useful || 0,
                source: r.source || 'ingested',
                review_id: r.review_id || null,
              }))
            }
          } catch { /* keep store data */ }
          finally { reviewsLoading.value = false }
        }
        return
      }

      if (businessId) {
        const ok = await loadFromApi(businessId)
        if (ok) { loading.value = false; return }
      }

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

    /* ─── Review Form Handlers ─── */
    function openWriteReview() {
      editingReview.value = null
      showReviewForm.value = true
    }

    function handleEditReview(r) {
      editingReview.value = {
        review_id: r.review_id,
        rating: r.rating,
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
      } catch (err) {
        alert(err.message || '删除失败，请稍后重试')
      }
    }

    function closeReviewForm() {
      showReviewForm.value = false
      editingReview.value = null
    }

    function handleReviewSaved() {
      // Refresh the review list
      const bizId = route.params.id
      if (bizId) {
        reviewsLoading.value = true
        getBusinessReviews(bizId, { pageSize: 10, sortBy: 'date' }).then(revData => {
          reviews.value = (revData.items || []).map(r => ({
            avatar: (r.user_name || r.user || '?')[0],
            user: r.user_name || r.user || '匿名用户',
            rating: r.rating || 0,
            text: r.text || '',
            date: r.date || '',
            likes: r.useful || 0,
            source: r.source || 'ingested',
            review_id: r.review_id || null,
          }))
        }).catch(() => {}).finally(() => { reviewsLoading.value = false })
      }
    }

    function handleReviewDeleted() {
      if (editingReview.value?.review_id) {
        reviews.value = reviews.value.filter(r => r.review_id !== editingReview.value.review_id)
      }
      editingReview.value = null
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
      businessId, restaurant, photos, dishes, reviews, reviewsLoading,
      heroBg, selectedSource, sourceDetailLoading, openSourceDetail, starFloor, starHalf, ratingPct,
      toggleHeart, goToDashboard, loadData,
      sourceStarClass, sourceStarChar,
      showReviewForm, editingReview,
      openWriteReview, handleEditReview, handleDeleteReview,
      closeReviewForm, handleReviewSaved, handleReviewDeleted,
      route,
    }
  },
}
</script>

<style scoped>
/* ── Hero ── */
.detail-hero {
  position: relative; width: 100%; height: 240px; overflow: hidden;
  background: linear-gradient(135deg, #1A1A2E, #3D2E3A);
}
.detail-hero-img {
  width: 100%; height: 100%; opacity: 0.9;
  background-size: cover;
  background-position: center;
  background-repeat: no-repeat;
}
.detail-hero-overlay {
  position: absolute; inset: 0;
  background: linear-gradient(to top, rgba(26,26,46,0.92) 0%, rgba(26,26,46,0.1) 50%, transparent 100%);
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
  padding: var(--space-6);
}
.detail-name {
  font-family: var(--font-display);
  font-size: var(--text-2xl); font-weight: 700;
  color: #fff; line-height: 1.2;
}

/* ── Rating Card ── */
.rating-card {
  margin: -16px var(--space-4) 0;
  background: var(--card-bg);
  border-radius: var(--radius-lg);
  padding: var(--space-4);
  box-shadow: var(--shadow-md);
  position: relative;
  z-index: 2;
}
.rating-main {
  display: flex; align-items: center; gap: var(--space-4);
  margin-bottom: var(--space-3);
}
.rating-big {
  font-family: var(--font-display);
  font-size: 3rem; font-weight: 700;
  color: var(--amber); line-height: 1;
}
.rating-right { flex: 1; }
.rating-stars {
  display: flex; gap: 2px; margin-bottom: 4px;
}
.rstar { font-size: 1rem; }
.rstar.full { color: var(--amber); }
.rstar.half { color: var(--amber); opacity: 0.5; }
.rstar.empty { color: #DDD; }
.rating-sub {
  font-size: var(--text-xs); color: var(--ink-muted);
}
.rating-bar-wrap {
  height: 4px; background: #F0EBE5;
  border-radius: 2px; overflow: hidden;
}
.rating-bar-fill {
  height: 100%; background: linear-gradient(90deg, var(--amber), var(--coral));
  border-radius: 2px; transition: width 0.6s var(--ease-out);
}

/* ── Info Section ── */
.info-section {
  padding: var(--space-4);
  display: flex; flex-direction: column; gap: var(--space-3);
}
.info-row {
  display: flex; align-items: flex-start; gap: var(--space-3);
  padding: var(--space-2) 0;
}
.info-icon { font-size: 1.125rem; flex-shrink: 0; margin-top: 1px; }
.info-content {
  display: flex; flex-direction: column; gap: 2px;
  min-width: 0;
}
.info-label {
  font-size: var(--text-xs); color: var(--ink-muted);
  font-weight: 500;
}
.info-value {
  font-size: var(--text-sm); color: var(--ink);
  line-height: var(--leading-relaxed);
  word-break: break-all;
}

/* ── Sections ── */
.detail-section {
  padding: var(--space-4) var(--space-4) var(--space-5);
  border-bottom: 6px solid var(--warm-bg);
}
.detail-section:last-child { border-bottom: none; }
.detail-section-title {
  font-family: var(--font-display);
  font-size: var(--text-lg); font-weight: 700;
  color: var(--ink); margin-bottom: var(--space-3);
  display: flex; align-items: baseline; gap: var(--space-2);
}
.title-count {
  font-family: var(--font-body);
  font-size: var(--text-xs); color: var(--ink-muted);
  font-weight: 400;
}

/* ── Reviews ── */
.btn-write-review {
  margin-left: auto;
  display: flex;
  align-items: center;
  gap: 4px;
  padding: var(--space-1) var(--space-3);
  background: var(--coral);
  color: #fff;
  border-radius: var(--radius-full);
  font-size: var(--text-xs);
  font-weight: 600;
  transition: background var(--duration-fast);
  flex-shrink: 0;
}
.btn-write-review:hover { background: var(--coral-deep); }
.btn-write-review svg { flex-shrink: 0; }

.review-list {
  display: flex; flex-direction: column;
}
.review-card-detail {
  display: flex; gap: var(--space-3);
  padding: var(--space-3) 0;
  border-bottom: 1px solid var(--border);
}
.review-card-detail:last-child { border-bottom: none; }
.review-card-detail.is-user-review {
  background: var(--coral-pale);
  border-radius: var(--radius-md);
  padding: var(--space-3);
  margin: 0 calc(-1 * var(--space-1));
  border-bottom: none;
}
.rv-avatar {
  width: 36px; height: 36px; border-radius: 50%;
  flex-shrink: 0;
  background: linear-gradient(135deg, var(--coral-pale), #FFE0D0);
  display: flex; align-items: center; justify-content: center;
  font-size: var(--text-sm); font-weight: 700; color: var(--coral-deep);
}
.rv-body { flex: 1; min-width: 0; }
.rv-header {
  display: flex; align-items: center; justify-content: space-between;
  margin-bottom: 4px;
}
.rv-user {
  font-size: var(--text-sm); font-weight: 600; color: var(--ink);
}
.rv-user-row {
  display: flex; align-items: center; gap: var(--space-2);
}
.rv-source-badge {
  font-size: 0.625rem;
  padding: 1px 6px;
  background: var(--coral);
  color: #fff;
  border-radius: var(--radius-full);
  font-weight: 600;
}
.rv-stars {
  display: flex; gap: 1px; font-size: 0.625rem;
}
.rv-star.on { color: var(--amber); }
.rv-star.off { color: #DDD; }
.rv-text {
  font-size: var(--text-sm); color: var(--ink-light);
  line-height: var(--leading-relaxed); margin-bottom: var(--space-1);
}
.rv-footer {
  display: flex; align-items: center; gap: var(--space-4);
  font-size: var(--text-xs); color: var(--ink-muted);
}
.rv-likes { color: var(--coral); }
.rv-action-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 24px;
  height: 24px;
  border-radius: 50%;
  color: var(--ink-muted);
  transition: all var(--duration-fast);
  margin-left: 2px;
}
.rv-action-btn:hover {
  background: var(--coral-pale);
  color: var(--coral);
}

.review-loading {
  display: flex; align-items: center; gap: var(--space-1);
  padding: var(--space-6); justify-content: center;
}
.review-empty { text-align: center; padding: var(--space-6); color: var(--ink-muted); font-size: var(--text-sm); }

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

/* ── Bottom Bar ── */
.detail-bottom-spacer { height: 80px; }
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
.source-loading { display: flex; align-items: center; gap: 4px; justify-content: center; padding: var(--space-4); }

@media (min-width: 768px) { .detail-hero { height: 320px; } }
@media (min-width: 1024px) { .page-detail { max-width: 900px; margin: 0 auto; } }
</style>
