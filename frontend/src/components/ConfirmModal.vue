<template>
  <div class="cm-backdrop" @click.self="onCancel" @keydown.esc="onCancel" tabindex="-1">
    <div class="cm-card" role="alertdialog" aria-modal="true" :aria-label="title">
      <header class="cm-header">
        <span class="cm-icon" :class="tone" aria-hidden="true">
          <svg v-if="tone === 'danger'" viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M10.3 3.86 1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/>
            <line x1="12" y1="9" x2="12" y2="13"/>
            <circle cx="12" cy="17" r="0.8"/>
          </svg>
          <svg v-else viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <circle cx="12" cy="12" r="10"/>
            <line x1="12" y1="8" x2="12" y2="13"/>
            <circle cx="12" cy="16" r="0.8"/>
          </svg>
        </span>
        <h3>{{ title }}</h3>
      </header>
      <p class="cm-message">{{ message }}</p>
      <footer class="cm-actions">
        <button class="cm-btn ghost" @click="onCancel">{{ cancelLabel }}</button>
        <button class="cm-btn" :class="tone === 'danger' ? 'danger' : 'primary'" @click="onConfirm" ref="confirmBtn">
          {{ confirmLabel }}
        </button>
      </footer>
    </div>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'

const props = defineProps({
  title: { type: String, default: 'Confirm' },
  message: { type: String, required: true },
  confirmLabel: { type: String, default: 'OK' },
  cancelLabel: { type: String, default: 'Cancel' },
  tone: { type: String, default: 'info' }, // 'info' | 'danger'
})
const emit = defineEmits(['confirm', 'cancel'])

const confirmBtn = ref(null)
function onConfirm() { emit('confirm') }
function onCancel() { emit('cancel') }

onMounted(() => {
  // Autofocus the confirm button so Enter accepts and Esc rejects.
  confirmBtn.value?.focus()
})
</script>

<style scoped>
.cm-backdrop {
  position: fixed; inset: 0;
  background: rgba(15, 20, 28, 0.5);
  display: flex; align-items: center; justify-content: center;
  z-index: 1200;
  animation: fade 0.12s ease-out;
}
@keyframes fade { from { opacity: 0; } to { opacity: 1; } }
.cm-card {
  background: var(--color-surface, #fff);
  border-radius: 12px;
  width: min(420px, 92vw);
  padding: 18px 20px 14px;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.25);
  animation: pop 0.14s ease-out;
}
@keyframes pop {
  from { transform: translateY(8px) scale(0.97); opacity: 0; }
  to   { transform: translateY(0) scale(1); opacity: 1; }
}
.cm-header { display: flex; align-items: center; gap: 10px; margin-bottom: 6px; }
.cm-header h3 { margin: 0; font-size: 15px; font-weight: 700; }
.cm-icon {
  width: 32px; height: 32px; border-radius: 50%;
  display: inline-flex; align-items: center; justify-content: center;
  flex-shrink: 0;
}
.cm-icon.info { background: #e3f0ff; color: #1f6feb; }
.cm-icon.danger { background: #ffd6d3; color: #a40e26; }
.cm-message {
  margin: 4px 0 16px;
  font-size: 13.5px;
  line-height: 1.5;
  color: var(--color-text, #1f2328);
}
.cm-actions { display: flex; justify-content: flex-end; gap: 8px; }
.cm-btn {
  border: none; border-radius: 6px;
  padding: 7px 16px; font-size: 13px; font-weight: 600;
  cursor: pointer;
}
.cm-btn.ghost {
  background: transparent;
  border: 1px solid var(--color-border, #d0d7de);
  color: var(--color-text, #1f2328);
}
.cm-btn.ghost:hover { background: var(--color-surface-2, #f6f8fa); }
.cm-btn.primary { background: #fb8500; color: #fff; }
.cm-btn.primary:hover { background: #e07700; }
.cm-btn.danger { background: #c33; color: #fff; }
.cm-btn.danger:hover { background: #a40e26; }
.cm-btn:focus-visible { outline: 2px solid #1f6feb; outline-offset: 2px; }
</style>
