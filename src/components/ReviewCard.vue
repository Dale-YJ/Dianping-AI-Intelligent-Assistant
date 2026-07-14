<template>
  <div class="review-card">
    <div class="review-avatar">{{ avatar }}</div>
    <div class="review-body">
      <div class="review-user-row">
        <span class="review-user">{{ user }}</span>
        <span class="review-rating">⭐ {{ rating }}</span>
      </div>
      <div class="review-text">{{ text }}</div>
      <div class="review-photos" v-if="photoCount">
        <div
          v-for="i in photoCount"
          :key="i"
          class="review-photo"
          :style="{ background: photoBg[i-1] }"
        ></div>
      </div>
      <div class="review-footer">
        <span>{{ date }}</span>
        <span>👍 {{ likes }}</span>
        <span>💬 {{ replies }}</span>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: 'ReviewCard',
  props: {
    avatar: { type: String, default: '🍴' },
    user: { type: String, required: true },
    rating: { type: Number, required: true },
    text: { type: String, required: true },
    date: { type: String, default: '' },
    likes: { type: Number, default: 0 },
    replies: { type: Number, default: 0 },
    photoCount: { type: Number, default: 0 },
    photoBg: { type: Array, default: () => [] }
  }
}
</script>

<style scoped>
.review-card {
  display: flex; gap: var(--space-3);
  padding: var(--space-4) 0;
  border-bottom: 1px solid var(--border);
}
.review-card:last-child { border-bottom: none; }

.review-avatar {
  width: 36px; height: 36px;
  border-radius: 50%;
  flex-shrink: 0;
  background: linear-gradient(135deg, var(--coral-pale), #FFE0D0);
  display: flex; align-items: center; justify-content: center;
  font-size: var(--text-sm); font-weight: 700; color: var(--coral-deep);
}

.review-body { flex: 1; min-width: 0; }

.review-user-row { display: flex; align-items: center; justify-content: space-between; margin-bottom: var(--space-1); }
.review-user { font-size: var(--text-sm); font-weight: 600; }
.review-rating { display: flex; align-items: center; gap: 2px; font-size: var(--text-xs); color: var(--amber); font-weight: 700; }

.review-text { font-size: var(--text-sm); color: var(--ink-light); line-height: var(--leading-relaxed); }

.review-photos { display: flex; gap: var(--space-1); margin-top: var(--space-2); }
.review-photo {
  width: 72px; height: 72px;
  border-radius: var(--radius-sm);
  flex-shrink: 0;
}

.review-footer { display: flex; align-items: center; gap: var(--space-4); margin-top: var(--space-2); font-size: var(--text-xs); color: var(--ink-muted); }
</style>
