<template>
  <div class="page-list">
    <TopNav>
      <template #left>
        <div class="back-row">
          <button class="back-btn" @click="$router.back()">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M19 12H5M12 19l-7-7 7-7"/></svg>
            返回
          </button>
        </div>
      </template>
      <template #center>
        <span class="page-title">美食商家</span>
      </template>
      <template #right>
        <div style="width:48px;"></div>
      </template>
    </TopNav>

    <!-- Filter Bar -->
    <div class="stagger-1">
      <FilterBar
        :active-chip="activeChip"
        :active-tags="activeTags"
        :total="total"
        @select="activeChip = $event"
        @remove-tag="removeTag"
      />
    </div>

    <!-- Loading -->
    <div class="state-container stagger-2" v-if="loading">
      <div class="loading-spinner"></div>
      <p class="state-text">正在加载商家列表...</p>
    </div>

    <!-- Error -->
    <div class="state-container stagger-2" v-else-if="error">
      <div class="state-icon">⚠️</div>
      <h3 class="state-title">加载失败</h3>
      <p class="state-text">{{ error }}</p>
      <button class="state-retry" @click="fetchList()">重新加载</button>
    </div>

    <!-- Empty -->
    <div class="state-container stagger-2" v-else-if="restaurants.length === 0">
      <div class="state-icon">🍽️</div>
      <h3 class="state-title">暂无商家</h3>
      <p class="state-text">商家列表接口尚未就绪，请通过首页 AI 助手探索美食推荐</p>
      <button class="state-retry" @click="$router.push('/')">前往 AI 助手</button>
    </div>

    <!-- Restaurant List -->
    <div class="restaurant-list" v-else>
      <div class="list-header">
        <span class="list-count">共 {{ total }} 家商家</span>
      </div>
      <div
        v-for="(r, idx) in restaurants"
        :key="r.id"
        :class="'stagger-' + Math.min(idx + 2, 10)"
      >
        <RestaurantCard v-bind="r" @click="goToDetail(r)" />
      </div>

      <!-- Pagination -->
      <div class="pagination" v-if="totalPages > 1">
        <button class="page-btn" :disabled="page <= 1" @click="goToPage(page - 1)">上一页</button>
        <span class="page-info">{{ page }} / {{ totalPages }}</span>
        <button class="page-btn" :disabled="page >= totalPages" @click="goToPage(page + 1)">下一页</button>
      </div>
    </div>
  </div>
</template>

<script>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import TopNav from '../components/TopNav.vue'
import FilterBar from '../components/FilterBar.vue'
import RestaurantCard from '../components/RestaurantCard.vue'
import { getBusinesses } from '../api/modules/business.js'
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
  name: 'FoodListPage',
  components: { TopNav, FilterBar, RestaurantCard },
  setup() {
    const router = useRouter()

    const activeChip = ref('🍽️ 菜系')
    const activeTags = ref([])
    const restaurants = ref([])
    const total = ref(0)
    const page = ref(1)
    const pageSize = 20
    const loading = ref(false)
    const error = ref(null)

    const totalPages = computed(() => Math.max(1, Math.ceil(total.value / pageSize)))

    function mapBiz(biz) {
      return {
        id: biz.business_id,
        name: biz.name,
        rating: Math.round((biz.rating || 0) * 10) / 10,
        tags: (biz.categories || []).slice(0, 4),
        price: (biz.attributes?.RestaurantsPriceRange2)
          ? '$'.repeat(Number(biz.attributes.RestaurantsPriceRange2) || 1) + ' · /人'
          : '--',
        area: [biz.city, biz.state].filter(Boolean).join(' · ') || '--',
        distance: '--',
        review: `${biz.review_count || 0} 条评价`,
        imgBg: hashGradient(biz.business_id || biz.name || ''),
      }
    }

    async function fetchList(params = {}) {
      loading.value = true
      error.value = null
      try {
        const result = await getBusinesses({
          page: page.value,
          pageSize,
          category: activeChip.value !== '🍽️ 菜系' ? activeChip.value : undefined,
          keyword: activeTags.value[0] || undefined,
          ...params,
        })
        restaurants.value = (result.items || []).map(mapBiz)
        total.value = result.total || 0
        sharedStore.setBusinessList(restaurants.value)
      } catch (e) {
        error.value = e.message || '加载失败'
        restaurants.value = []
      } finally {
        loading.value = false
      }
    }

    function removeTag(tag) {
      activeTags.value = activeTags.value.filter(t => t !== tag)
      page.value = 1
      fetchList()
    }

    function goToPage(p) {
      page.value = p
      fetchList()
      window.scrollTo({ top: 0, behavior: 'smooth' })
    }

    function goToDetail(r) {
      sharedStore.setBusiness({
        business_id: r.id,
        name: r.name,
        rating: r.rating,
        review_count: parseInt(r.review) || 0,
        categories: r.tags,
        address: r.area,
        city: r.area?.split(' · ')[0] || '',
        state: r.area?.split(' · ')[1] || '',
        imgBg: r.imgBg,
      })
      router.push(`/detail/${encodeURIComponent(r.id)}`)
    }

    onMounted(() => fetchList())

    return {
      activeChip, activeTags, restaurants, total, page, totalPages,
      loading, error,
      removeTag, goToPage, goToDetail, fetchList,
    }
  },
}
</script>

<style scoped>
.page-list { padding-bottom: calc(var(--tab-height) + var(--space-8)); }

.back-row { display: flex; align-items: center; justify-content: space-between; width: 100%; }
.back-btn {
  display: flex; align-items: center; gap: var(--space-1);
  font-size: var(--text-sm); color: var(--ink-light);
  padding: var(--space-2) 0;
  transition: color var(--duration-fast);
}
.back-btn:hover { color: var(--coral); }
.back-btn svg { width: 18px; height: 18px; }

.page-title { font-weight: 600; font-family: var(--font-display); }

/* ── States ── */
.state-container {
  text-align: center; padding: var(--space-16) var(--space-4);
  animation: fadeIn 0.5s ease;
}
.state-icon { font-size: 3rem; margin-bottom: var(--space-4); }
.state-title {
  font-family: var(--font-display); font-size: var(--text-xl);
  font-weight: 700; margin-bottom: var(--space-2); color: var(--ink);
}
.state-text { font-size: var(--text-sm); color: var(--ink-muted); margin-bottom: var(--space-6); }
.state-retry {
  padding: var(--space-2) var(--space-6);
  background: var(--coral); color: #fff;
  border-radius: var(--radius-full);
  font-size: var(--text-sm); font-weight: 600;
  transition: background var(--duration-fast);
}
.state-retry:hover { background: var(--coral-deep); }

.loading-spinner {
  width: 36px; height: 36px;
  border: 3px solid var(--border); border-top-color: var(--coral);
  border-radius: 50%; margin: 0 auto var(--space-4);
  animation: spin 0.8s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }

/* ── List ── */
.restaurant-list { padding: 0 var(--space-4); display: flex; flex-direction: column; gap: var(--space-3); }
.list-header { padding: var(--space-1) 0; }
.list-count { font-size: var(--text-xs); color: var(--ink-muted); }

/* ── Pagination ── */
.pagination {
  display: flex; align-items: center; justify-content: center;
  gap: var(--space-4); padding: var(--space-4) 0;
}
.page-btn {
  padding: var(--space-2) var(--space-4);
  border: 1px solid var(--border); border-radius: var(--radius-full);
  font-size: var(--text-sm); color: var(--ink-light);
  transition: all var(--duration-fast);
}
.page-btn:hover:not(:disabled) { border-color: var(--coral); color: var(--coral); }
.page-btn:disabled { opacity: 0.4; cursor: not-allowed; }
.page-info { font-size: var(--text-sm); color: var(--ink-muted); }

@media (min-width: 768px) { .restaurant-list { padding: 0 var(--space-6); } }
@media (min-width: 1024px) { .page-list { max-width: 900px; margin: 0 auto; } }
</style>
