/**
 * detectCuisine — 从用户查询中提取菜系关键词并匹配推荐结果
 * ============================================================
 * 当用户明确提到某个菜系时（如"日料"、"川菜"），过滤掉不相关的结果，
 * 避免出现用户没提到的菜系类型。
 *
 * 用法：
 *   import { extractCuisineMatcher } from '../utils/detectCuisine.js'
 *   const matcher = extractCuisineMatcher('上海的日料店')
 *   if (matcher) {
 *     filtered = recommendations.filter(r => matcher(r.categories))
 *   }
 */

/* ─── 菜系关键词及别名映射（严格匹配，仅包含同义词/简称，不跨菜系） ─── */
const CUISINE_ALIASES = {
  // 日料 ↔ 日本料理（同义词）
  '日料': ['日料', '日本料理', '日式料理'],
  '日本料理': ['日料', '日本料理', '日式料理'],
  // 韩料 ↔ 韩国料理（同义词）
  '韩料': ['韩料', '韩式料理', '韩国料理'],
  '韩国料理': ['韩料', '韩式料理', '韩国料理'],
  // 川菜
  '川菜': ['川菜', '川菜馆', '四川菜'],
  // 粤菜
  '粤菜': ['粤菜', '粤菜馆', '广东菜'],
  // 火锅
  '火锅': ['火锅', '四川火锅', '老北京火锅', '火锅自助'],
  // 烧烤
  '烧烤': ['烧烤', '烤肉'],
  // 西餐
  '西餐': ['西餐', '牛排', '意大利菜', '法国菜'],
  '意大利菜': ['意大利菜'],
  '法国菜': ['法国菜'],
  // 寿司
  '寿司': ['寿司'],
  // 湘菜
  '湘菜': ['湘菜', '湖南菜'],
  // 本帮菜 / 苏浙菜
  '本帮菜': ['本帮菜', '上海菜', '苏浙菜', '浙菜', '淮扬菜'],
  // 面馆
  '面馆': ['面馆', '粉面', '面食', '拉面'],
  // 烤鸭
  '烤鸭': ['烤鸭', '北京菜', '京菜'],
  // 海鲜
  '海鲜': ['海鲜'],
  // 小吃
  '小吃': ['小吃', '中式小吃'],
  // 咖啡
  '咖啡': ['咖啡', '西式简餐', '烘焙', '面包甜点'],
  // 泰国菜
  '泰国菜': ['泰国菜', '泰式料理'],
  // 云南菜
  '云南菜': ['云南菜', '滇菜'],
  // 新疆菜
  '新疆菜': ['新疆菜', '西北菜'],
  // 东北菜
  '东北菜': ['东北菜'],
  // 鲁菜
  '鲁菜': ['鲁菜', '山东菜'],
  // 自助餐
  '自助餐': ['自助餐'],
  // 素食
  '素食': ['素食'],
  // 甜品
  '甜品': ['甜品', '甜点', '面包', '蛋糕', '冰淇淋'],
  // 早餐
  '早餐': ['早餐', '早茶', '粥店'],
  // 小龙虾
  '小龙虾': ['小龙虾'],
  // 烤鱼
  '烤鱼': ['烤鱼'],
  // 奶茶饮品
  '奶茶': ['奶茶', '饮品', '果汁'],
  // 快餐
  '快餐': ['快餐', '简餐'],
  // 茶餐厅
  '茶餐厅': ['茶餐厅'],
  // 顺德菜
  '顺德菜': ['顺德菜'],
  // 潮汕菜
  '潮汕菜': ['潮汕菜'],
  // 农家菜
  '农家菜': ['农家菜', '土菜馆'],
  // 私房菜
  '私房菜': ['私房菜'],
  // 墨西哥菜
  '墨西哥菜': ['墨西哥菜'],
}

/* ─── 反向索引：alias → 主菜系 key（用于从用户输入中识别简称） ─── */
const ALIAS_TO_KEY = {}
for (const [key, aliases] of Object.entries(CUISINE_ALIASES)) {
  for (const alias of aliases) {
    const lower = alias.toLowerCase()
    // 保留最长匹配（如"日本料理"优先于"日本"）
    if (!ALIAS_TO_KEY[lower] || alias.length > ALIAS_TO_KEY[lower].length) {
      ALIAS_TO_KEY[lower] = key
    }
  }
}

/**
 * 从用户查询中提取菜系关键词。
 * 同时匹配别名表的 key 和 value，确保"烤肉""日料"等简称也能被识别。
 * @param {string} text - 用户原始查询
 * @returns {string[]} 菜系关键词数组，未匹配返回空数组
 */
export function extractCuisines(text) {
  if (!text) return []

  const found = []
  // 按长度降序，确保长词优先匹配
  const sorted = Object.keys(ALIAS_TO_KEY).sort((a, b) => b.length - a.length)

  for (const alias of sorted) {
    if (text.toLowerCase().includes(alias)) {
      const key = ALIAS_TO_KEY[alias]
      if (!found.includes(key)) {
        found.push(key)
      }
    }
  }

  return found
}

/**
 * 创建一个菜系匹配函数，用于过滤推荐结果
 *
 * 当用户提到了菜系时，只保留 categories 中包含任一匹配项的结果。
 * 通过别名映射，即使用户说"日料"也能匹配到"日本料理"。
 *
 * @param {string} query - 用户原始查询
 * @returns {function|null} 匹配函数 (categories: string) => boolean，无菜系提示时返回 null
 */
export function extractCuisineMatcher(query) {
  if (!query) return null

  const cuisines = extractCuisines(query)
  if (!cuisines.length) return null

  // 收集所有展开后的匹配词
  const allMatchTerms = new Set()
  for (const cuisine of cuisines) {
    const aliases = CUISINE_ALIASES[cuisine]
    if (aliases) {
      for (const alias of aliases) {
        allMatchTerms.add(alias.toLowerCase())
      }
    } else {
      allMatchTerms.add(cuisine.toLowerCase())
    }
  }

  const matchTerms = Array.from(allMatchTerms)

  return (categoriesStr) => {
    if (!categoriesStr) return false
    const lower = categoriesStr.toLowerCase()
    // 任一匹配词命中 categories 即保留
    return matchTerms.some(term => lower.includes(term))
  }
}

export default extractCuisineMatcher
