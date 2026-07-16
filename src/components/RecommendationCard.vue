<template>
  <div class="rec-card" @click="$emit('click')">
    <div class="rec-header">
      <div class="rec-img" :style="{ background: imgBg }">
        <span class="rec-rank" v-if="rank">#{{ rank }}</span>
      </div>
      <div class="rec-info">
        <h3 class="rec-name">{{ name }}</h3>
        <div class="rec-rating">
          <span class="stars">
            <span v-for="i in 5" :key="i" class="star" :class="starClass(i)">{{ starChar(i) }}</span>
          </span>
          <span class="rating-num">{{ rating }}</span>
        </div>
        <div class="rec-meta">
          <span v-if="categories">{{ categories }}</span>
          <span v-if="price">· {{ price }}</span>
          <span v-if="distance">· {{ distance }}</span>
        </div>
      </div>
    </div>
    <p class="rec-reason">💡 {{ reason }}</p>
    <div class="rec-sources" v-if="sources && sources.length">
      <span class="source-label">📎 来源：</span>
      <span
        v-for="(s, i) in sources"
        :key="i"
        class="source-tag"
        @click.stop="$emit('source-click', s)"
      >
        {{ s.user }} · {{ s.date }}
      </span>
    </div>
  </div>
</template>

<script>
export default {
  name: 'RecommendationCard',
  props: {
    name: { type: String, required: true },
    rating: { type: Number, default: 0 },
    categories: { type: String, default: '' },
    price: { type: String, default: '' },
    distance: { type: String, default: '' },
    reason: { type: String, default: '' },
    sources: { type: Array, default: () => [] },
    imgBg: { type: String, default: 'linear-gradient(135deg, #3D2E2E, #5D3A3A)' },
    rank: { type: Number, default: 0 }
  },
  emits: ['click', 'source-click'],
  methods: {
    starClass(i) {
      const full = Math.floor(this.rating)
      const half = this.rating % 1 >= 0.5 ? 1 : 0
      if (i <= full) return 'star-full'
      if (i === full + 1 && half) return 'star-half'
      return 'star-empty'
    },
    starChar(i) {
      const full = Math.floor(this.rating)
      const half = this.rating % 1 >= 0.5 ? 1 : 0
      if (i <= full) return '★'
      if (i === full + 1 && half) return '★'
      return '☆'
    }
  }
}
</script>

<style scoped>
.rec-card {
  background: var(--card-bg);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  padding: var(--space-4);
  cursor: pointer;
  transition: all var(--duration-fast) var(--ease-out);
  animation: slideInUp 0.4s var(--ease-out) both;
}
.rec-card:hover {
  border-color: var(--coral);
  box-shadow: var(--shadow-md);
  transform: translateY(-1px);
}
.rec-card:active { transform: scale(0.985); }
.rec-header {
  display: flex;
  gap: var(--space-3);
  margin-bottom: var(--space-3);
}
.rec-img {
  width: 72px;
  height: 72px;
  border-radius: var(--radius-md);
  flex-shrink: 0;
  display: flex;
  align-items: flex-start;
  justify-content: flex-start;
  padding: var(--space-1);
}
.rec-rank {
  font-family: var(--font-display);
  font-size: 1.5rem;
  font-weight: 700;
  color: rgba(255,255,255,0.9);
  text-shadow: 0 2px 4px rgba(0,0,0,0.3);
}
.rec-info { flex: 1; min-width: 0; }
.rec-name {
  font-family: var(--font-display);
  font-size: var(--text-md);
  font-weight: 700;
  color: var(--ink);
  margin-bottom: var(--space-1);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.rec-rating { display: flex; align-items: center; gap: var(--space-1); margin-bottom: 2px; }
.stars { font-size: var(--text-sm); letter-spacing: 1px; display: inline-flex; align-items: center; }
.star { display: inline-block; position: relative; }
.star-full { color: var(--amber); }
.star-empty { color: #DDD; }
.star-half { color: #DDD; }
.star-half::after {
  content: '★';
  position: absolute;
  left: 0;
  top: 0;
  width: 50%;
  overflow: hidden;
  color: var(--amber);
  pointer-events: none;
}
.rating-num { font-size: var(--text-sm); font-weight: 600; color: var(--ink); }
.rec-meta { font-size: var(--text-xs); color: var(--ink-muted); }
.rec-reason {
  font-size: var(--text-sm);
  color: var(--ink-light);
  line-height: var(--leading-relaxed);
  margin-bottom: var(--space-2);
  padding: var(--space-2);
  background: var(--warm-bg);
  border-radius: var(--radius-sm);
}
.rec-sources { display: flex; align-items: center; gap: var(--space-1); flex-wrap: wrap; }
.source-label { font-size: var(--text-xs); color: var(--ink-muted); }
.source-tag {
  font-size: var(--text-xs);
  color: var(--coral);
  background: var(--coral-pale);
  padding: 2px var(--space-2);
  border-radius: var(--radius-full);
  cursor: pointer;
  transition: background var(--duration-fast);
}
.source-tag:hover { background: #FFE0D0; }

@media (min-width: 768px) {
  .rec-img { width: 88px; height: 88px; }
}
</style>
