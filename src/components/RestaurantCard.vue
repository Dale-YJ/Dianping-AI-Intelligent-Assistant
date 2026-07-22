<template>
  <div class="restaurant-card" @click="$emit('click')">
    <div class="rc-image" :style="{ background: imgBg }"></div>
    <div class="rc-body">
      <div class="rc-name-row">
        <span class="rc-name">{{ name }}</span>
        <span class="rc-badge">
          <svg viewBox="0 0 24 24" fill="currentColor" class="star-icon"><path d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z"/></svg>
          {{ rating }}
        </span>
      </div>
      <div class="rc-tags">
        <span v-for="tag in tags" :key="tag" class="rc-tag">{{ tag }}</span>
      </div>
      <div class="rc-info">
        <span>{{ area }}</span>
        <span>{{ distance }}</span>
      </div>
      <div class="rc-review" v-if="review">
        "<em>{{ review }}</em>"
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: 'RestaurantCard',
  props: {
    name: { type: String, required: true },
    rating: { type: Number, required: true },
    tags: { type: Array, default: () => [] },
    price: { type: String, default: '' },
    area: { type: String, default: '' },
    distance: { type: String, default: '' },
    review: { type: String, default: '' },
    imgBg: { type: String, default: 'linear-gradient(135deg, #E8E4DF, #F0ECE8)' }
  },
  emits: ['click']
}
</script>

<style scoped>
.restaurant-card {
  display: flex; gap: var(--space-3);
  padding: var(--space-3);
  background: var(--card-bg);
  border-radius: var(--radius-lg);
  border: 1px solid var(--border);
  transition: transform var(--duration-fast) var(--ease-out),
              box-shadow var(--duration-fast) var(--ease-out);
  cursor: pointer;
}
.restaurant-card:active { transform: scale(0.985); }
.restaurant-card:hover { box-shadow: var(--shadow-md); }

.rc-image {
  width: 110px; height: 110px;
  border-radius: var(--radius-md);
  flex-shrink: 0;
  background-size: cover;
  background-position: center;
  background-repeat: no-repeat;
}

.rc-body { flex: 1; min-width: 0; display: flex; flex-direction: column; gap: var(--space-1); }

.rc-name-row { display: flex; align-items: center; gap: var(--space-2); }
.rc-name {
  font-size: var(--text-md); font-weight: 600;
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}

.rc-badge {
  flex-shrink: 0;
  display: flex; align-items: center; gap: 2px;
  font-size: var(--text-xs); font-weight: 700;
  background: #FFF8E5; color: var(--amber);
  padding: 1px 6px; border-radius: var(--radius-sm);
}
.star-icon { width: 12px; height: 12px; }

.rc-tags { display: flex; gap: var(--space-1); flex-wrap: wrap; }
.rc-tag {
  font-size: var(--text-xs);
  padding: 1px 6px;
  border-radius: var(--radius-sm);
  background: #F5F3F0;
  color: var(--ink-light);
}

.rc-info { display: flex; align-items: center; gap: var(--space-3); font-size: var(--text-xs); color: var(--ink-muted); }
.rc-price { font-weight: 600; color: var(--coral); }

.rc-review {
  font-size: var(--text-xs); color: var(--ink-muted);
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
  margin-top: auto;
}
.rc-review em { font-style: normal; color: var(--ink-light); }

@media (min-width: 768px) {
  .rc-image { width: 140px; height: 140px; }
}
</style>
