<template>
  <div class="inference-view">
    <n-grid :x-gap="20" :cols="24">
      <!-- 左侧：知识库和事实管理 -->
      <n-grid-item :span="8">
        <!-- 规则列表 -->
        <n-card class="panel-card" title="知识库规则">
          <template #header-extra>
            <n-tag type="info">{{ rules.length }} 条</n-tag>
          </template>
          <n-scrollbar style="max-height: 300px">
            <div v-for="(rule, index) in rules" :key="index" class="rule-item">
              <n-tag size="small" type="primary">R{{ rule.id }}</n-tag>
              <span class="rule-text"
                >{{ rule.premises.join(" + ") }} → {{ rule.conclusion }}</span
              >
            </div>
          </n-scrollbar>
        </n-card>

        <!-- 事实管理 -->
        <n-card class="panel-card" style="margin-top: 15px" title="事实管理">
          <template #header-extra>
            <n-button type="primary" size="small" @click="openFactDialog">
              选择事实
            </n-button>
          </template>
          <n-scrollbar style="max-height: 100px">
            <div class="facts-section">
              <div class="section-title">已知事实：</div>
              <div class="facts-tags">
                <n-tag
                  v-for="fact in userFacts"
                  :key="fact"
                  closable
                  @close="removeFact(fact)"
                  type="success"
                  class="fact-tag"
                >
                  {{ fact }}
                </n-tag>
                <n-tag
                  v-for="fact in derivedFacts"
                  :key="'d-' + fact"
                  type="warning"
                  class="fact-tag"
                >
                  *{{ fact }}
                </n-tag>
                <span
                  v-if="!userFacts.length && !derivedFacts.length"
                  class="no-data"
                >
                  暂无事实
                </span>
              </div>
            </div>
          </n-scrollbar>
          <n-scrollbar style="max-height: 100px">
            <div class="facts-section" style="margin-top: 15px">
              <div class="section-title">已知为假：</div>
              <div class="facts-tags">
                <n-tag
                  v-for="fact in falseFacts"
                  :key="fact"
                  closable
                  @close="removeFalseFact(fact)"
                  type="error"
                  class="fact-tag"
                >
                  {{ fact }}
                </n-tag>
                <span v-if="!falseFacts.length" class="no-data">暂无</span>
              </div>
            </div>
          </n-scrollbar>
          <n-button
            @click="clearAllFacts"
            type="error"
            ghost
            size="small"
            style="margin-top: 15px; width: 100%"
          >
            清空所有事实
          </n-button>
        </n-card>
      </n-grid-item>

      <!-- 中间：推理控制 -->
      <n-grid-item :span="8">
        <n-card class="panel-card" title="推理控制">
          <div class="inference-controls">
            <n-button
              type="success"
              size="large"
              @click="doForwardInference"
              :loading="loading"
              style="width: 100%; margin-bottom: 20px"
            >
              <template #icon>
                <n-icon :component="PlayOutline" />
              </template>
              正向推理
            </n-button>

            <n-divider>反向推理</n-divider>

            <n-select
              v-model:value="backwardTarget"
              placeholder="选择或输入目标结论"
              filterable
              tag
              :options="conclusionOptions"
              style="width: 100%; margin-bottom: 15px"
            />

            <n-button
              type="primary"
              size="large"
              @click="doBackwardInference"
              :loading="loading"
              style="width: 100%"
            >
              <template #icon>
                <n-icon :component="ArrowBackOutline" />
              </template>
              反向推理
            </n-button>
          </div>
        </n-card>

        <!-- 推理结果摘要 -->
        <n-card class="panel-card" style="margin-top: 15px" title="推理结果">
          <div class="result-content">
            <n-result
              v-if="resultStatus === 'success'"
              status="success"
              :title="resultMessage"
            />
            <n-result
              v-else-if="resultStatus === 'failed'"
              status="error"
              :title="resultMessage"
            />
            <n-result
              v-else-if="resultStatus === 'query'"
              status="warning"
              title="需要确认事实"
              description="请确认以下事实是否为真"
            />
            <div v-else class="no-result">
              <n-icon size="48" color="#999" :component="HelpCircleOutline" />
              <p>点击上方按钮开始推理</p>
            </div>
          </div>
        </n-card>
      </n-grid-item>

      <!-- 右侧：可视化 -->
      <n-grid-item :span="8">
        <n-card
          class="panel-card viz-card"
          :class="{ fullscreen: isFullscreen }"
          title="推理过程可视化"
        >
          <template #header-extra>
            <div class="step-controls">
              <n-button
                @click="toggleFullscreen"
                style="margin-right: 10px"
                :title="isFullscreen ? '退出全屏' : '全屏'"
              >
                <template #icon>
                  <n-icon
                    :component="isFullscreen ? CloseOutline : ResizeOutline"
                  />
                </template>
              </n-button>
              <n-button
                size="small"
                :disabled="currentStep <= 0"
                @click="prevStep"
              >
                <template #icon>
                  <n-icon :component="ArrowBackOutline" />
                </template>
              </n-button>
              <span class="step-label"
                >{{ currentStep }} / {{ totalSteps }}</span
              >
              <n-button
                size="small"
                :disabled="currentStep >= totalSteps"
                @click="nextStep"
              >
                <template #icon>
                  <n-icon :component="ArrowForwardOutline" />
                </template>
              </n-button>
            </div>
          </template>

          <div ref="graphContainer" class="graph-container"></div>

          <n-slider
            v-model:value="currentStep"
            :min="0"
            :max="totalSteps"
            :tooltip="false"
            style="margin-top: 10px"
          />

          <n-scrollbar class="explanation-box" style="max-height: 20vh;">
            <div class="section-title">推理解释：</div>
            <div class="explanation-text">
              {{ currentExplanation || "暂无" }}
            </div>
          </n-scrollbar>
        </n-card>
      </n-grid-item>
    </n-grid>

    <!-- 事实选择对话框 -->
    <n-modal v-model:show="factDialogVisible">
      <n-card
        style="width: 700px"
        title="选择事实"
        :bordered="false"
        size="huge"
        role="dialog"
        aria-modal="true"
      >
        <n-input
          v-model:value="factSearch"
          placeholder="搜索事实..."
          style="margin-bottom: 15px"
          clearable
        />

        <n-grid :x-gap="20" :cols="2">
          <n-grid-item>
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
          </n-grid-item>
          <n-grid-item>
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
              <div
                v-if="!userFacts.length && !derivedFacts.length"
                class="no-data"
              >
                暂无
              </div>
            </div>
          </n-grid-item>
        </n-grid>

        <template #footer>
          <div style="display: flex; justify-content: flex-end">
            <n-button @click="factDialogVisible = false">关闭</n-button>
          </div>
        </template>
      </n-card>
    </n-modal>

    <!-- 反向推理询问对话框 -->
    <n-modal
      v-model:show="queryDialogVisible"
      :mask-closable="false"
      :close-on-esc="false"
    >
      <n-card
        style="width: 500px"
        title="需要确认事实"
        :bordered="false"
        size="huge"
        role="dialog"
        aria-modal="true"
      >
        <p style="margin-bottom: 15px">
          推理过程需要以下事实，请勾选已知为真的事实：
        </p>
        <n-checkbox-group v-model:value="selectedQueryFacts">
          <n-checkbox
            v-for="fact in queryFacts"
            :key="fact"
            :value="fact"
            style="display: block; margin: 10px 0"
          >
            {{ fact }}
          </n-checkbox>
        </n-checkbox-group>

        <template #footer>
          <div style="display: flex; justify-content: flex-end; gap: 10px">
            <n-button @click="handleQueryCancel" :disabled="queryProcessing"
              >全部为假 / 取消</n-button
            >
            <n-button
              type="primary"
              @click="handleQueryConfirm"
              :loading="queryProcessing"
              >确认选中为真</n-button
            >
          </div>
        </template>
      </n-card>
    </n-modal>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch, nextTick } from "vue";
import { useMessage } from "naive-ui";
import api from "../api";
import { Network } from "vis-network";
import {
  PlayOutline,
  ArrowBackOutline,
  ArrowForwardOutline,
  HelpCircleOutline,
  CloseOutline,
  ResizeOutline,
} from "@vicons/ionicons5";

const message = useMessage();

// 数据状态
const rules = ref([]);
const atoms = ref([]);
const conclusions = ref([]);
const userFacts = ref([]);
const derivedFacts = ref([]);
const falseFacts = ref([]);

// 推理状态
const loading = ref(false);
const backwardTarget = ref("");
const resultStatus = ref("");
const resultMessage = ref("");

// 可视化状态
const graphContainer = ref(null);
const isFullscreen = ref(false);
const pathAll = ref([]);
const currentStep = ref(0);
const totalSteps = computed(() => pathAll.value.length);
const stepStates = ref([]);
const currentExplanation = computed(() => {
  if (currentStep.value < stepStates.value.length) {
    return stepStates.value[currentStep.value]?.explanation || "";
  }
  return "";
});

let network = null;

function refitNetwork() {
  nextTick(() => {
    requestAnimationFrame(() => {
      if (network) {
        network.setSize("100%", "100%");
        network.redraw();
        network.fit({
          animation: { duration: 120, easingFunction: "easeInOutQuad" },
        });
      }
    });
    setTimeout(() => {
      if (network) {
        network.redraw();
        network.fit({ animation: false });
      }
    }, 180);
  });
}

// 事实选择对话框
const factDialogVisible = ref(false);
const factSearch = ref("");
const filteredAtoms = computed(() => {
  const search = factSearch.value.toLowerCase();
  const used = new Set([...userFacts.value, ...derivedFacts.value]);
  return atoms.value.filter(
    (a) => !used.has(a) && a.toLowerCase().includes(search)
  );
});

const conclusionOptions = computed(() => {
  return conclusions.value.map((c) => ({ label: c, value: c }));
});

// 反向推理询问
const queryDialogVisible = ref(false);
const queryFacts = ref([]);
const selectedQueryFacts = ref([]);
const queryProcessing = ref(false);
let lastDialogCloseTime = 0;
const MIN_DIALOG_INTERVAL = 500; // 最小对话框打开间隔(ms)

function toggleFullscreen() {
  isFullscreen.value = !isFullscreen.value;
  // 等待 DOM 更新后重新适应画布（进入/退出全屏都执行两次以防偏移）
  refitNetwork();
}

// 初始化
onMounted(async () => {
  await loadData();
});

async function loadData() {
  try {
    const [rulesRes, atomsRes, conclusionsRes, knownRes, falseRes] =
      await Promise.all([
        api.getRules(),
        api.getAtoms(),
        api.getConclusions(),
        api.getKnownFacts(),
        api.getFalseFacts(),
      ]);

    rules.value = rulesRes.rules || [];
    atoms.value = atomsRes.atoms || [];
    conclusions.value = conclusionsRes.conclusions || [];
    userFacts.value = knownRes.user_facts || [];
    derivedFacts.value = knownRes.derived_facts || [];
    falseFacts.value = falseRes.facts || [];
  } catch (e) {
    message.error("加载数据失败");
  }
}

function openFactDialog() {
  factSearch.value = "";
  factDialogVisible.value = true;
}

async function addFact(fact) {
  if (!userFacts.value.includes(fact)) {
    userFacts.value.push(fact);
    await api.setKnownFacts(userFacts.value);
  }
}

async function removeFact(fact) {
  const index = userFacts.value.indexOf(fact);
  if (index > -1) {
    userFacts.value.splice(index, 1);
    // 移除事实需要重置推理状态
    derivedFacts.value = [];
    pathAll.value = [];
    await api.setKnownFacts(userFacts.value);
    resetVisualization();
  }
}

async function removeFalseFact(fact) {
  const index = falseFacts.value.indexOf(fact);
  if (index > -1) {
    falseFacts.value.splice(index, 1);
    await api.setFalseFacts(falseFacts.value);
  }
}

async function clearAllFacts() {
  userFacts.value = [];
  derivedFacts.value = [];
  falseFacts.value = [];
  pathAll.value = [];
  resultStatus.value = "";
  resultMessage.value = "";
  await api.clearFacts();
  resetVisualization();
}

// 正向推理
async function doForwardInference() {
  if (!userFacts.value.length) {
    message.warning("请先添加已知事实");
    return;
  }

  loading.value = true;
  try {
    const res = await api.forwardInference();

    if (res.conclusions?.length) {
      resultStatus.value = "success";
      resultMessage.value = `推理成功！结论: ${res.conclusions[0]}`;
    } else {
      resultStatus.value = "failed";
      resultMessage.value = "无法推出新的结论";
    }

    // 更新状态
    derivedFacts.value = res.derived_facts || [];
    pathAll.value = res.path || [];

    // 更新可视化
    precalculateSteps(res.known_facts, res.path, res.rules);
    currentStep.value = totalSteps.value;
    drawGraph();
  } catch (e) {
    message.error(e.error || "推理失败");
  } finally {
    loading.value = false;
  }
}

// 反向推理
async function doBackwardInference() {
  if (!backwardTarget.value) {
    message.warning("请选择目标结论");
    return;
  }

  loading.value = true;
  try {
    const res = await api.startBackward(backwardTarget.value);
    await handleBackwardResult(res);
  } catch (e) {
    message.error(e.error || "推理失败");
    loading.value = false;
  }
}

async function handleBackwardResult(res) {
  if (res.status === "success") {
    loading.value = false;
    resultStatus.value = "success";
    resultMessage.value = res.message;

    derivedFacts.value = res.derived_facts || [];
    pathAll.value = res.path || [];

    precalculateSteps(res.known_facts, res.path, res.rules);
    currentStep.value = totalSteps.value;
    drawGraph();
  } else if (res.status === "failed") {
    loading.value = false;
    resultStatus.value = "failed";
    resultMessage.value = res.message;

    derivedFacts.value = res.derived_facts || [];
    pathAll.value = res.path || [];

    precalculateSteps(res.known_facts, res.path, res.rules);
    currentStep.value = totalSteps.value;
    drawGraph();
  } else if (res.status === "query") {
    loading.value = false;
    resultStatus.value = "query";
    queryFacts.value = res.query_facts || [];
    selectedQueryFacts.value = [...queryFacts.value];
    // 计算需要等待的时间，确保距离上次关闭至少 MIN_DIALOG_INTERVAL ms
    const now = Date.now();
    const elapsed = now - lastDialogCloseTime;
    const delay = Math.max(MIN_DIALOG_INTERVAL - elapsed, 100);
    await nextTick();
    setTimeout(() => {
      queryDialogVisible.value = true;
    }, delay);
  }
}

async function handleQueryConfirm() {
  if (queryProcessing.value) return;
  queryProcessing.value = true;
  queryDialogVisible.value = false;
  lastDialogCloseTime = Date.now();
  loading.value = true;

  const trueFacts = selectedQueryFacts.value;
  const falseFacts_new = queryFacts.value.filter((f) => !trueFacts.includes(f));

  // 更新本地状态
  trueFacts.forEach((f) => {
    if (!userFacts.value.includes(f)) {
      userFacts.value.push(f);
    }
  });
  falseFacts_new.forEach((f) => {
    if (!falseFacts.value.includes(f)) {
      falseFacts.value.push(f);
    }
  });

  try {
    const res = await api.continueBackward(trueFacts, falseFacts_new);
    queryProcessing.value = false;
    await handleBackwardResult(res);
  } catch (e) {
    message.error(e.error || "推理失败");
    loading.value = false;
    queryProcessing.value = false;
  }
}

async function handleQueryCancel() {
  if (queryProcessing.value) return;
  queryProcessing.value = true;
  queryDialogVisible.value = false;
  lastDialogCloseTime = Date.now();
  loading.value = true;

  const falseFacts_new = queryFacts.value;
  falseFacts_new.forEach((f) => {
    if (!falseFacts.value.includes(f)) {
      falseFacts.value.push(f);
    }
  });

  try {
    const res = await api.continueBackward([], falseFacts_new);
    queryProcessing.value = false;
    await handleBackwardResult(res);
  } catch (e) {
    message.error(e.error || "推理失败");
    loading.value = false;
    queryProcessing.value = false;
  }
}

// 可视化相关
function precalculateSteps(initialFacts, path, allRules) {
  stepStates.value = [];
  let currentFacts = new Set(initialFacts || []);

  // 步骤0：初始状态
  stepStates.value.push({
    facts: new Set(currentFacts),
    explanation: "初始状态，仅包含已知事实。",
    pathIds: [],
  });

  let explanationLines = [];
  for (let i = 0; i < path.length; i++) {
    const ruleId = path[i];
    if (ruleId < allRules.length) {
      const rule = allRules[ruleId];
      currentFacts.add(rule.conclusion);
      explanationLines.push(
        `步骤${i + 1}: ${rule.premises.join(" + ")} → ${
          rule.conclusion
        } (规则${ruleId})`
      );
    }

    stepStates.value.push({
      facts: new Set(currentFacts),
      explanation: explanationLines.join("\n"),
      pathIds: path.slice(0, i + 1),
    });
  }
}

function resetVisualization() {
  stepStates.value = [];
  currentStep.value = 0;
  if (network) {
    network.destroy();
    network = null;
  }
}

function prevStep() {
  if (currentStep.value > 0) {
    currentStep.value--;
  }
}

function nextStep() {
  if (currentStep.value < totalSteps.value) {
    currentStep.value++;
  }
}

watch(currentStep, () => {
  drawGraph();
});

function drawGraph() {
  if (!graphContainer.value) return;
  if (currentStep.value >= stepStates.value.length) return;

  const state = stepStates.value[currentStep.value];
  const nodes = [];
  const edges = [];
  const addedNodes = new Set();

  function addNode(id, label, group) {
    if (addedNodes.has(id)) return;

    let color = {};
    let font = { color: "#ffffff" };

    if (group === "initial_fact") {
      color = { background: "#2d4059", border: "#decdc3" };
    } else if (group === "new_fact") {
      color = { background: "#f07b3f", border: "#decdc3" };
    } else if (group === "conclusion") {
      color = { background: "#ffd460", border: "#decdc3" };
      font = { color: "#2d4059" };
    } else if (group === "rule") {
      color = { background: "#ea5455", border: "#decdc3" };
    }

    nodes.push({
      id,
      label,
      color,
      font,
      shape: "box",
      margin: 10,
      widthConstraint: { maximum: 100 },
    });
    addedNodes.add(id);
  }

  // 添加事实节点
  const initialFacts = new Set(userFacts.value);
  state.facts.forEach((fact) => {
    let group = "new_fact";
    if (initialFacts.has(fact)) {
      group = "initial_fact";
    }
    if (fact === backwardTarget.value) {
      group = "conclusion";
    }
    addNode(fact, fact, group);
  });

  // 添加规则节点和边
  state.pathIds.forEach((ruleId) => {
    if (ruleId >= rules.value.length) return;

    const rule = rules.value[ruleId];
    const ruleNodeId = `R${ruleId}`;

    addNode(ruleNodeId, `规则${ruleId}`, "rule");

    rule.premises.forEach((pre) => {
      addNode(pre, pre, "new_fact");
      edges.push({ from: pre, to: ruleNodeId });
    });

    addNode(rule.conclusion, rule.conclusion, "new_fact");
    edges.push({ from: ruleNodeId, to: rule.conclusion });
  });

  const data = {
    nodes: nodes,
    edges: edges,
  };

  const options = {
    nodes: {
      font: { size: 14, face: "Microsoft YaHei" },
      shadow: true,
    },
    edges: {
      arrows: "to",
      color: { color: "#decdc3" },
      smooth: {
        type: "cubicBezier",
        forceDirection: "vertical",
        roundness: 0.5,
      },
    },
    layout: {
      hierarchical: {
        direction: "DU",
        sortMethod: "directed",
        levelSeparation: 80,
        nodeSpacing: 100,
      },
    },
    physics: {
      enabled: true,
      hierarchicalRepulsion: {
        centralGravity: 0.3,
        springLength: 100,
        springConstant: 1,
        nodeDistance: 100,
        damping: 1,
      },
      solver: "hierarchicalRepulsion",
    },
  };

  if (network) {
    network.destroy();
  }

  nextTick(() => {
    if (graphContainer.value) {
      network = new Network(graphContainer.value, data, options);
    }
  });
}
</script>

<style scoped>
.inference-view {
  height: calc(100vh - 120px);
}

.panel-card {
  height: fit-content;
}

.viz-card {
  height: calc(100vh - 140px);
  display: flex;
  flex-direction: column;
}

:deep(.viz-card > .n-card__content) {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
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
  border-bottom: 1px solid var(--n-border-color);
  font-size: 13px;
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
  opacity: 0.8;
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
  opacity: 0.6;
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
  opacity: 0.6;
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
  opacity: 0.8;
}

.graph-container {
  flex: 1;
  min-height: 300px;
  background: var(--n-action-color);
  border-radius: 4px;
  overflow: hidden;
  position: relative;
}

.explanation-box {
  margin-top: 15px;
  padding: 10px;
  background: var(--n-action-color);
  border-radius: 4px;
  max-height: 100px;
  overflow-y: auto;
  flex-shrink: 0;
}

.explanation-text {
  font-size: 13px;
  white-space: pre-wrap;
}

/* 事实选择对话框 */
.dialog-section-title {
  font-weight: bold;
  margin-bottom: 10px;
}

.fact-select-list {
  height: 300px;
  overflow-y: auto;
  border: 1px solid var(--n-border-color);
  border-radius: 4px;
  padding: 10px;
}

.fact-select-list.selected {
  background: var(--n-action-color);
}

.fact-select-item {
  padding: 8px 12px;
  margin: 4px 0;
  background: var(--n-card-color);
  border: 1px solid var(--n-border-color);
  border-radius: 4px;
  cursor: pointer;
  transition: all 0.2s;
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

.viz-card.fullscreen :deep(.n-card__content) {
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
  background: var(--n-color-primary);
  color: #fff;
}

.fact-select-item.derived {
  opacity: 0.7;
  cursor: not-allowed;
  font-style: italic;
}
</style>
