<template>
  <div class="chat-page">
    <!-- Chat Panel -->
    <div class="chat-panel" ref="chatPanel">
      <div class="chat-header">
        <div class="header-brand">
          <span class="brand-icon">🥢</span>
          <div>
            <h1 class="brand-name">AI 探店助手</h1>
            <p class="brand-sub">3 公里生活圈 · 智能推荐</p>
          </div>
        </div>
        <button class="header-action" @click="clearChat" v-if="messages.length > 1">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="1 4 1 10 7 10"/><path d="M3.51 15a9 9 0 1 0 2.13-9.36L1 10"/></svg>
        </button>
      </div>

      <div class="chat-messages" ref="msgContainer">
        <!-- Welcome -->
        <div v-if="messages.length === 0" class="welcome-area">
          <div class="welcome-icon">🍜</div>
          <h2 class="welcome-title">今天想吃什么？</h2>
          <p class="welcome-sub">告诉我你的口味、预算、场景，我来帮你找</p>
          <div class="quick-chips">
            <button
              v-for="q in quickQueries"
              :key="q"
              class="quick-chip"
              @click="sendMessage(q)"
            >{{ q }}</button>
          </div>
        </div>

        <!-- Messages -->
        <template v-for="(msg, i) in messages" :key="i">
          <!-- User message -->
          <ChatBubble role="user" :time="msg.time" v-if="msg.role === 'user'">
            {{ msg.text }}
          </ChatBubble>

          <!-- AI thinking -->
          <ChatBubble role="ai" v-else-if="msg.role === 'thinking'">
            <span class="typing-dot"></span>
            <span class="typing-dot"></span>
            <span class="typing-dot"></span>
          </ChatBubble>

          <!-- AI response -->
          <ChatBubble role="ai" :time="msg.time" v-else-if="msg.role === 'ai'">
            <p class="ai-intro" v-if="msg.intro">{{ msg.intro }}</p>
            <div class="rec-list" v-if="msg.recs && msg.recs.length">
              <RecommendationCard
                v-for="(rec, j) in msg.recs"
                :key="j"
                v-bind="rec"
                :style="{ animationDelay: (j * 0.1) + 's' }"
                @click="goToShop(rec.id)"
                @source-click="s => showSource(s)"
              />
            </div>
            <div class="fallback-msg" v-if="msg.fallback">
              <p>😅 {{ msg.fallback }}</p>
            </div>
          </ChatBubble>
        </template>
        <div ref="msgEnd"></div>
      </div>

      <ChatInput
        :disabled="isThinking"
        :show-hint="messages.length === 0"
        placeholder="输入你想吃的、想玩的... 如「附近有什么好吃的川菜」"
        @send="sendMessage"
      />
    </div>

    <!-- Desktop: Recommendation Side Panel -->
    <div class="side-panel" v-if="latestRecs.length && isDesktop">
      <div class="side-panel-header">
        <h2 class="side-title">推荐结果</h2>
      </div>
      <div class="side-panel-body">
        <RecommendationCard
          v-for="(rec, j) in latestRecs"
          :key="j"
          v-bind="rec"
          :style="{ animationDelay: (j * 0.08) + 's' }"
          @click="goToShop(rec.id)"
          @source-click="s => showSource(s)"
        />
      </div>
    </div>

    <!-- Source Modal -->
    <Teleport to="body">
      <div class="modal-overlay" v-if="selectedSource" @click.self="selectedSource = null">
        <div class="modal-content">
          <div class="modal-header">
            <h3>📎 原始评价</h3>
            <button class="modal-close" @click="selectedSource = null">✕</button>
          </div>
          <div class="modal-body">
            <div class="source-user-info">
              <span class="source-avatar">{{ selectedSource.user[0] }}</span>
              <div>
                <strong>{{ selectedSource.user }}</strong>
                <span class="source-date">{{ selectedSource.date }}</span>
              </div>
            </div>
            <div class="source-stars">{{ '★'.repeat(selectedSource.stars || 4) }}{{ '☆'.repeat(5 - (selectedSource.stars || 4)) }}</div>
            <p class="source-full-text">{{ selectedSource.fullText || selectedSource.snippet }}</p>
          </div>
        </div>
      </div>
    </Teleport>
  </div>
</template>

<script>
import { ref, computed, onMounted, onBeforeUnmount, nextTick } from 'vue'
import ChatInput from '../components/ChatInput.vue'
import ChatBubble from '../components/ChatBubble.vue'
import RecommendationCard from '../components/RecommendationCard.vue'
import { postRecommend, getQuickTags } from '../api/modules/chat.js'

/* ─── 推荐数据映射: API → 组件 props ─── */
const IMG_GRADIENTS = [
  'linear-gradient(135deg, #C0392B, #E74C3C)',
  'linear-gradient(135deg, #8B0000, #DC143C)',
  'linear-gradient(135deg, #5D4037, #8D6E63)',
  'linear-gradient(135deg, #2D1B2E, #3D2E3E)',
  'linear-gradient(135deg, #1A3A2A, #2A4A3A)',
  'linear-gradient(135deg, #3D2E1A, #5D4E3A)',
  'linear-gradient(135deg, #2D1A1A, #4D2A2A)',
  'linear-gradient(135deg, #1A2D3D, #2A3D4D)',
]

function hashGradient(str) {
  let hash = 0
  for (let i = 0; i < str.length; i++) hash = str.charCodeAt(i) + ((hash << 5) - hash)
  return IMG_GRADIENTS[Math.abs(hash) % IMG_GRADIENTS.length]
}

function mapRecommendation(apiRec) {
  return {
    id: apiRec.business_id,
    name: apiRec.name,
    rating: apiRec.rating,
    categories: (apiRec.categories || []).join(' · '),
    price: '--',
    distance: '--',
    reason: apiRec.reason,
    tags: apiRec.tags || [],
    imgBg: hashGradient(apiRec.business_id || apiRec.name),
    sources: (apiRec.sources || []).map(s => ({
      user: s.user_name,
      date: s.date,
      snippet: s.snippet,
      fullText: s.snippet,
      stars: s.rating,
      reviewId: s.review_id,
    })),
  }
}

/** dev mock 回退数据 */
const MOCK_RECS = [
  {
    id: 'biz_001', name: '川味轩', rating: 4.3,
    categories: '川菜', price: '¥85', distance: '0.8km',
    reason: '口水鸡被28位食客推荐，红油鲜香、鸡肉嫩滑；水煮鱼也是招牌。',
    imgBg: 'linear-gradient(135deg, #C0392B, #E74C3C)',
    sources: [
      { user: '食客小王', date: '2026-07-10', snippet: '口水鸡超级好吃！鸡肉嫩滑，红油特别香...', fullText: '口水鸡超级好吃！鸡肉嫩滑，红油特别香，分量也足。', stars: 5 },
    ],
  },
]

export default {
  name: 'HomePage',
  components: { ChatInput, ChatBubble, RecommendationCard },
  setup() {
    /* ─── 响应式状态 ─── */
    const messages = ref([])
    const isThinking = ref(false)
    const sessionId = ref(tryLoadSession())
    const selectedSource = ref(null)
    const isDesktop = ref(false)
    const quickQueries = ref([
      '附近有什么好吃的川菜？',
      '适合约会的安静餐厅推荐',
      '哪家咖啡馆适合学习？',
      '实惠的夜宵推荐',
      '适合聚餐的地方',
    ])

    /* ─── 计算属性 ─── */
    const latestRecs = computed(() => {
      for (let i = messages.value.length - 1; i >= 0; i--) {
        const m = messages.value[i]
        if (m.role === 'ai' && m.recs && m.recs.length) return m.recs
      }
      return []
    })

    /* ─── 工具函数 ─── */
    function timeStr() {
      return new Date().toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
    }
    function scrollDown() {
      nextTick(() => {
        const end = document.querySelector('.chat-messages')
        if (end) end.lastElementChild?.scrollIntoView({ behavior: 'smooth' })
      })
    }
    function tryLoadSession() {
      try { return sessionStorage.getItem('dp_ai_session_id') || null } catch { return null }
    }
    function saveSession(id) {
      try { sessionStorage.setItem('dp_ai_session_id', id) } catch {}
    }

    /* ─── 发送消息（真实 API + dev mock 回退） ─── */
    async function sendMessage(text) {
      if (!text.trim() || isThinking.value) return

      const t = timeStr()
      messages.value.push({ role: 'user', text: text.trim(), time: t })
      scrollDown()

      isThinking.value = true
      messages.value.push({ role: 'thinking', time: '' })
      scrollDown()

      try {
        const data = await postRecommend({
          query: text.trim(),
          sessionId: sessionId.value,
          topK: 5,
        })

        if (data.session_id) {
          sessionId.value = data.session_id
          saveSession(data.session_id)
        }

        messages.value.pop()
        messages.value.push({
          role: 'ai',
          intro: data.answer,
          recs: (data.recommendations || []).map(mapRecommendation),
          fallback: '',
          time: timeStr(),
        })
      } catch (err) {
        messages.value.pop()

        // 兜底 code 1001 — API 返回了 alternatives
        if (err.code === 1001 && err.data) {
          messages.value.push({
            role: 'ai', intro: '', recs: [],
            fallback: err.data.answer || err.message,
            time: timeStr(),
          })
        } else if (import.meta.env.DEV) {
          // 开发环境 mock 回退
          console.warn('[DEV] API 不可用，使用 mock 数据:', err.message)
          await new Promise(r => setTimeout(r, 400 + Math.random() * 400))
          messages.value.push({
            role: 'ai',
            intro: '（开发模式）为你找到以下推荐 👇',
            recs: MOCK_RECS,
            fallback: '',
            time: timeStr(),
          })
        } else {
          messages.value.push({
            role: 'ai', intro: '', recs: [],
            fallback: err.message || '抱歉，发生了未知错误',
            time: timeStr(),
          })
        }
      } finally {
        isThinking.value = false
        scrollDown()
      }
    }

    /* ─── 其他操作 ─── */
    function clearChat() { messages.value = [] }
    function showSource(s) { selectedSource.value = s }
    function goToShop(id) {
      const detailId = typeof id === 'string' ? id : String(id)
      this.$router.push(`/detail/${detailId}`)
    }

    /* ─── 加载快捷标签 ─── */
    async function loadQuickTags() {
      try {
        const tags = await getQuickTags()
        if (tags && tags.length) quickQueries.value = tags.map(t => t.text)
      } catch { /* 后端未就绪，保留默认 */ }
    }

    /* ─── 响应式断点 ─── */
    function onResize() { isDesktop.value = window.innerWidth >= 1024 }
    onMounted(() => { onResize(); window.addEventListener('resize', onResize); loadQuickTags() })
    onBeforeUnmount(() => window.removeEventListener('resize', onResize))

    return {
      messages, isThinking, sessionId,
      selectedSource, isDesktop, quickQueries, latestRecs,
      sendMessage, clearChat, showSource, goToShop,
    }
  },
}
</script>

<style scoped>
.chat-page {
  display: flex;
  height: calc(100dvh - var(--tab-height));
  overflow: hidden;
}

/* ── Chat Panel ── */
.chat-panel {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
}
.chat-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--space-3) var(--space-4);
  border-bottom: 1px solid var(--border);
  background: var(--card-bg);
  flex-shrink: 0;
}
.header-brand { display: flex; align-items: center; gap: var(--space-3); }
.brand-icon { font-size: 1.75rem; }
.brand-name {
  font-family: var(--font-display);
  font-size: var(--text-lg);
  font-weight: 700;
  line-height: var(--leading-tight);
}
.brand-sub { font-size: var(--text-xs); color: var(--ink-muted); }
.header-action {
  width: 2.5rem;
  height: 2.5rem;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--ink-muted);
  transition: all var(--duration-fast);
}
.header-action:hover { background: var(--warm-bg); color: var(--coral); }

/* ── Messages ── */
.chat-messages {
  flex: 1;
  overflow-y: auto;
  padding: var(--space-4);
  overscroll-behavior: contain;
  -webkit-overflow-scrolling: touch;
}

/* Welcome */
.welcome-area { text-align: center; padding: var(--space-10) var(--space-4); }
.welcome-icon { font-size: 3.5rem; margin-bottom: var(--space-4); }
.welcome-title {
  font-family: var(--font-display);
  font-size: var(--text-2xl);
  font-weight: 700;
  margin-bottom: var(--space-2);
}
.welcome-sub { font-size: var(--text-sm); color: var(--ink-muted); margin-bottom: var(--space-6); }
.quick-chips {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2);
  justify-content: center;
}
.quick-chip {
  padding: var(--space-2) var(--space-4);
  background: var(--card-warm);
  border: 1px solid var(--border);
  border-radius: var(--radius-full);
  font-size: var(--text-sm);
  color: var(--ink-light);
  transition: all var(--duration-fast);
  white-space: nowrap;
}
.quick-chip:hover {
  border-color: var(--coral);
  color: var(--coral);
  background: var(--coral-pale);
}

.ai-intro {
  font-size: var(--text-sm);
  color: var(--ink-muted);
  margin-bottom: var(--space-3);
}
.rec-list { display: flex; flex-direction: column; gap: var(--space-3); }
.fallback-msg { padding: var(--space-3); background: var(--warm-bg); border-radius: var(--radius-md); }
.fallback-msg p { font-size: var(--text-sm); color: var(--ink-light); }

/* ── Side Panel (Desktop) ── */
.side-panel {
  width: 45%;
  max-width: 520px;
  border-left: 1px solid var(--border);
  background: var(--warm-bg);
  display: flex;
  flex-direction: column;
  overflow: hidden;
}
.side-panel-header {
  padding: var(--space-3) var(--space-4);
  background: var(--card-bg);
  border-bottom: 1px solid var(--border);
  flex-shrink: 0;
}
.side-title {
  font-family: var(--font-display);
  font-size: var(--text-md);
  font-weight: 700;
}
.side-panel-body {
  flex: 1;
  overflow-y: auto;
  padding: var(--space-4);
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}

/* ── Modal ── */
.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(26, 26, 46, 0.5);
  backdrop-filter: blur(4px);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 200;
  padding: var(--space-4);
  animation: fadeIn 0.2s ease;
}
.modal-content {
  background: var(--card-bg);
  border-radius: var(--radius-xl);
  max-width: 480px;
  width: 100%;
  max-height: 80vh;
  overflow-y: auto;
  box-shadow: var(--shadow-xl);
  animation: scaleIn 0.3s var(--ease-spring);
}
.modal-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--space-4);
  border-bottom: 1px solid var(--border);
  position: sticky;
  top: 0;
  background: var(--card-bg);
  z-index: 1;
}
.modal-header h3 { font-family: var(--font-display); font-size: var(--text-md); }
.modal-close {
  width: 2rem;
  height: 2rem;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--warm-bg);
  font-size: var(--text-sm);
}
.modal-body { padding: var(--space-4); }
.source-user-info { display: flex; gap: var(--space-3); align-items: center; margin-bottom: var(--space-3); }
.source-avatar {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  background: var(--coral-pale);
  color: var(--coral);
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 700;
  font-size: var(--text-md);
}
.source-date { display: block; font-size: var(--text-xs); color: var(--ink-muted); }
.source-stars { color: var(--amber); font-size: var(--text-sm); margin-bottom: var(--space-3); }
.source-full-text { font-size: var(--text-base); line-height: var(--leading-relaxed); color: var(--ink-light); }

/* ── Responsive ── */
@media (max-width: 1023px) {
  .side-panel { display: none; }
}
@media (min-width: 1024px) {
  .chat-panel { border-right: none; }
  .chat-header { padding: var(--space-4) var(--space-6); }
  .chat-messages { padding: var(--space-4) var(--space-6); }
  .welcome-area { padding: var(--space-12) var(--space-6); }
}
</style>
