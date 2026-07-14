<template>
  <div>
    <div class="filter-bar">
      <button
        v-for="chip in chips"
        :key="chip"
        class="filter-chip"
        :class="{ active: chip === activeChip }"
        @click="$emit('select', chip)"
      >{{ chip }}</button>
    </div>
    <div class="active-tags" v-if="activeTags.length">
      <span v-for="tag in activeTags" :key="tag" class="tag">
        {{ tag }}
        <span class="tag-close" @click="$emit('remove-tag', tag)">×</span>
      </span>
    </div>
    <div class="result-info">
      <span>找到 <strong>{{ total }}</strong> 家餐厅</span>
      <span>{{ sortLabel }}</span>
    </div>
  </div>
</template>

<script>
export default {
  name: 'FilterBar',
  props: {
    chips: { type: Array, default: () => ['📍 区域 ▾', '🍽️ 菜系', '💰 价格 ▾', '⭐ 评分 ▾', '🔤 排序 ▾'] },
    activeChip: { type: String, default: '🍽️ 菜系' },
    activeTags: { type: Array, default: () => ['本帮菜', '静安区', '¥100-300'] },
    total: { type: Number, default: 128 },
    sortLabel: { type: String, default: '默认排序' }
  },
  emits: ['select', 'remove-tag']
}
</script>

<style scoped>
.filter-bar {
  display: flex; gap: var(--space-2);
  padding: var(--space-3) var(--space-4);
  overflow-x: auto;
  scrollbar-width: none;
  border-bottom: 1px solid var(--border);
  position: sticky; top: 0;
  background: rgba(255,255,255,0.9);
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  z-index: 50;
}
.filter-bar::-webkit-scrollbar { display: none; }

.filter-chip {
  flex-shrink: 0;
  padding: var(--space-1) var(--space-3);
  border-radius: var(--radius-full);
  font-size: var(--text-sm);
  color: var(--ink-light);
  background: #F5F3F0;
  transition: all var(--duration-fast);
  white-space: nowrap;
}
.filter-chip.active { background: var(--coral); color: #fff; font-weight: 600; }
.filter-chip:active { transform: scale(0.95); }

.active-tags { display: flex; gap: var(--space-2); padding: var(--space-2) var(--space-4) var(--space-3); flex-wrap: wrap; }
.tag {
  display: flex; align-items: center; gap: var(--space-1);
  font-size: var(--text-xs);
  padding: 2px 10px;
  border-radius: var(--radius-full);
  background: var(--coral-pale);
  color: var(--coral-deep);
  font-weight: 500;
}
.tag-close { cursor: pointer; opacity: 0.6; font-size: 14px; }
.tag-close:hover { opacity: 1; }

.result-info {
  display: flex; align-items: center; justify-content: space-between;
  padding: 0 var(--space-4) var(--space-3);
  font-size: var(--text-xs);
  color: var(--ink-muted);
}
</style>
