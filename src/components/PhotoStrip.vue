<template>
  <div class="photo-strip">
    <div
      v-for="(photo, idx) in photos"
      :key="idx"
      class="photo-item"
      :style="{ width: photo.w || '160px', height: photo.h || '110px', background: photo.bg }"
    ></div>
  </div>
</template>

<script>
export default {
  name: 'PhotoStrip',
  props: {
    photos: { type: Array, required: true }
  }
}
</script>

<style scoped>
.photo-strip {
  display: flex; gap: var(--space-2);
  overflow-x: auto;
  scrollbar-width: none;
  padding-bottom: var(--space-1);
}
.photo-strip::-webkit-scrollbar { display: none; }
.photo-item {
  border-radius: var(--radius-md);
  flex-shrink: 0;
}
</style>
