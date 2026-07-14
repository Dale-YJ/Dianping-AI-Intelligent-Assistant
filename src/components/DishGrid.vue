<template>
  <div class="dish-grid">
    <div v-for="dish in dishes" :key="dish.name" class="dish-card">
      <div class="dish-img" :style="{ background: dish.bg }"></div>
      <div class="dish-name">{{ dish.name }}</div>
      <div class="dish-likes">👍 {{ dish.likes }}推荐</div>
    </div>
  </div>
</template>

<script>
export default {
  name: 'DishGrid',
  props: {
    dishes: { type: Array, required: true }
  }
}
</script>

<style scoped>
.dish-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: var(--space-3);
}
.dish-card { text-align: center; }
.dish-img {
  width: 100%; aspect-ratio: 1;
  border-radius: var(--radius-md);
  margin-bottom: var(--space-1);
}
.dish-name { font-size: var(--text-sm); font-weight: 500; }
.dish-likes { font-size: var(--text-xs); color: var(--ink-muted); display: flex; align-items: center; justify-content: center; gap: 2px; }

@media (min-width: 768px) {
  .dish-grid { grid-template-columns: repeat(4, 1fr); }
}
</style>
