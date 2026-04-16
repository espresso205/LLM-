import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '../stores/auth'
const routes = [
  { path: '/', redirect: '/test' },
  { path: '/test', component: () => import('../views/TestUI.vue') },
  { path: '/model', component: () => import('../views/ModelInfo.vue') },
  { path: '/logs', component: () => import('../views/Logs.vue') },
]
const router = createRouter({ history: createWebHistory(), routes })
router.beforeEach(() => { useAuthStore().checkAndRedirect(); return true })
export default router
