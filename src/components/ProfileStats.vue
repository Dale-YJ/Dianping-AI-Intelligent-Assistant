<template>
  <div class="profile-stats">
    <div v-for="stat in stats" :key="stat.label" class="stat-item">
      <div class="stat-num">{{ stat.num }}</div>
      <div class="stat-label">{{ stat.label }}</div>
    </div>
  </div>
</template>

<script>
export default {
  name: 'ProfileStats',
  props: {
    stats: { type: Array, required: true }
  }
}
</script>

<style scoped>
.profile-stats {
  display: flex; justify-content: center; gap: var(--space-10);
  padding: var(--space-4) var(--space-4) var(--space-6);
}
.stat-item { text-align: center; }
.stat-num { font-size: var(--text-xl); font-weight: 700; color: var(--coral); }
.stat-label { font-size: var(--text-xs); color: var(--ink-muted); margin-top: 2px; }
</style>
