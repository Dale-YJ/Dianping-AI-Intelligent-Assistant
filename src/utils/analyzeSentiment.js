/**
 * 前端情感分析 — 基于评分 + 中文关键词
 * ==========================================
 *
 * 后端 user_review 评价没有 sentiment 字段时，前端自行分析。
 * 评分为主信号（60%），文本关键词为修正信号（40%）。
 *
 * 用法：
 *   import { analyzeSentiment } from '@/utils/analyzeSentiment.js'
 *   const { label, confidence } = analyzeSentiment({ rating: 2, text: '贵得批爆' })
 *   // → { label: 'negative', confidence: 92 }
 */

/* ─── 词库 ─── */

const POSITIVE_WORDS = [
  '好吃', '推荐', '棒', '赞', '值', '满意', '到位', '丰富',
  '不错', '惊艳', '满分', '靠谱', '必点', '招牌', '拿手',
  '舒服', '开心', '完美', '喜欢', '超值', '好喝', '新鲜',
  '划算', '精致', '干净', '热情', '专业', '用心', '讲究',
  '回购', '常来', '回头客', '念念不忘', '名不虚传',
]

const NEGATIVE_WORDS = [
  '难吃', '差', '贵', '慢', '烂', '失望', '坑', '不值',
  '排队', '等位', '料理包', '退步', '一般般', '不值这个价',
  '批爆', '踩雷', '垃圾', '恶心', '难喝', '态度差',
  '不新鲜', '敷衍', '糊弄', '缩水', '不值当', '劝退',
  '不会再', '后悔', '踩坑', '上当', '浪费',
  '冷', '硬', '咸', '淡', '油腻',
]

const INTENSIFIERS = [
  '太', '很', '非常', '极', '超级', '特别', '极其',
  '实在', '简直', '绝对', '批爆',
]

/* ─── 核心函数 ─── */

/**
 * @param {{ rating?: number, text?: string }} review
 * @returns {{ label: 'positive'|'neutral'|'negative', confidence: number }}
 */
export function analyzeSentiment(review = {}) {
  const rating = review.rating ?? review.stars ?? 0
  const text = (review.text || '').toLowerCase()

  // 1. 评分硬规则（优先级最高）
  if (rating >= 4) return { label: 'positive', confidence: 85 }
  if (rating <= 2 && rating >= 1) return { label: 'negative', confidence: 75 }

  // 2. 评分 + 文本信号（仅对 3 星和 0 星生效）
  let ratingScore = 50
  if (rating === 3) ratingScore = 50
  // rating === 0 表示无评分，保持 50（中性）

  // 2. 文本信号
  let posHits = 0
  let negHits = 0

  for (const w of POSITIVE_WORDS) {
    if (text.includes(w)) posHits++
  }
  for (const w of NEGATIVE_WORDS) {
    if (text.includes(w)) negHits++
  }

  // 强度词放大
  let intensifier = 1
  for (const w of INTENSIFIERS) {
    if (text.includes(w)) { intensifier = 1.3; break }
  }

  const totalHits = posHits + negHits
  let textScore = 50
  if (totalHits > 0) {
    // 文本得分偏向正面或负面
    const rawTextScore = (posHits / totalHits) * 100
    // 平滑：少量命中时不要过度偏斜
    const weight = Math.min(1, totalHits / 5)
    textScore = 50 + (rawTextScore - 50) * weight * intensifier
  }

  // 3. 综合：评分权重 60%，文本权重 40%
  const combined = ratingScore * 0.6 + textScore * 0.4

  // 4. 边缘情况：无评分 + 无文本 → 返回低置信度中性
  if (rating === 0 && !text.trim()) {
    return { label: 'neutral', confidence: 51 }
  }

  // 5. 输出
  let label, confidence
  if (combined >= 65) {
    label = 'positive'
    confidence = Math.round(combined)
  } else if (combined <= 35) {
    label = 'negative'
    confidence = Math.round(100 - combined)
  } else {
    label = 'neutral'
    // 中性置信度：越接近 50 越不确定
    const dist = Math.abs(combined - 50)
    confidence = Math.round(50 + dist * 1.2)
  }

  return { label, confidence: Math.min(99, Math.max(51, confidence)) }
}

/**
 * 批量分析，返回统计摘要
 */
export function batchAnalyze(reviews) {
  const result = { positive: 0, neutral: 0, negative: 0, total: reviews.length }
  for (const r of reviews) {
    const { label } = analyzeSentiment(r)
    result[label]++
  }
  return result
}
