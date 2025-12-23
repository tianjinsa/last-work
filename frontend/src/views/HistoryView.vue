<template>
  <div class="history-view">
    <n-card class="main-card" title="推理历史记录" content-style="padding: 0; display: flex; flex-direction: column; height: 100%;">
      <template #header-extra>
        <div class="header-actions">
          <n-button type="error" ghost size="small" @click="handleClearHistory">
            <template #icon>
              <n-icon :component="TrashOutline" />
            </template>
            清空历史
          </n-button>
          <n-button type="primary" size="small" @click="loadHistory">
            <template #icon>
              <n-icon :component="RefreshOutline" />
            </template>
            刷新
          </n-button>
        </div>
      </template>
      
      <div class="history-list-container">
        <n-scrollbar>
          <n-spin :show="loading">
            <n-collapse arrow-placement="right" accordion style="padding: 12px 24px;">
              <n-collapse-item v-for="item in historyList" :key="item.id" :name="item.id">
                <template #header>
                  <div class="item-header">
                    <span class="item-time">{{ formatTime(item.timestamp) }}</span>
                    <n-tag :type="item.type === 'forward' ? 'success' : 'info'" size="small" round>
                      {{ item.type === 'forward' ? '正向' : '反向' }}
                    </n-tag>
                    <span class="item-conclusion">{{ item.conclusion || '无结论' }}</span>
                  </div>
                </template>
                <template #header-extra>
                  <n-space>
                    <n-button text type="primary" size="small" @click.stop="viewDetail(item)">详情</n-button>
                    <n-button text type="error" size="small" @click.stop="deleteRecord(item)">删除</n-button>
                  </n-space>
                </template>
                
                <div class="item-content">
                  <div class="content-section">
                    <strong>已知事实：</strong>
                    <n-space :size="4" style="margin-top: 8px">
                      <n-tag v-for="fact in item.facts" :key="fact" size="small" type="success">{{ fact }}</n-tag>
                      <span v-if="!item.facts?.length" class="no-data">无</span>
                    </n-space>
                  </div>
                  <div class="content-section" style="margin-top: 12px">
                    <strong>推理路径：</strong>
                    <div class="path-display" style="margin-top: 8px">
                      <template v-if="item.path?.length">
                        <template v-for="(ruleId, index) in item.path" :key="index">
                          <n-tag type="primary" size="small">规则 {{ ruleId }}</n-tag>
                          <n-icon v-if="index < item.path.length - 1" :component="ArrowForwardOutline" style="margin: 0 4px; vertical-align: middle;" />
                        </template>
                      </template>
                      <span v-else class="no-data">无</span>
                    </div>
                  </div>
                </div>
              </n-collapse-item>
            </n-collapse>
            <n-empty v-if="!loading && historyList.length === 0" description="暂无历史记录" style="padding: 40px 0" />
          </n-spin>
        </n-scrollbar>
      </div>

      <template #footer>
        <div class="pagination-container">
          <n-pagination
            v-model:page="pagination.page"
            v-model:page-size="pagination.pageSize"
            :item-count="pagination.itemCount"
            :page-sizes="[10, 20, 50, 100]"
            show-size-picker
            @update:page="pagination.onChange"
            @update:page-size="pagination.onUpdatePageSize"
          />
        </div>
      </template>
    </n-card>
    
    <!-- 详情对话框 -->
    <n-modal v-model:show="detailDialogVisible">
      <n-card style="width: 700px" title="推理详情" :bordered="false" size="huge" role="dialog" aria-modal="true">
        <div v-if="selectedRecord" class="detail-content">
          <n-descriptions bordered :column="2">
            <n-descriptions-item label="时间">{{ formatTime(selectedRecord.timestamp) }}</n-descriptions-item>
            <n-descriptions-item label="用户">{{ selectedRecord.username }}</n-descriptions-item>
            <n-descriptions-item label="推理类型">
              <n-tag :type="selectedRecord.type === 'forward' ? 'success' : 'info'">
                {{ selectedRecord.type === 'forward' ? '正向推理' : '反向推理' }}
              </n-tag>
            </n-descriptions-item>
            <n-descriptions-item label="结论">
              <strong>{{ selectedRecord.conclusion || '无' }}</strong>
            </n-descriptions-item>
          </n-descriptions>
          
          <div class="detail-section">
            <h4>已知事实：</h4>
            <div class="tags-container">
              <n-tag v-for="fact in selectedRecord.facts" :key="fact" type="success" style="margin: 4px;">
                {{ fact }}
              </n-tag>
              <span v-if="!selectedRecord.facts?.length" class="no-data">无</span>
            </div>
          </div>
          
          <div class="detail-section">
            <h4>推理路径：</h4>
            <div v-if="selectedRecord.path?.length" class="path-display">
              <div v-for="(ruleId, index) in selectedRecord.path" :key="index" class="path-step">
                <n-tag type="primary">规则 {{ ruleId }}</n-tag>
                <n-icon v-if="index < selectedRecord.path.length - 1" :component="ArrowForwardOutline" />
              </div>
            </div>
            <span v-else class="no-data">无推理路径</span>
          </div>
          
          <div class="detail-section">
            <h4>重现推理：</h4>
            <n-button type="primary" @click="reproduceInference(selectedRecord)">
              <template #icon>
                <n-icon :component="ArrowRedoOutline" />
              </template>
              使用这些事实进行推理
            </n-button>
          </div>
        </div>
        
        <template #footer>
          <div style="display: flex; justify-content: flex-end;">
            <n-button @click="detailDialogVisible = false">关闭</n-button>
          </div>
        </template>
      </n-card>
    </n-modal>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { useMessage, useDialog } from 'naive-ui'
import { useUserStore } from '../stores/user'
import api from '../api'
import {
  TrashOutline,
  RefreshOutline,
  ArrowForwardOutline,
  ArrowRedoOutline
} from '@vicons/ionicons5'

const router = useRouter()
const userStore = useUserStore()
const message = useMessage()
const dialog = useDialog()
const isAdmin = computed(() => userStore.isAdmin)

const loading = ref(false)
const historyList = ref([])

const pagination = reactive({
  page: 1,
  pageSize: 20,
  itemCount: 0,
  onChange: (page) => {
    pagination.page = page
    loadHistory()
  },
  onUpdatePageSize: (pageSize) => {
    pagination.pageSize = pageSize
    pagination.page = 1
    loadHistory()
  }
})

const detailDialogVisible = ref(false)
const selectedRecord = ref(null)

onMounted(() => {
  loadHistory()
})

async function loadHistory() {
  loading.value = true
  try {
    const res = await api.getHistory(pagination.page, pagination.pageSize)
    historyList.value = res.history || []
    pagination.itemCount = res.total || 0
  } catch (e) {
    message.error('加载历史记录失败')
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

function deleteRecord(record) {
  dialog.warning({
    title: '确认删除',
    content: '确定要删除这条记录吗？',
    positiveText: '确定',
    negativeText: '取消',
    onPositiveClick: async () => {
      try {
        await api.deleteHistory(record.id)
        message.success('删除成功')
        loadHistory()
      } catch (e) {
        message.error(e.error || '删除失败')
      }
    }
  })
}

function handleClearHistory() {
  dialog.warning({
    title: '确认清空',
    content: isAdmin.value ? '确定要清空所有历史记录吗？' : '确定要清空您的历史记录吗？',
    positiveText: '确定',
    negativeText: '取消',
    onPositiveClick: async () => {
      try {
        await api.clearHistory()
        message.success('清空成功')
        loadHistory()
      } catch (e) {
        message.error(e.error || '清空失败')
      }
    }
  })
}

async function reproduceInference(record) {
  if (!record.facts?.length) {
    message.warning('该记录没有事实数据')
    return
  }
  
  try {
    await api.clearFacts()
    await api.setKnownFacts(record.facts)
    message.success('已加载事实，正在跳转...')
    detailDialogVisible.value = false
    router.push('/inference')
  } catch (e) {
    message.error('加载事实失败')
  }
}
</script>

<script>
// 为了在 template 中使用图标组件，需要在这里导出或者在 setup 中定义
import { ArrowForwardOutline } from '@vicons/ionicons5'
</script>

<style scoped>
.history-view {
  height: 100%;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.main-card {
  height: 100%;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.main-card :deep(.n-card__content) {
  flex: 1;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  padding: 0 !important;
}

.main-card :deep(.n-card__footer) {
  flex-shrink: 0;
}

.history-list-container {
  flex: 1;
  overflow: hidden;
}

.header-actions {
  display: flex;
  gap: 10px;
}

.item-header {
  display: flex;
  align-items: center;
  gap: 16px;
}

.item-time {
  font-family: monospace;
  color: var(--n-text-color-3);
}

.item-conclusion {
  font-weight: bold;
  color: var(--n-color-warning);
}

.item-content {
  padding: 8px 0;
}

.no-data {
  opacity: 0.6;
  font-style: italic;
}

.pagination-container {
  padding: 12px 24px;
  display: flex;
  justify-content: flex-end;
  border-top: 1px solid var(--n-border-color);
}

.detail-section {
  margin-top: 20px;
}

.detail-section h4 {
  margin-bottom: 10px;
}

.tags-container {
  display: flex;
  flex-wrap: wrap;
}

.path-display {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 4px;
}

.path-step {
  display: flex;
  align-items: center;
  gap: 8px;
}
</style>
