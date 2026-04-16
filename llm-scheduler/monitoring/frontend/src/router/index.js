import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '../stores/auth'
const routes = [
  { path: '/', redirect: '/dashboard' },
  { path: '/dashboard', component: () => import('../views/Dashboard.vue') },
  { path: '/trends', component: () => import('../views/Trends.vue') },
  { path: '/nodes', component: () => import('../views/NodeCompare.vue') },
  { path: '/alerts', component: () => import('../views/Alerts.vue') },
]
const router = createRouter({ history: createWebHistory(), routes })
router.beforeEach(() => { useAuthStore().checkAndRedirect(); return true })
export default router
