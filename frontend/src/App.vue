<template>
  <n-config-provider :locale="zhCN" :date-locale="dateZhCN" :theme="darkTheme">
    <n-message-provider>
      <n-dialog-provider>
        <n-notification-provider>
          <n-loading-bar-provider>
            <div class="app-container">
              <router-view />
            </div>
          </n-loading-bar-provider>
        </n-notification-provider>
      </n-dialog-provider>
    </n-message-provider>
  </n-config-provider>
</template>

<script setup>
import { zhCN, dateZhCN, darkTheme } from 'naive-ui'
</script>

<style>
/* 全局基础样式 - Element Plus 暗色模式会自动处理大部分组件 */
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

body {
  font-family: 'Microsoft YaHei', sans-serif;
  min-height: 100vh;
}

.app-container {
  min-height: 100vh;
}
</style>
