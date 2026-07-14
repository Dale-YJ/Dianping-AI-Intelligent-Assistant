<template>
  <div class="profile-header">
    <div class="profile-bg"></div>
    <div class="profile-avatar reveal-scale">{{ avatarInitial }}</div>
    <div class="profile-name">{{ name }}</div>
    <div class="profile-level">{{ level }}</div>
  </div>
</template>

<script>
export default {
  name: 'ProfileHeader',
  props: {
    avatarInitial: { type: String, default: 'M' },
    name: { type: String, default: '美食猎人小王' },
    level: { type: String, default: '🌟 钻石会员 · 签到 365 天' }
  },
  mounted() {
    // reveal-scale triggers on mount
  }
}
</script>

<style scoped>
.profile-header {
  padding: var(--space-8) var(--space-4) var(--space-6);
  text-align: center;
  position: relative;
  overflow: hidden;
}
.profile-bg {
  position: absolute; inset: 0;
  background: linear-gradient(180deg, var(--coral-pale) 0%, var(--warm-bg) 100%);
  z-index: -1;
}
.profile-avatar {
  width: 72px; height: 72px;
  border-radius: 50%;
  background: linear-gradient(135deg, #FF6B35, #FF8C42);
  display: flex; align-items: center; justify-content: center;
  font-size: var(--text-2xl); color: #fff; font-weight: 700;
  margin: 0 auto var(--space-3);
  box-shadow: 0 4px 20px rgba(255,107,53,0.3);
}
.profile-name { font-family: var(--font-display); font-size: var(--text-xl); font-weight: 700; margin-bottom: var(--space-1); }
.profile-level { font-size: var(--text-sm); color: var(--ink-muted); }
</style>
