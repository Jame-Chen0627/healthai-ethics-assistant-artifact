import { createRouter, createWebHistory } from 'vue-router'
import EthicsAssistantView from '../views/EthicsAssistantView.vue'
import LoginView from '../views/LoginView.vue'
import OAuthCallback from '../views/OAuthCallback.vue'

const routes = [
  { path: '/login', name: 'login', component: LoginView },
  { path: '/auth/callback', name: 'oauth-callback', component: OAuthCallback },
  { path: '/', name: 'home', component: EthicsAssistantView },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

router.beforeEach((to) => {
  const token = localStorage.getItem('access_token')
  if (to.name === 'login' && token) {
    return { name: 'home' }
  }
})

export default router
