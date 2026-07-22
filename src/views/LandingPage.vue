<template>
  <div class="landing-page">
    <!-- Background atmosphere -->
    <div class="landing-bg"></div>

    <div class="landing-content">
      <!-- Logo & Tagline -->
      <div class="landing-hero">
        <div class="hero-icon">🍜</div>
        <h1 class="hero-title">大众点评 AI 助手</h1>
        <p class="hero-sub">智能美食推荐 · 真实口碑分析</p>
      </div>

      <!-- Entry Cards -->
      <div class="entry-cards">
        <button class="entry-card user-card stagger-1" @click="$router.push('/user')">
          <div class="card-illustration user-illustration">
            <span class="illu-icon">🔍</span>
            <span class="illu-icon-2">🍽️</span>
            <span class="illu-icon-3">💬</span>
          </div>
          <div class="card-body">
            <h2 class="card-title">我是食客</h2>
            <p class="card-desc">AI 对话推荐美食<br/>发现身边好店</p>
          </div>
          <div class="card-arrow">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="9 18 15 12 9 6"/></svg>
          </div>
        </button>

        <button class="entry-card biz-card stagger-2" @click="$router.push('/business-home')">
          <div class="card-illustration biz-illustration">
            <span class="illu-icon">📊</span>
            <span class="illu-icon-2">🏪</span>
            <span class="illu-icon-3">⭐</span>
          </div>
          <div class="card-body">
            <h2 class="card-title">我是商家</h2>
            <p class="card-desc">查看店铺数据与口碑<br/>AI 辅助经营决策</p>
          </div>
          <div class="card-arrow">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="9 18 15 12 9 6"/></svg>
          </div>
        </button>
      </div>

      <!-- Footer -->
      <p class="landing-footer">已有账号？<a href="javascript:;">直接进入</a></p>
    </div>
  </div>
</template>

<script>
export default {
  name: 'LandingPage',
}
</script>

<style scoped>
.landing-page {
  min-height: 100dvh;
  display: flex; align-items: center; justify-content: center;
  position: relative;
  overflow: hidden;
  background: linear-gradient(160deg, #FFF8F0 0%, #FFFAF5 30%, #FFF5EC 60%, #FFF8F2 100%);
}

/* ── Background atmosphere ── */
.landing-bg {
  position: absolute; inset: 0;
  pointer-events: none; z-index: 0;
}
.landing-bg::before {
  content: '';
  position: absolute;
  top: -30%; right: -20%;
  width: 500px; height: 500px;
  border-radius: 50%;
  background: radial-gradient(circle, rgba(255,107,53,0.08) 0%, transparent 70%);
}
.landing-bg::after {
  content: '';
  position: absolute;
  bottom: -20%; left: -25%;
  width: 400px; height: 400px;
  border-radius: 50%;
  background: radial-gradient(circle, rgba(240,165,0,0.06) 0%, transparent 70%);
}

.landing-content {
  position: relative; z-index: 1;
  width: 100%; max-width: 400px;
  padding: var(--space-8) var(--space-6);
  display: flex; flex-direction: column; align-items: center; gap: var(--space-10);
}

/* ── Hero ── */
.landing-hero { text-align: center; }
.hero-icon { font-size: 3.5rem; display: block; margin-bottom: var(--space-4); }
.hero-title {
  font-family: var(--font-display);
  font-size: var(--text-2xl); font-weight: 800;
  color: var(--ink); margin-bottom: var(--space-2);
  letter-spacing: -0.5px;
}
.hero-sub {
  font-size: var(--text-sm);
  color: var(--ink-muted);
  letter-spacing: 1px;
}

/* ── Entry Cards ── */
.entry-cards {
  width: 100%;
  display: flex; flex-direction: column; gap: var(--space-4);
}

.entry-card {
  display: flex; align-items: center; gap: var(--space-4);
  width: 100%;
  padding: var(--space-5) var(--space-4);
  border-radius: var(--radius-xl);
  text-align: left;
  cursor: pointer;
  transition: transform 0.3s var(--ease-out), box-shadow 0.3s var(--ease-out);
  position: relative; overflow: hidden;
}
.entry-card:active { transform: scale(0.97); }

/* ── Foodie card ── */
.user-card {
  background: #FFFFFF;
  border: 1.5px solid var(--border);
  box-shadow: 0 4px 20px rgba(26,26,46,0.06);
}
.user-card:hover {
  box-shadow: 0 8px 32px rgba(255,107,53,0.12);
  border-color: var(--coral-pale);
  transform: translateY(-2px);
}

/* ── Business card ── */
.biz-card {
  background: linear-gradient(135deg, #2D2D3A 0%, #1A1A2E 100%);
  color: #fff;
  box-shadow: 0 6px 24px rgba(26,26,46,0.15);
}
.biz-card:hover {
  box-shadow: 0 10px 36px rgba(26,26,46,0.25);
  transform: translateY(-2px);
}
.biz-card .card-desc { color: rgba(255,255,255,0.55); }
.biz-card .card-arrow { color: rgba(255,255,255,0.4); }

/* ── Card Illustration ── */
.card-illustration {
  width: 64px; height: 64px;
  border-radius: var(--radius-lg);
  flex-shrink: 0;
  display: flex; flex-wrap: wrap;
  align-items: center; justify-content: center;
  gap: 4px;
  padding: 10px;
  position: relative;
}
.user-illustration { background: linear-gradient(135deg, var(--coral-pale), #FFF0E8); }
.biz-illustration { background: rgba(255,255,255,0.1); }
.illu-icon { font-size: 1.25rem; }
.illu-icon-2 { font-size: 1.1rem; opacity: 0.7; }
.illu-icon-3 { font-size: 0.9rem; opacity: 0.5; }

/* ── Card Body ── */
.card-body { flex: 1; min-width: 0; }
.card-title {
  font-family: var(--font-display);
  font-size: var(--text-lg); font-weight: 700;
  margin-bottom: var(--space-1);
}
.biz-card .card-title { color: #fff; }
.card-desc {
  font-size: var(--text-sm); color: var(--ink-muted);
  line-height: 1.5; margin: 0;
}

.card-arrow {
  flex-shrink: 0;
  color: var(--ink-muted);
  transition: transform 0.3s var(--ease-out);
}
.entry-card:hover .card-arrow { transform: translateX(4px); }

/* ── Footer ── */
.landing-footer {
  font-size: var(--text-xs); color: var(--ink-muted);
}
.landing-footer a {
  color: var(--coral); font-weight: 600;
  text-decoration: none;
}

/* ── Motion ── */
.stagger-1 { animation: fadeUp 0.6s var(--ease-out) 0.1s both; }
.stagger-2 { animation: fadeUp 0.6s var(--ease-out) 0.2s both; }

@media (min-width: 768px) {
  .hero-icon { font-size: 4rem; }
  .hero-title { font-size: var(--text-3xl); }
}
</style>
