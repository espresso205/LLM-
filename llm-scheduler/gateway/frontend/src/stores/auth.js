import { defineStore } from 'pinia'
import axios from 'axios'

export const useAuthStore = defineStore('auth', {
  state: () => ({
    token: localStorage.getItem('llm_token') || null,
    user: JSON.parse(localStorage.getItem('llm_user') || 'null'),
  }),
  getters: {
    isAuthenticated: s => !!s.token,
    isAdmin: s => s.user?.role === 'admin',
    username: s => s.user?.username || '',
    role: s => s.user?.role || '',
  },
  actions: {
    async login(username, password) {
      const form = new FormData()
      form.append('username', username)
      form.append('password', password)
      const { data } = await axios.post('/auth/login', form)
      this.token = data.access_token
      // Decode user info from JWT payload
      const payload = JSON.parse(atob(data.access_token.split('.')[1]))
      this.user = { id: payload.sub, username: payload.username, role: payload.role }
      localStorage.setItem('llm_token', this.token)
      localStorage.setItem('llm_user', JSON.stringify(this.user))
    },
    logout() {
      this.token = null
      this.user = null
      localStorage.removeItem('llm_token')
      localStorage.removeItem('llm_user')
    },
  },
})
