<template>
  <header class="top-nav">
    <slot name="left">
      <div class="nav-location">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="icon-sm"><path d="M12 2C8.13 2 5 5.13 5 9c0 5.25 7 13 7 13s7-7.75 7-13c0-3.87-3.13-7-7-7z"/><circle cx="12" cy="9" r="2.5"/></svg>
        {{ location }}
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="icon-xs"><path d="M6 9l6 6 6-6"/></svg>
      </div>
    </slot>
    <slot name="center">
      <div class="search-bar" @click="$emit('search')">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="icon-sm"><circle cx="11" cy="11" r="8"/><path d="M21 21l-4.35-4.35"/></svg>
        <span>{{ searchPlaceholder }}</span>
      </div>
    </slot>
    <slot name="right" />
  </header>
</template>

<script>
export default {
  name: 'TopNav',
  props: {
    location: { type: String, default: '上海市 · 静安区' },
    searchPlaceholder: { type: String, default: '搜索餐厅、菜系或地点...' }
  },
  emits: ['search']
}
</script>

<style scoped>
.top-nav {
  position: sticky;
  top: 0;
  z-index: 100;
  background: rgba(255,255,255,0.85);
  backdrop-filter: blur(20px) saturate(1.8);
  -webkit-backdrop-filter: blur(20px) saturate(1.8);
  border-bottom: 1px solid var(--border);
  padding: var(--space-3) var(--space-4);
}

.nav-location {
  display: flex;
  align-items: center;
  gap: var(--space-1);
  font-size: var(--text-sm);
  color: var(--ink);
}

.search-bar {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  background: #F5F3F0;
  border-radius: var(--radius-full);
  padding: var(--space-2) var(--space-4);
  margin-top: var(--space-2);
  cursor: pointer;
  transition: background var(--duration-fast);
  animation: gentlePulse 3s ease-in-out infinite;
}
.search-bar:hover { background: #EFECE8; }
.search-bar span { font-size: var(--text-sm); color: var(--ink-muted); }

.icon-sm { width: 16px; height: 16px; color: var(--ink-muted); flex-shrink: 0; }
.icon-xs { width: 12px; height: 12px; }

.back-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.back-btn {
  display: flex;
  align-items: center;
  gap: var(--space-1);
  font-size: var(--text-sm);
  color: var(--ink-light);
  padding: var(--space-2) 0;
  transition: color var(--duration-fast);
}
.back-btn:hover { color: var(--coral); }
.back-btn svg { width: 18px; height: 18px; }

.page-title { font-weight: 600; }
</style>
