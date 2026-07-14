import { createRouter, createWebHashHistory } from 'vue-router'
import HomePage from '../views/HomePage.vue'
import FoodListPage from '../views/FoodListPage.vue'
import RestaurantDetail from '../views/RestaurantDetail.vue'
import ProfilePage from '../views/ProfilePage.vue'
import BusinessDashboard from '../views/BusinessDashboard.vue'

const routes = [
  { path: '/', name: 'home', component: HomePage },
  { path: '/list', name: 'list', component: FoodListPage },
  { path: '/detail/:id?', name: 'detail', component: RestaurantDetail },
  { path: '/business/:id?', name: 'business', component: BusinessDashboard },
  { path: '/profile', name: 'profile', component: ProfilePage }
]

const router = createRouter({
  history: createWebHashHistory(),
  routes
})

export default router
