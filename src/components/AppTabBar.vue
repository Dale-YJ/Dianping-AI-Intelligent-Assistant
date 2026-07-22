<template>
  <nav class="tab-bar">
    <button
      v-for="tab in tabs"
      :key="tab.route"
      class="tab-item"
      :class="{
        active: isActive(tab),
        center: tab.center
      }"
      @click="$router.push(tab.route)"
    >
      <!-- Active indicator dot -->
      <span class="tab-indicator" v-if="isActive(tab)"></span>

      <!-- Icon -->
      <div class="tab-icon-wrap" :class="{ raised: tab.center }">
        <svg
          class="tab-icon"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          stroke-width="1.8"
          stroke-linecap="round"
          stroke-linejoin="round"
          v-html="tab.icon"
        ></svg>
      </div>

      <!-- Label -->
      <span class="tab-label">{{ tab.label }}</span>
    </button>
  </nav>
</template>

<script>
const CUSTOMER_TABS = [
  {
    route: '/user',
    label: '探店',
    icon: '<path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/><path d="M8 10h.01"/><path d="M12 10h.01"/><path d="M16 10h.01"/>',
    match: ['/user', '/detail']
  },
  {
    route: '/list',
    label: '发现',
    icon: '<circle cx="11" cy="11" r="8"/><path d="m21 21-4.35-4.35"/><path d="M11 8v6"/><path d="M8 11h6"/>',
    match: []
  }
]

const BUSINESS_TABS = [
  {
    route: '/business-home',
    label: 'AI助手',
    icon: '<path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/><path d="M8 10h.01"/><path d="M12 10h.01"/><path d="M16 10h.01"/>',
    match: [],
    center: true
  },
  {
    route: '/select-shop',
    label: '选择餐厅',
    icon: '<path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z"/><circle cx="12" cy="10" r="3"/>',
    match: []
  }
]

export default {
  name: 'AppTabBar',
  computed: {
    currentRoute() {
      return this.$route.path
    },
    tabs() {
      return (this.currentRoute.startsWith('/business') || this.currentRoute.startsWith('/select-shop'))
        ? BUSINESS_TABS
        : CUSTOMER_TABS
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
/* ── Tab Bar Container ── */
.tab-bar {
  position: fixed;
  bottom: 0;
  left: 50%;
  transform: translateX(-50%);
  width: 100%;
  max-width: var(--max-width);
  height: var(--tab-height);
  background: #FFFFFF;
  display: flex;
  align-items: stretch;
  justify-content: space-around;
  z-index: 100;
  padding-bottom: env(safe-area-inset-bottom, 0);
  box-shadow: 0 -2px 12px rgba(0, 0, 0, 0.06);
}

/* ── Tab Item ── */
.tab-item {
  position: relative;
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 2px;
  font-size: 0.625rem;
  color: #999999;
  transition: color 0.2s ease;
  padding: 4px 0 2px;
  -webkit-tap-highlight-color: transparent;
}

.tab-item.active {
  color: var(--coral);
}

/* ── Active Indicator ── */
.tab-indicator {
  position: absolute;
  top: 0;
  left: 50%;
  transform: translateX(-50%);
  width: 18px;
  height: 2.5px;
  border-radius: 0 0 3px 3px;
  background: var(--coral);
  animation: indicatorIn 0.25s var(--ease-out);
}

@keyframes indicatorIn {
  from { width: 0; opacity: 0; }
  to   { width: 18px; opacity: 1; }
}

/* ── Icon Wrapper ── */
.tab-icon-wrap {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  transition: transform 0.25s var(--ease-spring);
}

.tab-item.active .tab-icon-wrap {
  transform: translateY(-1px);
}

/* ── Center (商家) raised button ── */
.tab-icon-wrap.raised {
  width: 44px;
  height: 44px;
  border-radius: 50%;
  background: var(--coral);
  color: #FFFFFF;
  margin-top: -16px;
  box-shadow: 0 4px 14px rgba(255, 107, 53, 0.35);
  transition: transform 0.25s var(--ease-spring), box-shadow 0.25s ease;
}

.tab-icon-wrap.raised .tab-icon {
  width: 22px;
  height: 22px;
}

.tab-item.active .tab-icon-wrap.raised {
  box-shadow: 0 6px 20px rgba(255, 107, 53, 0.45);
  transform: translateY(-2px) scale(1.05);
}

.tab-item:not(.active) .tab-icon-wrap.raised {
  background: linear-gradient(135deg, #FF8A5C, #FF6B35);
}

/* ── Icon ── */
.tab-icon {
  width: 24px;
  height: 24px;
  display: block;
}

.tab-item.active .tab-icon {
  fill: currentColor;
  stroke: none;
}

/* ── Active tab filled icon effect ── */
.tab-item:not(.active) .tab-icon {
  fill: none;
  stroke: currentColor;
}

/* Center icon stays stroke-only on white bg */
.tab-icon-wrap.raised .tab-icon {
  fill: none;
  stroke: #FFFFFF;
}
.tab-item.active .tab-icon-wrap.raised .tab-icon {
  fill: none;
  stroke: #FFFFFF;
}

/* ── Label ── */
.tab-label {
  font-weight: 400;
  line-height: 1;
  transition: font-weight 0.2s ease, transform 0.2s ease;
}

.tab-item.active .tab-label {
  font-weight: 700;
  transform: scale(1.05);
}
</style>
