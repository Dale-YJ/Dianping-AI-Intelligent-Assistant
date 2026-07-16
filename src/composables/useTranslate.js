/**
 * useTranslate — 中文 → 英文翻译
 * ================================
 * 因为 embedding 模型 (all-MiniLM-L6-v2) 仅支持英文，
 * 中文查询在 OpenSearch 向量检索中效果很差。
 *
 * 此 composable 在发送查询前将中文翻译为英文，
 * 让 embedding 模型能正确编码查询语义，提升 RAG 召回质量。
 *
 * 用法：
 *   const { translate, isTranslating } = useTranslate()
 *   const enQuery = await translate('附近有什么好吃的川菜？')
 *   // → 'What are some good Sichuan restaurants nearby?'
 */

import { ref } from 'vue'
import { postChatSend } from '../api/modules/chat.js'

/* ─── LRU 翻译缓存（避免重复请求） ─── */
const CACHE_MAX = 200
const cache = new Map()

/* ─── 翻译专用 system prompt（要求只返回译文） ─── */
const TRANSLATE_PROMPT = `You are a translator. Translate the following Chinese query into natural English suitable for a restaurant/food search.

Rules:
- Output ONLY the English translation, nothing else.
- Keep food names in pinyin if they don't have common English names (e.g. "川菜" → "Sichuan cuisine", "火锅" → "hotpot").
- Preserve the user's intent: if they ask for recommendations, keep it as a question/seeking query.
- Use natural, conversational English.`

/**
 * 检测文本是否包含中文字符
 */
export function hasChinese(text) {
  return /[一-鿿㐀-䶿]/.test(text)
}

export function useTranslate() {
  const isTranslating = ref(false)

  /**
   * 将中文查询翻译为英文。
   * 如果文本不含中文，直接返回原文。
   * 命中缓存时直接返回，不发起请求。
   */
  async function translate(text) {
    if (!text || !text.trim()) return text

    const trimmed = text.trim()

    // 不含中文 → 直接返回
    if (!hasChinese(trimmed)) return trimmed

    // 命中缓存 → 直接返回
    if (cache.has(trimmed)) return cache.get(trimmed)

    isTranslating.value = true

    try {
      const result = await postChatSend(
        `${TRANSLATE_PROMPT}\n\nChinese: ${trimmed}\nEnglish:`,
        null // 不需要多轮对话
      )

      // 提取翻译结果（LLM 回复在 result.text 中）
      let translation = (result.text || '').trim()

      // 清理可能的残留格式
      translation = translation
        .replace(/^English:\s*/i, '')
        .replace(/^Translation:\s*/i, '')
        .replace(/^["']|["']$/g, '')
        .trim()

      // 如果翻译结果为空或明显异常，回退到原文
      if (!translation || translation.length < 2) {
        return trimmed
      }

      // 写入缓存（LRU 淘汰）
      if (cache.size >= CACHE_MAX) {
        const firstKey = cache.keys().next().value
        cache.delete(firstKey)
      }
      cache.set(trimmed, translation)

      return translation
    } catch {
      // 翻译失败时回退到原文（至少还能用 BM25 关键词匹配）
      console.warn('[翻译] 翻译失败，使用原文发送')
      return trimmed
    } finally {
      isTranslating.value = false
    }
  }

  /** 清除翻译缓存 */
  function clearCache() {
    cache.clear()
  }

  return { translate, isTranslating, clearCache }
}
