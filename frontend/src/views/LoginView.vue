<template>
  <div class="login-page">
    <aside class="brand-pane">
      <div class="brand-content">
        <div class="brand-logo">⚕️</div>
        <h1 class="brand-title">HealthAI Ethics Assistant</h1>
        <p class="brand-tagline">
          Reason about ethical requirements for healthcare AI across
          <strong>privacy, safety, bias, transparency,</strong> and
          <strong>accountability</strong>.
        </p>

        <ul class="brand-features">
          <li><span class="feat-icon">🧭</span> Grounded in EU AI Act and NIST AI RMF</li>
          <li><span class="feat-icon">🔬</span> Triangulated with practitioner findings</li>
          <li><span class="feat-icon">💾</span> Save and revisit your past chats</li>
        </ul>
      </div>
      <div class="brand-footer">© HealthAI Ethics Assistant</div>
    </aside>

    <main class="form-pane">
      <div class="form-pane-inner">
        <div class="form-header">
          <h2 class="form-title">{{ initialMode === 'signup' ? 'Create your account' : 'Welcome back' }}</h2>
          <p class="form-subtitle">
            {{ initialMode === 'signup'
              ? 'Sign up to save your ethics chats.'
              : 'Sign in to continue where you left off.' }}
          </p>
        </div>

        <AuthForm :initial-mode="initialMode" @success="onSuccess" />

        <button type="button" class="guest-btn" @click="continueAsGuest">
          Continue without signing in
        </button>
      </div>
    </main>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import AuthForm from '../components/AuthForm.vue'

const router = useRouter()
const route = useRoute()

const initialMode = computed(() => (route.query.mode === 'signup' ? 'signup' : 'signin'))

function onSuccess() {
  router.push('/')
}

function continueAsGuest() {
  router.push('/')
}
</script>

<style scoped>
.login-page {
  display: grid;
  grid-template-columns: 1fr 1fr;
  min-height: 100vh;
  background: var(--color-bg);
}

/* ── Left brand pane ───────────────────────────────────────── */
.brand-pane {
  position: relative;
  background:
    radial-gradient(1200px 600px at -10% -10%, rgba(9, 105, 218, 0.18), transparent 60%),
    radial-gradient(900px 600px at 110% 110%, rgba(26, 127, 55, 0.18), transparent 60%),
    linear-gradient(160deg, #0b1f3a 0%, #0a1830 60%, #0a223a 100%);
  color: #f5f7fb;
  padding: 56px 56px 32px;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  overflow: hidden;
}
.brand-content { max-width: 460px; }
.brand-logo {
  width: 56px;
  height: 56px;
  border-radius: 16px;
  background: rgba(255, 255, 255, 0.08);
  border: 1px solid rgba(255, 255, 255, 0.14);
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-size: 28px;
  margin-bottom: 28px;
  backdrop-filter: blur(6px);
}
.brand-title {
  font-size: 28px;
  font-weight: 700;
  margin: 0 0 14px;
  letter-spacing: -0.01em;
}
.brand-tagline {
  font-size: 15px;
  line-height: 1.6;
  color: rgba(245, 247, 251, 0.78);
  margin: 0 0 28px;
}
.brand-tagline strong { color: #fff; font-weight: 600; }

.brand-features {
  list-style: none;
  padding: 0;
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.brand-features li {
  font-size: 14px;
  color: rgba(245, 247, 251, 0.85);
  display: flex;
  align-items: center;
  gap: 12px;
}
.feat-icon {
  width: 28px;
  height: 28px;
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.08);
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-size: 14px;
}

.brand-footer {
  font-size: 12px;
  color: rgba(245, 247, 251, 0.45);
}

/* ── Right form pane ───────────────────────────────────────── */
.form-pane {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 32px;
}
.form-pane-inner {
  width: 100%;
  max-width: 380px;
}
.form-header {
  margin-bottom: 22px;
}
.form-title {
  font-size: 22px;
  font-weight: 700;
  margin: 0 0 6px;
}
.form-subtitle {
  font-size: 14px;
  color: var(--color-text-muted);
}
.guest-btn {
  width: 100%;
  margin-top: 14px;
  padding: 11px;
  font-size: 14px;
  font-weight: 600;
  border-radius: var(--radius);
  border: 1px solid var(--color-border);
  background: var(--color-surface);
  color: var(--color-text);
  cursor: pointer;
  transition: background 0.15s, border-color 0.15s;
}
.guest-btn:hover { background: #f6f8fa; border-color: #bdc1c6; }

@media (max-width: 900px) {
  .login-page { grid-template-columns: 1fr; }
  .brand-pane {
    padding: 36px 28px;
    min-height: auto;
  }
  .brand-features { display: none; }
  .brand-tagline { font-size: 14px; margin-bottom: 0; }
}
</style>
