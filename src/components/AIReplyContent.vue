<template>
  <div class="ai-reply" :class="{ 'is-fallback': parsed.isFallback }">
    <!-- ═══ Fallback / No Results ═══ -->
    <div class="reply-fallback" v-if="parsed.isFallback">
      <div class="fallback-icon">🔍</div>
      <p class="fallback-text" v-if="parsed.fallbackText">{{ parsed.fallbackText }}</p>
      <p class="fallback-hint" v-if="parsed.fallbackHint">{{ parsed.fallbackHint }}</p>
    </div>

    <!-- ═══ Conversational Reply ═══ -->
    <div class="reply-conversational" v-else-if="parsed.mode === 'conversational'">
      <p
        v-for="(block, bi) in conversationalBlocks"
        :key="bi"
        class="conv-block"
        :class="block.type"
        v-html="block.html"
      ></p>
    </div>

    <!-- ═══ Structured Reply (legacy format) ═══ -->
    <template v-else>
      <!-- Header -->
      <div class="reply-header" v-if="parsed.header">
        <span class="header-emoji">{{ parsed.header.emoji }}</span>
        <span class="header-text">{{ parsed.header.text }}</span>
      </div>

      <!-- Ranked Items -->
      <ol class="reply-items" v-if="parsed.items.length">
        <li
          v-for="(item, i) in parsed.items"
          :key="i"
          class="reply-item"
          :class="rankClass(i)"
          :style="{ animationDelay: (i * 0.08) + 's' }"
        >
          <span class="item-medal">{{ item.medal }}</span>
          <div class="item-body">
            <div class="item-main">
              <strong class="item-name">{{ item.name }}</strong>
              <span class="item-stars">
                <span v-for="s in 5" :key="s" class="star" :class="s <= item.stars ? 'star-full' : 'star-empty'">{{ s <= item.stars ? '★' : '☆' }}</span>
              </span>
              <span class="item-rating">{{ item.rating }}</span>
              <span class="item-reviews" v-if="item.reviews">{{ item.reviews }}</span>
            </div>
            <div class="item-location" v-if="item.location">
              <span>📍 {{ item.location }}</span>
            </div>
          </div>
        </li>
      </ol>

      <!-- Teaser -->
      <p class="reply-teaser" v-if="parsed.teaser">{{ parsed.teaser }}</p>

      <!-- Categories -->
      <div class="reply-categories" v-if="parsed.categories">
        <span class="cat-icon">🏷️</span>
        <span class="cat-text">{{ parsed.categories }}</span>
      </div>
    </template>
  </div>
</template>

<script>
import { parseAIReply } from '../utils/parseAIReply.js'

/**
 * 将对话式 AI 回复文本逐行渲染为段落和列表块。
 * 规则：
 * - 以 - 或 • 开头的行 → 列表项，连续列表项合并为一个 <ul>
 * - 空行 → 段落边界
 * - 其他行 → 普通段落
 * - **text** → <strong> 行内加粗
 */
function renderConversational(text) {
  if (!text) return []

  const lines = text.split('\n')
  const blocks = []
  let currentList = [] // 收集连续的列表项
  let currentPara = [] // 收集连续的普通行

  function flushList() {
    if (!currentList.length) return
    const items = currentList
      .map(l => `<li>${renderInline(l.replace(/^[-•]\s*/, ''))}</li>`)
      .join('')
    blocks.push({ type: 'conv-list', html: `<ul>${items}</ul>` })
    currentList = []
  }

  function flushPara() {
    if (!currentPara.length) return
    const html = currentPara
      .map(l => renderInline(l))
      .join('<br>')
    blocks.push({ type: 'conv-para', html })
    currentPara = []
  }

  for (const raw of lines) {
    const line = raw.trim()

    // 空行 → 刷新所有缓冲
    if (!line) {
      flushList()
      flushPara()
      continue
    }

    // 列表项
    if (/^[-•]\s/.test(line)) {
      flushPara()  // 先刷新前面的普通行
      currentList.push(line)
      continue
    }

    // 普通行
    flushList()    // 先刷新前面的列表
    currentPara.push(line)
  }

  // 收尾
  flushList()
  flushPara()

  return blocks
}

/** 行内 markdown：转义 HTML → **bold** → <strong> */
function renderInline(text) {
  if (!text) return ''
  let html = text
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
  html = html.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
  return html
}

export default {
  name: 'AIReplyContent',
  props: {
    text: { type: String, default: '' }
  },
  computed: {
    parsed() {
      return parseAIReply(this.text)
    },
    conversationalBlocks() {
      if (this.parsed.mode !== 'conversational') return []
      return renderConversational(this.parsed.conversationalText || this.text)
    },
  },
  methods: {
    rankClass(index) {
      if (index === 0) return 'rank-gold'
      if (index === 1) return 'rank-silver'
      if (index === 2) return 'rank-bronze'
      return ''
    }
  }
}
</script>

<style scoped>
/* ── Container ── */
.ai-reply {
  animation: fadeUp 0.4s var(--ease-out) both;
}

/* ═══════════════════════════════
   CONVERSATIONAL MODE
   ═══════════════════════════════ */
.reply-conversational {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}

.conv-block {
  font-size: var(--text-sm);
  color: var(--ink-light);
  line-height: var(--leading-relaxed);
  margin: 0;
}

/* 列表样式 */
.conv-block.conv-list ul {
  margin: 0;
  padding-left: var(--space-4);
  list-style: none;
}
.conv-block.conv-list li {
  position: relative;
  padding-left: var(--space-3);
  margin-bottom: 4px;
  color: var(--ink-light);
  line-height: var(--leading-relaxed);
}
.conv-block.conv-list li::before {
  content: '·';
  position: absolute;
  left: 0;
  top: 0;
  color: var(--coral);
  font-weight: 700;
  font-size: 1.25rem;
  line-height: 1;
}
.conv-block.conv-list li:last-child { margin-bottom: 0; }

/* 段落中的 strong */
.conv-block.conv-para :deep(strong),
.conv-block.conv-list :deep(strong) {
  color: var(--ink);
  font-weight: 700;
}

/* ═══════════════════════════════
   STRUCTURED MODE (legacy)
   ═══════════════════════════════ */

/* ── Header ── */
.reply-header {
  display: flex;
  align-items: flex-start;
  gap: var(--space-2);
  padding-bottom: var(--space-3);
  margin-bottom: var(--space-3);
  border-bottom: 1px solid var(--border);
}
.header-emoji {
  font-size: 1.5rem;
  line-height: 1.2;
}
.header-text {
  font-family: var(--font-display);
  font-size: var(--text-md);
  font-weight: 700;
  color: var(--ink);
  line-height: var(--leading-tight);
}

/* ── Items List ── */
.reply-items {
  list-style: none;
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}
.reply-item {
  display: flex;
  gap: var(--space-2);
  padding: var(--space-3);
  background: var(--card-warm);
  border-radius: var(--radius-md);
  border: 1px solid var(--border);
  animation: slideInUp 0.35s var(--ease-out) both;
  transition: border-color var(--duration-fast);
}
.reply-item.rank-gold { border-left: 3px solid var(--rank-gold); }
.reply-item.rank-silver { border-left: 3px solid var(--rank-silver); }
.reply-item.rank-bronze { border-left: 3px solid var(--rank-bronze); }

.item-medal {
  font-size: 1.5rem;
  flex-shrink: 0;
  line-height: 1.2;
}
.item-body {
  flex: 1;
  min-width: 0;
}
.item-main {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: var(--space-1);
  line-height: var(--leading-relaxed);
}
.item-name {
  font-family: var(--font-display);
  font-size: var(--text-md);
  font-weight: 700;
  color: var(--ink);
}
.item-stars {
  font-size: var(--text-sm);
  letter-spacing: 1px;
  display: inline-flex;
  align-items: center;
  margin-left: var(--space-1);
}
.star-full { color: var(--amber); }
.star-empty { color: #DDD; }
.item-rating {
  font-size: var(--text-sm);
  font-weight: 700;
  color: var(--amber);
  min-width: 2em;
}
.item-reviews {
  font-size: var(--text-xs);
  color: var(--ink-muted);
}
.item-location {
  margin-top: var(--space-1);
  font-size: var(--text-xs);
  color: var(--ink-muted);
}

/* ── Teaser ── */
.reply-teaser {
  margin-top: var(--space-3);
  padding: var(--space-2) 0;
  text-align: center;
  font-size: var(--text-sm);
  color: var(--ink-muted);
  font-style: italic;
  border-top: 1px dashed var(--border);
}

/* ── Categories ── */
.reply-categories {
  margin-top: var(--space-3);
  padding: var(--space-2) var(--space-3);
  background: var(--coral-pale);
  border-radius: var(--radius-full);
  display: inline-flex;
  align-items: center;
  gap: var(--space-1);
  font-size: var(--text-xs);
  color: var(--coral-deep);
}
.cat-icon { flex-shrink: 0; }
.cat-text { white-space: nowrap; }

/* ═══════════════════════════════
   FALLBACK MODE
   ═══════════════════════════════ */
.reply-fallback {
  text-align: center;
  padding: var(--space-4);
  background: var(--card-warm);
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
  animation: fadeUp 0.3s var(--ease-out) both;
}
.fallback-icon {
  font-size: 2.5rem;
  margin-bottom: var(--space-3);
}
.fallback-text {
  font-size: var(--text-base);
  color: var(--ink-light);
  line-height: var(--leading-relaxed);
  white-space: pre-line;
}
.fallback-hint {
  margin-top: var(--space-2);
  font-size: var(--text-sm);
  color: var(--ink-muted);
  white-space: pre-line;
}
</style>
