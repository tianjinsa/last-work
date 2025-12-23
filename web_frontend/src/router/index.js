import { createRouter, createWebHistory } from 'vue-router'
import { useUserStore } from '../stores/user'
import api from '../api'

const routes = [
  {
    path: '/login',
    name: 'Login',
    component: () => import('../views/LoginView.vue'),
    meta: { requiresAuth: false }
  },
  {
    path: '/',
    name: 'Layout',
    component: () => import('../views/LayoutView.vue'),
    meta: { requiresAuth: true },
    children: [
      {
        path: '',
        name: 'Home',
        component: () => import('../views/HomeView.vue')
      },
      {
        path: 'inference',
        name: 'Inference',
        component: () => import('../views/InferenceView.vue')
      },
      {
        path: 'history',
        name: 'History',
        component: () => import('../views/HistoryView.vue')
      },
      {
        path: 'admin',
        name: 'Admin',
        component: () => import('../views/AdminView.vue'),
        meta: { requiresAdmin: true }
      }
    ]
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

// 标记是否已验证过 token
let tokenVerified = false

router.beforeEach(async (to, from, next) => {
  const userStore = useUserStore()
  
  // 如果用户看起来已登录，但还没验证过 token，先验证
  if (userStore.isLoggedIn && !tokenVerified && to.meta.requiresAuth) {
    try {
      await api.getMe()
      tokenVerified = true
    } catch (e) {
      // token 无效，清除登录状态
      userStore.logout()
      tokenVerified = false
      next('/login')
      return
    }
  }
  
  if (to.meta.requiresAuth && !userStore.isLoggedIn) {
    next('/login')
  } else if (to.meta.requiresAdmin && !userStore.isAdmin) {
    next('/')
  } else if (to.path === '/login' && userStore.isLoggedIn) {
    next('/')
  } else {
    next()
  }
})

export default router
