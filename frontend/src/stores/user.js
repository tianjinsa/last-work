import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import api from '../api'

export const useUserStore = defineStore('user', () => {
  const token = ref(localStorage.getItem('token') || '')
  const username = ref(localStorage.getItem('username') || '')
  const role = ref(localStorage.getItem('role') || '')

  const isLoggedIn = computed(() => !!token.value)
  const isAdmin = computed(() => role.value === 'admin')

  async function login(user, pass) {
    const res = await api.login(user, pass)
    token.value = res.token
    username.value = res.username
    role.value = res.role
    
    localStorage.setItem('token', res.token)
    localStorage.setItem('username', res.username)
    localStorage.setItem('role', res.role)
    
    return res
  }

  async function register(user, pass) {
    return await api.register(user, pass)
  }

  async function logout() {
    try {
      await api.logout()
    } catch (e) {
      // 忽略错误
    }
    token.value = ''
    username.value = ''
    role.value = ''
    
    localStorage.removeItem('token')
    localStorage.removeItem('username')
    localStorage.removeItem('role')
  }

  function getToken() {
    return token.value
  }

  return {
    token,
    username,
    role,
    isLoggedIn,
    isAdmin,
    login,
    register,
    logout,
    getToken
  }
})
