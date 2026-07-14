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
        <span class="page-title">美食</span>
      </template>
      <template #right>
        <div style="width:48px;"></div>
      </template>
    </TopNav>

    <div class="stagger-1">
      <FilterBar
        :active-chip="activeChip"
        :active-tags="activeTags"
        :total="restaurants.length"
        @select="activeChip = $event"
        @remove-tag="removeTag"
      />
    </div>

    <div class="restaurant-list">
      <div
        v-for="(r, idx) in restaurants"
        :key="r.name"
        :class="'stagger-' + Math.min(idx + 2, 10)"
      >
        <RestaurantCard v-bind="r" @click="$router.push('/detail')" />
      </div>
    </div>
  </div>
</template>

<script>
import { ref, onMounted } from 'vue'
import TopNav from '../components/TopNav.vue'
import FilterBar from '../components/FilterBar.vue'
import RestaurantCard from '../components/RestaurantCard.vue'
import { getBusinesses } from '../api/modules/business.js'

export default {
  name: 'FoodListPage',
  components: { TopNav, FilterBar, RestaurantCard },
  setup() {
    const activeChip = ref('🍽️ 菜系')
    const activeTags = ref([])
    const restaurants = ref([])
    const total = ref(0)
    const loading = ref(true)
    const error = ref(null)

    async function fetchRestaurants(params = {}) {
      loading.value = true
      error.value = null
      try {
        const result = await getBusinesses({ pageSize: 20, ...params })
        restaurants.value = (result.items || []).map(biz => ({
          id: biz.business_id,
          name: biz.name,
          rating: Math.round(biz.rating * 10) / 10,
          tags: biz.categories || [],
          price: '--',
          area: biz.city || biz.state || '',
          distance: '--',
          review: `${biz.review_count}条评论`,
          imgBg: 'linear-gradient(135deg, #3D2E1A, #5D4E3A)',
        }))
        total.value = result.total || 0
      } catch (e) {
        error.value = e.message
      } finally {
        loading.value = false
      }
    }

    function removeTag(tag) {
      activeTags.value = activeTags.value.filter(t => t !== tag)
      fetchRestaurants({ keyword: activeTags.value[0] })
    }

    onMounted(() => fetchRestaurants())

    return {
      activeChip, activeTags, restaurants, total, loading, error,
      removeTag,
    }
  },
}
</script>

<style scoped>
.back-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  width: 100%;
}
.back-btn {
  display: flex; align-items: center; gap: var(--space-1);
  font-size: var(--text-sm); color: var(--ink-light);
  padding: var(--space-2) 0;
  transition: color var(--duration-fast);
}
.back-btn:hover { color: var(--coral); }
.back-btn svg { width: 18px; height: 18px; }

.page-title { font-weight: 600; }

.restaurant-list { padding: 0 var(--space-4); display: flex; flex-direction: column; gap: var(--space-3); }
</style>
