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

          <!-- AI response -->
          <ChatBubble role="ai" :time="msg.time" v-else-if="msg.role === 'ai'">
            <p class="ai-intro" v-if="msg.intro">{{ msg.intro }}</p>
            <div class="rec-list" v-if="msg.recs && msg.recs.length && !isDesktop">
              <RecommendationCard
                v-for="(rec, j) in msg.recs"
                :key="j"
                v-bind="rec"
                :style="{ animationDelay: (j * 0.1) + 's' }"
                @click="goToShop(rec)"
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
                <span class="source-biz" v-if="selectedSource.businessName">@{{ selectedSource.businessName }}</span>
              </div>
            </div>
            <div class="source-stars">
              <span v-for="i in 5" :key="i" class="star" :class="sourceStarClass(i)">{{ sourceStarChar(i) }}</span>
            </div>
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
import { postChatSend } from '../api/modules/chat.js'
import { sharedStore } from '../stores/sharedData.js'
import { useTranslate } from '../composables/useTranslate.js'

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
    reviewCount: apiRec.review_count || 0,
    address: apiRec.address || '',
    city: apiRec.city || '',
    score: apiRec.score || 0,
    imgBg: hashGradient(apiRec.business_id || apiRec.name),
    sources: (apiRec.sources || []).map((s, i) => ({
      user: s.user_name,
      date: s.date,
      snippet: s.text,
      fullText: s.text,
      stars: s.rating,
      reviewId: `src_${i}`,
      businessName: s.business_name || '',
    })),
  }
}

/**
 * 非餐饮类关键词 — 用于前端过滤明显不相关的商家（如理发店、修车行等）。
 * 后端 embedding 模型仅支持英文 + similarity_threshold 过低，
 * 导致不相关结果通过。前端做最后一道防线。
 */
const NON_FOOD_WORDS = /\b(barber|hair\s*cut|hair\s*styl|salon|spa|nail\s|massage|gym|fitness|yoga|auto\s|car\s|gas\s|laundry|dry\s*clean|dentist|doctor|hospital|pharmacy|vet\s|pet\s|bank|atm|insurance|real\s*estate|lawyer|plumber|electric|storage|moving|shipping|hardware|jewelry|watch|clothing|shoe|tailor|tobacco|vape|cannabis|liquor|cleaner|carpet|glass|roofing|pest\s)\b/i

function isFoodBusiness(rec) {
  const cats = (rec.categories || '').toLowerCase()
  // 命中了非餐饮关键词 → 过滤掉
  return !NON_FOOD_WORDS.test(cats)
}

/**
 * 过滤推荐结果：去重 + 分数断崖 + 非餐饮排除。
 */
function filterRecommendations(recs) {
  if (!recs || !recs.length) return []

  // 0. 按 business_id 去重（保留分数最高的那条）
  const seen = new Set()
  const deduped = []
  for (const r of recs) {
    const id = r.id || r.business_id
    if (!id || seen.has(id)) continue
    seen.add(id)
    deduped.push(r)
  }

  // 按分数降序
  const sorted = [...deduped].sort((a, b) => (b.score || 0) - (a.score || 0))

  // 1. 检测分数断崖 — 相邻落差 > 30% 则截断
  const cutoff = []
  for (let i = 0; i < sorted.length; i++) {
    if (i === 0) {
      cutoff.push(sorted[i])
      continue
    }
    const prevScore = sorted[i - 1].score || 0
    const curScore = sorted[i].score || 0
    if (prevScore > 0 && curScore / prevScore < 0.7) break
    cutoff.push(sorted[i])
  }

  // 2. 排除非餐饮类
  return cutoff.filter(isFoodBusiness)
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
    const { translate, isTranslating } = useTranslate()
    const conversationId = ref(tryLoadConversation())
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
    function tryLoadConversation() {
      try { return sessionStorage.getItem('dp_ai_conversation_id') || null } catch { return null }
    }
    function saveConversation(id) {
      try { sessionStorage.setItem('dp_ai_conversation_id', id) } catch {}
    }

    /* ─── 发送消息（翻译 → RAG → LLM） ─── */
    async function sendMessage(text) {
      if (!text.trim() || isThinking.value) return

      const t = timeStr()
      const rawText = text.trim()

      messages.value.push({ role: 'user', text: rawText, time: t })
      scrollDown()

      isThinking.value = true

      try {
        // 翻译中文 → 英文（解决 embedding 仅支持英文的问题）
        const enQuery = await translate(rawText)

        // 发送英文查询到 RAG 链路
        const data = await postChatSend(enQuery, conversationId.value)

        if (data.conversation_id) {
          conversationId.value = data.conversation_id
          saveConversation(data.conversation_id)
        }

        const wasTranslated = enQuery !== rawText

        messages.value.push({
          role: 'ai',
          intro: data.is_fallback ? '' : data.text,
          recs: filterRecommendations((data.recommendations || []).map(mapRecommendation)),
          fallback: data.is_fallback ? data.text : '',
          translated: wasTranslated,
          enQuery: wasTranslated ? enQuery : undefined,
          time: timeStr(),
        })
      } catch (err) {
        if (import.meta.env.DEV) {
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
    function goToShop(rec) {
      // 将推荐数据存入共享 store，供详情页/商家后台使用
      if (rec && typeof rec === 'object') {
        sharedStore.setBusiness({
          business_id: rec.id || rec.business_id,
          name: rec.name,
          rating: rec.rating,
          review_count: rec.reviewCount || rec.review_count || 0,
          categories: typeof rec.categories === 'string'
            ? rec.categories.split(' · ')
            : (rec.categories || []),
          address: rec.address || '',
          city: rec.city || '',
          state: rec.state || '',
          sources: rec.sources || [],
          imgBg: rec.imgBg || '',
          reason: rec.reason || '',
          price: rec.price || '--',
        })
      }
      const detailId = rec?.id || rec?.business_id || rec
      if (detailId && typeof detailId === 'string') {
        this.$router.push(`/detail/${encodeURIComponent(detailId)}`)
      }
    }

    /* ─── 星级评分辅助 ─── */
    function sourceStarClass(i) {
      const stars = selectedSource.value?.stars || 0
      const full = Math.floor(stars)
      const half = stars % 1 >= 0.5 ? 1 : 0
      if (i <= full) return 'star-full'
      if (i === full + 1 && half) return 'star-half'
      return 'star-empty'
    }
    function sourceStarChar(i) {
      const stars = selectedSource.value?.stars || 0
      const full = Math.floor(stars)
      const half = stars % 1 >= 0.5 ? 1 : 0
      if (i <= full) return '★'
      if (i === full + 1 && half) return '★'
      return '☆'
    }

    /* ─── 响应式断点 ─── */
    function onResize() { isDesktop.value = window.innerWidth >= 1024 }
    onMounted(() => { onResize(); window.addEventListener('resize', onResize) })
    onBeforeUnmount(() => window.removeEventListener('resize', onResize))

    return {
      messages, isThinking, isTranslating, conversationId,
      selectedSource, isDesktop, quickQueries, latestRecs,
      sendMessage, clearChat, showSource, goToShop, sourceStarClass, sourceStarChar,
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
.source-stars .star { display: inline-block; position: relative; }
.source-stars .star-full { color: var(--amber); }
.source-stars .star-empty { color: #DDD; }
.source-stars .star-half { color: #DDD; }
.source-stars .star-half::after {
  content: '★';
  position: absolute;
  left: 0;
  top: 0;
  width: 50%;
  overflow: hidden;
  color: var(--amber);
  pointer-events: none;
}
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
