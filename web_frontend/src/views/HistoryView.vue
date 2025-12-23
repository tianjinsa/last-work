<template>
  <div class="history-view">
    <el-card class="main-card">
      <template #header>
        <div class="card-header">
          <span>推理历史记录</span>
          <div class="header-actions">
            <el-button type="danger" plain size="small" @click="handleClearHistory">
              <el-icon><Delete /></el-icon>
              清空历史
            </el-button>
            <el-button type="primary" size="small" @click="loadHistory">
              <el-icon><Refresh /></el-icon>
              刷新
            </el-button>
          </div>
        </div>
      </template>
      
      <el-table 
        :data="historyList" 
        stripe 
        style="width: 100%"
        v-loading="loading"
        row-class-name="history-row"
      >
        <el-table-column type="expand">
          <template #default="props">
            <div class="expand-content">
              <div class="expand-section">
                <strong>已知事实：</strong>
                <el-tag v-for="fact in props.row.facts" :key="fact" size="small" type="success" style="margin: 2px;">
                  {{ fact }}
                </el-tag>
              </div>
              <div class="expand-section">
                <strong>推理路径：</strong>
                <span v-if="props.row.path?.length">
                  规则 {{ props.row.path.join(' → ') }}
                </span>
                <span v-else class="no-data">无</span>
              </div>
            </div>
          </template>
        </el-table-column>
        
        <el-table-column prop="timestamp" label="时间" width="180">
          <template #default="scope">
            {{ formatTime(scope.row.timestamp) }}
          </template>
        </el-table-column>
        
        <el-table-column prop="username" label="用户" width="120" v-if="isAdmin" />
        
        <el-table-column prop="type" label="推理类型" width="120">
          <template #default="scope">
            <el-tag :type="scope.row.type === 'forward' ? 'success' : 'primary'">
              {{ scope.row.type === 'forward' ? '正向推理' : '反向推理' }}
            </el-tag>
          </template>
        </el-table-column>
        
        <el-table-column prop="conclusion" label="结论">
          <template #default="scope">
            <span class="conclusion-text">{{ scope.row.conclusion || '无结论' }}</span>
          </template>
        </el-table-column>
        
        <el-table-column label="事实数" width="100">
          <template #default="scope">
            {{ scope.row.facts?.length || 0 }}
          </template>
        </el-table-column>
        
        <el-table-column label="操作" width="150" fixed="right">
          <template #default="scope">
            <el-button type="primary" link size="small" @click="viewDetail(scope.row)">
              详情
            </el-button>
            <el-button type="danger" link size="small" @click="deleteRecord(scope.row)">
              删除
            </el-button>
          </template>
        </el-table-column>
      </el-table>
      
      <el-pagination
        v-model:current-page="currentPage"
        v-model:page-size="pageSize"
        :page-sizes="[10, 20, 50, 100]"
        :total="total"
        layout="total, sizes, prev, pager, next, jumper"
        @size-change="loadHistory"
        @current-change="loadHistory"
        style="margin-top: 20px; justify-content: flex-end;"
      />
    </el-card>
    
    <!-- 详情对话框 -->
    <el-dialog v-model="detailDialogVisible" title="推理详情" width="700px">
      <div v-if="selectedRecord" class="detail-content">
        <el-descriptions :column="2" border>
          <el-descriptions-item label="时间">{{ formatTime(selectedRecord.timestamp) }}</el-descriptions-item>
          <el-descriptions-item label="用户">{{ selectedRecord.username }}</el-descriptions-item>
          <el-descriptions-item label="推理类型">
            <el-tag :type="selectedRecord.type === 'forward' ? 'success' : 'primary'">
              {{ selectedRecord.type === 'forward' ? '正向推理' : '反向推理' }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="结论">
            <strong>{{ selectedRecord.conclusion || '无' }}</strong>
          </el-descriptions-item>
        </el-descriptions>
        
        <div class="detail-section">
          <h4>已知事实：</h4>
          <div class="tags-container">
            <el-tag v-for="fact in selectedRecord.facts" :key="fact" type="success" style="margin: 4px;">
              {{ fact }}
            </el-tag>
            <span v-if="!selectedRecord.facts?.length" class="no-data">无</span>
          </div>
        </div>
        
        <div class="detail-section">
          <h4>推理路径：</h4>
          <div v-if="selectedRecord.path?.length" class="path-display">
            <div v-for="(ruleId, index) in selectedRecord.path" :key="index" class="path-step">
              <el-tag type="primary">规则 {{ ruleId }}</el-tag>
              <el-icon v-if="index < selectedRecord.path.length - 1"><ArrowRight /></el-icon>
            </div>
          </div>
          <span v-else class="no-data">无推理路径</span>
        </div>
        
        <div class="detail-section">
          <h4>重现推理：</h4>
          <el-button type="primary" @click="reproduceInference(selectedRecord)">
            <el-icon><Promotion /></el-icon>
            使用这些事实进行推理
          </el-button>
        </div>
      </div>
      
      <template #footer>
        <el-button @click="detailDialogVisible = false">关闭</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useUserStore } from '../stores/user'
import api from '../api'

const router = useRouter()
const userStore = useUserStore()
const isAdmin = computed(() => userStore.isAdmin)

const loading = ref(false)
const historyList = ref([])
const currentPage = ref(1)
const pageSize = ref(20)
const total = ref(0)

const detailDialogVisible = ref(false)
const selectedRecord = ref(null)

onMounted(() => {
  loadHistory()
})

async function loadHistory() {
  loading.value = true
  try {
    const res = await api.getHistory(currentPage.value, pageSize.value)
    historyList.value = res.history || []
    total.value = res.total || 0
  } catch (e) {
    ElMessage.error('加载历史记录失败')
  } finally {
    loading.value = false
  }
}

function formatTime(timestamp) {
  if (!timestamp) return ''
  const date = new Date(timestamp)
  return date.toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit'
  })
}

function viewDetail(record) {
  selectedRecord.value = record
  detailDialogVisible.value = true
}

async function deleteRecord(record) {
  try {
    await ElMessageBox.confirm('确定要删除这条记录吗？', '确认删除', {
      type: 'warning'
    })
    
    await api.deleteHistory(record.id)
    ElMessage.success('删除成功')
    loadHistory()
  } catch (e) {
    if (e !== 'cancel') {
      ElMessage.error(e.error || '删除失败')
    }
  }
}

async function handleClearHistory() {
  try {
    await ElMessageBox.confirm(
      isAdmin.value ? '确定要清空所有历史记录吗？' : '确定要清空您的历史记录吗？',
      '确认清空',
      { type: 'warning' }
    )
    
    await api.clearHistory()
    ElMessage.success('清空成功')
    loadHistory()
  } catch (e) {
    if (e !== 'cancel') {
      ElMessage.error(e.error || '清空失败')
    }
  }
}

async function reproduceInference(record) {
  if (!record.facts?.length) {
    ElMessage.warning('该记录没有事实数据')
    return
  }
  
  try {
    await api.clearFacts()
    await api.setKnownFacts(record.facts)
    ElMessage.success('已加载事实，正在跳转...')
    detailDialogVisible.value = false
    router.push('/inference')
  } catch (e) {
    ElMessage.error('加载事实失败')
  }
}
</script>

<style scoped>
.history-view {
  max-width: 1400px;
  margin: 0 auto;
}

.main-card {
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

.history-row {
  background-color: var(--el-bg-color-overlay);
}

/* 表格样式 - 减小条纹对比度 */
:deep(.el-table) {
  --el-table-row-hover-bg-color: var(--el-fill-color-light);
}

:deep(.el-table--striped .el-table__body tr.el-table__row--striped td.el-table__cell) {
  background: var(--el-fill-color-lighter);
}

.expand-content {
  padding: 15px 20px;
  background: var(--el-bg-color);
}

.expand-section {
  margin-bottom: 10px;
  color: var(--el-text-color-regular);
}

.conclusion-text {
  font-weight: bold;
  color: var(--el-color-warning);
}

.no-data {
  color: var(--el-text-color-secondary);
  font-style: italic;
}

.detail-content {
  color: var(--el-text-color-regular);
}

.detail-section {
  margin-top: 20px;
}

.detail-section h4 {
  margin-bottom: 10px;
  color: var(--el-text-color-primary);
}

.tags-container {
  display: flex;
  flex-wrap: wrap;
}

.path-display {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
}

.path-step {
  display: flex;
  align-items: center;
  gap: 8px;
}
</style>
