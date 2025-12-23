<template>
  <div class="login-container">
    <n-card class="login-card">
      <template #header>
        <div class="card-header">
          <h2>基于产生式知识表示的专家系统</h2>
        </div>
      </template>
      
      <n-tabs v-model:value="activeTab" type="line" animated>
        <n-tab-pane name="login" tab="登录">
          <n-form :model="loginForm" :rules="rules" ref="loginFormRef">
            <n-form-item path="username" label="用户名">
              <n-input v-model:value="loginForm.username" placeholder="用户名">
                <template #prefix>
                  <n-icon :component="PersonOutline" />
                </template>
              </n-input>
            </n-form-item>
            <n-form-item path="password" label="密码">
              <n-input v-model:value="loginForm.password" placeholder="密码" type="password" 
                        show-password-on="click" @keyup.enter="handleLogin">
                <template #prefix>
                  <n-icon :component="LockClosedOutline" />
                </template>
              </n-input>
            </n-form-item>
            <n-form-item>
              <n-button type="primary" @click="handleLogin" :loading="loading" style="width: 100%">
                登录
              </n-button>
            </n-form-item>
          </n-form>
        </n-tab-pane>
        
        <n-tab-pane name="register" tab="注册">
          <n-form :model="registerForm" :rules="registerRules" ref="registerFormRef">
            <n-form-item path="username" label="用户名">
              <n-input v-model:value="registerForm.username" placeholder="用户名">
                <template #prefix>
                  <n-icon :component="PersonOutline" />
                </template>
              </n-input>
            </n-form-item>
            <n-form-item path="password" label="密码">
              <n-input v-model:value="registerForm.password" placeholder="密码" type="password" 
                        show-password-on="click">
                <template #prefix>
                  <n-icon :component="LockClosedOutline" />
                </template>
              </n-input>
            </n-form-item>
            <n-form-item path="confirmPassword" label="确认密码">
              <n-input v-model:value="registerForm.confirmPassword" placeholder="确认密码" type="password" 
                        show-password-on="click" @keyup.enter="handleRegister">
                <template #prefix>
                  <n-icon :component="LockClosedOutline" />
                </template>
              </n-input>
            </n-form-item>
            <n-form-item>
              <n-button type="primary" @click="handleRegister" :loading="loading" style="width: 100%">
                注册
              </n-button>
            </n-form-item>
          </n-form>
        </n-tab-pane>
      </n-tabs>
      
      <div class="tips">
        <p>默认管理员账号：admin / admin123</p>
      </div>
    </n-card>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { useMessage } from 'naive-ui'
import { PersonOutline, LockClosedOutline } from '@vicons/ionicons5'
import { useUserStore } from '../stores/user'

const router = useRouter()
const userStore = useUserStore()
const message = useMessage()

const activeTab = ref('login')
const loading = ref(false)

const loginFormRef = ref(null)
const registerFormRef = ref(null)

const loginForm = reactive({
  username: '',
  password: ''
})

const registerForm = reactive({
  username: '',
  password: '',
  confirmPassword: ''
})

const rules = {
  username: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
  password: [{ required: true, message: '请输入密码', trigger: 'blur' }]
}

const validateConfirmPassword = (rule, value) => {
  if (value !== registerForm.password) {
    return new Error('两次输入的密码不一致')
  }
  return true
}

const registerRules = {
  username: [
    { required: true, message: '请输入用户名', trigger: 'blur' },
    { min: 3, max: 20, message: '用户名长度在3-20个字符', trigger: 'blur' }
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 6, message: '密码至少6个字符', trigger: 'blur' }
  ],
  confirmPassword: [
    { required: true, message: '请确认密码', trigger: 'blur' },
    { validator: validateConfirmPassword, trigger: 'blur' }
  ]
}

const handleLogin = (e) => {
  e?.preventDefault()
  loginFormRef.value?.validate((errors) => {
    if (!errors) {
      loading.value = true
      userStore.login(loginForm.username, loginForm.password)
        .then(() => {
          message.success('登录成功')
          router.push('/')
        })
        .catch((error) => {
          message.error(error.error || '登录失败')
        })
        .finally(() => {
          loading.value = false
        })
    }
  })
}

const handleRegister = (e) => {
  e?.preventDefault()
  registerFormRef.value?.validate((errors) => {
    if (!errors) {
      loading.value = true
      userStore.register(registerForm.username, registerForm.password)
        .then(() => {
          message.success('注册成功，请登录')
          activeTab.value = 'login'
          loginForm.username = registerForm.username
          loginForm.password = ''
        })
        .catch((error) => {
          message.error(error.error || '注册失败')
        })
        .finally(() => {
          loading.value = false
        })
    }
  })
}
</script>

<style scoped>
.login-container {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
}

.login-card {
  width: 400px;
}

.card-header {
  text-align: center;
}

.card-header h2 {
  margin: 0;
  font-size: 1.5rem;
}

.tips {
  margin-top: 20px;
  text-align: center;
  opacity: 0.8;
  font-size: 12px;
}
</style>
