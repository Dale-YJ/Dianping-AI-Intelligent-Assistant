/**
 * 共享数据 Store — 跨页面传递商家数据
 * ==========================================
 * 利用后端已有的 Chat API 返回的 RecommendationItem 数据，
 * 在页面间传递，无需新增后端接口。
 *
 * 用法：
 *   import { sharedStore } from '@/stores/sharedData.js'
 *   sharedStore.setBusiness(recData)      // 在首页点击推荐时存储
 *   const biz = sharedStore.currentBusiness  // 在详情页读取
 */

import { reactive } from 'vue'

export const sharedStore = reactive({
  /** 当前查看的商家完整数据 */
  currentBusiness: null,

  /** 最近一次搜索的商家列表 */
  businessList: [],

  /** 存储当前商家数据（从推荐卡片点击时调用） */
  setBusiness(data) {
    this.currentBusiness = data
  },

  /** 存储商家列表 */
  setBusinessList(list) {
    this.businessList = list
  },

  /** 清除 */
  clear() {
    this.currentBusiness = null
    this.businessList = []
  },
})
