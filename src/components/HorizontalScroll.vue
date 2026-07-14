<template>
  <div class="hscroll">
    <div class="section-header" v-if="title">
      <h2 class="section-title">{{ title }}</h2>
      <a class="section-more" href="#">更多 →</a>
    </div>
    <div class="scroll-track" v-if="layout === 'hscroll'">
      <div
        v-for="(item, idx) in items"
        :key="idx"
        class="hcard"
        @click="$emit('item-click', item)"
      >
        <div class="hcard-img" :style="{ background: item.imgBg }"></div>
        <div class="hcard-body">
          <div class="hcard-name">{{ item.name }}</div>
          <div class="hcard-meta">
            <span class="hcard-rating">
              <svg viewBox="0 0 24 24" fill="currentColor" class="star-sm"><path d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z"/></svg>
              {{ item.rating }}
            </span>
            <span v-if="item.price">{{ item.price }}/人</span>
            <span v-if="item.distance">{{ item.distance }}</span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: 'HorizontalScroll',
  props: {
    title: { type: String, default: '' },
    items: { type: Array, default: () => [] },
    layout: { type: String, default: 'hscroll' }  // 'hscroll' or 'list'
  },
  emits: ['item-click']
}
</script>

<style scoped>
.hscroll { padding: var(--space-5) var(--space-4) 0; }

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

.scroll-track {
  display: flex;
  gap: var(--space-3);
  overflow-x: auto;
  scroll-snap-type: x mandatory;
  padding-bottom: var(--space-2);
  -webkit-overflow-scrolling: touch;
  scrollbar-width: none;
}
.scroll-track::-webkit-scrollbar { display: none; }

.hcard {
  flex: 0 0 260px;
  scroll-snap-align: start;
  border-radius: var(--radius-lg);
  overflow: hidden;
  background: var(--card-bg);
  box-shadow: var(--shadow-sm);
  border: 1px solid var(--border);
  transition: transform var(--duration-fast) var(--ease-out), box-shadow var(--duration-fast) var(--ease-out);
  cursor: pointer;
}
.hcard:active { transform: scale(0.98); }

.hcard-img { width: 100%; height: 140px; }
.hcard-body { padding: var(--space-3); }

.hcard-name {
  font-size: var(--text-md); font-weight: 600;
  margin-bottom: var(--space-1);
  display: -webkit-box; -webkit-line-clamp: 1; -webkit-box-orient: vertical;
  overflow: hidden;
}

.hcard-meta { display: flex; align-items: center; gap: var(--space-2); font-size: var(--text-xs); color: var(--ink-muted); }
.hcard-rating { display: flex; align-items: center; gap: 2px; font-weight: 700; color: var(--amber); }
.star-sm { width: 14px; height: 14px; }
</style>
