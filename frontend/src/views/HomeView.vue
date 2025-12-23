<template>
  <div class="home-view">
    <n-grid :x-gap="20" :cols="3">
      <n-grid-item>
        <n-card class="stat-card">
          <template #header>
            <div class="stat-header">
              <n-icon size="24" color="#409eff" :component="LibraryOutline" />
              <span>知识库规则</span>
            </div>
          </template>
          <div class="stat-value">
            <n-number-animation
              :from="0"
              :to="stats.rulesCount"
            />
          </div>
          <div class="stat-desc">条规则</div>
        </n-card>
      </n-grid-item>

      <n-grid-item>
        <n-card class="stat-card">
          <template #header>
            <div class="stat-header">
              <n-icon
                size="24"
                color="#67c23a"
                :component="DocumentTextOutline"
              />
              <span>原子命题</span>
            </div>
          </template>
          <div class="stat-value">
            <n-number-animation
              :from="0"
              :to="stats.atomsCount"
            />
          </div>
          <div class="stat-desc">个事实</div>
        </n-card>
      </n-grid-item>

      <n-grid-item>
        <n-card class="stat-card">
          <template #header>
            <div class="stat-header">
              <n-icon
                size="24"
                color="#e6a23c"
                :component="TrendingUpOutline"
              />
              <span>推理历史</span>
            </div>
          </template>
          <div class="stat-value">
            <n-number-animation
              :from="0"
              :to="stats.historyCount"
            />
          </div>
          <div class="stat-desc">次推理</div>
        </n-card>
      </n-grid-item>
    </n-grid>

    <n-grid :x-gap="20" :cols="24" style="margin-top: 20px">
      <n-grid-item :span="16">
        <n-card class="info-card" title="系统介绍">
          <div class="intro-content">
            <h3>基于产生式知识表示的专家系统</h3>
            <p>
              本系统是一个基于规则的专家系统，使用产生式规则进行知识表示和推理。
            </p>

            <h4>主要功能：</h4>
            <ul>
              <li>
                <strong>正向推理</strong
                >：从已知事实出发，逐步应用规则推导出新的结论
              </li>
              <li>
                <strong>反向推理</strong
                >：从目标结论出发，反向寻找需要满足的条件
              </li>
              <li>
                <strong>冲突消解</strong
                >：当多条规则可应用时，选择优先级最高的规则
              </li>
              <li><strong>推理可视化</strong>：通过图形展示推理过程和路径</li>
              <li>
                <strong>知识库管理</strong>：支持规则的增删改查（需管理员权限）
              </li>
              <li><strong>历史记录</strong>：保存每次推理的结果，方便回顾</li>
            </ul>

            <h4>使用说明：</h4>
            <ol>
              <li>进入"推理系统"页面</li>
              <li>在左侧选择或添加已知事实</li>
              <li>点击"正向推理"按钮进行推理</li>
              <li>或选择目标结论进行"反向推理"</li>
              <li>查看推理结果和可视化图形</li>
            </ol>
          </div>
        </n-card>
      </n-grid-item>

      <n-grid-item :span="8">
        <n-card class="info-card" title="快速开始">
          <div class="quick-actions">
            <n-button
              type="primary"
              size="large"
              @click="$router.push('/inference')"
              style="width: 100%; margin-bottom: 15px"
            >
              <template #icon>
                <n-icon :component="GitNetworkOutline" />
              </template>
              开始推理
            </n-button>

            <n-button
              size="large"
              @click="$router.push('/history')"
              style="width: 100%; margin-bottom: 15px"
            >
              <template #icon>
                <n-icon :component="TimeOutline" />
              </template>
              查看历史
            </n-button>

            <n-button
              v-if="userStore.isAdmin"
              size="large"
              @click="$router.push('/admin')"
              style="width: 100%"
            >
              <template #icon>
                <n-icon :component="SettingsOutline" />
              </template>
              管理设置
            </n-button>
          </div>
        </n-card>

        <n-card class="info-card" style="margin-top: 20px" title="示例规则">
          <div class="example-rules">
            <div
              class="rule-item"
              v-for="(rule, index) in exampleRules"
              :key="index"
            >
              <n-tag type="info" size="small">R{{ index }}</n-tag>
              <span
                >{{ rule.premises.join(" + ") }} → {{ rule.conclusion }}</span
              >
            </div>
          </div>
        </n-card>
      </n-grid-item>
    </n-grid>
  </div>
</template>

<script setup>
import { ref, onMounted } from "vue";
import { useUserStore } from "../stores/user";
import api from "../api";
import {
  LibraryOutline,
  DocumentTextOutline,
  TrendingUpOutline,
  GitNetworkOutline,
  TimeOutline,
  SettingsOutline,
} from "@vicons/ionicons5";

const userStore = useUserStore();

const stats = ref({
  rulesCount: 0,
  atomsCount: 0,
  historyCount: 0,
});

const exampleRules = ref([]);

onMounted(async () => {
  try {
    const rulesRes = await api.getRules();
    stats.value.rulesCount = rulesRes.rules?.length || 0;
    exampleRules.value = rulesRes.rules?.slice(0, 5) || [];

    const atomsRes = await api.getAtoms();
    stats.value.atomsCount = atomsRes.atoms?.length || 0;

    const historyRes = await api.getHistory(1, 1);
    stats.value.historyCount = historyRes.total || 0;
  } catch (e) {
    console.error("加载统计信息失败", e);
  }
});
</script>

<style scoped>
.home-view {
  max-width: 1400px;
  margin: 0 auto;
}

.stat-card {
  text-align: center;
}

.stat-header {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
}

.stat-value {
  font-size: 48px;
  font-weight: bold;
  margin: 20px 0 10px;
}

.stat-desc {
  font-size: 14px;
  opacity: 0.8;
}

.intro-content {
  line-height: 1.8;
}

.intro-content h3 {
  margin-bottom: 15px;
}

.intro-content h4 {
  margin: 20px 0 10px;
}

.intro-content ul,
.intro-content ol {
  padding-left: 20px;
}

.intro-content li {
  margin-bottom: 8px;
}

.quick-actions {
  padding: 10px 0;
}

.example-rules {
  max-height: 200px;
  overflow-y: auto;
}

.rule-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 0;
  border-bottom: 1px solid rgba(255, 255, 255, 0.09);
  font-size: 13px;
}

.rule-item:last-child {
  border-bottom: none;
}
</style>
