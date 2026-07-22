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

export default router
