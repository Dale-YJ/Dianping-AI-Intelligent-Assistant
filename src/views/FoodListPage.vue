<template>
  <div class="page-discover">
    <!-- Header -->
    <div class="discover-header">
      <div class="header-top">
        <h1 class="header-title">发现美食</h1>
        <span class="header-sub" v-if="!loading">{{ total }} 家商家</span>
      </div>
      <!-- Search -->
      <div class="search-wrap">
        <svg class="search-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="8"/><path d="M21 21l-4.35-4.35"/></svg>
        <input
          class="search-input"
          v-model="searchText"
          placeholder="搜索商家名称、菜系..."
          @keyup.enter="doSearch"
        />
        <button class="search-clear" v-if="searchText" @click="clearSearch">✕</button>
      </div>
    </div>

    <!-- Category Chips — 按菜品来源国家地区分组 -->
    <div class="category-strip">
      <button
        v-for="cat in categories"
        :key="cat.value"
        class="cat-chip"
        :class="{ active: activeCategory === cat.value }"
        @click="selectCategory(cat.value)"
      ><span class="cat-flag">{{ cat.flag }}</span>{{ cat.label }}</button>
    </div>

    <!-- City Chips -->
    <div class="city-strip" v-if="cities.length > 1" :class="{ expanded: cityExpanded }">
      <button class="city-toggle" @click="cityExpanded = !cityExpanded">
        <svg class="city-pin" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z"/><circle cx="12" cy="10" r="3"/></svg>
        <span class="city-current">{{ activeCity || '全部城市' }}</span>
        <svg class="city-chevron" :class="{ open: cityExpanded }" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="6 9 12 15 18 9"/></svg>
      </button>
      <div class="city-list">
        <button class="city-chip" :class="{ active: activeCity === '' }" @click="selectCity(''); cityExpanded = false">全部</button>
        <button
          v-for="c in cities"
          :key="c"
          class="city-chip"
          :class="{ active: activeCity === c, china: isChinaCity(c) }"
          @click="selectCity(c); cityExpanded = false"
        >
          <span class="city-dot" v-if="isChinaCity(c) && activeCity !== c"></span>
          {{ c }}
        </button>
      </div>
    </div>

    <!-- Sort & Filter Row -->
    <div class="toolbar">
      <div class="sort-group">
        <button
          v-for="s in sorts"
          :key="s.value"
          class="sort-btn"
          :class="{ active: activeSort === s.value }"
          @click="selectSort(s.value)"
        >{{ s.label }}</button>
      </div>
      <button class="filter-btn" :class="{ on: minRating > 0 }" @click="toggleRatingFilter">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="14" height="14"><polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/></svg>
        {{ minRating > 0 ? '≥ ' + minRating + '分' : '评分' }}
      </button>
    </div>

    <!-- Loading Skeleton -->
    <div class="skeleton-list" v-if="loading">
      <div v-for="i in 5" :key="i" class="sk-card">
        <div class="sk-img skeleton"></div>
        <div class="sk-body">
          <div class="sk-line w70 skeleton"></div>
          <div class="sk-line w40 skeleton"></div>
          <div class="sk-line w90 skeleton"></div>
        </div>
      </div>
    </div>

    <!-- Error -->
    <div class="state-box" v-else-if="error">
      <span class="state-emoji">⚠️</span>
      <p class="state-msg">{{ error }}</p>
      <button class="state-retry" @click="fetchList()">重新加载</button>
    </div>

    <!-- Empty -->
    <div class="state-box" v-else-if="restaurants.length === 0">
      <span class="state-emoji">🔍</span>
      <p class="state-msg">没有找到匹配的商家</p>
      <p class="state-hint">试试更换筛选条件或搜索关键词</p>
    </div>

    <!-- Restaurant List -->
    <div class="restaurant-list" v-else>
      <div
        v-for="(r, idx) in restaurants"
        :key="r.id"
        :style="{ animationDelay: (idx * 0.05) + 's' }"
        class="list-item"
      >
        <RestaurantCard v-bind="r" @click="goToDetail(r)" />
      </div>
    </div>

    <!-- Pagination -->
    <div class="pagination" v-if="totalPages > 1 && !loading">
      <button class="page-btn" :disabled="page <= 1" @click="goToPage(page - 1)">‹ 上一页</button>
      <span class="page-info">{{ page }} / {{ totalPages }}</span>
      <button class="page-btn" :disabled="page >= totalPages" @click="goToPage(page + 1)">下一页 ›</button>
    </div>

    <div class="list-bottom-spacer"></div>
  </div>
</template>

<script>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import RestaurantCard from '../components/RestaurantCard.vue'
import { getBusinessesWithReviews } from '../api/modules/business.js'
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

// 按菜品来源国家地区组织的统一分类
const CATEGORY_LIST = [
  // ── 中国各大菜系 ──
  { label: '全部', value: '', flag: '🍽️' },
  { label: '火锅', value: 'hotpot', flag: '🇨🇳', match: ['火锅', 'hot pot', '串串香', '钵钵鸡'] },
  { label: '川菜', value: 'sichuan', flag: '🇨🇳', match: ['川菜', 'sichuan', 'szechuan', '四川'] },
  { label: '粤菜', value: 'cantonese', flag: '🇨🇳', match: ['粤菜', '粤式', '广州菜', '潮汕', '顺德', '茶餐厅', '茶点', '广东', 'cantonese', 'dim sum'] },
  { label: '本帮江浙', value: 'jiangzhe', flag: '🇨🇳', match: ['本帮菜', '淮扬菜', '苏浙菜', '浙菜', '上海', 'shanghai'] },
  { label: '湘菜', value: 'hunan', flag: '🇨🇳', match: ['湘菜', 'hunan', '湖南'] },
  { label: '云南菜', value: 'yunnan', flag: '🇨🇳', match: ['云南菜', '滇菜', '云南'] },
  { label: '京菜鲁菜', value: 'beijing-lu', flag: '🇨🇳', match: ['京菜', '鲁菜', '烤鸭', '内蒙', '私房菜', '农家菜'] },
  { label: '西北新疆', value: 'northwest', flag: '🇨🇳', match: ['新疆菜', '西北', '陕西', '西安', '兰州'] },
  { label: '闽菜', value: 'fujian', flag: '🇨🇳', match: ['福建菜', '闽菜', '福建'] },
  { label: '小吃快餐', value: 'snacks', flag: '🇨🇳', match: ['快餐', '面馆', '小吃', '粥店', '简餐', '牛杂', '豆花', '特色菜'] },
  { label: '甜点饮品', value: 'dessert-cn', flag: '🇨🇳', match: ['甜品', '咖啡', '茶饮', '果汁', '奶茶', '冰淇淋'] },
  { label: '海鲜', value: 'seafood-cn', flag: '🇨🇳', match: ['海鲜', '蟹', '虾', '海鲜火锅'] },
  { label: '素食', value: 'vegetarian', flag: '🇨🇳', match: ['素食', 'vegetarian', 'vegan'] },
  { label: '自助餐', value: 'buffet', flag: '🇨🇳', match: ['自助', 'buffet'] },

  // ── 日本 ──
  { label: '日本料理', value: 'japanese', flag: '🇯🇵', match: ['日本料理', '日料', 'japanese', 'sushi', 'ramen', '居酒屋', 'izakaya', 'yakitori'] },

  // ── 韩国 ──
  { label: '韩国料理', value: 'korean', flag: '🇰🇷', match: ['韩式', '韩餐', '韩国', 'korean', 'bbq'] },

  // ── 意大利 ──
  { label: '意大利菜', value: 'italian', flag: '🇮🇹', match: ['意大利菜', 'italian', 'pizza', 'pasta', '比萨'] },

  // ── 法国 ──
  { label: '法国菜', value: 'french', flag: '🇫🇷', match: ['法国菜', 'french', 'bistro', 'brasserie'] },

  // ── 美国 ──
  { label: '美式', value: 'american', flag: '🇺🇸', match: ['american', 'burgers', 'steakhouse', 'bbq', 'southern', 'diner', '牛排'] },

  // ── 墨西哥 ──
  { label: '墨西哥菜', value: 'mexican', flag: '🇲🇽', match: ['mexican', 'tacos', 'latin', '墨西哥'] },

  // ── 印度 ──
  { label: '印度菜', value: 'indian', flag: '🇮🇳', match: ['indian', 'curry', '印度'] },

  // ── 东南亚 ──
  { label: '东南亚菜', value: 'southeast', flag: '🇹🇭', match: ['泰国菜', '越南', 'pho', 'thai', 'vietnamese', '东南亚'] },

  // ── 地中海 ──
  { label: '地中海', value: 'mediterranean', flag: '🇬🇷', match: ['mediterranean', 'greek', 'middle eastern', 'turkish'] },

  // ── 其他 ──
  { label: '西餐', value: 'western', flag: '🍴', match: ['西餐'] },
  { label: '酒吧', value: 'bars', flag: '🍸', match: ['bar', 'pub', 'cocktail', 'wine', 'beer', '酒吧', '清吧', '精酿'] },
  { label: '甜点咖啡', value: 'dessert', flag: '☕', match: ['dessert', 'coffee', 'cafe', 'bakery', 'bubble tea', 'ice cream'] },
  { label: '早餐', value: 'breakfast', flag: '🥞', match: ['breakfast', 'brunch', 'diner'] },
  { label: '海鲜', value: 'seafood', flag: '🦞', match: ['seafood', 'oyster', 'fish'] },
]

const SORTS = [
  { label: '综合排序', value: '' },
  { label: '评分最高', value: 'rating' },
  { label: '评价最多', value: 'review_count' },
]

export default {
  name: 'FoodListPage',
  components: { RestaurantCard },
  setup() {
    const router = useRouter()

    const searchText = ref('')
    const activeCategory = ref('')
    const activeSort = ref('')
    const minRating = ref(0)
    const restaurants = ref([])
    const total = ref(0)
    const page = ref(1)
    const pageSize = 20
    const loading = ref(false)
    const error = ref(null)

    // 全量数据缓存 + 客户端筛选/排序/分页
    let allBusinesses = []

    // 城市 & 国家判断
    const CHINA_CITIES = ['北京', '成都', '广州', '上海']
    const categories = CATEGORY_LIST
    const sorts = SORTS
    const totalPages = computed(() => Math.max(1, Math.ceil(total.value / pageSize)))

    // 城市筛选
    const activeCity = ref('')
    const cityExpanded = ref(false)
    const cities = ref([])
    function updateCities() {
      const set = new Set(allBusinesses.map(b => b.city).filter(Boolean))
      const cn = CHINA_CITIES.filter(c => set.has(c))
      const others = [...set].filter(c => !CHINA_CITIES.includes(c)).sort()
      cities.value = [...cn, ...others]
    }

    // 判断商家是否来自中国
    function isChinaBiz(biz) {
      return (biz.source === 'dianping') || CHINA_CITIES.includes(biz.city)
    }

    function mapBiz(biz) {
      const firstPhoto = (Array.isArray(biz.photos) && biz.photos[0]) || null
      return {
        id: biz.business_id,
        name: biz.name,
        rating: Math.round((biz.rating || 0) * 10) / 10,
        tags: (biz.categories || []).flatMap(c => c.split('|')).map(c => c.trim()).filter(Boolean).slice(0, 4),
        price: (biz.attributes?.RestaurantsPriceRange2)
          ? '$'.repeat(Number(biz.attributes.RestaurantsPriceRange2) || 1) + ' · /人'
          : '--',
        area: [biz.city, biz.state].filter(Boolean).join(' · ') || '--',
        distance: '--',
        review: `${biz.review_count || 0} 条评价`,
        imgBg: firstPhoto
          ? `url(${firstPhoto}) center/cover no-repeat`
          : hashGradient(biz.business_id || biz.name || ''),
      }
    }

    /** 客户端筛选 + 排序 + 分页 */
    function applyFilters() {
      let items = [...allBusinesses]

      // 评分筛选
      if (minRating.value > 0) {
        items = items.filter(biz => (biz.rating || 0) >= minRating.value)
      }

      // 搜索
      const kw = searchText.value.trim().toLowerCase()
      if (kw) {
        items = items.filter(biz =>
          (biz.name || '').toLowerCase().includes(kw) ||
          (biz.categories || []).some(c => c.toLowerCase().includes(kw)) ||
          (biz.address || '').toLowerCase().includes(kw) ||
          (biz.city || '').toLowerCase().includes(kw)
        )
      }

      // 细分类别筛选
      const cat = categories.find(c => c.value === activeCategory.value)
      if (cat && cat.match) {
        items = items.filter(biz => {
          const lower = (biz.categories || []).map(c => c.toLowerCase())
          return cat.match.some(kw => lower.some(lc => lc.includes(kw)))
        })
      }

      // 城市筛选
      if (activeCity.value) {
        items = items.filter(biz => (biz.city || '') === activeCity.value)
      }

      // 排序：中文商家优先，然后按评分/评价数
      const sortFn = (a, b) => {
        const aCn = isChinaBiz(a) ? 0 : 1
        const bCn = isChinaBiz(b) ? 0 : 1
        if (aCn !== bCn) return aCn - bCn
        if (activeSort.value === 'review_count') return (b.review_count || 0) - (a.review_count || 0)
        return (b.rating || 0) - (a.rating || 0)
      }
      items.sort(sortFn)

      total.value = items.length

      // 分页
      const start = (page.value - 1) * pageSize
      restaurants.value = items.slice(start, start + pageSize).map(mapBiz)
    }

    async function fetchList() {
      loading.value = true
      error.value = null
      try {
        const result = await getBusinessesWithReviews({
          page: 1,
          pageSize: 10000,
        })
        allBusinesses = result.items || []
        updateCities()
        applyFilters()
      } catch (e) {
        error.value = e.message || '加载失败'
        restaurants.value = []
      } finally {
        loading.value = false
      }
    }

    function refresh() {
      page.value = 1
      applyFilters()
    }

    function selectCategory(val) {
      activeCategory.value = activeCategory.value === val ? '' : val
      refresh()
    }

    function selectCity(val) {
      activeCity.value = activeCity.value === val ? '' : val
      refresh()
    }

    function isChinaCity(c) {
      return CHINA_CITIES.includes(c)
    }

    function selectSort(val) {
      activeSort.value = activeSort.value === val ? '' : val
      refresh()
    }

    function toggleRatingFilter() {
      if (minRating.value === 0) minRating.value = 4
      else if (minRating.value === 4) minRating.value = 3
      else minRating.value = 0
      refresh()
    }

    function doSearch() { refresh() }

    function clearSearch() {
      searchText.value = ''
      refresh()
    }

    function goToPage(p) {
      page.value = p
      applyFilters()
      document.querySelector('.discover-header')?.scrollIntoView({ behavior: 'smooth' })
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
      searchText, activeCategory, activeSort, minRating,
      restaurants, total, page, totalPages, loading, error,
      categories, sorts, activeCity, cities, cityExpanded,
      selectCategory, selectSort, toggleRatingFilter, selectCity, isChinaCity,
      doSearch, clearSearch, goToPage, goToDetail, fetchList,
    }
  },
}
</script>

<style scoped>
.page-discover {
  padding-bottom: calc(var(--tab-height) + var(--space-4));
}

/* ── Header ── */
.discover-header {
  padding: var(--space-4) var(--space-4) var(--space-3);
  position: sticky; top: 0; z-index: 50;
  background: rgba(255,255,255,0.92);
  backdrop-filter: blur(12px);
}
.header-top {
  display: flex; align-items: baseline; justify-content: space-between;
  margin-bottom: var(--space-3);
}
.header-title {
  font-family: var(--font-display);
  font-size: var(--text-2xl); font-weight: 700;
  color: var(--ink);
}
.header-sub { font-size: var(--text-xs); color: var(--ink-muted); }

/* ── Search ── */
.search-wrap {
  display: flex; align-items: center; gap: var(--space-2);
  background: #F5F3F0; border-radius: var(--radius-lg);
  padding: 0 var(--space-3); height: 44px;
}
.search-icon { width: 18px; height: 18px; color: var(--ink-muted); flex-shrink: 0; }
.search-input {
  flex: 1; border: none; background: none; outline: none;
  font-size: var(--text-sm); color: var(--ink);
}
.search-input::placeholder { color: var(--ink-muted); }
.search-clear {
  width: 24px; height: 24px; border-radius: 50%;
  background: var(--border); font-size: 0.75rem;
  display: flex; align-items: center; justify-content: center;
  color: var(--ink-muted); flex-shrink: 0;
  transition: background var(--duration-fast);
}
.search-clear:hover { background: var(--border-strong); }

/* ── Category Strip ── */
.category-strip {
  display: flex; gap: var(--space-2);
  padding: var(--space-3) var(--space-4);
  overflow-x: auto; scrollbar-width: none;
}
.category-strip::-webkit-scrollbar { display: none; }
.cat-chip {
  flex-shrink: 0;
  display: flex; align-items: center; gap: 4px;
  padding: var(--space-1) var(--space-3);
  border-radius: var(--radius-full);
  font-size: var(--text-sm); color: var(--ink-light);
  background: #F5F3F0; transition: all var(--duration-fast);
  white-space: nowrap;
}
.cat-flag { font-size: 0.75rem; line-height: 1; }
.cat-chip:hover { background: var(--coral-pale); color: var(--coral); }
.cat-chip.active { background: var(--coral); color: #fff; font-weight: 600; }

/* ── City Strip ── */
.city-strip {
  padding: 0 var(--space-4) var(--space-3);
  position: relative;
}
.city-toggle {
  display: flex; align-items: center; gap: 6px;
  padding: 8px 14px;
  border-radius: var(--radius-full);
  font-size: var(--text-sm); font-weight: 600;
  color: var(--ink-light);
  background: #F6F5F3;
  transition: all 0.2s ease;
  width: fit-content;
}
.city-toggle:hover { background: var(--coral-pale); color: var(--coral); }
.city-strip.expanded .city-toggle {
  background: var(--coral-pale); color: var(--coral);
}
.city-pin { width: 16px; height: 16px; flex-shrink: 0; }
.city-current { min-width: 3em; text-align: left; }
.city-chevron { width: 14px; height: 14px; transition: transform 0.25s ease; }
.city-chevron.open { transform: rotate(180deg); }

/* Dropdown list */
.city-list {
  display: none;
  flex-wrap: wrap;
  gap: 8px;
  padding-top: var(--space-3);
}
.city-strip.expanded .city-list {
  display: flex;
  animation: cityDropIn 0.25s var(--ease-out);
}
@keyframes cityDropIn {
  from { opacity: 0; transform: translateY(-8px); }
  to   { opacity: 1; transform: translateY(0); }
}

/* City chips inside dropdown */
.city-chip {
  position: relative;
  flex-shrink: 0;
  display: flex; align-items: center; gap: 4px;
  padding: 6px 14px;
  border-radius: var(--radius-full);
  font-size: var(--text-sm); color: var(--ink-light);
  background: #F6F5F3;
  transition: all 0.2s ease;
  white-space: nowrap;
  font-weight: 500;
}
.city-chip:hover { background: var(--coral-pale); color: var(--coral); }
.city-chip.active {
  background: var(--coral);
  color: #fff;
  font-weight: 700;
  box-shadow: 0 2px 8px rgba(255, 107, 53, 0.25);
}
.city-dot {
  width: 5px; height: 5px;
  border-radius: 50%;
  background: var(--coral);
  flex-shrink: 0;
}
.city-chip.active .city-dot {
  background: #fff;
  opacity: 0.6;
}

/* ── Toolbar ── */
.toolbar {
  display: flex; align-items: center; justify-content: space-between;
  padding: 0 var(--space-4) var(--space-3);
}
.sort-group { display: flex; gap: var(--space-1); }
.sort-btn {
  padding: 4px var(--space-3); border-radius: var(--radius-full);
  font-size: var(--text-xs); color: var(--ink-muted);
  transition: all var(--duration-fast);
}
.sort-btn:hover { color: var(--coral); }
.sort-btn.active { background: var(--coral-pale); color: var(--coral); font-weight: 600; }
.filter-btn {
  display: flex; align-items: center; gap: 4px;
  padding: 4px var(--space-3); border-radius: var(--radius-full);
  font-size: var(--text-xs); color: var(--ink-muted);
  border: 1px solid var(--border); transition: all var(--duration-fast);
}
.filter-btn:hover { border-color: var(--coral); color: var(--coral); }
.filter-btn.on { background: var(--coral-pale); border-color: var(--coral); color: var(--coral); font-weight: 600; }

/* ── Skeleton ── */
.skeleton-list {
  padding: 0 var(--space-4); display: flex; flex-direction: column; gap: var(--space-3);
}
.sk-card {
  display: flex; gap: var(--space-3); padding: var(--space-3);
  background: var(--card-bg); border-radius: var(--radius-lg);
  border: 1px solid var(--border);
}
.sk-img {
  width: 110px; height: 110px; border-radius: var(--radius-md); flex-shrink: 0;
}
.sk-body { flex: 1; display: flex; flex-direction: column; gap: var(--space-2); justify-content: center; }
.sk-line { height: 14px; border-radius: 4px; }
.sk-line.w70 { width: 70%; }
.sk-line.w40 { width: 40%; }
.sk-line.w90 { width: 90%; }

/* ── State ── */
.state-box { text-align: center; padding: var(--space-16) var(--space-4); }
.state-emoji { font-size: 3rem; display: block; margin-bottom: var(--space-4); }
.state-msg { font-size: var(--text-md); color: var(--ink); font-weight: 600; margin-bottom: var(--space-2); }
.state-hint { font-size: var(--text-sm); color: var(--ink-muted); margin-bottom: var(--space-4); }
.state-retry {
  padding: var(--space-2) var(--space-6);
  background: var(--coral); color: #fff;
  border-radius: var(--radius-full); font-size: var(--text-sm);
  font-weight: 600; transition: background var(--duration-fast);
}
.state-retry:hover { background: var(--coral-deep); }

/* ── List ── */
.restaurant-list {
  padding: 0 var(--space-4);
  display: flex; flex-direction: column; gap: var(--space-3);
}
.list-item {
  animation: slideInUp 0.4s var(--ease-out) both;
}

/* ── Pagination ── */
.pagination {
  display: flex; align-items: center; justify-content: center;
  gap: var(--space-4); padding: var(--space-6) 0;
}
.page-btn {
  padding: var(--space-2) var(--space-5);
  border: 1px solid var(--border); border-radius: var(--radius-full);
  font-size: var(--text-sm); color: var(--ink-light);
  transition: all var(--duration-fast);
}
.page-btn:hover:not(:disabled) { border-color: var(--coral); color: var(--coral); background: var(--coral-pale); }
.page-btn:disabled { opacity: 0.35; cursor: not-allowed; }
.page-info { font-size: var(--text-sm); color: var(--ink-muted); font-weight: 600; }

.list-bottom-spacer { height: var(--space-8); }

@media (min-width: 768px) {
  .restaurant-list, .skeleton-list { padding: 0 var(--space-6); }
  .category-strip, .city-strip, .toolbar { padding-left: var(--space-6); padding-right: var(--space-6); }
  .discover-header { padding-left: var(--space-6); padding-right: var(--space-6); }
}
@media (min-width: 1024px) {
  .page-discover { max-width: 900px; margin: 0 auto; }
}
</style>
