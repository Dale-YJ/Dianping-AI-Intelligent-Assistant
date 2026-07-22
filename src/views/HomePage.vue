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
        <div class="header-actions">
          <button class="header-action" @click="openHistory" title="对话记录">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>
          </button>
          <button class="header-action" @click="clearChat" v-if="messages.length > 1" title="重置对话">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="1 4 1 10 7 10"/><path d="M3.51 15a9 9 0 1 0 2.13-9.36L1 10"/></svg>
          </button>
        </div>
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
        <template v-for="(msg, i) in displayMessages" :key="i">
          <!-- User message -->
          <ChatBubble
            v-if="msg.role === 'user' && !msg.thinking"
            role="user"
            :time="msg.time"
            :is-first-in-group="isFirstInGroup(i, 'user')"
            :is-last-in-group="isLastInGroup(i, 'user')"
          >
            {{ msg.text }}
          </ChatBubble>

          <!-- AI thinking -->
          <ChatBubble
            v-else-if="msg.role === 'ai' && msg.thinking"
            role="ai"
          >
            <TypingIndicator label="正在为你寻找..." />
          </ChatBubble>

          <!-- AI response -->
          <ChatBubble
            v-else-if="msg.role === 'ai'"
            role="ai"
            :time="msg.time"
            :is-first-in-group="isFirstInGroup(i, 'ai')"
            :is-last-in-group="isLastInGroup(i, 'ai')"
          >
            <AIReplyContent :text="msg.intro" v-if="msg.intro" />
            <div class="rec-section" v-if="msg.recs && msg.recs.length && !isDesktop">
              <div class="rec-section-header">
                <span class="section-label">📋 推荐结果</span>
                <span class="section-badge">{{ msg.recs.length }} 家</span>
              </div>
              <div class="rec-list">
                <RecommendationCard
                  v-for="(rec, j) in msg.recs"
                  :key="j"
                  v-bind="rec"
                  :rank="j + 1"
                  :style="{ animationDelay: (j * 0.1) + 's' }"
                  @click="goToShop(rec)"
                  @source-click="s => showSource(s)"
                />
              </div>
            </div>
            <!-- Fallback suggestion chips -->
            <div class="fallback-chips" v-if="msg.fallback && quickQueries.length">
              <p class="fallback-chip-hint">试试这些热门搜索：</p>
              <div class="chip-row">
                <button
                  v-for="q in quickQueries.slice(0, 3)"
                  :key="q"
                  class="fallback-chip"
                  @click="sendMessage(q)"
                >{{ q }}</button>
              </div>
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
        <template v-for="(round, ri) in recRounds" :key="ri">
          <!-- 轮次分隔：显示用户的原始提问 -->
          <div class="round-divider" v-if="recRounds.length > 1">
            <span class="round-query">{{ round.query }}</span>
          </div>
          <RecommendationCard
            v-for="(rec, j) in round.recs"
            :key="rec.id || rec.business_id || j"
            v-bind="rec"
            :rank="j + 1"
            :style="{ animationDelay: (j * 0.06) + 's' }"
            @click="goToShop(rec)"
            @source-click="s => showSource(s)"
          />
        </template>
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

    <!-- Chat History Panel -->
    <ChatHistoryPanel
      :visible="showHistory"
      :conversations="historyConversations"
      :current-id="conversationId"
      @close="closeHistory"
      @new-chat="startNewChat"
      @load-conversation="loadHistoryConversation"
      @delete-conversation="handleDeleteConversation"
    />
  </div>
</template>

<script>
import { ref, computed, onMounted, onBeforeUnmount, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import ChatInput from '../components/ChatInput.vue'
import ChatBubble from '../components/ChatBubble.vue'
import RecommendationCard from '../components/RecommendationCard.vue'
import TypingIndicator from '../components/TypingIndicator.vue'
import AIReplyContent from '../components/AIReplyContent.vue'
import ChatHistoryPanel from '../components/ChatHistoryPanel.vue'
import { postChatSend, getQuickTags } from '../api/modules/chat.js'
import { getBusinessDetail } from '../api/modules/business.js'
import { sharedStore } from '../stores/sharedData.js'
import { clearConversation } from '../composables/useChat.js'
import { useChatHistory } from '../composables/useChatHistory.js'
import { useTranslate } from '../composables/useTranslate.js'
import { hasNonChinaLocation, extractCity } from '../utils/detectRegion.js'
import { extractCuisineMatcher } from '../utils/detectCuisine.js'

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
  // 优先使用商家真实照片，没有则降级为渐变色占位
  const photoUrl = apiRec.photo_url
    || (Array.isArray(apiRec.photos) && apiRec.photos[0])
    || null

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
    imgBg: photoUrl
      ? `url(${photoUrl}) center/cover no-repeat`
      : hashGradient(apiRec.business_id || apiRec.name),
    photos: apiRec.photos || [],
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
 * 过滤推荐结果：去重 + 菜系匹配过滤。
 * 当用户明确提到菜系时，只保留匹配的结果，不展示用户未提及的种类。
 */
function filterRecommendations(recs, query) {
  if (!recs || !recs.length) return []

  const cuisineMatcher = extractCuisineMatcher(query)

  const seen = new Set()
  const deduped = []
  for (const r of recs) {
    const id = r.id || r.business_id
    if (!id || seen.has(id)) continue
    // 菜系过滤：用户提到了菜系但此结果不匹配 → 跳过
    if (cuisineMatcher) {
      const catStr = typeof r.categories === 'string'
        ? r.categories
        : (r.categories || []).join(' ')
      if (!cuisineMatcher(catStr)) continue
    }
    seen.add(id)
    deduped.push(r)
  }

  return deduped.sort((a, b) => (b.score || 0) - (a.score || 0))
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
  components: { ChatInput, ChatBubble, RecommendationCard, TypingIndicator, AIReplyContent, ChatHistoryPanel },
  setup() {
    /* ─── 响应式状态 ─── */
    const messages = ref([])
    const isThinking = ref(false)
    const router = useRouter()
    const { translate } = useTranslate()
    const {
      loadConversations, loadConversation, saveConversation,
      deleteConversation, getCurrentId, setCurrentId, generateId,
    } = useChatHistory()

    // 对话 ID：优先恢复上次活跃会话
    const conversationId = ref(getCurrentId() || generateId())

    const selectedSource = ref(null)
    const isDesktop = ref(false)
    const showHistory = ref(false)
    const historyConversations = ref([])
    const DEFAULT_TAGS = [
      '附近有什么好吃的川菜？',
      '适合约会的安静餐厅推荐',
      '哪家咖啡馆适合学习？',
      '实惠的夜宵推荐',
      '适合聚餐的地方',
    ]

    const quickQueries = ref([...DEFAULT_TAGS])

    async function fetchQuickTags() {
      try {
        const data = await getQuickTags()
        if (data?.tags?.length) {
          const texts = data.tags
            .map(t => typeof t === 'string' ? t : (t.text || t.label || ''))
            .filter(t => t && t !== '经济实惠')
          if (texts.length) quickQueries.value = texts
        }
      } catch {
        // 后端未就绪时使用默认标签
      }
    }

    /* ─── 计算属性 ─── */
    /** 按对话轮次分组推荐结果，每组关联到用户的原始提问 */
    const recRounds = computed(() => {
      const rounds = []
      for (let i = 0; i < messages.value.length; i++) {
        const m = messages.value[i]
        if (m.role === 'ai' && m.recs && m.recs.length) {
          // 找到本轮对话中该 AI 消息之前的最近一条用户消息
          let query = ''
          for (let j = i - 1; j >= 0; j--) {
            if (messages.value[j].role === 'user') {
              query = messages.value[j].text || ''
              break
            }
          }
          rounds.push({
            query,
            recs: m.recs,
          })
        }
      }
      return rounds
    })

    /** 累积所有轮次的推荐结果（去重），桌面端侧边栏使用 */
    const latestRecs = computed(() => {
      const seen = new Set()
      const all = []
      for (const m of messages.value) {
        if (m.role === 'ai' && m.recs && m.recs.length) {
          for (const rec of m.recs) {
            const id = rec.id || rec.business_id
            if (id && !seen.has(id)) {
              seen.add(id)
              all.push(rec)
            }
          }
        }
      }
      return all
    })

    /* 在消息列表末尾插入 thinking 占位（纯视图层，不污染 messages） */
    const displayMessages = computed(() => {
      const result = [...messages.value]
      if (isThinking.value) {
        result.push({ role: 'ai', thinking: true, time: timeStr() })
      }
      return result
    })

    /* 消息分组：判断某条消息是否是同角色的第一条 / 最后一条 */
    function isFirstInGroup(index, role) {
      if (index === 0) return true
      const prev = displayMessages.value[index - 1]
      if (!prev) return true
      if (prev.thinking) return true
      return prev.role !== role
    }
    function isLastInGroup(index, role) {
      if (index >= displayMessages.value.length - 1) return true
      const next = displayMessages.value[index + 1]
      if (!next) return true
      if (next.thinking) return false // thinking 后续是真正的 AI 消息
      return next.role !== role
    }

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
    /* ── 启动时恢复上次活跃对话 ── */
    async function restoreLastConversation() {
      const restored = await loadConversation(conversationId.value)
      if (restored && restored.messages && restored.messages.length) {
        messages.value = restored.messages
        nextTick(() => scrollDown())
      }
    }

    /* ── 历史面板操作 ── */
    function openHistory() {
      historyConversations.value = loadConversations()
      showHistory.value = true
    }
    function closeHistory() {
      showHistory.value = false
    }
    async function loadHistoryConversation(id) {
      const conv = await loadConversation(id)
      if (conv && conv.messages) {
        messages.value = conv.messages
        conversationId.value = id
        setCurrentId(id)
        showHistory.value = false
        nextTick(() => scrollDown())
      }
    }
    function startNewChat() {
      const newId = generateId()
      messages.value = []
      conversationId.value = newId
      setCurrentId(newId)
      showHistory.value = false
    }
    async function handleDeleteConversation(id) {
      await deleteConversation(id)
      if (conversationId.value === id) {
        messages.value = []
        const newId = generateId()
        conversationId.value = newId
        setCurrentId(newId)
      }
      // 刷新面板列表
      historyConversations.value = loadConversations()
    }

    /* ── 持久化辅助 ── */
    function persistChat() {
      saveConversation(conversationId.value, messages.value)
      setCurrentId(conversationId.value)
    }

    /* ─── 话题组（用于检测话题切换，自动清上下文） ─── */
    const TOPIC_GROUPS = [
      ['素食', '素菜', '斋', '吃素', '素', '菜卷', '松茸', '清淡'],
      ['聚餐', '聚会', '朋友一起', '请客', '多人', '包间', '一桌', '大家'],
      ['约会', '情侣', '浪漫', '安静', '二人', '烛光'],
      ['火锅', '涮', '串串', '麻辣'],
      ['日料', '寿司', '刺身', '居酒屋', '拉面'],
      ['咖啡', '奶茶', '甜品', '蛋糕', '下午茶'],
    ]

    function getTopicGroup(text) {
      for (let i = 0; i < TOPIC_GROUPS.length; i++) {
        if (TOPIC_GROUPS[i].some(kw => text.includes(kw))) return i
      }
      return -1
    }

    /* ─── 发送消息（翻译 → RAG → LLM） ─── */
    async function sendMessage(text) {
      if (!text.trim() || isThinking.value) return

      const t = timeStr()
      const rawText = text.trim()

      // 话题切换检测：当前消息与上一条 AI 回复话题不同 → 清空对话重新开始
      const curGroup = getTopicGroup(rawText)
      if (curGroup >= 0 && messages.value.length >= 2) {
        const lastAi = [...messages.value].reverse().find(m => m.role === 'ai')
        if (lastAi?.intro) {
          const prevGroup = getTopicGroup(lastAi.intro)
          if (prevGroup >= 0 && prevGroup !== curGroup) {
            conversationId.value = null
            messages.value = []
            clearConversation()
          }
        }
      }

      messages.value.push({ role: 'user', text: rawText, time: t })
      scrollDown()

      isThinking.value = true

      try {
        // 检测非中国地区 → 按需翻译为英文关键词
        const needTranslate = hasNonChinaLocation(rawText)
        const query = needTranslate ? await translate(rawText) : rawText
        const city = extractCity(rawText)

        const data = await postChatSend(query, conversationId.value, city)

        if (data.conversation_id) {
          conversationId.value = data.conversation_id
        }

        // 并行拉取推荐商家的图片（中文数据有 image_url，Yelp 没有）
        const rawRecs = data.recommendations || []
        if (rawRecs.length) {
          const details = await Promise.allSettled(
            rawRecs.map(r => getBusinessDetail(r.business_id))
          )
          details.forEach((d, i) => {
            if (d.status === 'fulfilled' && d.value?.photos) {
              rawRecs[i] = { ...rawRecs[i], ...d.value }
            }
          })
        }

        messages.value.push({
          role: 'ai',
          intro: data.text,
          recs: filterRecommendations(rawRecs.map(mapRecommendation), rawText),
          fallback: data.is_fallback,
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
            fallback: false,
            time: timeStr(),
          })
        } else {
          messages.value.push({
            role: 'ai',
            intro: err.message || '抱歉，发生了未知错误，请稍后再试',
            recs: [],
            fallback: true,
            time: timeStr(),
          })
        }
      } finally {
        isThinking.value = false
        persistChat()
        scrollDown()
      }
    }

    /* ─── 其他操作 ─── */
    function clearChat() {
      messages.value = []
      const newId = generateId()
      conversationId.value = newId
      setCurrentId(newId)
      saveConversation(newId, [])
    }
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
          photos: rec.photos || [],
          reason: rec.reason || '',
          price: rec.price || '--',
        })
      }
      const detailId = rec?.id || rec?.business_id || rec
      if (detailId && typeof detailId === 'string') {
        router.push(`/detail/${encodeURIComponent(detailId)}`)
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
    onMounted(() => { onResize(); restoreLastConversation(); fetchQuickTags(); window.addEventListener('resize', onResize) })
    onBeforeUnmount(() => window.removeEventListener('resize', onResize))

    return {
      messages, displayMessages, isThinking, conversationId,
      selectedSource, isDesktop, showHistory, historyConversations, quickQueries, latestRecs, recRounds,
      sendMessage, clearChat, openHistory, closeHistory, loadHistoryConversation,
      startNewChat, handleDeleteConversation,
      showSource, goToShop, sourceStarClass, sourceStarChar,
      isFirstInGroup, isLastInGroup,
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
.header-actions { display: flex; align-items: center; gap: var(--space-1); }
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

/* ── Recommendation Section ── */
.rec-section {
  margin-top: var(--space-4);
  padding-top: var(--space-3);
  border-top: 1px dashed var(--border);
}
.rec-section-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: var(--space-3);
}
.section-label {
  font-family: var(--font-display);
  font-size: var(--text-sm);
  font-weight: 700;
  color: var(--ink);
}
.section-badge {
  font-size: var(--text-xs);
  background: var(--coral-pale);
  color: var(--coral);
  padding: 2px var(--space-2);
  border-radius: var(--radius-full);
  font-weight: 600;
}
.rec-list { display: flex; flex-direction: column; gap: var(--space-3); }

/* ── Fallback Chips ── */
.fallback-chips {
  margin-top: var(--space-3);
  padding-top: var(--space-3);
  border-top: 1px dashed var(--border);
}
.fallback-chip-hint {
  font-size: var(--text-xs);
  color: var(--ink-muted);
  margin-bottom: var(--space-2);
}
.chip-row {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2);
}
.fallback-chip {
  padding: var(--space-1) var(--space-3);
  background: var(--card-warm);
  border: 1px solid var(--border);
  border-radius: var(--radius-full);
  font-size: var(--text-xs);
  color: var(--coral);
  transition: all var(--duration-fast);
  white-space: nowrap;
  cursor: pointer;
}
.fallback-chip:hover {
  background: var(--coral-pale);
  border-color: var(--coral);
}

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

/* ── Round Divider ── */
.round-divider {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  margin-top: var(--space-3);
  padding-top: var(--space-3);
  border-top: 1px dashed var(--border);
}
.round-divider:first-child {
  margin-top: 0;
  padding-top: 0;
  border-top: none;
}
.round-query {
  font-size: var(--text-xs);
  color: var(--ink-muted);
  font-weight: 600;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.round-query::before {
  content: '🔍 ';
  font-weight: 400;
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
