/**
 * detectRegion — 检测用户输入中是否包含非中国地区
 * ================================================
 * Yelp 数据集以美国为主，当用户查询中提到非中国地区时，
 * 需要翻译为英文关键词以提高搜索精度。
 *
 * 用法：
 *   import { hasNonChinaLocation } from '../utils/detectRegion.js'
 *   if (hasNonChinaLocation('纽约有什么好吃的川菜')) → true → 翻译
 *   if (hasNonChinaLocation('附近有什么好吃的川菜')) → false → 不翻译
 */

/* ─── 非中国城市名（中英文） ─── */
const NON_CHINA_CITIES = [
  // 美国
  '纽约', 'New York', 'NYC',
  '旧金山', '三藩', 'San Francisco',
  '洛杉矶', 'LA', 'Los Angeles',
  '芝加哥', 'Chicago',
  '波士顿', 'Boston',
  '西雅图', 'Seattle',
  '拉斯维加斯', 'Las Vegas',
  '迈阿密', 'Miami',
  '华盛顿', 'DC', 'Washington',
  '休斯顿', 'Houston',
  '费城', 'Philadelphia',
  '圣地亚哥', 'San Diego',
  '波特兰', 'Portland',
  '奥斯汀', 'Austin',
  '亚特兰大', 'Atlanta',
  '丹佛', 'Denver',
  '凤凰城', 'Phoenix',
  '达拉斯', 'Dallas',
  '匹兹堡', 'Pittsburgh',
  '底特律', 'Detroit',
  '圣何塞', 'San Jose',
  '夏威夷', 'Hawaii', '檀香山', 'Honolulu',
  // 加拿大
  '多伦多', 'Toronto',
  '温哥华', 'Vancouver',
  '蒙特利尔', 'Montreal',
  // 日本
  '东京', 'Tokyo',
  '大阪', 'Osaka',
  '京都', 'Kyoto',
  '北海道', 'Hokkaido',
  '福冈', 'Fukuoka',
  '名古屋', 'Nagoya',
  // 韩国
  '首尔', 'Seoul',
  '釜山', 'Busan',
  '济州', 'Jeju',
  // 欧洲
  '伦敦', 'London',
  '巴黎', 'Paris',
  '罗马', 'Rome',
  '米兰', 'Milan',
  '巴塞罗那', 'Barcelona',
  '马德里', 'Madrid',
  '柏林', 'Berlin',
  '慕尼黑', 'Munich',
  '阿姆斯特丹', 'Amsterdam',
  // 东南亚
  '曼谷', 'Bangkok',
  '新加坡', 'Singapore',
  '吉隆坡', 'Kuala Lumpur',
  '巴厘岛', 'Bali',
  '普吉', 'Phuket',
  '清迈', 'Chiang Mai',
  '胡志明', 'Ho Chi Minh',
  '河内', 'Hanoi',
  // 澳洲
  '悉尼', 'Sydney',
  '墨尔本', 'Melbourne',
  '布里斯班', 'Brisbane',
  // 中东/其他
  '迪拜', 'Dubai',
  '伊斯坦布尔', 'Istanbul',
]

/* ─── 非中国国家/地区名 ─── */
const NON_CHINA_COUNTRIES = [
  '美国', 'USA', 'America', 'US',
  '日本', 'Japan',
  '韩国', 'Korea', 'South Korea',
  '英国', 'UK', 'England', 'Britain',
  '法国', 'France',
  '意大利', 'Italy',
  '德国', 'Germany',
  '西班牙', 'Spain',
  '加拿大', 'Canada',
  '澳大利亚', 'Australia', '澳洲',
  '泰国', 'Thailand',
  '越南', 'Vietnam',
  '新加坡', 'Singapore',
  '马来西亚', 'Malaysia',
  '印尼', 'Indonesia',
  '印度', 'India',
  '阿联酋', 'UAE',
  '土耳其', 'Turkey',
  '瑞士', 'Switzerland',
  '荷兰', 'Netherlands',
]

/* ─── 中国城市（不触发翻译） ─── */
const CHINA_CITIES = [
  '北京', 'Beijing', '上海', 'Shanghai', '广州', 'Guangzhou',
  '深圳', 'Shenzhen', '成都', 'Chengdu', '重庆', 'Chongqing',
  '杭州', 'Hangzhou', '南京', 'Nanjing', '武汉', 'Wuhan',
  '西安', "Xi'an", '长沙', 'Changsha', '天津', 'Tianjin',
  '苏州', 'Suzhou', '厦门', 'Xiamen', '青岛', 'Qingdao',
  '大连', 'Dalian', '昆明', 'Kunming', '三亚', 'Sanya',
]

/**
 * 判断用户查询是否指定了非中国地区
 * @param {string} text
 * @returns {boolean}
 */
export function hasNonChinaLocation(text) {
  if (!text) return false

  // 先检查是否是明确的中国城市 → 不翻译
  for (const city of CHINA_CITIES) {
    if (text.includes(city)) return false
  }

  // 检查非中国城市
  for (const city of NON_CHINA_CITIES) {
    if (text.includes(city)) return true
  }

  // 检查非中国国家
  for (const country of NON_CHINA_COUNTRIES) {
    if (text.includes(country)) return true
  }

  // 包含纯英文（可能是英文城市名），也触发翻译
  if (/[a-zA-Z]{3,}/.test(text)) return true

  return false
}

/**
 * 从用户查询中提取中国城市名（最长匹配优先）
 * @param {string} text - 用户原始查询
 * @returns {string|null} 城市英文名，如 'Shanghai'；未匹配返回 null
 */
export function extractCity(text) {
  if (!text) return null

  // 按长度降序排列，保证"石家庄"不会只匹配到"石"
  const sorted = [...CHINA_CITIES].sort((a, b) => b.length - a.length)

  for (const city of sorted) {
    if (text.includes(city)) {
      // 返回对应的英文名（用于 API 过滤）
      switch (city) {
        case '北京': case 'Beijing': return 'Beijing'
        case '上海': case 'Shanghai': return 'Shanghai'
        case '广州': case 'Guangzhou': return 'Guangzhou'
        case '深圳': case 'Shenzhen': return 'Shenzhen'
        case '成都': case 'Chengdu': return 'Chengdu'
        case '重庆': case 'Chongqing': return 'Chongqing'
        case '杭州': case 'Hangzhou': return 'Hangzhou'
        case '南京': case 'Nanjing': return 'Nanjing'
        case '武汉': case 'Wuhan': return 'Wuhan'
        case '西安': case "Xi'an": return "Xi'an"
        case '长沙': case 'Changsha': return 'Changsha'
        case '天津': case 'Tianjin': return 'Tianjin'
        case '苏州': case 'Suzhou': return 'Suzhou'
        case '厦门': case 'Xiamen': return 'Xiamen'
        case '青岛': case 'Qingdao': return 'Qingdao'
        case '大连': case 'Dalian': return 'Dalian'
        case '昆明': case 'Kunming': return 'Kunming'
        case '三亚': case 'Sanya': return 'Sanya'
        default: return null
      }
    }
  }
  return null
}

export default hasNonChinaLocation
