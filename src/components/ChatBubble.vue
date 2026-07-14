<template>
  <div class="chat-msg" :class="role">
    <div class="bubble" :class="role">
      <slot />
    </div>
    <div class="meta" v-if="time">{{ time }}</div>
  </div>
</template>

<script>
export default {
  name: 'ChatBubble',
  props: {
    role: { type: String, default: 'ai', validator: v => ['user', 'ai'].includes(v) },
    time: { type: String, default: '' }
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

.bubble {
  max-width: 85%;
  padding: var(--space-3) var(--space-4);
  border-radius: var(--bubble-radius);
  font-size: var(--text-base);
  line-height: var(--leading-relaxed);
  word-break: break-word;
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
