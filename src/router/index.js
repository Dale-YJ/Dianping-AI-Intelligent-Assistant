import { createRouter, createWebHashHistory } from 'vue-router'
import LandingPage from '../views/LandingPage.vue'
import HomePage from '../views/HomePage.vue'
import FoodListPage from '../views/FoodListPage.vue'
import RestaurantDetail from '../views/RestaurantDetail.vue'
import BusinessDashboard from '../views/BusinessDashboard.vue'
import BusinessHome from '../views/BusinessHome.vue'
import RestaurantSelect from '../views/RestaurantSelect.vue'

const routes = [
  { path: '/', name: 'landing', component: LandingPage },
  { path: '/user', name: 'user', component: HomePage },
  { path: '/list', name: 'list', component: FoodListPage },
  { path: '/detail/:id?', name: 'detail', component: RestaurantDetail },
  { path: '/business/:id?', name: 'business', component: BusinessDashboard },
  { path: '/business-home', name: 'biz-home', component: BusinessHome },
  { path: '/select-shop', name: 'select-shop', component: RestaurantSelect },
]

const router = createRouter({
  history: createWebHashHistory(),
  routes
})

/**
 * 路由守卫：切换商家端 ↔ 客户端时清除 sessionStorage 会话 ID，
 * 防止后端对话上下文跨身份泄露。
 */
router.beforeEach((to, from) => {
  if (!from.path) return // 首次进入，跳过

  const wasBiz = from.path.startsWith('/business') || from.path.startsWith('/select-shop')
  const isBiz = to.path.startsWith('/business') || to.path.startsWith('/select-shop')

  if (wasBiz !== isBiz) {
    try {
      sessionStorage.removeItem('dp_ai_conversation_id')
      sessionStorage.removeItem('dp_ai_conversation_id_biz')
    } catch {}
  }
})

export default router
