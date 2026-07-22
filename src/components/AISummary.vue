<template>
  <div class="ai-summary">
    <div class="summary-header">
      <span class="summary-icon">🤖</span>
      <span class="summary-label">AI 口碑摘要</span>
      <span class="summary-badge">Beta</span>
    </div>
    <div class="summary-body" v-if="!isLoading">
      <div class="summary-section positive">
        <h5>👍 好评亮点</h5>
        <p>{{ displayHighlights || '暂无数据' }}</p>
      </div>
      <div class="summary-section negative">
        <h5>👎 差评槽点</h5>
        <p>{{ displayComplaints || '暂无数据' }}</p>
      </div>
      <div class="summary-section recent" v-if="displayRecent">
        <h5>📊 近期动态</h5>
        <p>{{ displayRecent }}</p>
      </div>
    </div>
    <div class="summary-loading" v-else>
      <span class="typing-dot"></span>
      <span class="typing-dot"></span>
      <span class="typing-dot"></span>
      <span class="loading-text">正在分析评价...</span>
    </div>
    <div class="summary-sources" v-if="!isLoading && displaySources.length">
      <SourceReference
        v-for="(s, i) in displaySources"
        :key="i"
        v-bind="s"
        @click="$emit('source-click', s)"
      />
    </div>
  </div>
</template>

<script>
import { ref, watch } from 'vue'
import SourceReference from './SourceReference.vue'
import { getBusinessSummary } from '../api/modules/reviews.js'

export default {
  name: 'AISummary',
  components: { SourceReference },
  props: {
    businessId: { type: String, default: '' },
    highlights: { type: String, default: '' },
    complaints: { type: String, default: '' },
    recent: { type: String, default: '' },
    sources: { type: Array, default: () => [] },
    loading: { type: Boolean, default: false }
  },
  emits: ['source-click'],
  data() {
    return {
      fetchedHighlights: '',
      fetchedComplaints: '',
      fetchedRecent: '',
      fetchedSources: [],
      fetching: false,
    }
  },
  computed: {
    displayHighlights() { return this.highlights || this.fetchedHighlights },
    displayComplaints() { return this.complaints || this.fetchedComplaints },
    displayRecent() { return this.recent || this.fetchedRecent },
    displaySources() { return this.sources.length ? this.sources : this.fetchedSources },
    isLoading() { return this.loading || this.fetching },
  },
  watch: {
    businessId: {
      immediate: true,
      handler(id) { if (id) this.fetchFromApi(id) },
    },
  },
  methods: {
    async fetchFromApi(bizId) {
      if (!bizId || this.highlights) return
      this.fetching = true
      try {
        const data = await getBusinessSummary(bizId)
        if (data) {
          const h = data.highlights
          const c = data.concerns || data.lowlights
          const r = data.recent_trend || data.recent_news || data.recent
          if (h?.title) this.fetchedHighlights = h.title + '：' + (h.items || []).map(i => i.point).join('；')
          else if (typeof h === 'string') this.fetchedHighlights = h
          if (c?.title) this.fetchedComplaints = c.title + '：' + (c.items || []).map(i => i.point).join('；')
          else if (typeof c === 'string') this.fetchedComplaints = c
          if (r?.summary) this.fetchedRecent = r.summary
          else if (typeof r === 'string') this.fetchedRecent = r
          const allSources = []
          for (const group of [h, c]) {
            if (group?.items) {
              for (const item of group.items) {
                if (item.sources) allSources.push(...item.sources)
              }
            }
          }
          this.fetchedSources = allSources
        }
      } catch { /* 静默失败 */ }
      finally { this.fetching = false }
    },
  },
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
