<template>
  <div class="app-shell">
    <router-view v-slot="{ Component }">
      <transition name="page" mode="out-in">
        <component :is="Component" />
      </transition>
    </router-view>
    <AppTabBar v-if="$route.name !== 'landing'" />
  </div>
</template>

<script>
import AppTabBar from './components/AppTabBar.vue'

export default {
  name: 'App',
  components: { AppTabBar }
}
</script>
