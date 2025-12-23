<template>
  <div class="inference-view">
    <el-row :gutter="20">
      <!-- 左侧：知识库和事实管理 -->
      <el-col :span="8">
        <!-- 规则列表 -->
        <el-card class="panel-card">
          <template #header>
            <div class="card-header">
              <span>知识库规则</span>
              <el-tag type="info">{{ rules.length }} 条</el-tag>
            </div>
          </template>
          <div class="rules-list">
            <div v-for="(rule, index) in rules" :key="index" class="rule-item">
              <el-tag size="small" type="primary">R{{ rule.id }}</el-tag>
              <span class="rule-text">{{ rule.premises.join(' + ') }} → {{ rule.conclusion }}</span>
            </div>
          </div>
        </el-card>
        
        <!-- 事实管理 -->
        <el-card class="panel-card" style="margin-top: 15px;">
          <template #header>
            <div class="card-header">
              <span>事实管理</span>
              <el-button type="primary" size="small" @click="openFactDialog">
                选择事实
              </el-button>
            </div>
          </template>
          
          <div class="facts-section">
            <div class="section-title">已知事实：</div>
            <div class="facts-tags">
              <el-tag 
                v-for="fact in userFacts" 
                :key="fact" 
                closable 
                @close="removeFact(fact)"
                type="success"
                class="fact-tag"
              >
                {{ fact }}
              </el-tag>
              <el-tag 
                v-for="fact in derivedFacts" 
                :key="'d-' + fact"
                type="warning"
                class="fact-tag"
              >
                *{{ fact }}
              </el-tag>
              <span v-if="!userFacts.length && !derivedFacts.length" class="no-data">
                暂无事实
              </span>
            </div>
          </div>
          
          <div class="facts-section" style="margin-top: 15px;">
            <div class="section-title">已知为假：</div>
            <div class="facts-tags">
              <el-tag 
                v-for="fact in falseFacts" 
                :key="fact" 
                closable 
                @close="removeFalseFact(fact)"
                type="danger"
                class="fact-tag"
              >
                {{ fact }}
              </el-tag>
              <span v-if="!falseFacts.length" class="no-data">暂无</span>
            </div>
          </div>
          
          <el-button @click="clearAllFacts" type="danger" plain size="small" style="margin-top: 15px; width: 100%;">
            清空所有事实
          </el-button>
        </el-card>
      </el-col>
      
      <!-- 中间：推理控制 -->
      <el-col :span="8">
        <el-card class="panel-card">
          <template #header>
            <span>推理控制</span>
          </template>
          
          <div class="inference-controls">
            <el-button 
              type="success" 
              size="large" 
              @click="doForwardInference"
              :loading="loading"
              style="width: 100%; margin-bottom: 20px;"
            >
              <el-icon><CaretRight /></el-icon>
              正向推理
            </el-button>
            
            <el-divider>反向推理</el-divider>
            
            <el-select 
              v-model="backwardTarget" 
              placeholder="选择或输入目标结论"
              filterable
              allow-create
              style="width: 100%; margin-bottom: 15px;"
            >
              <el-option 
                v-for="c in conclusions" 
                :key="c" 
                :label="c" 
                :value="c" 
              />
            </el-select>
            
            <el-button 
              type="primary" 
              size="large" 
              @click="doBackwardInference"
              :loading="loading"
              style="width: 100%;"
            >
              <el-icon><Back /></el-icon>
              反向推理
            </el-button>
          </div>
        </el-card>
        
        <!-- 推理结果摘要 -->
        <el-card class="panel-card" style="margin-top: 15px;">
          <template #header>
            <span>推理结果</span>
          </template>
          <div class="result-content">
            <el-result v-if="resultStatus === 'success'" icon="success" :title="resultMessage" />
            <el-result v-else-if="resultStatus === 'failed'" icon="error" :title="resultMessage" />
            <el-result v-else-if="resultStatus === 'query'" icon="warning" title="需要确认事实">
              <template #sub-title>
                请确认以下事实是否为真
              </template>
            </el-result>
            <div v-else class="no-result">
              <el-icon size="48" color="#999"><QuestionFilled /></el-icon>
              <p>点击上方按钮开始推理</p>
            </div>
          </div>
        </el-card>
      </el-col>
      
      <!-- 右侧：可视化 -->
      <el-col :span="8">
        <el-card class="panel-card viz-card" :class="{ 'fullscreen': isFullscreen }">
          <template #header>
            <div class="card-header">
              <span>推理过程可视化</span>
              <div class="step-controls">
                <el-button size="small" @click="toggleFullscreen" circle style="margin-right: 10px;" :title="isFullscreen ? '退出全屏' : '全屏'">
                  <el-icon v-if="isFullscreen"><Close /></el-icon>
                  <el-icon v-else><FullScreen /></el-icon>
                </el-button>
                <el-button size="small" :disabled="currentStep <= 0" @click="prevStep">
                  <el-icon><ArrowLeft /></el-icon>
                </el-button>
                <span class="step-label">{{ currentStep }} / {{ totalSteps }}</span>
                <el-button size="small" :disabled="currentStep >= totalSteps" @click="nextStep">
                  <el-icon><ArrowRight /></el-icon>
                </el-button>
              </div>
            </div>
          </template>
          
          <div ref="graphContainer" class="graph-container"></div>
          
          <el-slider 
            v-model="currentStep" 
            :min="0" 
            :max="totalSteps" 
            :show-tooltip="false"
            style="margin-top: 10px;"
          />
          
          <div class="explanation-box">
            <div class="section-title">推理解释：</div>
            <div class="explanation-text">{{ currentExplanation || '暂无' }}</div>
          </div>
        </el-card>
      </el-col>
    </el-row>
    
    <!-- 事实选择对话框 -->
    <el-dialog v-model="factDialogVisible" title="选择事实" width="700px">
      <el-input v-model="factSearch" placeholder="搜索事实..." style="margin-bottom: 15px;" clearable />
      
      <el-row :gutter="20">
        <el-col :span="12">
          <div class="dialog-section-title">可选事实（点击添加）</div>
          <div class="fact-select-list">
            <div 
              v-for="fact in filteredAtoms" 
              :key="fact" 
              class="fact-select-item"
              @click="addFact(fact)"
            >
              {{ fact }}
            </div>
            <div v-if="!filteredAtoms.length" class="no-data">无可选事实</div>
          </div>
        </el-col>
        <el-col :span="12">
          <div class="dialog-section-title">已选事实（点击移除）</div>
          <div class="fact-select-list selected">
            <div 
              v-for="fact in derivedFacts" 
              :key="'d-' + fact" 
              class="fact-select-item derived"
            >
              *{{ fact }}
            </div>
            <div 
              v-for="fact in userFacts" 
              :key="fact" 
              class="fact-select-item"
              @click="removeFact(fact)"
            >
              {{ fact }}
            </div>
            <div v-if="!userFacts.length && !derivedFacts.length" class="no-data">暂无</div>
          </div>
        </el-col>
      </el-row>
      
      <template #footer>
        <el-button @click="factDialogVisible = false">关闭</el-button>
      </template>
    </el-dialog>
    
    <!-- 反向推理询问对话框 -->
    <el-dialog v-model="queryDialogVisible" title="需要确认事实" width="500px" :close-on-click-modal="false" :close-on-press-escape="false">
      <p style="margin-bottom: 15px;">推理过程需要以下事实，请勾选已知为真的事实：</p>
      <el-checkbox-group v-model="selectedQueryFacts">
        <el-checkbox v-for="fact in queryFacts" :key="fact" :label="fact" style="display: block; margin: 10px 0;">
          {{ fact }}
        </el-checkbox>
      </el-checkbox-group>
      
      <template #footer>
        <el-button @click="handleQueryCancel" :disabled="queryProcessing">全部为假 / 取消</el-button>
        <el-button type="primary" @click="handleQueryConfirm" :loading="queryProcessing">确认选中为真</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch, nextTick } from 'vue'
import { ElMessage } from 'element-plus'
import api from '../api'
import { Network } from 'vis-network'

// 数据状态
const rules = ref([])
const atoms = ref([])
const conclusions = ref([])
const userFacts = ref([])
const derivedFacts = ref([])
const falseFacts = ref([])

// 推理状态
const loading = ref(false)
const backwardTarget = ref('')
const resultStatus = ref('')
const resultMessage = ref('')

// 可视化状态
const graphContainer = ref(null)
const isFullscreen = ref(false)
const pathAll = ref([])
const currentStep = ref(0)
const totalSteps = computed(() => pathAll.value.length)
const stepStates = ref([])
const currentExplanation = computed(() => {
  if (currentStep.value < stepStates.value.length) {
    return stepStates.value[currentStep.value]?.explanation || ''
  }
  return ''
})

let network = null

// 事实选择对话框
const factDialogVisible = ref(false)
const factSearch = ref('')
const filteredAtoms = computed(() => {
  const search = factSearch.value.toLowerCase()
  const used = new Set([...userFacts.value, ...derivedFacts.value])
  return atoms.value.filter(a => !used.has(a) && a.toLowerCase().includes(search))
})

// 反向推理询问
const queryDialogVisible = ref(false)
const queryFacts = ref([])
const selectedQueryFacts = ref([])
const queryProcessing = ref(false)
let lastDialogCloseTime = 0
const MIN_DIALOG_INTERVAL = 500 // 最小对话框打开间隔(ms)

function toggleFullscreen() {
  isFullscreen.value = !isFullscreen.value
  // 等待 DOM 更新后重新适应画布
  nextTick(() => {
    if (network) {
      network.fit()
    }
  })
}

// 初始化
onMounted(async () => {
  await loadData()
})

async function loadData() {
  try {
    const [rulesRes, atomsRes, conclusionsRes, knownRes, falseRes] = await Promise.all([
      api.getRules(),
      api.getAtoms(),
      api.getConclusions(),
      api.getKnownFacts(),
      api.getFalseFacts()
    ])
    
    rules.value = rulesRes.rules || []
    atoms.value = atomsRes.atoms || []
    conclusions.value = conclusionsRes.conclusions || []
    userFacts.value = knownRes.user_facts || []
    derivedFacts.value = knownRes.derived_facts || []
    falseFacts.value = falseRes.facts || []
  } catch (e) {
    ElMessage.error('加载数据失败')
  }
}

function openFactDialog() {
  factSearch.value = ''
  factDialogVisible.value = true
}

async function addFact(fact) {
  if (!userFacts.value.includes(fact)) {
    userFacts.value.push(fact)
    await api.setKnownFacts(userFacts.value)
  }
}

async function removeFact(fact) {
  const index = userFacts.value.indexOf(fact)
  if (index > -1) {
    userFacts.value.splice(index, 1)
    // 移除事实需要重置推理状态
    derivedFacts.value = []
    pathAll.value = []
    await api.setKnownFacts(userFacts.value)
    resetVisualization()
  }
}

async function removeFalseFact(fact) {
  const index = falseFacts.value.indexOf(fact)
  if (index > -1) {
    falseFacts.value.splice(index, 1)
    await api.setFalseFacts(falseFacts.value)
  }
}

async function clearAllFacts() {
  userFacts.value = []
  derivedFacts.value = []
  falseFacts.value = []
  pathAll.value = []
  resultStatus.value = ''
  resultMessage.value = ''
  await api.clearFacts()
  resetVisualization()
}

// 正向推理
async function doForwardInference() {
  if (!userFacts.value.length) {
    ElMessage.warning('请先添加已知事实')
    return
  }
  
  loading.value = true
  try {
    const res = await api.forwardInference()
    
    if (res.conclusions?.length) {
      resultStatus.value = 'success'
      resultMessage.value = `推理成功！结论: ${res.conclusions[0]}`
    } else {
      resultStatus.value = 'failed'
      resultMessage.value = '无法推出新的结论'
    }
    
    // 更新状态
    derivedFacts.value = res.derived_facts || []
    pathAll.value = res.path || []
    
    // 更新可视化
    precalculateSteps(res.known_facts, res.path, res.rules)
    currentStep.value = totalSteps.value
    drawGraph()
    
  } catch (e) {
    ElMessage.error(e.error || '推理失败')
  } finally {
    loading.value = false
  }
}

// 反向推理
async function doBackwardInference() {
  if (!backwardTarget.value) {
    ElMessage.warning('请选择目标结论')
    return
  }
  
  loading.value = true
  try {
    const res = await api.startBackward(backwardTarget.value)
    await handleBackwardResult(res)
  } catch (e) {
    ElMessage.error(e.error || '推理失败')
    loading.value = false
  }
}

async function handleBackwardResult(res) {
  if (res.status === 'success') {
    loading.value = false
    resultStatus.value = 'success'
    resultMessage.value = res.message
    
    derivedFacts.value = res.derived_facts || []
    pathAll.value = res.path || []
    
    precalculateSteps(res.known_facts, res.path, res.rules)
    currentStep.value = totalSteps.value
    drawGraph()
    
  } else if (res.status === 'failed') {
    loading.value = false
    resultStatus.value = 'failed'
    resultMessage.value = res.message
    
    derivedFacts.value = res.derived_facts || []
    pathAll.value = res.path || []
    
    precalculateSteps(res.known_facts, res.path, res.rules)
    currentStep.value = totalSteps.value
    drawGraph()
    
  } else if (res.status === 'query') {
    loading.value = false
    resultStatus.value = 'query'
    queryFacts.value = res.query_facts || []
    selectedQueryFacts.value = [...queryFacts.value]
    // 计算需要等待的时间，确保距离上次关闭至少 MIN_DIALOG_INTERVAL ms
    const now = Date.now()
    const elapsed = now - lastDialogCloseTime
    const delay = Math.max(MIN_DIALOG_INTERVAL - elapsed, 100)
    await nextTick()
    setTimeout(() => {
      queryDialogVisible.value = true
    }, delay)
  }
}

async function handleQueryConfirm() {
  if (queryProcessing.value) return
  queryProcessing.value = true
  queryDialogVisible.value = false
  lastDialogCloseTime = Date.now()
  loading.value = true
  
  const trueFacts = selectedQueryFacts.value
  const falseFacts_new = queryFacts.value.filter(f => !trueFacts.includes(f))
  
  // 更新本地状态
  trueFacts.forEach(f => {
    if (!userFacts.value.includes(f)) {
      userFacts.value.push(f)
    }
  })
  falseFacts_new.forEach(f => {
    if (!falseFacts.value.includes(f)) {
      falseFacts.value.push(f)
    }
  })
  
  try {
    const res = await api.continueBackward(trueFacts, falseFacts_new)
    queryProcessing.value = false
    await handleBackwardResult(res)
  } catch (e) {
    ElMessage.error(e.error || '推理失败')
    loading.value = false
    queryProcessing.value = false
  }
}

async function handleQueryCancel() {
  if (queryProcessing.value) return
  queryProcessing.value = true
  queryDialogVisible.value = false
  lastDialogCloseTime = Date.now()
  loading.value = true
  
  const falseFacts_new = queryFacts.value
  falseFacts_new.forEach(f => {
    if (!falseFacts.value.includes(f)) {
      falseFacts.value.push(f)
    }
  })
  
  try {
    const res = await api.continueBackward([], falseFacts_new)
    queryProcessing.value = false
    await handleBackwardResult(res)
  } catch (e) {
    ElMessage.error(e.error || '推理失败')
    loading.value = false
    queryProcessing.value = false
  }
}

// 可视化相关
function precalculateSteps(initialFacts, path, allRules) {
  stepStates.value = []
  let currentFacts = new Set(initialFacts || [])
  
  // 步骤0：初始状态
  stepStates.value.push({
    facts: new Set(currentFacts),
    explanation: '初始状态，仅包含已知事实。',
    pathIds: []
  })
  
  let explanationLines = []
  for (let i = 0; i < path.length; i++) {
    const ruleId = path[i]
    if (ruleId < allRules.length) {
      const rule = allRules[ruleId]
      currentFacts.add(rule.conclusion)
      explanationLines.push(`步骤${i + 1}: ${rule.premises.join(' + ')} → ${rule.conclusion} (规则${ruleId})`)
    }
    
    stepStates.value.push({
      facts: new Set(currentFacts),
      explanation: explanationLines.join('\n'),
      pathIds: path.slice(0, i + 1)
    })
  }
}

function resetVisualization() {
  stepStates.value = []
  currentStep.value = 0
  if (network) {
    network.destroy()
    network = null
  }
}

function prevStep() {
  if (currentStep.value > 0) {
    currentStep.value--
  }
}

function nextStep() {
  if (currentStep.value < totalSteps.value) {
    currentStep.value++
  }
}

watch(currentStep, () => {
  drawGraph()
})

function drawGraph() {
  if (!graphContainer.value) return
  if (currentStep.value >= stepStates.value.length) return
  
  const state = stepStates.value[currentStep.value]
  const nodes = []
  const edges = []
  const addedNodes = new Set()
  
  function addNode(id, label, group) {
    if (addedNodes.has(id)) return
    
    let color = {}
    let font = { color: '#ffffff' }
    
    if (group === 'initial_fact') {
      color = { background: '#2d4059', border: '#decdc3' }
    } else if (group === 'new_fact') {
      color = { background: '#f07b3f', border: '#decdc3' }
    } else if (group === 'conclusion') {
      color = { background: '#ffd460', border: '#decdc3' }
      font = { color: '#2d4059' }
    } else if (group === 'rule') {
      color = { background: '#ea5455', border: '#decdc3' }
    }
    
    nodes.push({ id, label, color, font, shape: 'box', margin: 10, widthConstraint: { maximum: 100 } })
    addedNodes.add(id)
  }
  
  // 添加事实节点
  const initialFacts = new Set(userFacts.value)
  state.facts.forEach(fact => {
    let group = 'new_fact'
    if (initialFacts.has(fact)) {
      group = 'initial_fact'
    }
    if (fact === backwardTarget.value) {
      group = 'conclusion'
    }
    addNode(fact, fact, group)
  })
  
  // 添加规则节点和边
  state.pathIds.forEach(ruleId => {
    if (ruleId >= rules.value.length) return
    
    const rule = rules.value[ruleId]
    const ruleNodeId = `R${ruleId}`
    
    addNode(ruleNodeId, `规则${ruleId}`, 'rule')
    
    rule.premises.forEach(pre => {
      addNode(pre, pre, 'new_fact')
      edges.push({ from: pre, to: ruleNodeId })
    })
    
    addNode(rule.conclusion, rule.conclusion, 'new_fact')
    edges.push({ from: ruleNodeId, to: rule.conclusion })
  })
  
  const data = {
    nodes: nodes,
    edges: edges
  }
  
  const options = {
    nodes: {
      font: { size: 14, face: 'Microsoft YaHei' },
      shadow: true
    },
    edges: {
      arrows: 'to',
      color: { color: '#decdc3' },
      smooth: { type: 'cubicBezier', forceDirection: 'vertical', roundness: 0.5 }
    },
    layout: {
      hierarchical: {
        direction: 'DU',
        sortMethod: 'directed',
        levelSeparation: 80,
        nodeSpacing: 100
      }
    },
    physics: {
      enabled: true,
      hierarchicalRepulsion: {
        centralGravity: 0.3,
        springLength: 100,
        springConstant: 1,
        nodeDistance: 100,
        damping: 1
      },
      solver: 'hierarchicalRepulsion'
    }
  }
  
  if (network) {
    network.destroy()
  }
  
  nextTick(() => {
    if (graphContainer.value) {
      network = new Network(graphContainer.value, data, options)
    }
  })
}
</script>

<style scoped>
.inference-view {
  height: calc(100vh - 120px);
}

.panel-card {
  background: var(--el-bg-color-overlay);
  border-color: var(--el-border-color);
  height: fit-content;
}

.viz-card {
  height: calc(100vh - 140px);
  display: flex;
  flex-direction: column;
}

:deep(.viz-card > .el-card__body) {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.rules-list {
  max-height: 200px;
  overflow-y: auto;
}

.rule-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 0;
  border-bottom: 1px solid var(--el-border-color);
  font-size: 13px;
  color: var(--el-text-color-regular);
}

.rule-item:last-child {
  border-bottom: none;
}

.rule-text {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.section-title {
  color: var(--el-text-color-secondary);
  font-size: 13px;
  margin-bottom: 8px;
}

.facts-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.fact-tag {
  cursor: pointer;
}

.no-data {
  color: var(--el-text-color-secondary);
  font-size: 13px;
}

.inference-controls {
  padding: 10px 0;
}

.result-content {
  min-height: 150px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.no-result {
  text-align: center;
  color: #666;
}

.no-result p {
  margin-top: 10px;
}

.step-controls {
  display: flex;
  align-items: center;
  gap: 10px;
}

.step-label {
  font-size: 12px;
  color: var(--el-text-color-secondary);
}

.graph-container {
  flex: 1;
  min-height: 300px;
  background: var(--el-bg-color-overlay);
  border-radius: 4px;
  overflow: hidden;
  position: relative;
}

.explanation-box {
  margin-top: 15px;
  padding: 10px;
  background: var(--el-bg-color-overlay);
  border-radius: 4px;
  max-height: 100px;
  overflow-y: auto;
  flex-shrink: 0;
}

.explanation-text {
  color: var(--el-text-color-regular);
  font-size: 13px;
  white-space: pre-wrap;
}

/* 事实选择对话框 */
.dialog-section-title {
  font-weight: bold;
  margin-bottom: 10px;
  color: var(--el-text-color-regular);
}

.fact-select-list {
  height: 300px;
  overflow-y: auto;
  border: 1px solid var(--el-border-color);
  border-radius: 4px;
  padding: 10px;
  background: var(--el-bg-color-overlay);
}

.fact-select-list.selected {
  background: var(--el-bg-color);
}

.fact-select-item {
  padding: 8px 12px;
  margin: 4px 0;
  background: var(--el-fill-color-light);
  border: 1px solid var(--el-border-color);
  border-radius: 4px;
  cursor: pointer;
  transition: all 0.2s;
  color: var(--el-text-color-regular);
}

/* 全屏模式 */
.viz-card.fullscreen {
  position: fixed;
  top: 0;
  left: 0;
  width: 100vw;
  height: 100vh;
  z-index: 2000;
  margin: 0 !important;
  border-radius: 0;
  display: flex;
  flex-direction: column;
}

.viz-card.fullscreen :deep(.el-card__body) {
  flex: 1;
  display: flex;
  flex-direction: column;
  height: 100%;
  padding: 20px;
  overflow: hidden;
}

.viz-card.fullscreen .graph-container {
  flex: 1;
  height: auto;
  min-height: 0;
}


.fact-select-item:hover {
  background: var(--el-color-primary-light-3);
  border-color: var(--el-color-primary);
  color: #fff;
}

.fact-select-item.derived {
  background: var(--el-color-warning-light-9);
  border-color: var(--el-color-warning-light-5);
  cursor: not-allowed;
  font-style: italic;
  color: var(--el-color-warning);
}
</style>
