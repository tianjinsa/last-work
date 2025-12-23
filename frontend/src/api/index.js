import axios from 'axios'
import { createDiscreteApi } from 'naive-ui'
import router from '../router'

const { message } = createDiscreteApi(['message'])

const instance = axios.create({
  baseURL: '/api',
  timeout: 30000
})

// 请求拦截器
instance.interceptors.request.use(
  config => {
    const token = localStorage.getItem('token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  error => Promise.reject(error)
)

// 响应拦截器
let isRelogging = false

instance.interceptors.response.use(
  response => response.data,
  error => {
    if (error.response?.status === 401) {
      if (!isRelogging) {
        isRelogging = true
        // 清除本地存储的登录信息
        localStorage.removeItem('token')
        localStorage.removeItem('username')
        localStorage.removeItem('role')
        // 提示用户
        message.warning('登录已过期，请重新登录')
        // 跳转到登录页
        if (router.currentRoute.value.path !== '/login') {
          router.push('/login')
        }
        
        // 3秒后重置标志，防止短时间内重复提示
        setTimeout(() => {
          isRelogging = false
        }, 3000)
      }
    }
    return Promise.reject(error.response?.data || error)
  }
)

export default {
  // 认证
  login: (username, password) => instance.post('/auth/login', { username, password }),
  register: (username, password) => instance.post('/auth/register', { username, password }),
  logout: () => instance.post('/auth/logout'),
  getMe: () => instance.get('/auth/me'),

  // 规则
  getRules: () => instance.get('/rules'),
  addRule: (premises, conclusion) => instance.post('/rules', { premises, conclusion }),
  batchAddRules: (rules) => instance.post('/rules/batch', { rules }),
  updateRule: (id, premises, conclusion) => instance.put(`/rules/${id}`, { premises, conclusion }),
  deleteRule: (id) => instance.delete(`/rules/${id}`),
  resetRules: () => instance.post('/rules/reset'),

  // 事实
  getAtoms: () => instance.get('/facts/atoms'),
  getConclusions: () => instance.get('/facts/conclusions'),
  getKnownFacts: () => instance.get('/facts/known'),
  setKnownFacts: (facts) => instance.post('/facts/known', { facts }),
  getFalseFacts: () => instance.get('/facts/false'),
  setFalseFacts: (facts) => instance.post('/facts/false', { facts }),
  clearFacts: () => instance.post('/facts/clear'),

  // 推理
  forwardInference: () => instance.post('/inference/forward'),
  startBackward: (target) => instance.post('/inference/backward/start', { target }),
  continueBackward: (trueFacts, falseFacts) => 
    instance.post('/inference/backward/continue', { true_facts: trueFacts, false_facts: falseFacts }),

  // 历史
  getHistory: (page = 1, perPage = 20) => instance.get('/history', { params: { page, per_page: perPage } }),
  deleteHistory: (id) => instance.delete(`/history/${id}`),
  clearHistory: () => instance.post('/history/clear'),

  // 管理员
  getUsers: () => instance.get('/admin/users'),
  updateUserRole: (username, role) => instance.put(`/admin/users/${username}/role`, { role }),
  deleteUser: (username) => instance.delete(`/admin/users/${username}`)
}
