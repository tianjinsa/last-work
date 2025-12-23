<template>
  <div class="admin-view">
    <el-tabs v-model="activeTab">
      <!-- 规则管理 -->
      <el-tab-pane label="规则管理" name="rules">
        <el-card class="panel-card">
          <template #header>
            <div class="card-header">
              <span>知识库规则管理</span>
              <div class="header-actions">
                <el-button type="primary" size="small" @click="openAddRuleDialog">
                  <el-icon><Plus /></el-icon>
                  添加规则
                </el-button>
                <el-button size="small" @click="openBatchAddDialog">
                  <el-icon><DocumentAdd /></el-icon>
                  批量添加
                </el-button>
                <el-button type="danger" plain size="small" @click="handleResetRules">
                  <el-icon><RefreshLeft /></el-icon>
                  重置默认
                </el-button>
              </div>
            </div>
          </template>
          
          <el-table :data="rules" stripe v-loading="rulesLoading">
            <el-table-column prop="id" label="ID" width="80" />
            <el-table-column prop="premises" label="前提条件">
              <template #default="scope">
                <el-tag v-for="p in scope.row.premises" :key="p" size="small" style="margin: 2px;">
                  {{ p }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column label="→" width="50" align="center">
              <template #default>
                <el-icon><Right /></el-icon>
              </template>
            </el-table-column>
            <el-table-column prop="conclusion" label="结论" width="150" />
            <el-table-column label="操作" width="150" fixed="right">
              <template #default="scope">
                <el-button type="primary" link size="small" @click="editRule(scope.row)">
                  编辑
                </el-button>
                <el-button type="danger" link size="small" @click="deleteRule(scope.row)">
                  删除
                </el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-tab-pane>
      
      <!-- 用户管理 -->
      <el-tab-pane label="用户管理" name="users">
        <el-card class="panel-card">
          <template #header>
            <div class="card-header">
              <span>用户管理</span>
              <el-button type="primary" size="small" @click="loadUsers">
                <el-icon><Refresh /></el-icon>
                刷新
              </el-button>
            </div>
          </template>
          
          <el-table :data="users" stripe v-loading="usersLoading">
            <el-table-column prop="username" label="用户名" width="200" />
            <el-table-column prop="role" label="角色" width="150">
              <template #default="scope">
                <el-tag :type="scope.row.role === 'admin' ? 'danger' : 'info'">
                  {{ scope.row.role === 'admin' ? '管理员' : '普通用户' }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="created_at" label="创建时间">
              <template #default="scope">
                {{ formatTime(scope.row.created_at) }}
              </template>
            </el-table-column>
            <el-table-column label="操作" width="200" fixed="right">
              <template #default="scope">
                <el-button 
                  v-if="scope.row.role !== 'admin'" 
                  type="warning" 
                  link 
                  size="small" 
                  @click="promoteUser(scope.row)"
                >
                  升为管理员
                </el-button>
                <el-button 
                  v-if="scope.row.role === 'admin' && scope.row.username !== 'admin'" 
                  type="info" 
                  link 
                  size="small" 
                  @click="demoteUser(scope.row)"
                >
                  降为用户
                </el-button>
                <el-button 
                  v-if="scope.row.username !== 'admin'"
                  type="danger" 
                  link 
                  size="small" 
                  @click="deleteUser(scope.row)"
                >
                  删除
                </el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-tab-pane>
      
      <!-- 系统历史 -->
      <el-tab-pane label="全部历史" name="history">
        <el-card class="panel-card">
          <template #header>
            <div class="card-header">
              <span>系统推理历史（所有用户）</span>
              <div class="header-actions">
                <el-button type="danger" plain size="small" @click="handleClearAllHistory">
                  <el-icon><Delete /></el-icon>
                  清空全部
                </el-button>
                <el-button type="primary" size="small" @click="loadAllHistory">
                  <el-icon><Refresh /></el-icon>
                  刷新
                </el-button>
              </div>
            </div>
          </template>
          
          <el-table :data="allHistory" stripe v-loading="historyLoading">
            <el-table-column prop="timestamp" label="时间" width="180">
              <template #default="scope">
                {{ formatTime(scope.row.timestamp) }}
              </template>
            </el-table-column>
            <el-table-column prop="username" label="用户" width="120" />
            <el-table-column prop="type" label="类型" width="100">
              <template #default="scope">
                <el-tag :type="scope.row.type === 'forward' ? 'success' : 'primary'" size="small">
                  {{ scope.row.type === 'forward' ? '正向' : '反向' }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="conclusion" label="结论" />
            <el-table-column label="事实数" width="80">
              <template #default="scope">
                {{ scope.row.facts?.length || 0 }}
              </template>
            </el-table-column>
          </el-table>
          
          <el-pagination
            v-model:current-page="historyPage"
            :page-size="20"
            :total="historyTotal"
            layout="prev, pager, next"
            @current-change="loadAllHistory"
            style="margin-top: 15px; justify-content: flex-end;"
          />
        </el-card>
      </el-tab-pane>
    </el-tabs>
    
    <!-- 添加/编辑规则对话框 -->
    <el-dialog v-model="ruleDialogVisible" :title="editingRule ? '编辑规则' : '添加规则'" width="500px">
      <el-form :model="ruleForm" label-width="80px">
        <el-form-item label="前提条件">
          <el-input v-model="ruleForm.premises" placeholder="用逗号分隔，如：会飞,下蛋" />
        </el-form-item>
        <el-form-item label="结论">
          <el-input v-model="ruleForm.conclusion" placeholder="结论" />
        </el-form-item>
      </el-form>
      
      <template #footer>
        <el-button @click="ruleDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="saveRule" :loading="saving">保存</el-button>
      </template>
    </el-dialog>
    
    <!-- 批量添加对话框 -->
    <el-dialog v-model="batchDialogVisible" title="批量添加规则" width="600px">
      <p style="margin-bottom: 15px; color: #666;">
        每行一条规则，格式：前提1, 前提2, ... = 结论<br>
        例如：会飞, 下蛋 = 鸟
      </p>
      <el-input
        v-model="batchText"
        type="textarea"
        :rows="10"
        placeholder="会飞, 下蛋 = 鸟
食肉, 有犬齿 = 哺乳动物"
      />
      
      <template #footer>
        <el-button @click="batchDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="batchAddRules" :loading="saving">添加</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import api from '../api'

const activeTab = ref('rules')

// 规则管理
const rules = ref([])
const rulesLoading = ref(false)
const ruleDialogVisible = ref(false)
const editingRule = ref(null)
const ruleForm = ref({ premises: '', conclusion: '' })
const saving = ref(false)

// 批量添加
const batchDialogVisible = ref(false)
const batchText = ref('')

// 用户管理
const users = ref([])
const usersLoading = ref(false)

// 历史
const allHistory = ref([])
const historyLoading = ref(false)
const historyPage = ref(1)
const historyTotal = ref(0)

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
    ElMessage.error('加载规则失败')
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
    ElMessage.warning('前提和结论不能为空')
    return
  }
  
  saving.value = true
  try {
    if (editingRule.value) {
      await api.updateRule(editingRule.value.id, premises, conclusion)
      ElMessage.success('规则已更新')
    } else {
      await api.addRule(premises, conclusion)
      ElMessage.success('规则已添加')
    }
    ruleDialogVisible.value = false
    loadRules()
  } catch (e) {
    ElMessage.error(e.error || '保存失败')
  } finally {
    saving.value = false
  }
}

async function deleteRule(rule) {
  try {
    await ElMessageBox.confirm(`确定要删除规则 ${rule.id} 吗？`, '确认删除', { type: 'warning' })
    await api.deleteRule(rule.id)
    ElMessage.success('删除成功')
    loadRules()
  } catch (e) {
    if (e !== 'cancel') {
      ElMessage.error(e.error || '删除失败')
    }
  }
}

async function handleResetRules() {
  try {
    await ElMessageBox.confirm('确定要重置为默认规则吗？这将清除所有修改。', '确认重置', { type: 'warning' })
    await api.resetRules()
    ElMessage.success('规则已重置')
    loadRules()
  } catch (e) {
    if (e !== 'cancel') {
      ElMessage.error(e.error || '重置失败')
    }
  }
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
    ElMessage.warning('没有有效的规则')
    return
  }
  
  saving.value = true
  try {
    await api.batchAddRules(newRules)
    ElMessage.success(`成功添加 ${newRules.length} 条规则`)
    batchDialogVisible.value = false
    loadRules()
  } catch (e) {
    ElMessage.error(e.error || '添加失败')
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
    ElMessage.error('加载用户失败')
  } finally {
    usersLoading.value = false
  }
}

async function promoteUser(user) {
  try {
    await ElMessageBox.confirm(`确定要将 ${user.username} 升级为管理员吗？`, '确认', { type: 'warning' })
    await api.updateUserRole(user.username, 'admin')
    ElMessage.success('已升级为管理员')
    loadUsers()
  } catch (e) {
    if (e !== 'cancel') {
      ElMessage.error(e.error || '操作失败')
    }
  }
}

async function demoteUser(user) {
  try {
    await ElMessageBox.confirm(`确定要将 ${user.username} 降级为普通用户吗？`, '确认', { type: 'warning' })
    await api.updateUserRole(user.username, 'user')
    ElMessage.success('已降级为普通用户')
    loadUsers()
  } catch (e) {
    if (e !== 'cancel') {
      ElMessage.error(e.error || '操作失败')
    }
  }
}

async function deleteUser(user) {
  try {
    await ElMessageBox.confirm(`确定要删除用户 ${user.username} 吗？`, '确认删除', { type: 'warning' })
    await api.deleteUser(user.username)
    ElMessage.success('用户已删除')
    loadUsers()
  } catch (e) {
    if (e !== 'cancel') {
      ElMessage.error(e.error || '删除失败')
    }
  }
}

// 历史管理方法
async function loadAllHistory() {
  historyLoading.value = true
  try {
    const res = await api.getHistory(historyPage.value, 20)
    allHistory.value = res.history || []
    historyTotal.value = res.total || 0
  } catch (e) {
    ElMessage.error('加载历史失败')
  } finally {
    historyLoading.value = false
  }
}

async function handleClearAllHistory() {
  try {
    await ElMessageBox.confirm('确定要清空所有用户的历史记录吗？', '确认清空', { type: 'warning' })
    await api.clearHistory()
    ElMessage.success('历史已清空')
    loadAllHistory()
  } catch (e) {
    if (e !== 'cancel') {
      ElMessage.error(e.error || '清空失败')
    }
  }
}

function formatTime(timestamp) {
  if (!timestamp) return ''
  return new Date(timestamp).toLocaleString('zh-CN')
}
</script>

<style scoped>
.admin-view {
  max-width: 1400px;
  margin: 0 auto;
}

.panel-card {
  background: var(--el-bg-color-overlay);
  border-color: var(--el-border-color);
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.header-actions {
  display: flex;
  gap: 10px;
}

/* 表格样式 - 减小条纹对比度 */
:deep(.el-table) {
  --el-table-row-hover-bg-color: var(--el-fill-color-light);
}

:deep(.el-table--striped .el-table__body tr.el-table__row--striped td.el-table__cell) {
  background: var(--el-fill-color-lighter);
}
</style>
