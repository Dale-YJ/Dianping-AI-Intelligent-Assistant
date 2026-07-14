<template>
  <div class="profile-menu">
    <div
      v-for="item in menuItems"
      :key="item.label"
      class="profile-menu-item"
      @click="$emit('click', item)"
    >
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="menu-icon" v-html="item.icon"></svg>
      {{ item.label }}
      <svg class="menu-arrow" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M9 18l6-6-6-6"/></svg>
    </div>
  </div>
</template>

<script>
export default {
  name: 'ProfileMenu',
  emits: ['click'],
  data() {
    return {
      menuItems: [
        { label: '我的订单', icon: '<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/>' },
        { label: '我的收藏', icon: '<path d="M19 21l-7-5-7 5V5a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2z"/>' },
        { label: '我的足迹', icon: '<path d="M12 2C8.13 2 5 5.13 5 9c0 5.25 7 13 7 13s7-7.75 7-13c0-3.87-3.13-7-7-7z"/><circle cx="12" cy="9" r="2.5"/>' },
        { label: '浏览记录', icon: '<circle cx="12" cy="12" r="10"/><path d="M12 6v6l4 2"/>' }
      ]
    }
  }
}
</script>

<style scoped>
.profile-menu {
  margin: 0 var(--space-4);
  background: var(--card-bg);
  border-radius: var(--radius-lg);
  border: 1px solid var(--border);
  overflow: hidden;
}
.profile-menu-item {
  display: flex; align-items: center; gap: var(--space-3);
  padding: var(--space-4);
  font-size: var(--text-sm);
  border-bottom: 1px solid var(--border);
  transition: background var(--duration-fast);
  cursor: pointer;
}
.profile-menu-item:last-child { border-bottom: none; }
.profile-menu-item:hover { background: var(--card-warm); }
.menu-icon { width: 20px; height: 20px; color: var(--ink-muted); flex-shrink: 0; }
.menu-arrow { margin-left: auto; width: 16px; height: 16px; }
</style>
