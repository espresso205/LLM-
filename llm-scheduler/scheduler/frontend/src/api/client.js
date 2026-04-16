import axios from 'axios'
import { useAuthStore } from '../stores/auth'

const client = axios.create({ baseURL: '/' })
client.interceptors.request.use(cfg => {
  const auth = useAuthStore()
  if (auth.token) cfg.headers['X-Internal-Token'] = 'internal-secret-change-me'
  return cfg
})
export default client
