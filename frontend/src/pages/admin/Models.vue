<template>
  <div class="page-container">
    <div class="page-header">
      <h2 class="page-title">模型管理</h2>
      <el-tag type="info" effect="plain">管理各智能体和任务使用的 AI 模型</el-tag>
    </div>

    <!-- 文本模型配置 - Agent 级别 -->
    <el-card class="page-card" shadow="never">
      <template #header>
        <div class="card-header">
          <div class="card-header-left">
            <h3 class="card-title">智能体文本模型配置</h3>
            <el-tag size="small" type="primary">每个 Agent 使用的对话/生成模型</el-tag>
          </div>
          <el-button type="primary" :loading="saving" @click="saveAgentModels">保存配置</el-button>
        </div>
      </template>

      <el-table :data="agentModelList" stripe>
        <el-table-column prop="agent_name" label="智能体" width="180">
          <template #default="{ row }">
            <span class="agent-name">{{ agentNames[row.agent_name] || row.agent_name }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="model_name" label="当前模型" width="180">
          <template #default="{ row }">
            <el-tag type="primary" effect="plain">{{ row.model_name }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="切换模型">
          <template #default="{ row }">
            <el-select v-model="row.model_key" size="small" style="width: 280px" @change="row.changed = true">
              <el-option-group v-for="(models, provider) in groupedTextModels" :key="provider" :label="provider">
                <el-option v-for="m in models" :key="m.key" :label="`${m.name} (${m.key})`" :value="m.key" />
              </el-option-group>
            </el-select>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="100">
          <template #default="{ row }">
            <el-tag v-if="row.changed" type="warning" size="small">已修改</el-tag>
            <el-tag v-else type="success" size="small">未变更</el-tag>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 图片模型配置 - 任务级别 -->
    <el-card class="page-card" shadow="never" style="margin-top: 24px;">
      <template #header>
        <div class="card-header">
          <div class="card-header-left">
            <h3 class="card-title">图片生成模型配置</h3>
            <el-tag size="small" type="success">不同任务使用不同的图片模型</el-tag>
          </div>
          <el-button type="primary" :loading="saving" @click="saveImageModels">保存配置</el-button>
        </div>
      </template>

      <el-table :data="imageTaskList" stripe>
        <el-table-column prop="task_name" label="任务" width="200">
          <template #default="{ row }">
            <span class="agent-name">{{ imageTaskNames[row.task_name] || row.task_name }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="model_name" label="当前模型" width="180">
          <template #default="{ row }">
            <el-tag type="success" effect="plain">{{ row.model_name }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="切换模型">
          <template #default="{ row }">
            <el-select v-model="row.model_key" size="small" style="width: 280px" @change="row.changed = true">
              <el-option v-for="m in imageModelList" :key="m.key" :label="`${m.name} (${m.key})`" :value="m.key" />
            </el-select>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="100">
          <template #default="{ row }">
            <el-tag v-if="row.changed" type="warning" size="small">已修改</el-tag>
            <el-tag v-else type="success" size="small">未变更</el-tag>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- TTS 音色配置 -->
    <el-card class="page-card" shadow="never">
      <template #header>
        <div class="card-header">
          <div class="card-header-left">
            <h3 class="card-title">TTS 语音音色</h3>
            <el-tag size="small" type="info">PPT 教学视频配音使用的音色</el-tag>
          </div>
        </div>
      </template>

      <el-table :data="ttsVoices" stripe>
        <el-table-column prop="name" label="音色名称" width="160" />
        <el-table-column prop="gender" label="性别" width="80" />
        <el-table-column prop="id" label="音色 ID" width="160">
          <template #default="{ row }">
            <code class="voice-id">{{ row.id }}</code>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="120">
          <template #default="{ row }">
            <el-tag v-if="row.id === currentTtsVoice" type="success" size="small" effect="dark">当前使用</el-tag>
            <el-button v-else type="primary" link size="small" @click="switchTtsVoice(row.id)">切换</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import request from '@/utils/axios'

interface AgentModel {
  agent_name: string
  model_key: string
  model_name: string
  changed?: boolean
}

interface ImageTask {
  task_name: string
  model_key: string
  model_name: string
  changed?: boolean
}

const saving = ref(false)
const agentModelList = ref<AgentModel[]>([])
const imageTaskList = ref<ImageTask[]>([])
const textModels = ref<Record<string, { name: string; provider: string }>>({})
const imageModels = ref<Record<string, { name: string; provider: string; status: string }>>({})
const ttsVoices = ref<{ id: string; name: string; gender: string }[]>([])
const currentTtsVoice = ref('')

const agentNames: Record<string, string> = {
  profile: '画像构建 Agent',
  document: '文档生成 Agent',
  question: '题库生成 Agent',
  code: '代码实操 Agent',
  mindmap: '思维导图 Agent',
  knowledge_graph: '知识图谱 Agent',
  learning_path: '路径规划 Agent',
  evaluation: '学习评估 Agent',
  tutor: '智能辅导 Agent',
  reading_material: '拓展阅读 Agent',
  glossary: '术语词汇 Agent',
  summary: '学习总结 Agent',
  ppt_video: 'PPT 视频 Agent',
  resource_quality: '质量评估 Agent',
}

const imageTaskNames: Record<string, string> = {
  document_illustration: '文档配图',
}

const imageModelList = computed(() =>
  Object.entries(imageModels.value).map(([key, info]) => ({ key, ...info }))
)

const groupedTextModels = computed(() => {
  const groups: Record<string, { key: string; name: string }[]> = {}
  for (const [key, info] of Object.entries(textModels.value)) {
    const label = info.provider === 'xunfei_spark' ? '讯飞星火' : '讯飞 MaaS (Qwen)'
    if (!groups[label]) groups[label] = []
    groups[label].push({ key, name: info.name })
  }
  return groups
})

async function fetchModels() {
  try {
    const res: any = await request.get('/v1/admin/models')
    textModels.value = res.text_models || {}
    imageModels.value = res.image_models || {}

    // Agent 文本模型
    agentModelList.value = Object.entries(res.agent_text_models || {}).map(([name, info]: [string, any]) => ({
      agent_name: name,
      model_key: info.model_key,
      model_name: info.model_name,
      changed: false,
    }))

    // 图片任务模型
    imageTaskList.value = Object.entries(res.image_task_models || {}).map(([task, model_key]) => ({
      task_name: task,
      model_key: model_key as string,
      model_name: imageModels.value[model_key as string]?.name || model_key,
      changed: false,
    }))

    // TTS 音色
    const ttsRes: any = await request.get('/v1/admin/tts/voices')
    ttsVoices.value = ttsRes.voices || []
    currentTtsVoice.value = ttsRes.current_voice || ''
  } catch {
    ElMessage.error('获取模型配置失败')
  }
}

async function saveAgentModels() {
  const changed = agentModelList.value.filter(a => a.changed)
  if (!changed.length) { ElMessage.info('没有变更'); return }

  saving.value = true
  try {
    for (const agent of changed) {
      await request.put(`/v1/admin/models/agent/${agent.agent_name}`, { model_key: agent.model_key })
      agent.changed = false
    }
    ElMessage.success(`已保存 ${changed.length} 个配置`)
  } catch { ElMessage.error('保存失败') }
  finally { saving.value = false }
}

async function saveImageModels() {
  const changed = imageTaskList.value.filter(t => t.changed)
  if (!changed.length) { ElMessage.info('没有变更'); return }

  saving.value = true
  try {
    for (const task of changed) {
      await request.put(`/v1/admin/models/image/${task.task_name}`, { model_key: task.model_key })
      task.changed = false
    }
    ElMessage.success(`已保存 ${changed.length} 个配置`)
  } catch { ElMessage.error('保存失败') }
  finally { saving.value = false }
}

onMounted(() => { fetchModels() })

async function switchTtsVoice(voiceId: string) {
  try {
    await request.put('/v1/admin/tts/voice', { voice: voiceId })
    currentTtsVoice.value = voiceId
    ElMessage.success('音色已切换')
  } catch {
    ElMessage.error('音色切换失败')
  }
}
</script>

<style scoped>
.page-container { max-width: 1200px; }
.page-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 24px; }
.page-title { font-size: 22px; font-weight: 700; color: var(--color-text-primary); }
.card-header { display: flex; align-items: center; justify-content: space-between; }
.card-header-left { display: flex; align-items: center; gap: 12px; }
.card-title { font-size: 16px; font-weight: 600; margin: 0; }
.agent-name { font-weight: 600; color: var(--color-text-primary); }
.page-card { border-radius: var(--radius-lg); box-shadow: var(--shadow-card); }
.voice-id { background: var(--color-bg-page); padding: 2px 6px; border-radius: 4px; font-size: 12px; color: var(--color-text-secondary); }
</style>
