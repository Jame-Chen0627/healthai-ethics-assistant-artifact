<template>
  <div class="auth-form-wrap">
    <div class="tabs" role="tablist">
      <button
        type="button"
        class="tab"
        :class="{ active: mode === 'signin' }"
        role="tab"
        :aria-selected="mode === 'signin'"
        @click="setMode('signin')"
      >Sign In</button>
      <button
        type="button"
        class="tab"
        :class="{ active: mode === 'signup' }"
        role="tab"
        :aria-selected="mode === 'signup'"
        @click="setMode('signup')"
      >Sign Up</button>
    </div>

    <form @submit.prevent="handleSubmit" class="auth-form" novalidate>
      <div class="form-group" :class="{ 'has-error': fieldErrors.username }">
        <label for="auth-username">Username / Address</label>
        <input id="auth-username" v-model.trim="form.username" type="text" autocomplete="username" placeholder="your-handle" />
        <p v-if="fieldErrors.username" class="field-error">{{ fieldErrors.username }}</p>
      </div>

      <div v-if="mode === 'signup'" class="form-group" :class="{ 'has-error': fieldErrors.email }">
        <label for="auth-email">Email</label>
        <input id="auth-email" v-model.trim="form.email" type="email" autocomplete="email" placeholder="you@example.com" />
        <p v-if="fieldErrors.email" class="field-error">{{ fieldErrors.email }}</p>
      </div>

      <div class="form-group" :class="{ 'has-error': fieldErrors.password }">
        <label for="auth-password">Password</label>
        <input id="auth-password" v-model="form.password" type="password" :autocomplete="mode === 'signup' ? 'new-password' : 'current-password'" :placeholder="mode === 'signup' ? 'At least 8 characters' : '••••••••'" />
        <p v-if="fieldErrors.password" class="field-error">{{ fieldErrors.password }}</p>
      </div>

      <div v-if="mode === 'signup'" class="form-group" :class="{ 'has-error': fieldErrors.confirmPassword }">
        <label for="auth-password-confirm">Confirm password</label>
        <input id="auth-password-confirm" v-model="form.confirmPassword" type="password" autocomplete="new-password" placeholder="Re-enter your password" />
        <p v-if="fieldErrors.confirmPassword" class="field-error">{{ fieldErrors.confirmPassword }}</p>
      </div>

      <p v-if="error" class="error-message" role="alert">{{ error }}</p>

      <button type="submit" class="primary submit-btn" :disabled="loading">
        {{ loading ? 'Please wait…' : (mode === 'signup' ? 'Create account' : 'Sign in') }}
      </button>
    </form>

    <div class="divider"><span>or continue with</span></div>

    <div class="oauth-buttons">
      <button type="button" class="oauth-btn google-btn" @click="loginWithGoogle">
        <svg class="oauth-icon" viewBox="0 0 18 18" width="18" height="18" xmlns="http://www.w3.org/2000/svg">
          <path fill="#4285F4" d="M17.64 9.2c0-.64-.06-1.25-.16-1.84H9v3.48h4.84a4.14 4.14 0 0 1-1.8 2.71v2.26h2.92c1.71-1.57 2.68-3.88 2.68-6.61z"/>
          <path fill="#34A853" d="M9 18c2.43 0 4.47-.81 5.96-2.18l-2.92-2.26c-.81.54-1.84.86-3.04.86-2.34 0-4.32-1.58-5.03-3.7H.96v2.33A9 9 0 0 0 9 18z"/>
          <path fill="#FBBC05" d="M3.97 10.71a5.41 5.41 0 0 1 0-3.42V4.96H.96a9 9 0 0 0 0 8.08l3.01-2.33z"/>
          <path fill="#EA4335" d="M9 3.58c1.32 0 2.5.45 3.44 1.35l2.58-2.58A9 9 0 0 0 .96 4.96l3.01 2.33C4.68 5.16 6.66 3.58 9 3.58z"/>
        </svg>
        <span>Continue with Google</span>
      </button>

      <button type="button" class="oauth-btn github-btn" @click="loginWithGithub">
        <svg class="oauth-icon" viewBox="0 0 16 16" width="18" height="18" fill="currentColor">
          <path d="M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 5.47 7.59.4.07.55-.17.55-.38 0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13-.28-.15-.68-.52-.01-.53.63-.01 1.08.58 1.23.82.72 1.21 1.87.87 2.33.66.07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82.64-.18 1.32-.27 2-.27.68 0 1.36.09 2 .27 1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82 1.27.82 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48 0 1.07-.01 1.93-.01 2.2 0 .21.15.46.55.38A8.013 8.013 0 0016 8c0-4.42-3.58-8-8-8z"/>
        </svg>
        <span>Continue with GitHub</span>
      </button>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, watch } from 'vue'
import { login, register } from '../api/index.js'

const props = defineProps({
  initialMode: { type: String, default: 'signin' }, // 'signin' | 'signup'
})
const emit = defineEmits(['success'])

const mode = ref(props.initialMode === 'signup' ? 'signup' : 'signin')
const loading = ref(false)
const error = ref('')
const form = reactive({ username: '', email: '', password: '', confirmPassword: '' })
const fieldErrors = reactive({ username: '', email: '', password: '', confirmPassword: '' })

watch(() => props.initialMode, (m) => {
  mode.value = m === 'signup' ? 'signup' : 'signin'
})

watch(mode, () => {
  error.value = ''
  resetFieldErrors()
  form.confirmPassword = ''
})

function setMode(m) {
  mode.value = m
  error.value = ''
  resetFieldErrors()
}

function resetFieldErrors() {
  fieldErrors.username = ''
  fieldErrors.email = ''
  fieldErrors.password = ''
  fieldErrors.confirmPassword = ''
}

const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/

function validate() {
  resetFieldErrors()
  let ok = true
  if (!form.username || form.username.length < 2) {
    fieldErrors.username = 'Please enter your username (at least 2 characters).'
    ok = false
  }
  if (mode.value === 'signup') {
    if (!form.email) {
      fieldErrors.email = 'Email is required.'
      ok = false
    } else if (!EMAIL_RE.test(form.email)) {
      fieldErrors.email = 'Please enter a valid email address.'
      ok = false
    }
  }
  if (!form.password) {
    fieldErrors.password = 'Password is required.'
    ok = false
  } else if (mode.value === 'signup' && form.password.length < 8) {
    fieldErrors.password = 'Password must be at least 8 characters.'
    ok = false
  }
  if (mode.value === 'signup') {
    if (!form.confirmPassword) {
      fieldErrors.confirmPassword = 'Please confirm your password.'
      ok = false
    } else if (form.confirmPassword !== form.password) {
      fieldErrors.confirmPassword = 'Passwords do not match.'
      ok = false
    }
  }
  return ok
}

const BACKEND_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

function loginWithGoogle() {
  window.location.href = `${BACKEND_URL}/auth/google/login`
}
function loginWithGithub() {
  window.location.href = `${BACKEND_URL}/auth/github/login`
}

async function handleSubmit() {
  error.value = ''
  if (!validate()) return
  loading.value = true
  try {
    const result = mode.value === 'signup'
      ? await register({ username: form.username, email: form.email, password: form.password })
      : await login({ username: form.username, password: form.password })
    localStorage.setItem('access_token', result.access_token)
    localStorage.setItem('user', JSON.stringify(result.user))
    window.dispatchEvent(new Event('healthai:auth'))
    emit('success', result)
  } catch (err) {
    error.value = err.response?.data?.detail || err.message || 'Something went wrong'
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.auth-form-wrap {
  display: flex;
  flex-direction: column;
  gap: 18px;
}

.tabs {
  display: flex;
  background: var(--color-surface-2);
  border-radius: var(--radius);
  padding: 4px;
  gap: 4px;
}
.tab {
  flex: 1;
  background: transparent;
  border: none;
  padding: 8px 12px;
  border-radius: 7px;
  font-size: 13px;
  font-weight: 600;
  color: var(--color-text-muted);
  transition: background 0.15s, color 0.15s;
}
.tab.active {
  background: var(--color-surface);
  color: var(--color-text);
  box-shadow: 0 1px 2px rgba(31, 35, 40, 0.08);
}

.oauth-buttons {
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.oauth-btn {
  width: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 10px;
  padding: 11px;
  font-size: 14px;
  font-weight: 600;
  border-radius: var(--radius);
  border: 1px solid var(--color-border);
  cursor: pointer;
  transition: all 0.15s;
  background: var(--color-surface);
  color: var(--color-text);
}
.google-btn { border-color: #dadce0; }
.google-btn:hover { background: #f8f9fa; border-color: #bdc1c6; }
.github-btn {
  background: #24292f;
  color: #fff;
  border-color: #24292f;
}
.github-btn:hover { background: #32383f; }
.oauth-icon { flex-shrink: 0; }

.divider {
  display: flex;
  align-items: center;
  gap: 12px;
  color: var(--color-text-muted);
  font-size: 12px;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}
.divider::before,
.divider::after {
  content: '';
  flex: 1;
  height: 1px;
  background: var(--color-border);
}
.divider span { flex-shrink: 0; }

.auth-form {
  display: flex;
  flex-direction: column;
  gap: 14px;
}
.form-group {
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.form-group label {
  font-size: 12px;
  font-weight: 600;
  color: var(--color-text-muted);
  text-transform: uppercase;
  letter-spacing: 0.4px;
}
.form-group input {
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius);
  padding: 10px 12px;
  font-size: 14px;
  color: var(--color-text);
  outline: none;
  transition: border-color 0.15s, box-shadow 0.15s;
}
.form-group input:focus {
  border-color: var(--color-accent);
  box-shadow: 0 0 0 3px rgba(9, 105, 218, 0.15);
}
.form-group.has-error input {
  border-color: var(--color-error, #cf222e);
}
.form-group.has-error input:focus {
  box-shadow: 0 0 0 3px rgba(207, 34, 46, 0.15);
}
.field-error {
  margin: 4px 0 0;
  font-size: 12px;
  color: var(--color-error, #cf222e);
}
.error-message {
  color: var(--color-error);
  font-size: 13px;
  margin: -4px 0 0;
  background: #ffebe9;
  border: 1px solid #ff818266;
  padding: 8px 10px;
  border-radius: 8px;
}
.submit-btn {
  width: 100%;
  padding: 11px;
  font-size: 14px;
  margin-top: 4px;
}
.submit-btn:disabled {
  opacity: 0.65;
  cursor: not-allowed;
}
</style>
