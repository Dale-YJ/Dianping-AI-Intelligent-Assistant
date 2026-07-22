<template>
  <div class="typing-indicator">
    <span class="typing-dot"></span>
    <span class="typing-dot"></span>
    <span class="typing-dot"></span>
    <span class="typing-label">{{ label }}</span>
  </div>
</template>

<script>
export default {
  name: 'TypingIndicator',
  props: {
    label: { type: String, default: '正在为你寻找...' }
  }
}
</script>

<style scoped>
.typing-indicator {
  display: flex;
  align-items: center;
  gap: var(--space-1);
  padding: var(--space-1) 0;
  animation: fadeUp 0.3s var(--ease-out) both;
}

/* 复用 tokens.css 的 typingDot 关键帧动画 */
@keyframes typingDot {
  0%, 60%, 100% { transform: translateY(0); opacity: 0.4; }
  30% { transform: translateY(-8px); opacity: 1; }
}

.typing-dot {
  display: inline-block;
  width: 0.5rem;
  height: 0.5rem;
  border-radius: 50%;
  background: var(--amber);
  animation: typingDot 1.4s infinite;
}

.typing-dot:nth-child(2) { animation-delay: 0.2s; }
.typing-dot:nth-child(3) { animation-delay: 0.4s; }

.typing-label {
  margin-left: var(--space-2);
  font-size: var(--text-sm);
  color: var(--ink-muted);
}
</style>
