<template>
  <div class="tag-cloud">
    <div class="tag-section" v-for="group in groups" :key="group.name">
      <h4 class="tag-section-title">{{ group.icon }} {{ group.name }}</h4>
      <div class="tag-row">
        <span
          v-for="tag in group.tags"
          :key="tag.text"
          class="tag"
          :style="{ fontSize: tagSize(tag.count, group.max), opacity: tagOpacity(tag.count, group.max) }"
        >
          {{ tag.text }}
          <sup class="tag-count">{{ tag.count }}</sup>
        </span>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: 'FeatureTagCloud',
  props: {
    groups: { type: Array, default: () => [] }
    /* groups: [{ name: '菜品', icon: '🍽️', tags: [{text:'红烧肉',count:15},...], max: 15 }, ...] */
  },
  methods: {
    tagSize(count, max) {
      const min = 0.75, range = 0.65
      return `${min + (count / max) * range}rem`
    },
    tagOpacity(count, max) {
      return 0.55 + (count / max) * 0.45
    }
  }
}
</script>

<style scoped>
.tag-cloud { display: flex; flex-direction: column; gap: var(--space-5); }
.tag-section-title {
  font-family: var(--font-display);
  font-size: var(--text-sm);
  font-weight: 600;
  color: var(--ink-light);
  margin-bottom: var(--space-2);
}
.tag-row {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2);
  align-items: baseline;
}
.tag {
  display: inline-flex;
  align-items: baseline;
  color: var(--coral-deep);
  font-weight: 600;
  padding: 2px var(--space-2);
  background: var(--coral-pale);
  border-radius: var(--radius-full);
  transition: transform var(--duration-fast);
  cursor: default;
  line-height: var(--leading-tight);
}
.tag:hover { transform: scale(1.08); }
.tag-count {
  font-size: 0.65em;
  margin-left: 1px;
  color: var(--coral);
}
</style>
