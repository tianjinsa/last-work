<template>
  <n-layout has-sider class="layout-container">
    <n-layout-sider
      bordered
      collapse-mode="width"
      :collapsed-width="64"
      :width="220"
      :native-scrollbar="false"
      class="aside"
    >
      <div class="logo">
        <n-icon size="24" :component="HardwareChipOutline" />
        <span>专家系统</span>
      </div>
      
      <n-menu
        :collapsed-width="64"
        :collapsed-icon-size="22"
        :options="menuOptions"
        :value="activeMenu"
        @update:value="handleMenuUpdate"
      />
    </n-layout-sider>
    
    <n-layout>
      <n-layout-header bordered class="header">
        <div class="header-left">
          <n-breadcrumb>
            <n-breadcrumb-item href="/">首页</n-breadcrumb-item>
            <n-breadcrumb-item v-if="currentRoute">{{ currentRoute }}</n-breadcrumb-item>
          </n-breadcrumb>
        </div>
        
        <div class="header-right">
          <n-dropdown :options="userOptions" @select="handleCommand">
            <div class="user-info">
              <n-avatar size="small" round>
                <n-icon :component="Person" />
              </n-avatar>
              <span class="username">{{ userStore.username }}</span>
              <n-tag v-if="userStore.isAdmin" type="error" size="small">管理员</n-tag>
            </div>
          </n-dropdown>
        </div>
      </n-layout-header>
      
      <n-layout-content content-style="padding: 24px;" class="main">
        <router-view />
      </n-layout-content>
    </n-layout>
  </n-layout>
</template>

<script setup>
import { h, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
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

const activeMenu = computed(() => route.path)

function renderIcon(icon) {
  return () => h(NIcon, null, { default: () => h(icon) })
}

const menuOptions = computed(() => {
  const options = [
    {
      label: '首页',
      key: '/',
      icon: renderIcon(Home)
    },
    {
      label: '推理系统',
      key: '/inference',
      icon: renderIcon(GitNetworkOutline)
    },
    {
      label: '历史记录',
      key: '/history',
      icon: renderIcon(TimeOutline)
    }
  ]

  if (userStore.isAdmin) {
    options.push({
      label: '管理员',
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

function handleMenuUpdate(key) {
  router.push(key)
}

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

.logo {
  height: 64px;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 12px;
  font-size: 18px;
  font-weight: bold;
  border-bottom: 1px solid rgba(255, 255, 255, 0.09);
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
  gap: 12px;
  cursor: pointer;
}

.username {
  font-size: 14px;
}
</style>
