<template>
  <div class="chat-page">
    <div class="chat-panel" ref="chatPanel">
      <div class="chat-header">
        <button class="back-btn" @click="$router.push('/')">
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="15 18 9 12 15 6"/></svg>
        </button>
        <div class="header-info" v-if="selectedBiz">
          <h1 class="header-title">{{ selectedBiz.name }}</h1>
          <span class="header-sub">⭐ {{ selectedBiz.rating }} · {{ selectedBiz.reviewCount }} 条评价</span>
        </div>
        <h1 class="header-title" v-else>商家助手</h1>
        <button class="shop-btn" @click="$router.push('/select-shop?returnTo=biz-home')">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="m3 9 9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/><path d="M9 22V12h6v10"/></svg>
          <span>{{ selectedBiz ? '切换' : '选择餐厅' }}</span>
        </button>
        <button
          v-if="selectedBiz"
          class="dashboard-btn"
          @click="router.push('/business/' + encodeURIComponent(selectedBiz.id))"
        >📊 评价汇总</button>
      </div>

      <div class="chat-messages">
        <!-- Welcome card -->
        <div class="welcome-card" v-if="messages.length === 0 && !isThinking">
          <div class="welcome-icon">🏪</div>
          <h2 class="welcome-title" v-if="selectedBiz">正在管理 {{ selectedBiz.name }}</h2>
          <h2 class="welcome-title" v-else>商家智能助手</h2>
          <p class="welcome-desc" v-if="selectedBiz">有什么可以帮你的？</p>
          <p class="welcome-desc" v-else>选一家餐厅，帮你分析评价、优化经营</p>
          <div class="quick-actions">
            <button class="action-btn" @click="$router.push('/select-shop?returnTo=biz-home')">
              {{ selectedBiz ? '🔍 切换餐厅' : '🔍 选择管理的餐厅' }}
            </button>
            <button class="action-btn secondary" @click="sendMessage('如何提升餐厅评分？')">💡 经营建议</button>
            <button class="action-btn secondary" @click="sendMessage('怎么回复差评比较合适？')">✍️ 差评回复技巧</button>
            <button class="action-btn secondary" @click="sendMessage('帮我分析最近的口碑趋势')">📊 口碑分析</button>
          </div>
        </div>

        <template v-for="(msg, i) in displayMessages" :key="i">
          <ChatBubble
            :role="msg.role"
            :time="msg.time"
            :thinking="msg.thinking"
            :is-first-in-group="isFirstInGroup(i, msg.role)"
            :is-last-in-group="isLastInGroup(i, msg.role)"
          >
            <template v-if="msg.text && !msg.intro">{{ msg.text }}</template>
            <AIReplyContent :text="msg.intro" v-if="msg.intro" />
            <div class="rec-section" v-if="msg.recs && msg.recs.length">
              <div class="rec-section-header">
                <span class="section-label">📋 分析结果</span>
              </div>
              <div class="rec-list">
                <RecommendationCard
                  v-for="(rec, j) in msg.recs" :key="j"
                  v-bind="rec" :rank="j + 1"
                  :style="{ animationDelay: (j * 0.1) + 's' }"
                  @click="goToShop(rec)"
                />
              </div>
            </div>
          </ChatBubble>
        </template>
        <div ref="msgEnd"></div>
      </div>

      <ChatInput
        :disabled="isThinking"
        :show-hint="messages.length === 0"
        placeholder="输入经营相关的问题… 如「如何提升差评率」"
        @send="sendMessage"
      />
    </div>
  </div>
</template>

<script>
import { ref, computed, nextTick, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import ChatInput from '../components/ChatInput.vue'
import ChatBubble from '../components/ChatBubble.vue'
import AIReplyContent from '../components/AIReplyContent.vue'
import RecommendationCard from '../components/RecommendationCard.vue'
import { postChatSend } from '../api/modules/chat.js'
import { getBusinessDetail } from '../api/modules/business.js'
import { sharedStore } from '../stores/sharedData.js'

const IMG_GRADIENTS = [
  'linear-gradient(135deg, #1A3A2A, #2A4A3A)',
  'linear-gradient(135deg, #2D1B2E, #3D2E3E)',
  'linear-gradient(135deg, #C0392B, #E74C3C)',
  'linear-gradient(135deg, #5D4037, #8D6E63)',
]

function hashGradient(str) {
  let hash = 0
  for (let i = 0; i < str.length; i++) hash = str.charCodeAt(i) + ((hash << 5) - hash)
  return IMG_GRADIENTS[Math.abs(hash) % IMG_GRADIENTS.length]
}

export default {
  name: 'BusinessHome',
  components: { ChatInput, ChatBubble, AIReplyContent, RecommendationCard },
  setup() {
    const router = useRouter()
    const messages = ref([])
    const isThinking = ref(false)
    const selectedBiz = ref(null)

    const displayMessages = computed(() => {
      const r = [...messages.value]
      if (isThinking.value) r.push({ role: 'ai', thinking: true, time: timeStr() })
      return r
    })

    function timeStr() {
      return new Date().toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
    }

    function isFirstInGroup(i, role) {
      if (i === 0) return true
      const prev = displayMessages.value[i - 1]
      return !prev || prev.thinking || prev.role !== role
    }
    function isLastInGroup(i, role) {
      if (i >= displayMessages.value.length - 1) return true
      const next = displayMessages.value[i + 1]
      return !next || next.role !== role
    }

    function scrollDown() {
      nextTick(() => {
        const el = document.querySelector('.chat-messages')
        if (el) el.lastElementChild?.scrollIntoView({ behavior: 'smooth' })
      })
    }

    function mapRecommendation(apiRec) {
      const photoUrl = apiRec.photo_url
        || (Array.isArray(apiRec.photos) && apiRec.photos[0])
        || null
      return {
        id: apiRec.business_id,
        name: apiRec.name,
        rating: apiRec.rating,
        categories: (apiRec.categories || []).join(' · '),
        reviewCount: apiRec.review_count || 0,
        address: apiRec.address || apiRec.city || '',
        imgBg: photoUrl
          ? `url(${photoUrl}) center/cover no-repeat`
          : hashGradient(apiRec.business_id || apiRec.name),
        photos: apiRec.photos || [],
      }
    }

    async function sendMessage(text) {
      if (!text.trim() || isThinking.value) return
      messages.value.push({ role: 'user', text: text.trim(), time: timeStr() })
      scrollDown()
      isThinking.value = true

      try {
        const data = await postChatSend(text.trim(), null, '', selectedBiz.value?.id)
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
          recs: rawRecs.map(mapRecommendation),
          time: timeStr(),
        })
      } catch (err) {
        messages.value.push({
          role: 'ai',
          intro: '抱歉，AI 服务暂时不可用，请稍后再试',
          recs: [],
          time: timeStr(),
        })
      } finally {
        isThinking.value = false
        scrollDown()
      }
    }

    function goToShop(rec) {
      const id = rec?.id || rec?.business_id
      if (id) {
        sharedStore.setBusiness({
          business_id: id, name: rec.name, rating: rec.rating,
          review_count: rec.reviewCount || 0, categories: rec.categories,
          photos: rec.photos || [],
        })
        router.push(`/business/${encodeURIComponent(id)}`)
      }
    }

    onMounted(() => {
      const biz = sharedStore.currentBusiness
      if (!biz || !biz.name) {
        router.push('/select-shop?returnTo=biz-home')
        return
      }
      selectedBiz.value = {
        id: biz.business_id,
        name: biz.name,
        rating: biz.rating,
        reviewCount: biz.review_count || 0,
      }
    })

    return {
      router, messages, isThinking, displayMessages, selectedBiz,
      isFirstInGroup, isLastInGroup, sendMessage, goToShop,
    }
  },
}
</script>

<style scoped>
.chat-page {
  display: flex; flex-direction: column;
  height: calc(100dvh - var(--tab-height));
  max-width: var(--max-width); margin: 0 auto;
}
.chat-panel {
  flex: 1; display: flex; flex-direction: column;
  overflow: hidden; position: relative;
}
.chat-header {
  display: flex; align-items: center; gap: var(--space-3);
  padding: var(--space-3) var(--space-4);
  border-bottom: 1px solid var(--border);
  background: rgba(255,255,255,0.92);
  backdrop-filter: blur(12px);
  z-index: 10;
}
.back-btn { padding: var(--space-1); color: var(--ink); }
.header-info { flex: 1; min-width: 0; }
.header-title {
  flex: 1;
  font-family: var(--font-display);
  font-size: var(--text-md); font-weight: 700;
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}
.header-sub { font-size: var(--text-xs); color: var(--ink-muted); display: block; }
.shop-btn {
  display: flex; align-items: center; gap: 4px;
  padding: var(--space-1) var(--space-3);
  background: var(--coral); color: #fff;
  border-radius: var(--radius-full);
  font-size: var(--text-sm); font-weight: 600;
  white-space: nowrap;
}
.dashboard-btn {
  display: flex; align-items: center; gap: 4px;
  padding: var(--space-1) var(--space-3);
  background: var(--warm-bg); color: var(--coral);
  border: 1px solid var(--coral);
  border-radius: var(--radius-full);
  font-size: var(--text-sm); font-weight: 600;
  white-space: nowrap;
  transition: all var(--duration-fast);
}
.dashboard-btn:hover { background: var(--coral-pale); }
.chat-messages {
  flex: 1; overflow-y: auto; padding: var(--space-4);
  display: flex; flex-direction: column; gap: var(--space-3);
}

/* Welcome */
.welcome-card {
  text-align: center; padding: var(--space-10) var(--space-4);
  animation: fadeUp 0.5s var(--ease-out);
}
.welcome-icon { font-size: 3.5rem; margin-bottom: var(--space-4); }
.welcome-title {
  font-family: var(--font-display);
  font-size: var(--text-xl); font-weight: 700; margin-bottom: var(--space-2);
}
.welcome-desc {
  font-size: var(--text-sm); color: var(--ink-muted); margin-bottom: var(--space-6);
}
.quick-actions {
  display: flex; flex-direction: column; gap: var(--space-2);
  max-width: 280px; margin: 0 auto;
}
.action-btn {
  padding: var(--space-3) var(--space-4);
  border-radius: var(--radius-lg);
  font-size: var(--text-sm); font-weight: 600;
  background: var(--coral); color: #fff;
  transition: all var(--duration-fast);
}
.action-btn.secondary {
  background: var(--warm-bg); color: var(--ink-light);
  border: 1px solid var(--border);
}
.action-btn:hover { opacity: 0.9; }
.action-btn.secondary:hover { background: var(--coral-pale); color: var(--coral); }

.rec-section { margin-top: var(--space-2); }
.rec-section-header { margin-bottom: var(--space-2); }
.section-label { font-size: var(--text-sm); font-weight: 600; color: var(--ink-light); }
.rec-list { display: flex; flex-direction: column; gap: var(--space-2); }
</style>
