<template>
  <div class="banner-card" @click="$emit('click')">
    <div class="banner-img" :style="{ background: bgGradient }"></div>
    <div class="banner-overlay"></div>
    <div class="banner-content">
      <span class="banner-tag">{{ tag }}</span>
      <div class="banner-title">{{ title }}</div>
      <div class="banner-sub">{{ subtitle }}</div>
    </div>
    <div class="banner-dots">
      <div v-for="i in dots" :key="i" class="dot" :class="{ active: i === activeDot }"></div>
    </div>
  </div>
</template>

<script>
export default {
  name: 'BannerCard',
  props: {
    tag: { type: String, default: '🔥 本周热门' },
    title: { type: String, required: true },
    subtitle: { type: String, default: '' },
    bgGradient: { type: String, default: 'linear-gradient(135deg, #2D1B2E, #1A1A2E, #3D2E2E)' },
    dots: { type: Number, default: 3 },
    activeDot: { type: Number, default: 1 }
  },
  emits: ['click']
}
</script>

<style scoped>
.banner-card {
  position: relative;
  border-radius: var(--radius-xl);
  overflow: hidden;
  aspect-ratio: 16/9;
  background: linear-gradient(135deg, #1A1A2E 0%, #2D2D44 100%);
  cursor: pointer;
}

.banner-img {
  width: 100%; height: 100%;
  opacity: 0.75;
}

.banner-overlay {
  position: absolute; inset: 0;
  background: linear-gradient(to top, rgba(26,26,46,0.85) 0%, rgba(26,26,46,0.1) 60%, transparent 100%);
}

.banner-content {
  position: absolute; bottom: 0; left: 0; right: 0;
  padding: var(--space-6);
  color: #fff;
}

.banner-tag {
  display: inline-block;
  background: var(--coral);
  font-size: var(--text-xs);
  font-weight: 600;
  padding: 2px 10px;
  border-radius: var(--radius-full);
  margin-bottom: var(--space-2);
}

.banner-title {
  font-family: var(--font-display);
  font-size: var(--text-xl);
  font-weight: 700;
  margin-bottom: var(--space-1);
}

.banner-sub { font-size: var(--text-sm); opacity: 0.85; }

.banner-dots {
  position: absolute; right: var(--space-4); bottom: var(--space-6);
  display: flex; gap: 6px;
}

.dot { width: 6px; height: 6px; border-radius: 50%; background: rgba(255,255,255,0.4); transition: all var(--duration-normal); }
.dot.active { background: #fff; width: 20px; border-radius: 3px; animation: bannerDot 2s ease-in-out infinite; }
</style>
