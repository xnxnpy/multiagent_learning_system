<template>
  <div class="learning-path-page">
    <!-- Header -->
    <div class="page-header">
      <h2 class="page-title">学习路径</h2>
      <div class="header-actions">
        <el-button type="primary" :loading="pathStore.generating" @click="handleGenerate">
          <el-icon><Lightning /></el-icon> 生成学习路径
        </el-button>
        <el-button @click="handleRefresh" :loading="loading">
          <el-icon><Refresh /></el-icon> 刷新
        </el-button>
      </div>
    </div>

    <!-- No path state -->
    <el-empty v-if="!pathStore.learningPath && !loading" description="暂无学习路径">
      <el-button type="primary" @click="handleGenerate">生成学习路径</el-button>
    </el-empty>

    <!-- Path content -->
    <template v-if="pathStore.learningPath">
      <!-- Steps overview -->
      <el-card class="path-card" shadow="never">
        <template #header>
          <div class="card-header">
            <span>{{ pathStore.learningPath.title }}</span>
            <el-tag :type="allCompleted ? 'success' : 'primary'">
              {{ allCompleted ? '全部完成' : `阶段 ${pathStore.currentStage + 1}/${totalStages}` }}
            </el-tag>
          </div>
        </template>
        <el-steps :active="pathStore.currentStage" finish-status="success" align-center>
          <el-step
            v-for="(stage, i) in pathStore.learningPath.stages"
            :key="i"
            :title="stage.title"
            :description="`${stage.estimated_hours || '?'} 小时`"
          />
        </el-steps>
      </el-card>

      <!-- Current stage detail -->
      <el-card v-if="currentStageData" class="stage-card" shadow="never">
        <template #header>
          <div class="card-header">
            <span>当前阶段：{{ currentStageData.title }}</span>
            <div class="stage-actions">
              <el-button type="primary" @click="handleStartStage">
                <el-icon><VideoPlay /></el-icon> 开始学习本阶段
              </el-button>
              <el-button
                type="warning" plain
                :loading="pathStore.stageGenerating"
                @click="handleGenerateStageResources"
              >
                <el-icon><MagicStick /></el-icon> 生成本阶段资源
              </el-button>
              <el-button v-if="!isCurrentStageCompleted && !allCompleted" @click="handleCompleteStage" type="success" plain>
                <el-icon><CircleCheck /></el-icon> 完成本阶段
              </el-button>
              <el-tag v-else-if="isCurrentStageCompleted" type="success">已完成</el-tag>
            </div>
          </div>
        </template>

        <el-descriptions :column="2" border>
          <el-descriptions-item label="阶段描述">{{ currentStageData.description || '暂无描述' }}</el-descriptions-item>
          <el-descriptions-item label="预计时长">{{ currentStageData.estimated_hours || '?' }} 小时</el-descriptions-item>
        </el-descriptions>

        <div v-if="currentStageData.knowledge_points?.length" class="kp-section">
          <h4>知识点：</h4>
          <div class="kp-tags">
            <el-tag v-for="kp in currentStageData.knowledge_points" :key="kp.id || kp" type="primary" effect="plain">{{ kp.name || kp }}</el-tag>
          </div>
        </div>

        <div v-if="currentStageData.recommended_resource_types?.length" class="rt-section">
          <h4>推荐资源类型：</h4>
          <div class="rt-tags">
            <el-tag v-for="rt in currentStageData.recommended_resource_types" :key="rt" :type="resourceTagType(rt)">{{ resourceText(rt) }}</el-tag>
          </div>
        </div>

        <!-- 资源生成中提示 -->
        <div v-if="pathStore.stageGenerating" class="stage-generating">
          <el-icon class="is-loading" :size="18"><Loading /></el-icon>
          <span>正在生成本阶段学习资源，请稍候...</span>
        </div>
      </el-card>

      <!-- 知识图谱（Neo4j） -->
      <el-card class="kg-card" shadow="never">
        <template #header>
          <div class="card-header">
            <span>知识图谱</span>
            <el-button
              type="primary" size="small"
              :loading="kgLoading"
              @click="handleGenerateKnowledgeGraph"
            >
              <el-icon><MagicStick /></el-icon>
              {{ knowledgeGraphData ? '重新生成' : '生成知识图谱' }}
            </el-button>
          </div>
        </template>
        <KnowledgeGraph v-if="knowledgeGraphData" :graphData="knowledgeGraphData" />
        <el-empty v-else-if="!kgLoading" description="暂无知识图谱，点击上方按钮生成" :image-size="80" />
        <div v-else class="kg-loading">
          <el-icon class="is-loading" :size="18"><Loading /></el-icon>
          <span>正在生成知识图谱...</span>
        </div>
      </el-card>

      <!-- All stages timeline -->
      <el-card class="timeline-card" shadow="never">
        <template #header><span>学习进度</span></template>
        <el-timeline>
          <el-timeline-item
            v-for="(stage, i) in pathStore.learningPath.stages"
            :key="i"
            :type="isStageCompleted(stage) ? 'success' : i === pathStore.currentStage ? 'primary' : 'info'"
            :hollow="!isStageCompleted(stage) && i !== pathStore.currentStage"
            :class="{ 'clickable-stage': isStageCompleted(stage) || i === pathStore.currentStage }"
            @click="handleStageClick(i)"
          >
            <div class="timeline-content">
              <div class="timeline-header">
                <span :class="{ 'font-bold': i === pathStore.currentStage }">{{ stage.title }}</span>
                <el-tag v-if="isStageCompleted(stage)" type="success" size="small">已完成</el-tag>
                <el-tag v-else-if="i === pathStore.currentStage" type="primary" size="small">进行中</el-tag>
                <el-tag v-else type="info" size="small">未开始</el-tag>
                <el-tag v-if="isStageCompleted(stage)" type="info" size="small" effect="plain">可复习</el-tag>
              </div>
              <p class="timeline-desc">{{ stage.description || '' }}</p>
              <div v-if="stage.knowledge_points?.length" class="timeline-kps">
                <el-tag v-for="kp in stage.knowledge_points" :key="kp.id || kp" size="small" effect="plain">{{ kp.name || kp }}</el-tag>
              </div>
            </div>
          </el-timeline-item>
        </el-timeline>
      </el-card>
    </template>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useLearningPathStore } from '@/stores/learningPathStore'
import KnowledgeGraph from '@/components/KnowledgeGraph.vue'
import { Loading, MagicStick } from '@element-plus/icons-vue'
import request from '@/utils/axios'
import { useLearningTracker } from '@/composables/useLearningTracker'

const router = useRouter()
const pathStore = useLearningPathStore()

// 学习行为追踪
useLearningTracker({ resourceType: 'learning_path' })
const loading = ref(false)
const autoGenerating = ref(false)
const knowledgeGraphData = ref<any>(null)
const kgLoading = ref(false)

const totalStages = computed(() => pathStore.learningPath?.stages?.length || 0)
const allCompleted = computed(() => pathStore.completedStages.length >= totalStages.value && totalStages.value > 0)
const currentStageData = computed(() => pathStore.learningPath?.stages?.[pathStore.currentStage])
const isCurrentStageCompleted = computed(() => {
  const stageId = currentStageData.value?.stage_id
  return stageId !== undefined && pathStore.completedStages.includes(stageId)
})

function isStageCompleted(stage: any): boolean {
  return pathStore.completedStages.includes(stage.stage_id)
}

function resourceTagType(rt: string) {
  const map: Record<string, string> = { document: '', video: 'warning', code: 'success', mindmap: 'info' }
  return (map[rt] || 'info') as any
}

function resourceText(rt: string) {
  const map: Record<string, string> = { document: '文档', video: '视频', code: '代码', mindmap: '思维导图', question: '练习题' }
  return map[rt] || rt
}

async function handleGenerate() {
  try {
    await pathStore.generatePath()
    ElMessage.success('学习路径生成完成！')
  } catch (err: any) {
    ElMessage.error('生成失败：' + (err?.message || '未知错误'))
  }
}

async function handleRefresh() {
  loading.value = true
  try {
    await pathStore.fetchPath()
  } finally {
    loading.value = false
  }
}

function handleStageClick(index: number) {
  const stage = pathStore.learningPath?.stages?.[index]
  if (!stage) return
  // 已完成阶段或当前阶段：跳转到学习资源页查看
  if (isStageCompleted(stage) || index === pathStore.currentStage) {
    pathStore.setCurrentStage(index)
    router.push({ path: '/student/resources', query: { stage: String(index) } })
  }
}

function handleStartStage() {
  router.push({ path: '/student/resources', query: { stage: String(pathStore.currentStage) } })
}

async function handleCompleteStage() {
  try {
    await ElMessageBox.confirm('确认完成本阶段？将进入下一阶段。', '完成阶段', {
      confirmButtonText: '确认完成',
      cancelButtonText: '取消',
      type: 'success',
    })
    await pathStore.completeStage()
    ElMessage.success(`已进入阶段 ${pathStore.currentStage + 1}`)
  } catch { /* cancelled */ }
}

async function handleGenerateStageResources() {
  const stageId = currentStageData.value?.stage_id
  if (stageId === undefined) return
  try {
    await pathStore.generateStageResources(stageId, true)
    ElMessage.success('本阶段资源生成完成！')
  } catch {
    ElMessage.error('资源生成失败，请重试')
  }
}

// ── 知识图谱 ──

async function loadKnowledgeGraph() {
  kgLoading.value = true
  knowledgeGraphData.value = null
  try {
    // 知识图谱为全局数据，stage_id=0 是全局图谱的标识
    const data = await request.get('/v1/student/knowledge-graph?stage_id=0')
    knowledgeGraphData.value = (data.nodes?.length > 0) ? data : null
  } catch {
    knowledgeGraphData.value = null
  } finally {
    kgLoading.value = false
  }
}

async function handleGenerateKnowledgeGraph() {
  kgLoading.value = true
  try {
    // 知识图谱为全局，用学习路径标题作为主题
    const topic = pathStore.learningPath?.title || '学习路径知识图谱'
    const data = await request.post('/v1/student/knowledge-graph/generate', {
      topic,
    })
    knowledgeGraphData.value = data
    ElMessage.success('知识图谱生成完成！')
  } catch {
    ElMessage.error('知识图谱生成失败')
  } finally {
    kgLoading.value = false
  }
}

onMounted(async () => {
  loading.value = true
  try {
    await pathStore.fetchPath()

    // 加载当前阶段资源
    const stageId = currentStageData.value?.stage_id
    if (stageId !== undefined) {
      await pathStore.fetchStageResources(stageId)
    }

    // 加载知识图谱
    await loadKnowledgeGraph()

    // 如果没有路径，提示用户去完成画像（由工作流统一生成路径+资源）
    if (!pathStore.learningPath) {
      ElMessage.warning('学习路径尚未生成，请先在「学习画像」页面完成画像采集，系统将自动生成学习路径')
    }
  } finally {
    loading.value = false
  }
})

// 切换阶段时加载对应资源
watch(() => pathStore.currentStage, async () => {
  const stageId = currentStageData.value?.stage_id
  if (stageId !== undefined) {
    await pathStore.fetchStageResources(stageId)
  }
  // 切换阶段时重新加载该阶段的知识图谱
  await loadKnowledgeGraph()
})
</script>

<style scoped>
.learning-path-page { max-width: 1400px; }
.page-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: var(--space-section-gap, 24px);
}
.page-title {
  font-size: var(--text-xl);
  font-weight: 700;
  color: var(--color-text-primary);
}
.header-actions { display: flex; gap: 12px; }

.path-card, .stage-card, .timeline-card, .kg-card {
  margin-bottom: var(--space-card-gap, 20px);
  border-radius: var(--radius-lg);
  background: var(--color-bg-card);
  border: 1px solid var(--color-border-light);
}

.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-weight: 600;
  color: var(--color-text-primary);
}

.stage-actions { display: flex; gap: 8px; }

.kp-section, .rt-section { margin-top: 16px; }
.kp-section h4, .rt-section h4 {
  font-size: 13px;
  color: var(--color-text-secondary);
  margin-bottom: 8px;
}
.kp-tags, .rt-tags { display: flex; flex-wrap: wrap; gap: 8px; }

.timeline-content { padding-bottom: 8px; }
.clickable-stage { cursor: pointer; }
.clickable-stage:hover :deep(.el-timeline-item__wrapper) {
  background: var(--color-bg-page);
  border-radius: var(--radius-md);
}
.timeline-header {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 4px;
}
.timeline-desc {
  color: var(--color-text-secondary);
  font-size: 13px;
  margin-bottom: 6px;
}
.timeline-kps { display: flex; flex-wrap: wrap; gap: 6px; }
.font-bold { font-weight: 700; }

.kg-loading, .stage-generating {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 24px;
  justify-content: center;
  color: var(--color-text-secondary);
}
</style>
