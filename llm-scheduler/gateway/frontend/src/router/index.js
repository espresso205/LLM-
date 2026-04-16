import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '../stores/auth'

const routes = [
  { path: '/login', component: () => import('../views/Login.vue'), meta: { guest: true } },
  { path: '/', redirect: '/chat' },
  { path: '/chat', component: () => import('../views/Chat.vue'), meta: { requiresAuth: true } },
  { path: '/history', component: () => import('../views/History.vue'), meta: { requiresAuth: true } },
  { path: '/admin/history', component: () => import('../views/AdminHistory.vue'), meta: { requiresAuth: true, requiresAdmin: true } },
  { path: '/admin/users', component: () => import('../views/AdminUsers.vue'), meta: { requiresAuth: true, requiresAdmin: true } },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

router.beforeEach((to) => {
  const auth = useAuthStore()
  if (to.meta.requiresAuth && !auth.isAuthenticated) return '/login'
  if (to.meta.requiresAdmin && !auth.isAdmin) return '/chat'
  if (to.meta.guest && auth.isAuthenticated) return '/chat'
  return true
})

export default router
