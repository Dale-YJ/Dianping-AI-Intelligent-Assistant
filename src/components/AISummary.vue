<template>
  <div class="ai-summary">
    <div class="summary-header">
      <span class="summary-icon">🤖</span>
      <span class="summary-label">AI 口碑摘要</span>
      <span class="summary-badge">Beta</span>
    </div>
    <div class="summary-body" v-if="!loading">
      <div class="summary-section positive">
        <h5>👍 好评亮点</h5>
        <p>{{ highlights }}</p>
      </div>
      <div class="summary-section negative">
        <h5>👎 差评槽点</h5>
        <p>{{ complaints }}</p>
      </div>
      <div class="summary-section recent" v-if="recent">
        <h5>📊 近期动态</h5>
        <p>{{ recent }}</p>
      </div>
    </div>
    <div class="summary-loading" v-else>
      <span class="typing-dot"></span>
      <span class="typing-dot"></span>
      <span class="typing-dot"></span>
      <span class="loading-text">正在分析评价...</span>
    </div>
    <div class="summary-sources" v-if="!loading && sources.length">
      <SourceReference
        v-for="(s, i) in sources"
        :key="i"
        v-bind="s"
        @click="$emit('source-click', s)"
      />
    </div>
  </div>
</template>

<script>
import SourceReference from './SourceReference.vue'

export default {
  name: 'AISummary',
  components: { SourceReference },
  props: {
    highlights: { type: String, default: '' },
    complaints: { type: String, default: '' },
    recent: { type: String, default: '' },
    sources: { type: Array, default: () => [] },
    loading: { type: Boolean, default: false }
  },
  emits: ['source-click']
}
</script>

<style scoped>
.ai-summary {
  background: var(--card-warm);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  padding: var(--space-4);
  margin-bottom: var(--space-4);
}
.summary-header {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  margin-bottom: var(--space-3);
  padding-bottom: var(--space-3);
  border-bottom: 1px solid var(--border);
}
.summary-icon { font-size: 1.2rem; }
.summary-label {
  font-family: var(--font-display);
  font-size: var(--text-md);
  font-weight: 700;
  color: var(--ink);
}
.summary-badge {
  font-size: var(--text-xs);
  background: var(--coral);
  color: #fff;
  padding: 1px var(--space-2);
  border-radius: var(--radius-full);
  font-weight: 600;
}
.summary-body { display: flex; flex-direction: column; gap: var(--space-3); }
.summary-section { font-size: var(--text-sm); line-height: var(--leading-relaxed); }
.summary-section h5 {
  font-family: var(--font-display);
  font-size: var(--text-sm);
  font-weight: 700;
  margin-bottom: var(--space-1);
}
.summary-section.positive h5 { color: var(--sentiment-positive); }
.summary-section.negative h5 { color: var(--sentiment-negative); }
.summary-section.recent h5 { color: var(--coral); }
.summary-section p { color: var(--ink-light); }
.summary-loading {
  display: flex;
  align-items: center;
  gap: var(--space-1);
  padding: var(--space-4) 0;
}
.loading-text {
  margin-left: var(--space-2);
  font-size: var(--text-sm);
  color: var(--ink-muted);
}
.summary-sources {
  margin-top: var(--space-3);
  padding-top: var(--space-3);
  border-top: 1px solid var(--border);
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}
</style>
