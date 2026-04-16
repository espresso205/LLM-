import { defineStore } from 'pinia'

function initFromUrl() {
  const params = new URLSearchParams(window.location.search)
  const token = params.get('token')
  if (token) {
    localStorage.setItem('llm_token', token)
    try {
      const payload = JSON.parse(atob(token.split('.')[1]))
      const user = { id: payload.sub, username: payload.username, role: payload.role }
      localStorage.setItem('llm_user', JSON.stringify(user))
    } catch {}
    // Clean token from URL without reload
    const url = new URL(window.location.href)
    url.searchParams.delete('token')
    window.history.replaceState({}, '', url.toString())
  }
}

initFromUrl()

export const useAuthStore = defineStore('auth', {
  state: () => ({
    token: localStorage.getItem('llm_token') || null,
    user: JSON.parse(localStorage.getItem('llm_user') || 'null'),
  }),
  getters: {
    isAuthenticated: s => !!s.token,
    isAdmin: s => s.user?.role === 'admin',
  },
  actions: {
    checkAndRedirect() {
      if (!this.isAuthenticated || !this.isAdmin) {
        window.location.href = 'http://localhost:8080/login'
      }
    },
  },
})
