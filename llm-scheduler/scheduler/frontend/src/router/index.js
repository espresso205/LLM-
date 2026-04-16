import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '../stores/auth'

const routes = [
  { path: '/', redirect: '/nodes' },
  { path: '/nodes', component: () => import('../views/Nodes.vue') },
  { path: '/strategy', component: () => import('../views/Strategy.vue') },
  { path: '/logs', component: () => import('../views/Logs.vue') },
]

const router = createRouter({ history: createWebHistory(), routes })

router.beforeEach(() => {
  const auth = useAuthStore()
  auth.checkAndRedirect()
  return true
})

export default router
