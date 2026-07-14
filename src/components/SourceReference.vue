<template>
  <div class="source-ref" @click="$emit('click')">
    <div class="source-quote">"{{ snippet }}"</div>
    <div class="source-meta">
      <span class="source-user">{{ user }}</span>
      <span class="source-date">{{ date }}</span>
      <span class="source-arrow">查看原文 →</span>
    </div>
  </div>
</template>

<script>
export default {
  name: 'SourceReference',
  props: {
    snippet: { type: String, default: '' },
    user: { type: String, default: '' },
    date: { type: String, default: '' }
  },
  emits: ['click']
}
</script>

<style scoped>
.source-ref {
  background: var(--warm-bg);
  border-left: 3px solid var(--coral);
  border-radius: 0 var(--radius-sm) var(--radius-sm) 0;
  padding: var(--space-2) var(--space-3);
  cursor: pointer;
  transition: all var(--duration-fast);
}
.source-ref:hover { background: var(--coral-pale); }
.source-quote {
  font-size: var(--text-sm);
  color: var(--ink-light);
  font-style: italic;
  margin-bottom: var(--space-1);
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
.source-meta {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  font-size: var(--text-xs);
}
.source-user { color: var(--ink); font-weight: 600; }
.source-date { color: var(--ink-muted); }
.source-arrow { color: var(--coral); margin-left: auto; font-size: var(--text-xs); }
</style>
