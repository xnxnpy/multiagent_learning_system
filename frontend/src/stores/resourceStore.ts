import { defineStore } from 'pinia'
import { ref, reactive } from 'vue'
import type { ResourceBundle, CodeResult } from '@/types'
import request from '@/utils/axios'

const emptyBundle = (): ResourceBundle => ({
  document: null,
  mindmap: null,
  mindmap_html: null,
  mindmap_markdown: null,
  knowledge_graph: null,
  questions: null,
  code: null,
  images: null,
  reading_material: null,
  glossary: null,
  knowledge_link: null,
  summary: null,
  ppt_video: null,
  filteredResources: [],
})

export const useResourceStore = defineStore('resource', () => {
  // ── State ──────────────────────────────────────────

  const resources = reactive<ResourceBundle>(emptyBundle())
  const loading = ref(false)
  const currentTopic = ref('')
  const currentStageIndex = ref<number | null>(null)
  const codeResult = ref<CodeResult | null>(null)

  // ── Load resources from backend (DB → Redis → API) ─

  async function fetchResources(topic?: string, _force = false) {
    // 统一从 DB 读取，资源生成走阶段级端点
    await loadFromDB(topic)
  }

  async function loadFromDB(topic?: string, stageId?: number) {
    if (topic) currentTopic.value = topic

    loading.value = true
    try {
      const url = stageId !== undefined
        ? `/v1/student/resources?stage_id=${stageId}`
        : '/v1/student/resources'
      const data = await request.get(url)
      resources.document = data.document || null
      resources.questions = data.questions || null
      resources.code = data.code || null
      resources.mindmap = data.mindmap || null
      resources.mindmap_html = data.mindmap_html || null
      resources.mindmap_markdown = data.mindmap_markdown || data.mindmap?.mindmap_markdown || null
      resources.knowledge_graph = data.knowledge_graph || null
      resources.reading_material = data.reading_material || null
      resources.glossary = data.glossary || null
      resources.knowledge_link = data.knowledge_link || null
      resources.summary = data.summary || null
      resources.ppt_video = data.ppt_video || null
      resources.filteredResources = data.filtered_resources || []
    } catch {
      // 静默失败，保持当前状态
    } finally {
      loading.value = false
    }
  }

  // ── Stage-aware loading ────────────────────────────

  async function loadForStage(stageIndex: number, stages?: any[]) {
    currentStageIndex.value = stageIndex
    let stageId: number | undefined

    // 确保 stages 可用
    if (!stages || !stages[stageIndex]) {
      // 从 learningPathStore 获取
      const { useLearningPathStore } = await import('@/stores/learningPathStore')
      const lpStore = useLearningPathStore()
      if (!lpStore.learningPath) await lpStore.fetchPath()
      stages = lpStore.learningPath?.stages
    }

    if (stages && stages[stageIndex]) {
      stageId = stages[stageIndex].stage_id
      const kps = stages[stageIndex].knowledge_points
      if (kps && kps.length > 0) {
        // 拼接所有知识点作为 topic（后端会从题目数据中提取具体 knowledge_point）
        currentTopic.value = kps
          .map(kp => typeof kp === 'string' ? kp : (kp.name || kp))
          .filter(name => name)
          .join('、')
      }
    }

    await loadFromDB(undefined, stageId)
  }

  // ── Actions ────────────────────────────────────────

  async function _currentStageId(): Promise<number | undefined> {
    try {
      const { useLearningPathStore } = await import('@/stores/learningPathStore')
      const lp = useLearningPathStore()
      if (!lp.learningPath) await lp.fetchPath()
      const stages = lp.learningPath?.stages
      const idx = currentStageIndex.value ?? lp.currentStage ?? 0
      return stages?.[idx]?.stage_id
    } catch {
      return undefined
    }
  }

  async function submitAnswers(answers: Record<number, string>, topic?: string) {
    const stageId = await _currentStageId()
    const submissions = Object.entries(answers)
      .filter(([, v]) => v !== undefined && v !== '')
      .map(([questionId, answer]) =>
        request.post('/v1/student/question/submit', {
          question_id: parseInt(questionId),
          answer: String(answer),
          topic: topic || currentTopic.value,
          ...(stageId !== undefined ? { stage_id: stageId } : {}),
        }).catch(() => null)
      )
    return Promise.all(submissions)
  }

  async function runCode(code: string, timeout = 30): Promise<CodeResult> {
    const res = await request.post('/v1/student/code/run', { code, timeout })
    codeResult.value = res
    return res
  }

  function clearResources() {
    Object.assign(resources, emptyBundle())
    codeResult.value = null
  }

  return {
    resources,
    loading,
    currentTopic,
    currentStageIndex,
    codeResult,
    fetchResources,
    loadFromDB,
    loadForStage,
    clearResources,
    submitAnswers,
    runCode,
  }
})
