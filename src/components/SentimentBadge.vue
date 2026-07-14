<template>
  <span class="sentiment-badge" :class="sentiment">
    <span class="dot"></span>
    {{ label }}
    <span class="confidence" v-if="confidence">{{ confidence }}%</span>
  </span>
</template>

<script>
export default {
  name: 'SentimentBadge',
  props: {
    sentiment: { type: String, default: 'neutral', validator: v => ['positive','neutral','negative'].includes(v) },
    confidence: { type: Number, default: 0 }
  },
  computed: {
    label() {
      return { positive: '😊 好评', neutral: '😐 中评', negative: '😞 差评' }[this.sentiment]
    }
  }
}
</script>

<style scoped>
.sentiment-badge {
  display: inline-flex;
  align-items: center;
  gap: var(--space-1);
  font-size: var(--text-xs);
  font-weight: 600;
  padding: 2px var(--space-2);
  border-radius: var(--radius-full);
  white-space: nowrap;
}
.sentiment-badge.positive {
  color: var(--sentiment-positive);
  background: var(--sentiment-positive-bg);
}
.sentiment-badge.neutral {
  color: #92400E;
  background: var(--sentiment-neutral-bg);
}
.sentiment-badge.negative {
  color: var(--sentiment-negative);
  background: var(--sentiment-negative-bg);
}
.dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: currentColor;
}
.confidence {
  opacity: 0.7;
  font-weight: 400;
}
</style>
