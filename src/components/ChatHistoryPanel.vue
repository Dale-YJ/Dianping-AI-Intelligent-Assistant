<template>
  <Teleport to="body">
    <div class="history-overlay" v-if="visible" @click.self="$emit('close')">
      <div class="history-panel" :class="{ 'panel-visible': visible }">
        <!-- Header -->
        <div class="panel-header">
          <h2 class="panel-title">📋 对话记录</h2>
          <button class="panel-close" @click="$emit('close')">✕</button>
        </div>

        <!-- New Chat -->
        <button class="new-chat-btn" @click="$emit('new-chat')">
          <span>＋</span> 新建对话
        </button>

        <!-- Conversation List -->
        <div class="panel-body" v-if="conversations.length">
          <div
            v-for="conv in conversations"
            :key="conv.id"
            class="conv-card"
            :class="{ 'conv-active': conv.id === currentId }"
            @click="$emit('load-conversation', conv.id)"
          >
            <div class="conv-icon">{{ convIcon(conv.title) }}</div>
            <div class="conv-content">
              <p class="conv-title">{{ conv.title }}</p>
              <p class="conv-meta">{{ conv.messageCount }} 条消息 · {{ relativeTime(conv.updatedAt) }}</p>
            </div>
            <button
              class="conv-delete"
              :class="{ 'delete-confirm': deletingId === conv.id }"
              @click.stop="handleDelete(conv.id)"
            >
              {{ deletingId === conv.id ? '确认？' : '🗑' }}
            </button>
          </div>
        </div>

        <!-- Empty State -->
        <div class="panel-empty" v-else>
          <div class="empty-icon">🍜</div>
          <p class="empty-text">暂无对话记录</p>
          <p class="empty-sub">开始你的第一次探店吧</p>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<script>
import { ref } from 'vue'

/* ─── 相对时间格式化 ─── */
function relativeTime(iso) {
  if (!iso) return ''
  const diff = Date.now() - new Date(iso).getTime()
  const minutes = Math.floor(diff / 60000)
  if (minutes < 1) return '刚刚'
  if (minutes < 60) return `${minutes}分钟前`
  const hours = Math.floor(minutes / 60)
  if (hours < 24) return `${hours}小时前`
  const days = Math.floor(hours / 24)
  if (days < 7) return `${days}天前`
  // 显示日期
  const d = new Date(iso)
  return `${d.getMonth() + 1}月${d.getDate()}日`
}

/* ─── 对话 icon 映射 ─── */
function convIcon(title) {
  if (!title) return '💬'
  const map = [
    [/川|辣|火锅|🌶/, '🌶️'],
    [/日料|寿司|拉面|居酒屋|🍣/, '🍣'],
    [/约会|浪漫|安静|💑/, '💑'],
    [/咖啡|学习|☕/, '☕'],
    [/夜宵|深夜|🌙/, '🌙'],
    [/聚餐|聚会|👥/, '👥'],
    [/韩|烤肉|🥩/, '🥩'],
    [/海鲜|🦞/, '🦞'],
    [/甜品|蛋糕|冰淇淋|🍰/, '🍰'],
    [/酒吧|酒|🍸/, '🍸'],
    [/意|披萨|🍝/, '🍝'],
    [/泰|越南|🍜/, '🍜'],
    [/印度|咖喱|🍛/, '🍛'],
    [/汉堡|炸鸡|🍔/, '🍔'],
    [/素食|🥗/, '🥗'],
  ]
  for (const [re, icon] of map) {
    if (re.test(title)) return icon
  }
  return '🍴'
}

export default {
  name: 'ChatHistoryPanel',
  props: {
    visible: { type: Boolean, default: false },
    conversations: { type: Array, default: () => [] },
    currentId: { type: String, default: '' }
  },
  emits: ['close', 'new-chat', 'load-conversation', 'delete-conversation'],
  data() {
    return { deletingId: null }
  },
  methods: {
    relativeTime,
    convIcon,
    handleDelete(id) {
      if (this.deletingId === id) {
        this.$emit('delete-conversation', id)
        this.deletingId = null
      } else {
        this.deletingId = id
        // 3 秒后恢复
        setTimeout(() => { if (this.deletingId === id) this.deletingId = null }, 3000)
      }
    }
  },
  watch: {
    visible(val) {
      if (!val) this.deletingId = null
    }
  }
}
</script>

<style scoped>
/* ── Overlay ── */
.history-overlay {
  position: fixed;
  inset: 0;
  background: rgba(26, 26, 46, 0.4);
  backdrop-filter: blur(4px);
  -webkit-backdrop-filter: blur(4px);
  z-index: 150;
  animation: fadeIn 0.2s ease;
}

/* ── Panel ── */
.history-panel {
  position: absolute;
  top: 0;
  right: 0;
  width: 85%;
  max-width: 400px;
  height: 100%;
  background: var(--card-bg);
  display: flex;
  flex-direction: column;
  box-shadow: var(--shadow-xl);
  animation: slideInRight 0.3s var(--ease-out) both;
}

/* ── Header ── */
.panel-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--space-4);
  border-bottom: 1px solid var(--border);
  flex-shrink: 0;
}
.panel-title {
  font-family: var(--font-display);
  font-size: var(--text-lg);
  font-weight: 700;
}
.panel-close {
  width: 2rem;
  height: 2rem;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--warm-bg);
  font-size: var(--text-sm);
  transition: background var(--duration-fast);
}
.panel-close:hover { background: var(--border); }

/* ── New Chat Button ── */
.new-chat-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: var(--space-1);
  margin: var(--space-3) var(--space-4);
  padding: var(--space-3);
  background: var(--coral-pale);
  color: var(--coral);
  border-radius: var(--radius-md);
  font-size: var(--text-sm);
  font-weight: 600;
  transition: all var(--duration-fast);
  flex-shrink: 0;
}
.new-chat-btn:hover { background: var(--coral); color: #fff; }

/* ── Body ── */
.panel-body {
  flex: 1;
  overflow-y: auto;
  padding: 0 var(--space-4) var(--space-4);
  overscroll-behavior: contain;
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

/* ── Conversation Card ── */
.conv-card {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  padding: var(--space-3);
  background: var(--card-warm);
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
  cursor: pointer;
  transition: all var(--duration-fast);
}
.conv-card:hover { border-color: var(--coral); }
.conv-card.conv-active { border-color: var(--coral); background: var(--coral-pale); }
.conv-icon {
  font-size: 1.5rem;
  flex-shrink: 0;
  width: 2.5rem;
  text-align: center;
}
.conv-content {
  flex: 1;
  min-width: 0;
}
.conv-title {
  font-size: var(--text-sm);
  font-weight: 600;
  color: var(--ink);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  margin-bottom: 2px;
}
.conv-meta {
  font-size: var(--text-xs);
  color: var(--ink-muted);
}
.conv-delete {
  flex-shrink: 0;
  font-size: var(--text-sm);
  padding: var(--space-1);
  border-radius: var(--radius-sm);
  transition: all var(--duration-fast);
  opacity: 0.5;
}
.conv-delete:hover { opacity: 1; background: var(--warm-bg); }
.conv-delete.delete-confirm {
  opacity: 1;
  background: #FEE2E2;
  color: #EF4444;
  font-size: var(--text-xs);
  padding: var(--space-1) var(--space-2);
  font-weight: 600;
}

/* ── Empty State ── */
.panel-empty {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: var(--space-8);
  text-align: center;
}
.empty-icon { font-size: 3rem; margin-bottom: var(--space-3); }
.empty-text {
  font-family: var(--font-display);
  font-size: var(--text-md);
  font-weight: 700;
  color: var(--ink);
  margin-bottom: var(--space-1);
}
.empty-sub { font-size: var(--text-sm); color: var(--ink-muted); }
</style>
