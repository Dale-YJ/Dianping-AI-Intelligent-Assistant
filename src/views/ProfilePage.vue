<template>
  <div class="page-profile">
    <TopNav>
      <template #left>
        <button class="back-btn" @click="$router.back()">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M19 12H5M12 19l-7-7 7-7"/></svg>
        </button>
      </template>
      <template #center>
        <span class="page-title">我的</span>
      </template>
      <template #right>
        <button class="more-btn">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="width:20px;height:20px;"><circle cx="12" cy="5" r="1"/><circle cx="12" cy="12" r="1"/><circle cx="12" cy="19" r="1"/></svg>
        </button>
      </template>
    </TopNav>

    <div class="stagger-1">
      <ProfileHeader />
    </div>

    <div class="stagger-2">
      <ProfileStats :stats="stats" />
    </div>

    <div class="stagger-3">
      <ProfileMenu />
    </div>

    <div class="my-reviews stagger-4">
      <div class="section-header">
        <h2 class="section-title">我的评价</h2>
        <a class="section-more" href="#">全部 →</a>
      </div>

      <div v-for="r in myReviews" :key="r.shop" class="my-review-card">
        <div class="my-review-header">
          <span class="my-review-shop">{{ r.shop }}</span>
          <span class="my-review-date">{{ r.date }}</span>
        </div>
        <div class="my-review-stars">{{ r.stars }}</div>
        <div class="my-review-text">{{ r.text }}</div>
        <div class="my-review-photos" v-if="r.photoBgs.length">
          <div
            v-for="(bg, i) in r.photoBgs"
            :key="i"
            class="my-review-photo"
            :style="{ background: bg }"
          ></div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import TopNav from '../components/TopNav.vue'
import ProfileHeader from '../components/ProfileHeader.vue'
import ProfileStats from '../components/ProfileStats.vue'
import ProfileMenu from '../components/ProfileMenu.vue'

export default {
  name: 'ProfilePage',
  components: { TopNav, ProfileHeader, ProfileStats, ProfileMenu },
  data() {
    return {
      stats: [
        { num: 128, label: '评价' },
        { num: '2.8k', label: '粉丝' },
        { num: 46, label: '收藏' },
        { num: 12, label: '徽章' }
      ],
      myReviews: [
        {
          shop: '人和馆 · 本帮菜', date: '06-08',
          stars: '⭐⭐⭐⭐⭐ 5.0',
          text: '来上海必吃的一家本帮菜！蟹粉豆腐鲜到骨子里，每一口都能吃到真实的蟹肉和蟹黄，配上一碗白米饭简直是人间美味...',
          photoBgs: ['linear-gradient(135deg,#4D3A2A,#5D4A3A)', 'linear-gradient(135deg,#3D2A1A,#4D3A2A)']
        },
        {
          shop: '珮姐老火锅', date: '06-03',
          stars: '⭐⭐⭐⭐⭐ 4.5',
          text: '毛肚是现切的，七上八下刚刚好，锅底越煮越香，排队两小时也值了。鸭血和鹅肠也是必点项...',
          photoBgs: ['linear-gradient(135deg,#5D2A2A,#6D3A3A)', 'linear-gradient(135deg,#4D2A1A,#5D3A2A)', 'linear-gradient(135deg,#3D1A2D,#4D2A3D)']
        }
      ]
    }
  }
}
</script>

<style scoped>
.back-btn {
  display: flex; align-items: center; gap: var(--space-1);
  font-size: var(--text-sm); color: var(--ink-light);
  padding: var(--space-2) 0;
  transition: color var(--duration-fast);
}
.back-btn:hover { color: var(--coral); }
.back-btn svg { width: 18px; height: 18px; }

.page-title { font-weight: 600; }
.more-btn { font-size: var(--text-sm); color: var(--ink-muted); }

.my-reviews { padding: var(--space-5) var(--space-4); }

.section-header {
  display: flex; align-items: flex-end; justify-content: space-between;
  margin-bottom: var(--space-3);
}
.section-title {
  font-family: var(--font-display);
  font-size: var(--text-xl);
  font-weight: 700;
  letter-spacing: -0.02em;
  color: var(--ink);
}
.section-more {
  font-size: var(--text-xs);
  color: var(--ink-muted);
  transition: color var(--duration-fast);
}
.section-more:hover { color: var(--coral); }

.my-review-card {
  padding: var(--space-4);
  background: var(--card-bg);
  border-radius: var(--radius-lg);
  border: 1px solid var(--border);
  margin-bottom: var(--space-3);
}
.my-review-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: var(--space-2); }
.my-review-shop { font-size: var(--text-sm); font-weight: 600; }
.my-review-date { font-size: var(--text-xs); color: var(--ink-muted); }
.my-review-stars { font-size: var(--text-xs); color: var(--ink-muted); margin-bottom: var(--space-1); }

.my-review-text {
  font-size: var(--text-sm); color: var(--ink-light);
  display: -webkit-box; -webkit-line-clamp: 3; -webkit-box-orient: vertical;
  overflow: hidden;
  margin-bottom: var(--space-2);
}
.my-review-photos { display: flex; gap: var(--space-1); }
.my-review-photo {
  width: 64px; height: 64px;
  border-radius: var(--radius-sm);
}
</style>
