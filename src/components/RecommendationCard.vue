<template>
  <div class="rec-card" :class="rankCardClass" @click="$emit('click')">
    <!-- Left: Image placeholder with rank badge overlay -->
    <div class="rec-img" :style="{ background: imgBg }">
      <div class="rank-badge" v-if="rank && rank <= 3" :class="'rank-' + rank">
        <span class="rank-medal">{{ rankMedal }}</span>
      </div>
      <div class="rank-circle" v-else-if="rank">
        <span class="rank-num">{{ rank }}</span>
      </div>
    </div>

    <!-- Center: Info -->
    <div class="rec-body">
      <!-- Name row -->
      <div class="rec-name-row">
        <h3 class="rec-name">{{ name }}</h3>
      </div>

      <!-- Rating row -->
      <div class="rec-rating-row">
        <span class="stars">
          <span v-for="i in 5" :key="i" class="star" :class="starClass(i)">{{ starChar(i) }}</span>
        </span>
        <span class="rating-score">{{ rating }}</span>
        <span class="review-count" v-if="reviewCount">· {{ reviewCount }}条评价</span>
      </div>

      <!-- Meta row -->
      <div class="rec-meta">
        <span v-if="categories" class="meta-cat">{{ categories }}</span>
        <span class="meta-sep" v-if="categories && (distance || address)">·</span>
        <span v-if="distance && distance !== '--'" class="meta-dist">{{ distance }}</span>
        <span v-if="address && !distance" class="meta-dist">{{ address }}</span>
      </div>

      <!-- Reason quote -->
      <p class="rec-reason" v-if="reason">
        <span class="reason-mark">「</span>{{ reason }}<span class="reason-mark">」</span>
      </p>

      <!-- Sources -->
      <div class="rec-sources" v-if="sources && sources.length">
        <span
          v-for="(s, i) in sources.slice(0, 2)"
          :key="i"
          class="source-chip"
          @click.stop="$emit('source-click', s)"
        >
          <span class="source-avatar-text">{{ s.user[0] }}</span>
          <span class="source-name">{{ s.user }}</span>
        </span>
        <span class="source-more" v-if="sources.length > 2">等{{ sources.length }}条评价</span>
      </div>
    </div>

    <!-- Right: Arrow -->
    <div class="rec-arrow">
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
        <polyline points="9 18 15 12 9 6"/>
      </svg>
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
    rank: { type: Number, default: 0 },
    reviewCount: { type: Number, default: 0 },
    address: { type: String, default: '' },
  },
  emits: ['click', 'source-click'],
  computed: {
    rankMedal() {
      const medals = { 1: '🥇', 2: '🥈', 3: '🥉' }
      return medals[this.rank] || ''
    },
    rankCardClass() {
      const classes = { 1: 'rank-gold', 2: 'rank-silver', 3: 'rank-bronze' }
      return classes[this.rank] || ''
    },
  },
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
    },
  },
}
</script>

<style scoped>
/* ── Card Container ── */
.rec-card {
  display: flex;
  align-items: flex-start;
  gap: var(--space-3);
  padding: var(--space-3);
  background: var(--card-bg);
  border-radius: var(--radius-lg);
  border: 1px solid var(--border);
  box-shadow: var(--shadow-sm);
  cursor: pointer;
  transition: transform var(--duration-fast) var(--ease-out),
              box-shadow var(--duration-fast) var(--ease-out),
              border-color var(--duration-fast) var(--ease-out);
  animation: slideInUp 0.4s var(--ease-out) both;
  position: relative;
  overflow: hidden;
}

/* ── Rank accent top bar ── */
.rec-card.rank-gold::before,
.rec-card.rank-silver::before,
.rec-card.rank-bronze::before {
  content: '';
  position: absolute;
  top: 0; left: 0; right: 0;
  height: 3px;
}
.rec-card.rank-gold::before   { background: linear-gradient(90deg, var(--rank-gold), #FFD700); }
.rec-card.rank-silver::before { background: linear-gradient(90deg, var(--rank-silver), #C0C0D0); }
.rec-card.rank-bronze::before { background: linear-gradient(90deg, var(--rank-bronze), #D4A574); }

.rec-card:hover {
  border-color: var(--border-strong);
  box-shadow: var(--shadow-md);
  transform: translateY(-2px);
}
.rec-card:active { transform: scale(0.985); }

/* ── Image ── */
.rec-img {
  width: 88px;
  height: 88px;
  border-radius: var(--radius-md);
  flex-shrink: 0;
  display: flex;
  align-items: flex-start;
  justify-content: flex-start;
  position: relative;
  background-size: cover;
  background-position: center;
  background-repeat: no-repeat;
}

/* ── Rank Badge ── */
.rank-badge {
  position: absolute;
  top: -2px;
  left: -2px;
  width: 36px;
  height: 36px;
  border-radius: 0 0 var(--radius-sm) 0;
  display: flex;
  align-items: center;
  justify-content: center;
}
.rank-badge.rank-1 { background: linear-gradient(135deg, #F0A500, #FFD700); }
.rank-badge.rank-2 { background: linear-gradient(135deg, #9090A0, #C0C0D0); }
.rank-badge.rank-3 { background: linear-gradient(135deg, #B87333, #D4A574); }
.rank-medal {
  font-size: 1.125rem;
  filter: drop-shadow(0 1px 2px rgba(0,0,0,0.2));
}

/* Rank circle (for #4+) */
.rank-circle {
  position: absolute;
  top: 4px;
  left: 4px;
  width: 26px;
  height: 26px;
  border-radius: 50%;
  background: rgba(0,0,0,0.45);
  backdrop-filter: blur(4px);
  display: flex;
  align-items: center;
  justify-content: center;
}
.rank-num {
  font-family: var(--font-display);
  font-size: 0.75rem;
  font-weight: 700;
  color: #fff;
  line-height: 1;
}

/* ── Body ── */
.rec-body {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

/* ── Name row ── */
.rec-name-row {
  display: flex;
  align-items: center;
  gap: var(--space-2);
}
.rec-name {
  font-family: var(--font-display);
  font-size: var(--text-md);
  font-weight: 700;
  color: var(--ink);
  line-height: var(--leading-tight);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  flex: 1;
  min-width: 0;
}
.rank-tag {
  flex-shrink: 0;
  font-size: 0.625rem;
  font-weight: 700;
  color: var(--coral);
  background: var(--coral-pale);
  padding: 1px 6px;
  border-radius: var(--radius-sm);
  letter-spacing: 0.5px;
}

/* ── Rating row ── */
.rec-rating-row {
  display: flex;
  align-items: baseline;
  gap: var(--space-1);
}
.stars {
  font-size: 0.8125rem;
  letter-spacing: 1px;
  display: inline-flex;
  align-items: center;
  line-height: 1;
}
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
.rating-score {
  font-size: 1.125rem;
  font-weight: 700;
  color: var(--amber);
  line-height: 1;
}
.review-count {
  font-size: var(--text-xs);
  color: var(--ink-muted);
  white-space: nowrap;
}

/* ── Meta row ── */
.rec-meta {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  font-size: var(--text-xs);
  color: var(--ink-muted);
  gap: 0;
}
.meta-sep {
  margin: 0 4px;
  color: var(--border-strong);
}
.meta-cat {
  color: var(--ink-muted);
}
.meta-price {
  color: var(--coral);
  font-weight: 600;
}
.meta-dist {
  color: var(--ink-muted);
}

/* ── Reason quote ── */
.rec-reason {
  font-size: var(--text-sm);
  color: var(--ink-light);
  line-height: var(--leading-relaxed);
  margin-top: 2px;
  padding: var(--space-2) var(--space-2) var(--space-2) var(--space-3);
  background: var(--warm-bg);
  border-radius: 0 var(--radius-sm) var(--radius-sm) 0;
  border-left: 2px solid var(--amber);
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
.reason-mark { color: var(--amber); font-weight: 700; }

/* ── Sources ── */
.rec-sources {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  flex-wrap: wrap;
  margin-top: 2px;
}
.source-chip {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 2px 8px 2px 2px;
  background: var(--coral-pale);
  border-radius: var(--radius-full);
  cursor: pointer;
  transition: background var(--duration-fast);
  font-size: var(--text-xs);
  color: var(--coral);
}
.source-chip:hover { background: #FFE0D0; }
.source-avatar-text {
  width: 20px;
  height: 20px;
  border-radius: 50%;
  background: var(--coral);
  color: #fff;
  font-size: 0.625rem;
  font-weight: 700;
  display: flex;
  align-items: center;
  justify-content: center;
  line-height: 1;
}
.source-name {
  font-weight: 600;
  max-width: 72px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.source-more {
  font-size: var(--text-xs);
  color: var(--ink-muted);
}

/* ── Arrow ── */
.rec-arrow {
  flex-shrink: 0;
  align-self: center;
  color: var(--ink-muted);
  opacity: 0.5;
  transition: opacity var(--duration-fast), transform var(--duration-fast);
  margin-left: -2px;
}
.rec-card:hover .rec-arrow {
  opacity: 1;
  transform: translateX(2px);
}

/* ── Responsive ── */
@media (min-width: 768px) {
  .rec-img {
    width: 100px;
    height: 100px;
  }
  .rec-name {
    font-size: var(--text-lg);
  }
  .rating-score {
    font-size: 1.25rem;
  }
}
</style>
