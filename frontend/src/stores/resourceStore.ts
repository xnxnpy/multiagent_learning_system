import { defineStore } from 'pinia'
import { ref, reactive } from 'vue'
import type { ResourceBundle, CodeResult, WorkflowState } from '@/types'
import request from '@/utils/axios'
import { createWorkflowWebSocket } from '@/utils/websocket'

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
  const generating = ref(false)
  const currentTopic = ref('')
  const currentStageIndex = ref<number | null>(null)
  const workflowSessionId = ref<string | null>(null)
  const codeResult = ref<CodeResult | null>(null)
  const workflowState = ref<WorkflowState | null>(null)

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

  function assignResults(docRes: any, qRes: any, codeRes: any, mmRes: any, kgRes: any) {
    if (docRes) resources.document = docRes
    if (qRes) resources.questions = qRes
    if (codeRes) resources.code = codeRes
    if (mmRes) {
      resources.mindmap = mmRes.mindmap
      resources.mindmap_html = mmRes.mindmap_html
      resources.mindmap_markdown = mmRes.mindmap_markdown || null
    }
    if (kgRes) resources.knowledge_graph = kgRes
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
        const kp = kps[0]
        currentTopic.value = typeof kp === 'string' ? kp : (kp.name || kp)
      }
    }

    await loadFromDB(undefined, stageId)
  }

  // ── Workflow ───────────────────────────────────────

  async function startWorkflow() {
    const res = await request.post('/v1/student/learn/start', {})
    workflowSessionId.value = res.session_id
    return res.session_id
  }

  function runWorkflow(
    sessionId: string,
    callbacks?: {
      onProgress?: (state: WorkflowState) => void
      onComplete?: () => void
      onError?: (err: Error) => void
    }
  ) {
    generating.value = true
    const token = localStorage.getItem('token') || ''
    const ws = createWorkflowWebSocket(token)
    let finished = false

    ws.on('message', async (data: any) => {
      switch (data.type) {
        case 'step':
          workflowState.value = data.data as WorkflowState
          callbacks?.onProgress?.(data.data as WorkflowState)
          break
        case 'complete':
          if (finished) break
          finished = true
          ws.close()
          await loadFromDB()
          generating.value = false
          callbacks?.onComplete?.()
          break
        case 'error':
          if (finished) break
          finished = true
          ws.close()
          generating.value = false
          callbacks?.onError?.(new Error(data.message))
          break
      }
    })

    ws.on('error', () => {
      if (!finished) {
        finished = true
        generating.value = false
        callbacks?.onError?.(new Error('WebSocket 连接失败'))
      }
    })

    ws.on('close', () => {
      if (!finished) {
        finished = true
        generating.value = false
      }
    })

    ws.connect(token).then(() => {
      ws.send({ type: 'start', session_id: sessionId })
    }).catch(() => {
      generating.value = false
      callbacks?.onError?.(new Error('WebSocket 连接失败'))
    })
  }

  // ── Actions ────────────────────────────────────────

  async function submitAnswers(answers: Record<number, string>, topic?: string) {
    const submissions = Object.entries(answers)
      .filter(([, v]) => v !== undefined && v !== '')
      .map(([questionId, answer]) =>
        request.post('/v1/student/question/submit', {
          question_id: parseInt(questionId),
          answer: String(answer),
          topic: topic || currentTopic.value,
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
    workflowState.value = null
    workflowSessionId.value = null
  }

  return {
    resources,
    loading,
    generating,
    currentTopic,
    currentStageIndex,
    workflowSessionId,
    codeResult,
    workflowState,
    fetchResources,
    loadFromDB,
    loadForStage,
    clearResources,
    startWorkflow,
    runWorkflow,
    submitAnswers,
    runCode,
  }
})
