<template>
  <div class="callback-container">
    <p>{{ message }}</p>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'

const router = useRouter()
const route = useRoute()
const message = ref('Signing you in...')

onMounted(() => {
  const token = route.query.token
  const user = route.query.user

  if (token && user) {
    try {
      localStorage.setItem('access_token', token)
      localStorage.setItem('user', user)
      window.dispatchEvent(new Event('healthai:auth'))
      router.replace('/')
    } catch {
      message.value = 'Login failed. Please try again.'
    }
  } else {
    message.value = 'Login failed. Please try again.'
  }
})
</script>

<style scoped>
.callback-container {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: calc(100vh - 200px);
  font-size: 16px;
  color: var(--color-text-muted);
}
</style>
