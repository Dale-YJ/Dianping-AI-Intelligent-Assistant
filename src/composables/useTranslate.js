/**
 * useTranslate — 中文查询 → 英文关键词翻译
 * ============================================
 * 将用户的中文自然语言查询转换为英文搜索关键词，
 * 解决 Yelp 英文数据集与中文查询之间的语言不匹配问题。
 *
 * 策略：
 * 1. 词典映射：覆盖常见菜系、菜品、场景（~60 个词条）
 * 2. 去除口语填充词（有没有、推荐、附近、呢、吗…）
 * 3. 最长匹配优先，避免"火锅"被"火"误匹配
 * 4. 无匹配时返回清洗后的原文（兼容英文输入）
 *
 * 用法：
 *   const { translate } = useTranslate()
 *   const enQuery = await translate('有没有火锅店推荐')
 *   // → 'hot pot restaurant'
 */

import { ref } from 'vue'

/* ─── 中文检测 ─── */
export function hasChinese(text) {
  return /[一-鿿㐀-䶿]/.test(text)
}

/* ─── 中文→英文 餐饮词典（按长度降序，保证最长匹配） ─── */
const ZH_TO_EN = new Map([
  // 场景 > 菜系 > 菜品，同组内按字符串长度降序

  // ── 场景 / 需求 ──
  ['适合约会', 'romantic date'],
  ['商务宴请', 'business dining fine dining'],
  ['家庭聚餐', 'family friendly'],
  ['朋友聚会', 'group dining'],
  ['一人食', 'solo dining'],
  ['安静', 'quiet cozy'],
  ['实惠', 'affordable cheap eats'],
  ['高档', 'upscale fine dining'],
  ['环境好', 'nice ambiance'],
  ['包间', 'private room'],
  ['停车', 'parking'],
  ['排队', 'popular'],

  // ── 菜系 ──
  ['日本料理', 'japanese food'],
  ['韩国料理', 'korean food'],
  ['泰国菜', 'thai food'],
  ['越南菜', 'vietnamese food'],
  ['印度菜', 'indian food'],
  ['墨西哥菜', 'mexican food'],
  ['意大利菜', 'italian food'],
  ['地中海', 'mediterranean food'],
  ['中餐馆', 'chinese restaurant'],
  ['火锅店', 'hot pot restaurant'],
  ['川菜馆', 'sichuan restaurant'],
  ['粤菜馆', 'cantonese restaurant'],
  ['烧烤店', 'bbq restaurant'],
  ['火锅', 'hot pot'],
  ['川菜', 'sichuan food'],
  ['粤菜', 'cantonese food'],
  ['日料', 'japanese food'],
  ['韩餐', 'korean food'],
  ['西餐', 'western food'],
  ['中餐', 'chinese food'],
  ['烧烤', 'bbq barbecue'],
  ['海鲜', 'seafood'],
  ['素食', 'vegetarian vegan'],
  ['清真', 'halal'],
  ['湘菜', 'hunan food'],
  ['湖南菜', 'hunan food'],
  ['潮州菜', 'chaozhou food'],
  ['客家菜', 'hakka food'],
  ['上海菜', 'shanghai food'],
  ['本帮菜', 'shanghai food'],
  ['北京菜', 'beijing food'],
  ['东北菜', 'dongbei food'],
  ['西北菜', 'northwest chinese food'],
  ['新疆菜', 'xinjiang food'],
  ['陕西菜', 'shaanxi food'],
  ['法国菜', 'french food'],
  ['法餐', 'french food'],
  ['西班牙菜', 'spanish food'],
  ['巴西烤肉', 'brazilian bbq'],
  ['涮锅', 'hot pot'],

  // ── 具体菜品 ──
  ['意大利面', 'pasta'],
  ['早茶', 'dim sum'],
  ['奶茶', 'bubble tea'],
  ['寿司', 'sushi'],
  ['拉面', 'ramen noodles'],
  ['披萨', 'pizza'],
  ['牛排', 'steak'],
  ['汉堡', 'burger'],
  ['炸鸡', 'fried chicken'],
  ['饺子', 'dumplings'],
  ['点心', 'dim sum'],
  ['面条', 'noodles'],
  ['沙拉', 'salad'],
  ['三明治', 'sandwich'],
  ['塔可', 'tacos'],
  ['甜品', 'dessert'],
  ['蛋糕', 'cake'],
  ['冰淇淋', 'ice cream'],
  ['咖啡', 'coffee'],
  ['酒吧', 'bar pub'],
  ['自助', 'buffet'],
  ['快餐', 'fast food'],
  ['小吃', 'snacks'],

  // ── 餐时段落 ──
  ['下午茶', 'afternoon tea brunch'],
  ['早餐', 'breakfast brunch'],
  ['午餐', 'lunch'],
  ['晚餐', 'dinner'],
  ['夜宵', 'late night food'],
  ['深夜', 'late night'],

  // ── 其他 ──
  ['外卖', 'takeout delivery'],
  ['堂食', 'dine in'],
  ['露台', 'outdoor patio'],
  ['户外', 'outdoor seating'],
  ['宠物友好', 'pet friendly'],
  ['浪漫', 'romantic'],
  ['风景', 'view'],
  ['江景', 'river view'],
  ['网红', 'trendy popular'],
  ['打卡', 'trendy popular instagram worthy'],
  ['性价比', 'affordable'],
  ['亲子', 'family friendly'],
  ['早午餐', 'brunch'],
  ['越南粉', 'vietnamese food pho'],
  ['河粉', 'pho'],
  ['咖喱', 'curry'],
  ['居酒屋', 'izakaya japanese'],
  ['精酿', 'craft beer'],
  ['鸡尾酒', 'cocktail'],
  ['聚餐', 'group dining'],
  ['私房菜', 'private kitchen'],
])

/* ─── 口语填充词（会被移除） ─── */
const FILLER_RE = /有没有什么|有没有|有什么|推荐|附近|什么|好吃的|好玩的|哪家|哪里|呢|吗|吧|啊|呀|嘛|哦|呗|地方|帮我|我想吃|我想|想吃|想找|想|找一个|找一下|一个|一下|有啥|给我|我要|排名|前十|前几|最好|最棒|最火|热门|得|的|店|麻烦|多少|几家|几个|哪些|帮我找|给我推荐|来一个|来点|看看/g

/* ─── 数字排名模式（前10名、top5 等） ─── */
const RANKING_RE = /排名前?\d{1,2}名?|前\d{1,2}名?|top\s?\d{1,2}|前几名|前几位/gi

/* ─── 多余的空白与标点 ─── */
const PUNCT_RE = /[，。！？、；：""''（）【】《》\s]+/g

/**
 * 中文查询 → 英文搜索关键词
 *
 * 算法：
 * 1. 去掉口语填充词
 * 2. 按词典键长度降序扫描，取最长匹配（保证"日本料理"不被"日料"截断）
 * 3. 每命中一个词就从字符串中移除，避免重复匹配
 * 4. 未命中词典的词保留原文（作为额外关键词）
 * 5. 最终合并为英文搜索字符串
 */
function zhToEnKeywords(text) {
  // 1. 去填充词 & 标点 & 数字排名模式
  let cleaned = text
    .replace(RANKING_RE, ' ')
    .replace(FILLER_RE, ' ')
    .replace(PUNCT_RE, ' ')
    .trim()

  if (!cleaned) return text.trim()  // 纯填充词，退回原文

  // 2. 构建词典键列表（按长度降序）
  const keys = [...ZH_TO_EN.keys()]  // 已是降序（构造顺序）

  // 3. 扫描匹配
  const matched = []
  for (const key of keys) {
    const idx = cleaned.indexOf(key)
    if (idx !== -1) {
      matched.push(ZH_TO_EN.get(key))
      cleaned = cleaned.slice(0, idx) + ' ' + cleaned.slice(idx + key.length)
    }
  }

  // 4. 丢弃剩余的中文碎片（未在词典中的中文字符对英文搜索无意义）
  const remaining = cleaned.replace(/\s+/g, ' ').trim()
  const fragments = remaining.split(' ').filter(s => s.length > 0 && !hasChinese(s))

  // 5. 组装结果（只保留翻译后的英文词 + 非中文碎片）
  const keywords = [...matched, ...fragments]
  if (keywords.length === 0) return cleaned || text.trim()

  // 6. 剔除泛词 — 避免污染搜索结果（"food" 会匹配所有 Food Truck 等）
  const result = keywords.join(' ')
  const cleaned_result = result
    .replace(/\b(food|restaurant|restaurants|good|best|place|nearby|popular)\b/gi, ' ')
    .replace(/\s+/g, ' ')
    .trim()
  return cleaned_result || result
}

/* ═══════════════════════════════════════════════════════════ */

export function useTranslate() {
  const isTranslating = ref(false)

  /**
   * 翻译入口：中文查询 → 英文关键词
   *
   * @param {string} text - 用户原始查询
   * @returns {Promise<string>} 英文搜索关键词
   */
  async function translate(text) {
    if (!text || !text.trim()) return text

    const raw = text.trim()

    // 不含中文 → 原样返回（用户可能直接输入英文）
    if (!hasChinese(raw)) return raw

    isTranslating.value = true
    try {
      const result = zhToEnKeywords(raw)
      return result || raw
    } finally {
      isTranslating.value = false
    }
  }

  /** 清除缓存（保留接口兼容） */
  function clearCache() {}

  return { translate, isTranslating, clearCache }
}
