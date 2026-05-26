<template>
  <transition name="fade">
    <div class="modal-overlay" @click.self="$emit('close')" role="dialog" aria-modal="true" aria-labelledby="auth-modal-title">
      <div class="modal-card">
        <button class="close-btn" @click="$emit('close')" aria-label="Close">×</button>

        <div class="modal-header">
          <div class="brand-mark">⚕️</div>
          <h2 id="auth-modal-title" class="modal-title">Welcome to HealthAI Ethics Assistant</h2>
          <p class="modal-subtitle">Sign in to save your ethics chats and pick up where you left off.</p>
        </div>

        <AuthForm :initial-mode="initialMode" @success="onSuccess" />
      </div>
    </div>
  </transition>
</template>

<script setup>
import { onMounted, onBeforeUnmount } from 'vue'
import AuthForm from './AuthForm.vue'

const props = defineProps({
  initialMode: { type: String, default: 'signin' },
})
const emit = defineEmits(['close', 'success'])

function onSuccess(result) {
  emit('success', result)
  emit('close')
}

function onKeydown(e) {
  if (e.key === 'Escape') emit('close')
}

onMounted(() => {
  document.addEventListener('keydown', onKeydown)
  document.body.style.overflow = 'hidden'
})
onBeforeUnmount(() => {
  document.removeEventListener('keydown', onKeydown)
  document.body.style.overflow = ''
})
</script>

<style scoped>
.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(15, 23, 42, 0.45);
  backdrop-filter: blur(6px);
  -webkit-backdrop-filter: blur(6px);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px;
  z-index: 1000;
}

.modal-card {
  position: relative;
  width: 100%;
  max-width: 420px;
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: 16px;
  padding: 28px 28px 26px;
  box-shadow: 0 20px 60px rgba(15, 23, 42, 0.25);
  animation: pop 0.18s ease-out;
}

@keyframes pop {
  from { transform: translateY(8px) scale(0.98); opacity: 0; }
  to   { transform: translateY(0) scale(1);     opacity: 1; }
}

.close-btn {
  position: absolute;
  top: 10px;
  right: 12px;
  width: 32px;
  height: 32px;
  border: none;
  background: transparent;
  font-size: 22px;
  line-height: 1;
  color: var(--color-text-muted);
  border-radius: 8px;
  cursor: pointer;
  padding: 0;
}
.close-btn:hover {
  background: var(--color-surface-2);
  color: var(--color-text);
}

.modal-header {
  text-align: center;
  margin-bottom: 18px;
}
.brand-mark {
  width: 48px;
  height: 48px;
  border-radius: 14px;
  background: linear-gradient(135deg, #ddf4ff, #dafbe1);
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-size: 26px;
  margin-bottom: 12px;
}
.modal-title {
  font-size: 18px;
  font-weight: 700;
  margin: 0 0 4px;
  color: var(--color-text);
}
.modal-subtitle {
  font-size: 13px;
  color: var(--color-text-muted);
  margin: 0;
}

.fade-enter-active, .fade-leave-active {
  transition: opacity 0.15s ease;
}
.fade-enter-from, .fade-leave-to { opacity: 0; }
</style>
