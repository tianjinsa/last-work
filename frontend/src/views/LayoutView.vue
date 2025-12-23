<template>
  <n-layout has-sider class="layout-container">
    <n-layout-sider
      bordered
      collapse-mode="width"
      :collapsed-width="64"
      :width="240"
      :native-scrollbar="false"
      show-trigger
      v-model:collapsed="collapsed"
      class="aside"
    >
      <div class="logo">
        <n-icon size="32" :component="HardwareChipOutline" color="#18a058" />
        <span v-if="!collapsed" class="logo-text">专家系统</span>
      </div>
      
      <n-menu
        :collapsed-width="64"
        :collapsed-icon-size="22"
        :options="menuOptions"
        :value="activeMenu"
      />
    </n-layout-sider>
    
    <n-layout>
      <n-layout-header bordered class="header">
        <div class="header-left">
          <n-breadcrumb>
            <n-breadcrumb-item>
              <router-link to="/">首页</router-link>
            </n-breadcrumb-item>
            <n-breadcrumb-item v-if="currentRoute">{{ currentRoute }}</n-breadcrumb-item>
          </n-breadcrumb>
        </div>
        
        <div class="header-right">
          <n-space align="center" :size="20">
            <n-dropdown :options="userOptions" @select="handleCommand">
              <div class="user-info">
                <n-avatar size="small" round>
                  <n-icon :component="Person" />
                </n-avatar>
                <span class="username">{{ userStore.username }}</span>
                <n-tag v-if="userStore.isAdmin" type="error" size="small" round>管理员</n-tag>
              </div>
            </n-dropdown>
          </n-space>
        </div>
      </n-layout-header>
      
      <n-layout-content class="main">
        <n-scrollbar style="max-height: 90vh">
        <div class="content-wrapper">
          <router-view v-slot="{ Component }">
            <transition name="fade-slide" mode="out-in">
              <component :is="Component" />
            </transition>
          </router-view>
        </div>
        
        <n-back-top :right="40" />
      </n-scrollbar>
      </n-layout-content>
    </n-layout>
  </n-layout>
</template>

<script setup>
import { h, computed, ref } from 'vue'
import { useRoute, useRouter, RouterLink } from 'vue-router'
import { useUserStore } from '../stores/user'
import { NIcon } from 'naive-ui'
import {
  HardwareChipOutline,
  Home,
  GitNetworkOutline,
  TimeOutline,
  SettingsOutline,
  Person,
  LogOutOutline
} from '@vicons/ionicons5'

const route = useRoute()
const router = useRouter()
const userStore = useUserStore()
const collapsed = ref(false)

const activeMenu = computed(() => route.path)

function renderIcon(icon) {
  return () => h(NIcon, null, { default: () => h(icon) })
}

const menuOptions = computed(() => {
  const options = [
    {
      label: () => h(RouterLink, { to: '/' }, { default: () => '首页' }),
      key: '/',
      icon: renderIcon(Home)
    },
    {
      label: () => h(RouterLink, { to: '/inference' }, { default: () => '推理系统' }),
      key: '/inference',
      icon: renderIcon(GitNetworkOutline)
    },
    {
      label: () => h(RouterLink, { to: '/history' }, { default: () => '历史记录' }),
      key: '/history',
      icon: renderIcon(TimeOutline)
    }
  ]

  if (userStore.isAdmin) {
    options.push({
      label: () => h(RouterLink, { to: '/admin' }, { default: () => '管理员' }),
      key: '/admin',
      icon: renderIcon(SettingsOutline)
    })
  }

  return options
})

const userOptions = [
  {
    label: '退出登录',
    key: 'logout',
    icon: renderIcon(LogOutOutline)
  }
]

const routeNames = {
  '/': '',
  '/inference': '推理系统',
  '/history': '历史记录',
  '/admin': '管理员'
}

const currentRoute = computed(() => routeNames[route.path] || '')

async function handleCommand(key) {
  if (key === 'logout') {
    await userStore.logout()
    router.push('/login')
  }
}
</script>

<style scoped>
.layout-container {
  height: 100vh;
}

.main {
  overflow: visible;
}

.content-wrapper {
  padding: 24px;
  display: flex;
  flex-direction: column;
  box-sizing: border-box;
  min-height: calc(100vh - 112px);
}

.logo {
  height: 64px;
  display: flex;
  align-items: center;
  padding: 0 16px;
  gap: 12px;
  overflow: hidden;
  white-space: nowrap;
}

.logo-text {
  font-size: 18px;
  font-weight: bold;
  transition: opacity 0.3s;
}

.header {
  height: 64px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 24px;
}

.user-info {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  padding: 4px 8px;
  border-radius: 4px;
  transition: background-color 0.3s;
}

.user-info:hover {
  background-color: rgba(128, 128, 128, 0.1);
}

.username {
  font-size: 14px;
}

/* 路由切换动画 */
.fade-slide-enter-active,
.fade-slide-leave-active {
  transition: all 0.3s ease;
}

.fade-slide-enter-from {
  opacity: 0;
  transform: translateX(20px);
}

.fade-slide-leave-to {
  opacity: 0;
  transform: translateX(-20px);
}
</style>
