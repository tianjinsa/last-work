<template>
  <div class="admin-view">
    <n-tabs v-model:value="activeTab" type="line" animated pane-style="flex: 1; display: flex; flex-direction: column; min-height: 0;">
      <!-- 规则管理 -->
      <n-tab-pane name="rules" tab="规则管理">
        <n-card class="panel-card" title="知识库规则管理">
          <template #header-extra>
            <div class="header-actions">
              <n-button type="primary" size="small" @click="openAddRuleDialog">
                <template #icon>
                  <n-icon :component="AddOutline" />
                </template>
                添加规则
              </n-button>
              <n-button size="small" @click="openBatchAddDialog">
                <template #icon>
                  <n-icon :component="DocumentTextOutline" />
                </template>
                批量添加
              </n-button>
              <n-button type="error" ghost size="small" @click="handleResetRules">
                <template #icon>
                  <n-icon :component="RefreshOutline" />
                </template>
                重置默认
              </n-button>
            </div>
          </template>
          
          <n-data-table
            flex-height
            :columns="rulesColumns"
            :data="rules"
            :loading="rulesLoading"
            :pagination="{ pageSize: 10 }"
            style="height: 100%"
          />
        </n-card>
      </n-tab-pane>
      
      <!-- 用户管理 -->
      <n-tab-pane name="users" tab="用户管理">
        <n-card class="panel-card" title="用户管理">
          <template #header-extra>
            <n-button type="primary" size="small" @click="loadUsers">
              <template #icon>
                <n-icon :component="RefreshOutline" />
              </template>
              刷新
            </n-button>
          </template>
          
          <n-data-table
            flex-height
            :columns="usersColumns"
            :data="users"
            :loading="usersLoading"
            :pagination="{ pageSize: 10 }"
            style="height: 100%"
          />
        </n-card>
      </n-tab-pane>
      
      <!-- 系统历史 -->
      <n-tab-pane name="history" tab="全部历史">
        <n-card class="panel-card" title="系统推理历史（所有用户）">
          <template #header-extra>
            <div class="header-actions">
              <n-button type="error" ghost size="small" @click="handleClearAllHistory">
                <template #icon>
                  <n-icon :component="TrashOutline" />
                </template>
                清空全部
              </n-button>
              <n-button type="primary" size="small" @click="loadAllHistory">
                <template #icon>
                  <n-icon :component="RefreshOutline" />
                </template>
                刷新
              </n-button>
            </div>
          </template>
          
          <n-data-table
            remote
            flex-height
            :columns="historyColumns"
            :data="allHistory"
            :loading="historyLoading"
            :pagination="historyPagination"
            style="height: 100%"
            @update:page="handleHistoryPageChange"
          />
        </n-card>
      </n-tab-pane>
    </n-tabs>
    
    <!-- 添加/编辑规则对话框 -->
    <n-modal v-model:show="ruleDialogVisible">
      <n-card style="width: 500px" :title="editingRule ? '编辑规则' : '添加规则'" :bordered="false" size="huge" role="dialog" aria-modal="true">
        <n-form :model="ruleForm" label-placement="left" label-width="80">
          <n-form-item label="前提条件">
            <n-input v-model:value="ruleForm.premises" placeholder="用逗号分隔，如：会飞,下蛋" />
          </n-form-item>
          <n-form-item label="结论">
            <n-input v-model:value="ruleForm.conclusion" placeholder="结论" />
          </n-form-item>
        </n-form>
        
        <template #footer>
          <div style="display: flex; justify-content: flex-end; gap: 10px;">
            <n-button @click="ruleDialogVisible = false">取消</n-button>
            <n-button type="primary" @click="saveRule" :loading="saving">保存</n-button>
          </div>
        </template>
      </n-card>
    </n-modal>
    
    <!-- 批量添加对话框 -->
    <n-modal v-model:show="batchDialogVisible">
      <n-card style="width: 600px" title="批量添加规则" :bordered="false" size="huge" role="dialog" aria-modal="true">
        <p style="margin-bottom: 15px; opacity: 0.6;">
          每行一条规则，格式：前提1, 前提2, ... = 结论<br>
          例如：会飞, 下蛋 = 鸟
        </p>
        <n-input
          v-model:value="batchText"
          type="textarea"
          :rows="10"
          placeholder="会飞, 下蛋 = 鸟
食肉, 有犬齿 = 哺乳动物"
        />
        
        <template #footer>
          <div style="display: flex; justify-content: flex-end; gap: 10px;">
            <n-button @click="batchDialogVisible = false">取消</n-button>
            <n-button type="primary" @click="batchAddRules" :loading="saving">添加</n-button>
          </div>
        </template>
      </n-card>
    </n-modal>
  </div>
</template>

<script setup>
import { ref, onMounted, h, reactive, computed } from 'vue'
import { useMessage, useDialog, NTag, NButton, NIcon } from 'naive-ui'
import api from '../api'
import {
  AddOutline,
  DocumentTextOutline,
  RefreshOutline,
  TrashOutline,
  ArrowForwardOutline
} from '@vicons/ionicons5'

const message = useMessage()
const dialog = useDialog()

const activeTab = ref('rules')

// 规则管理
const rules = ref([])
const rulesLoading = ref(false)
const ruleDialogVisible = ref(false)
const editingRule = ref(null)
const ruleForm = ref({ premises: '', conclusion: '' })
const saving = ref(false)

const rulesColumns = [
  { title: 'ID', key: 'id', width: 80 },
  {
    title: '前提条件',
    key: 'premises',
    render: (row) => {
      return row.premises.map(p => h(NTag, { size: 'small', style: 'margin: 2px;' }, { default: () => p }))
    }
  },
  {
    title: '→',
    key: 'arrow',
    width: 50,
    align: 'center',
    render: () => h(NIcon, { component: ArrowForwardOutline })
  },
  { title: '结论', key: 'conclusion', width: 150 },
  {
    title: '操作',
    key: 'actions',
    width: 150,
    fixed: 'right',
    render: (row) => {
      return [
        h(
          NButton,
          {
            text: true,
            type: 'primary',
            size: 'small',
            onClick: () => editRule(row),
            style: 'margin-right: 10px'
          },
          { default: () => '编辑' }
        ),
        h(
          NButton,
          {
            text: true,
            type: 'error',
            size: 'small',
            onClick: () => deleteRule(row)
          },
          { default: () => '删除' }
        )
      ]
    }
  }
]

// 批量添加
const batchDialogVisible = ref(false)
const batchText = ref('')

// 用户管理
const users = ref([])
const usersLoading = ref(false)

const usersColumns = [
  { title: '用户名', key: 'username', width: 200 },
  {
    title: '角色',
    key: 'role',
    width: 150,
    render: (row) => {
      return h(
        NTag,
        { type: row.role === 'admin' ? 'error' : 'info' },
        { default: () => (row.role === 'admin' ? '管理员' : '普通用户') }
      )
    }
  },
  {
    title: '创建时间',
    key: 'created_at',
    render: (row) => formatTime(row.created_at)
  },
  {
    title: '操作',
    key: 'actions',
    width: 200,
    fixed: 'right',
    render: (row) => {
      const actions = []
      if (row.role !== 'admin') {
        actions.push(
          h(
            NButton,
            {
              text: true,
              type: 'warning',
              size: 'small',
              onClick: () => promoteUser(row),
              style: 'margin-right: 10px'
            },
            { default: () => '升为管理员' }
          )
        )
      }
      if (row.role === 'admin' && row.username !== 'admin') {
        actions.push(
          h(
            NButton,
            {
              text: true,
              type: 'info',
              size: 'small',
              onClick: () => demoteUser(row),
              style: 'margin-right: 10px'
            },
            { default: () => '降为用户' }
          )
        )
      }
      if (row.username !== 'admin') {
        actions.push(
          h(
            NButton,
            {
              text: true,
              type: 'error',
              size: 'small',
              onClick: () => deleteUser(row)
            },
            { default: () => '删除' }
          )
        )
      }
      return actions
    }
  }
]

// 历史
const allHistory = ref([])
const historyLoading = ref(false)
const historyPagination = reactive({
  page: 1,
  pageSize: 20,
  itemCount: 0,
  onChange: (page) => {
    historyPagination.page = page
    loadAllHistory()
  }
})

const historyColumns = [
  {
    title: '时间',
    key: 'timestamp',
    width: 180,
    render: (row) => formatTime(row.timestamp)
  },
  { title: '用户', key: 'username', width: 120 },
  {
    title: '类型',
    key: 'type',
    width: 100,
    render: (row) => {
      return h(
        NTag,
        { type: row.type === 'forward' ? 'success' : 'info', size: 'small' },
        { default: () => (row.type === 'forward' ? '正向' : '反向') }
      )
    }
  },
  { title: '结论', key: 'conclusion' },
  {
    title: '事实数',
    key: 'facts',
    width: 80,
    render: (row) => row.facts?.length || 0
  }
]

onMounted(() => {
  loadRules()
  loadUsers()
  loadAllHistory()
})

// 规则管理方法
async function loadRules() {
  rulesLoading.value = true
  try {
    const res = await api.getRules()
    rules.value = res.rules || []
  } catch (e) {
    message.error('加载规则失败')
  } finally {
    rulesLoading.value = false
  }
}

function openAddRuleDialog() {
  editingRule.value = null
  ruleForm.value = { premises: '', conclusion: '' }
  ruleDialogVisible.value = true
}

function editRule(rule) {
  editingRule.value = rule
  ruleForm.value = {
    premises: rule.premises.join(', '),
    conclusion: rule.conclusion
  }
  ruleDialogVisible.value = true
}

async function saveRule() {
  const premises = ruleForm.value.premises.split(',').map(p => p.trim()).filter(p => p)
  const conclusion = ruleForm.value.conclusion.trim()
  
  if (!premises.length || !conclusion) {
    message.warning('前提和结论不能为空')
    return
  }
  
  saving.value = true
  try {
    if (editingRule.value) {
      await api.updateRule(editingRule.value.id, premises, conclusion)
      message.success('规则已更新')
    } else {
      await api.addRule(premises, conclusion)
      message.success('规则已添加')
    }
    ruleDialogVisible.value = false
    loadRules()
  } catch (e) {
    message.error(e.error || '保存失败')
  } finally {
    saving.value = false
  }
}

function deleteRule(rule) {
  dialog.warning({
    title: '确认删除',
    content: `确定要删除规则 ${rule.id} 吗？`,
    positiveText: '确定',
    negativeText: '取消',
    onPositiveClick: async () => {
      try {
        await api.deleteRule(rule.id)
        message.success('删除成功')
        loadRules()
      } catch (e) {
        message.error(e.error || '删除失败')
      }
    }
  })
}

function handleResetRules() {
  dialog.warning({
    title: '确认重置',
    content: '确定要重置为默认规则吗？这将清除所有修改。',
    positiveText: '确定',
    negativeText: '取消',
    onPositiveClick: async () => {
      try {
        await api.resetRules()
        message.success('规则已重置')
        loadRules()
      } catch (e) {
        message.error(e.error || '重置失败')
      }
    }
  })
}

function openBatchAddDialog() {
  batchText.value = ''
  batchDialogVisible.value = true
}

async function batchAddRules() {
  const lines = batchText.value.split('\n')
  const newRules = []
  
  for (const line of lines) {
    const trimmed = line.trim()
    if (!trimmed || !trimmed.includes('=')) continue
    
    const parts = trimmed.split('=')
    if (parts.length !== 2) continue
    
    const premises = parts[0].split(',').map(p => p.trim()).filter(p => p)
    const conclusion = parts[1].trim()
    
    if (premises.length && conclusion) {
      newRules.push({ premises, conclusion })
    }
  }
  
  if (!newRules.length) {
    message.warning('没有有效的规则')
    return
  }
  
  saving.value = true
  try {
    await api.batchAddRules(newRules)
    message.success(`成功添加 ${newRules.length} 条规则`)
    batchDialogVisible.value = false
    loadRules()
  } catch (e) {
    message.error(e.error || '添加失败')
  } finally {
    saving.value = false
  }
}

// 用户管理方法
async function loadUsers() {
  usersLoading.value = true
  try {
    const res = await api.getUsers()
    users.value = res.users || []
  } catch (e) {
    message.error('加载用户失败')
  } finally {
    usersLoading.value = false
  }
}

function promoteUser(user) {
  dialog.warning({
    title: '确认',
    content: `确定要将 ${user.username} 升级为管理员吗？`,
    positiveText: '确定',
    negativeText: '取消',
    onPositiveClick: async () => {
      try {
        await api.updateUserRole(user.username, 'admin')
        message.success('已升级为管理员')
        loadUsers()
      } catch (e) {
        message.error(e.error || '操作失败')
      }
    }
  })
}

function demoteUser(user) {
  dialog.warning({
    title: '确认',
    content: `确定要将 ${user.username} 降级为普通用户吗？`,
    positiveText: '确定',
    negativeText: '取消',
    onPositiveClick: async () => {
      try {
        await api.updateUserRole(user.username, 'user')
        message.success('已降级为普通用户')
        loadUsers()
      } catch (e) {
        message.error(e.error || '操作失败')
      }
    }
  })
}

function deleteUser(user) {
  dialog.warning({
    title: '确认删除',
    content: `确定要删除用户 ${user.username} 吗？`,
    positiveText: '确定',
    negativeText: '取消',
    onPositiveClick: async () => {
      try {
        await api.deleteUser(user.username)
        message.success('用户已删除')
        loadUsers()
      } catch (e) {
        message.error(e.error || '删除失败')
      }
    }
  })
}

// 历史管理方法
async function loadAllHistory() {
  historyLoading.value = true
  try {
    const res = await api.getHistory(historyPagination.page, 20)
    allHistory.value = res.history || []
    historyPagination.itemCount = res.total || 0
  } catch (e) {
    message.error('加载历史失败')
  } finally {
    historyLoading.value = false
  }
}

function handleHistoryPageChange(page) {
  historyPagination.page = page
  loadAllHistory()
}

function handleClearAllHistory() {
  dialog.warning({
    title: '确认清空',
    content: '确定要清空所有用户的历史记录吗？',
    positiveText: '确定',
    negativeText: '取消',
    onPositiveClick: async () => {
      try {
        await api.clearHistory()
        message.success('历史已清空')
        loadAllHistory()
      } catch (e) {
        message.error(e.error || '清空失败')
      }
    }
  })
}

function formatTime(timestamp) {
  if (!timestamp) return ''
  return new Date(timestamp).toLocaleString('zh-CN')
}
</script>

<style scoped>
.admin-view {
  height: 100%;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.admin-view :deep(.n-tabs) {
  height: 100%;
  display: flex;
  flex-direction: column;
}

.admin-view :deep(.n-tabs-nav) {
  flex-shrink: 0;
}

.admin-view :deep(.n-tabs-pane-wrapper) {
  flex: 1;
  overflow: hidden;
}

.admin-view :deep(.n-tab-pane) {
  height: 100%;
  display: flex;
  flex-direction: column;
}

.panel-card {
  height: 100%;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.panel-card :deep(.n-card__content) {
  flex: 1;
  overflow: hidden;
  padding: 12px;
}

.header-actions {
  display: flex;
  gap: 10px;
}
</style>
