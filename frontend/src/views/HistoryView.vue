<template>
  <div class="history-view">
    <n-card class="main-card" title="推理历史记录">
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
      
      <n-data-table
        :columns="columns"
        :data="historyList"
        :loading="loading"
        :pagination="pagination"
        @update:page="handlePageChange"
        @update:page-size="handlePageSizeChange"
      />
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
import { ref, computed, onMounted, h, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { useMessage, useDialog, NTag, NButton, NIcon } from 'naive-ui'
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
const total = ref(0)

const pagination = reactive({
  page: 1,
  pageSize: 20,
  showSizePicker: true,
  pageSizes: [10, 20, 50, 100],
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

const columns = computed(() => {
  const cols = [
    {
      type: 'expand',
      renderExpand: (row) => {
        return h('div', { class: 'expand-content' }, [
          h('div', { class: 'expand-section' }, [
            h('strong', '已知事实：'),
            row.facts.map(fact => h(NTag, { size: 'small', type: 'success', style: 'margin: 2px;' }, { default: () => fact }))
          ]),
          h('div', { class: 'expand-section' }, [
            h('strong', '推理路径：'),
            row.path?.length 
              ? h('span', `规则 ${row.path.join(' → ')}`)
              : h('span', { class: 'no-data' }, '无')
          ])
        ])
      }
    },
    {
      title: '时间',
      key: 'timestamp',
      width: 180,
      render: (row) => formatTime(row.timestamp)
    }
  ]

  if (isAdmin.value) {
    cols.push({
      title: '用户',
      key: 'username',
      width: 120
    })
  }

  cols.push(
    {
      title: '推理类型',
      key: 'type',
      width: 120,
      render: (row) => {
        return h(
          NTag,
          { type: row.type === 'forward' ? 'success' : 'info' },
          { default: () => (row.type === 'forward' ? '正向推理' : '反向推理') }
        )
      }
    },
    {
      title: '结论',
      key: 'conclusion',
      render: (row) => {
        return h('span', { class: 'conclusion-text' }, row.conclusion || '无结论')
      }
    },
    {
      title: '事实数',
      key: 'facts',
      width: 100,
      render: (row) => row.facts?.length || 0
    },
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
              onClick: () => viewDetail(row),
              style: 'margin-right: 10px'
            },
            { default: () => '详情' }
          ),
          h(
            NButton,
            {
              text: true,
              type: 'error',
              size: 'small',
              onClick: () => deleteRecord(row)
            },
            { default: () => '删除' }
          )
        ]
      }
    }
  )

  return cols
})

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

<style scoped>
.history-view {
  max-width: 1400px;
  margin: 0 auto;
}

.header-actions {
  display: flex;
  gap: 10px;
}

.expand-content {
  padding: 15px 20px;
  background: rgba(0, 0, 0, 0.02);
}

.expand-section {
  margin-bottom: 10px;
}

.conclusion-text {
  font-weight: bold;
  color: var(--n-color-warning);
}

.no-data {
  opacity: 0.6;
  font-style: italic;
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
  gap: 8px;
}

.path-step {
  display: flex;
  align-items: center;
  gap: 8px;
}
</style>
