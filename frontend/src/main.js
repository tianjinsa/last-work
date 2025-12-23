import { createApp } from 'vue'
import { createPinia } from 'pinia'


import App from './App.vue'
import router from './router'



const app = createApp(App)
const pinia = createPinia()

// 注册所有图标

app.use(pinia)
app.use(router)

app.mount('#app')
