<template>
  <div class="chat-input-wrapper">
    <div class="chat-input-bar">
      <input
        ref="inputRef"
        v-model="text"
        class="chat-input"
        type="text"
        :placeholder="placeholder"
        @keydown.enter.exact.prevent="send"
        @compositionstart="composing = true"
        @compositionend="composing = false"
      />
      <button
        class="send-btn"
        :class="{ active: text.trim() && !disabled }"
        :disabled="!text.trim() || disabled"
        @click="send"
      >
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
          <line x1="12" y1="19" x2="12" y2="5"/>
          <polyline points="5 12 12 5 19 12"/>
        </svg>
      </button>
    </div>
    <p class="chat-hint" v-if="showHint && !warningMsg">💡 试试：「附近有什么好吃的川菜」「安静的咖啡馆推荐」</p>
    <p class="chat-warning" v-if="warningMsg">{{ warningMsg }}</p>
  </div>
</template>

<script>
import { validateInput } from '../utils/contentFilter.js'

export default {
  name: 'ChatInput',
  props: {
    placeholder: { type: String, default: '输入你想吃的、想玩的...' },
    disabled: { type: Boolean, default: false },
    showHint: { type: Boolean, default: true }
  },
  emits: ['send'],
  data() {
    return { text: '', composing: false, warningMsg: '' }
  },
  methods: {
    send() {
      const val = this.text.trim()
      if (!val || this.disabled) return
      if (this.composing) return

      // 违禁词审核
      const result = validateInput(val)
      if (!result.valid) {
        this.warningMsg = result.reason
        setTimeout(() => { this.warningMsg = '' }, 3000)
        return
      }

      this.warningMsg = ''
      this.$emit('send', val)
      this.text = ''
    }
  }
}
</script>

<style scoped>
.chat-input-wrapper {
  padding: var(--space-3) var(--space-4);
  background: var(--card-bg);
  border-top: 1px solid var(--border);
}
.chat-input-bar {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  background: var(--warm-bg);
  border: 1px solid var(--border);
  border-radius: var(--radius-full);
  padding: var(--space-1) var(--space-1) var(--space-1) var(--space-5);
  transition: border-color var(--duration-fast), box-shadow var(--duration-fast);
}
.chat-input-bar:focus-within {
  border-color: var(--coral);
  box-shadow: 0 0 0 3px rgba(255, 107, 53, 0.1);
}
.chat-input {
  flex: 1;
  border: none;
  background: transparent;
  font-size: var(--text-base);
  color: var(--ink);
  outline: none;
  padding: var(--space-3) 0;
  min-width: 0;
}
.chat-input::placeholder { color: var(--ink-muted); }
.send-btn {
  flex-shrink: 0;
  width: 2.75rem;
  height: 2.75rem;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--ink-muted);
  background: var(--border);
  transition: all var(--duration-fast) var(--ease-out);
}
.send-btn.active {
  color: #fff;
  background: var(--coral);
}
.chat-hint {
  margin-top: var(--space-2);
  font-size: var(--text-xs);
  color: var(--ink-muted);
  text-align: center;
}
.chat-warning {
  margin-top: var(--space-2);
  font-size: var(--text-xs);
  color: #DC2626;
  text-align: center;
  animation: fadeUp 0.2s ease;
}
</style>
