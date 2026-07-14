<template>
  <nav class="tab-bar">
    <button
      v-for="tab in tabs"
      :key="tab.route"
      class="tab-item"
      :class="{ active: currentRoute === tab.route || tab.match?.includes(currentRoute) }"
      @click="$router.push(tab.route)"
    >
      <!-- outline icon -->
      <svg v-if="!isActive(tab)" class="tab-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" v-html="tab.iconOuter"></svg>
      <!-- filled icon -->
      <svg v-else class="tab-icon" viewBox="0 0 24 24" fill="currentColor" stroke="none" v-html="tab.iconInner"></svg>
      {{ tab.label }}
    </button>
  </nav>
</template>

<script>
export default {
  name: 'AppTabBar',
  data() {
    return {
      tabs: [
        {
          route: '/',
          label: '探店',
          iconOuter: '<path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>',
          iconInner: '<path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/><circle cx="9" cy="10" r="2" fill="white"/><circle cx="15" cy="10" r="2" fill="white"/>',
          match: []
        },
        {
          route: '/list',
          label: '发现',
          iconOuter: '<circle cx="11" cy="11" r="8"/><path d="M21 21l-4.35-4.35"/>',
          iconInner: '<circle cx="11" cy="11" r="8"/><path d="M21 21l-4.35-4.35"/><circle cx="11" cy="11" r="5" fill="white"/>',
          match: []
        },
        {
          route: '/business/1',
          label: '商家',
          iconOuter: '<path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/><polyline points="9 22 9 12 15 12 15 22"/>',
          iconInner: '<path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/><rect x="11" y="14" width="4" height="8" fill="white"/>',
          match: ['/business']
        },
        {
          route: '/profile',
          label: '我的',
          iconOuter: '<path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/>',
          iconInner: '<path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/>',
          match: []
        }
      ]
    }
  },
  computed: {
    currentRoute() {
      return this.$route.path
    }
  },
  methods: {
    isActive(tab) {
      if (this.currentRoute === tab.route) return true
      if (tab.match) return tab.match.some(p => this.currentRoute.startsWith(p))
      return false
    }
  }
}
</script>

<style scoped>
.tab-bar {
  position: fixed;
  bottom: 0;
  left: 50%;
  transform: translateX(-50%);
  width: 100%;
  max-width: var(--max-width);
  height: var(--tab-height);
  background: rgba(255,255,255,0.9);
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
  border-top: 1px solid var(--border);
  display: flex;
  align-items: center;
  justify-content: space-around;
  z-index: 100;
  padding-bottom: env(safe-area-inset-bottom, 0);
}

.tab-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 2px;
  font-size: 0.625rem;
  color: var(--ink-muted);
  transition: color var(--duration-normal);
  padding: var(--space-1) var(--space-2);
}
.tab-item.active { color: var(--coral); }
.tab-icon { width: 22px; height: 22px; }
</style>
