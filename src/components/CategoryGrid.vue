<template>
  <div class="category-grid">
    <div v-for="cat in categories" :key="cat.label" class="cat-item">
      <div class="cat-icon" :class="cat.colorClass" @click="$emit('select', cat)">
        {{ cat.icon }}
      </div>
      <span class="cat-label">{{ cat.label }}</span>
    </div>
  </div>
</template>

<script>
export default {
  name: 'CategoryGrid',
  emits: ['select'],
  data() {
    return {
      categories: [
        { icon: '🍜', label: '美食', colorClass: 'cat-icon--orange' },
        { icon: '🫕', label: '火锅', colorClass: 'cat-icon--rose' },
        { icon: '🍖', label: '烧烤', colorClass: 'cat-icon--amber' },
        { icon: '🍣', label: '日料', colorClass: 'cat-icon--mint' },
        { icon: '☕', label: '咖啡', colorClass: 'cat-icon--lavender' },
        { icon: '🍷', label: '酒吧', colorClass: 'cat-icon--sky' },
        { icon: '🍰', label: '甜品', colorClass: 'cat-icon--peach' },
        { icon: '🥗', label: '轻食', colorClass: 'cat-icon--lime' },
        { icon: '🏨', label: '酒店', colorClass: 'cat-icon--coral' },
        { icon: '🎬', label: '娱乐', colorClass: 'cat-icon--teal' }
      ]
    }
  }
}
</script>

<style scoped>
.category-grid {
  display: grid;
  grid-template-columns: repeat(5, 1fr);
  gap: var(--space-4) var(--space-2);
  padding: var(--space-4) var(--space-4) 0;
}

.cat-item { display: flex; flex-direction: column; align-items: center; gap: var(--space-1); }

.cat-icon {
  width: 48px; height: 48px;
  border-radius: var(--radius-lg);
  display: flex; align-items: center; justify-content: center;
  font-size: 1.4rem;
  transition: transform var(--duration-fast) var(--ease-out);
  cursor: pointer;
}
.cat-icon:active { transform: scale(0.92); }

.cat-label { font-size: var(--text-xs); color: var(--ink-light); }

.cat-icon--orange  { background: #FFF0E8; }
.cat-icon--amber   { background: #FFF8E5; }
.cat-icon--rose    { background: #FFF0F0; }
.cat-icon--mint    { background: #EDF7F0; }
.cat-icon--lavender { background: #F3F0FF; }
.cat-icon--sky     { background: #F0F5FF; }
.cat-icon--peach   { background: #FFF5F0; }
.cat-icon--lime    { background: #F5FAF0; }
.cat-icon--coral   { background: #FFF0EC; }
.cat-icon--teal    { background: #F0F8F7; }

@media (min-width: 768px) {
  .category-grid { grid-template-columns: repeat(10, 1fr); }
}
</style>
