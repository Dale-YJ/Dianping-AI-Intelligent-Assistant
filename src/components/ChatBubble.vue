<template>
  <div class="chat-msg" :class="[role, { 'msg-grouped': !isFirstInGroup }]">
    <div class="bubble" :class="role">
      <slot />
    </div>
    <div class="meta" v-if="time && isLastInGroup">{{ time }}</div>
  </div>
</template>

<script>
export default {
  name: 'ChatBubble',
  props: {
    role: { type: String, default: 'ai', validator: v => ['user', 'ai'].includes(v) },
    time: { type: String, default: '' },
    isFirstInGroup: { type: Boolean, default: true },
    isLastInGroup: { type: Boolean, default: true }
  }
}
</script>

<style scoped>
.chat-msg {
  display: flex;
  flex-direction: column;
  margin-bottom: var(--space-4);
  animation: slideInUp 0.35s var(--ease-out) both;
}
.chat-msg.user { align-items: flex-end; }
.chat-msg.ai   { align-items: flex-start; }
/* Grouped messages: tighter spacing */
.chat-msg.msg-grouped { margin-top: calc(var(--space-3) * -1); margin-bottom: var(--space-3); }
.chat-msg.msg-grouped .bubble.ai {
  border-top-left-radius: var(--radius-sm);
}

.bubble {
  max-width: 85%;
  padding: var(--space-3) var(--space-4);
  border-radius: var(--bubble-radius);
  font-size: var(--text-base);
  line-height: var(--leading-relaxed);
  word-break: break-word;
  position: relative;
}
.bubble.user {
  background: var(--bubble-user-bg);
  color: var(--ink);
  border-bottom-right-radius: var(--radius-sm);
}
.bubble.ai {
  background: var(--bubble-ai-bg);
  color: var(--ink);
  border: 1px solid var(--border);
  border-bottom-left-radius: var(--radius-sm);
  overflow: hidden;
}
/* AI bubble left accent bar */
.bubble.ai::before {
  content: '';
  position: absolute;
  left: 0;
  top: 0;
  bottom: 0;
  width: 3px;
  background: var(--ai-accent-bar);
}
.meta {
  margin-top: var(--space-1);
  font-size: var(--text-xs);
  color: var(--ink-muted);
  padding: 0 var(--space-2);
}

@media (min-width: 1024px) {
  .bubble { max-width: 75%; }
}
</style>
