import { defineStore } from 'pinia'
import { ref } from 'vue'
import type { LearningPath } from '@/types'
import request from '@/utils/axios'
import { createWorkflowWebSocket } from '@/utils/websocket'
import { useAppStore } from '@/stores/appStore'

const STAGE_KEY = 'learning_path_current_stage'

export const useLearningPathStore = defineStore('learningPath', () => {
  const appStore = useAppStore()
  const learningPath = ref<LearningPath | null>(null)
  const currentStage = ref(parseInt(localStorage.getItem(STAGE_KEY) || '0', 10))
  const generating = ref(false)
  const workflowState = ref<any>(null)
  const completedStages = ref<number[]>([])
  const stageResources = ref<Record<string, any>>({})
  const stageGenerating = ref(false)

  async function fetchPath() {
    try {
      const data = await request.get('/v1/student/learning-path')
      if (data) {
        learningPath.value = data
        completedStages.value = data.completed_stages || []
        const stages = data.stages || []
        if (stages.length > 0) {
          // 找到最后一个已完成的阶段的数组索引，当前阶段 = 下一个
          let lastCompletedIndex = -1
          for (let i = 0; i < stages.length; i++) {
            if (completedStages.value.includes(stages[i].stage_id)) {
              lastCompletedIndex = i
            }
          }
          const nextStage = Math.min(lastCompletedIndex + 1, stages.length - 1)
          setCurrentStage(nextStage)
        }
      }
      return data
    } catch {
      return null
    }
  }

  function generatePath(): Promise<void> {
    return new Promise(async (resolve, reject) => {
      generating.value = true
      appStore.addTask({ id: 'workflow', type: 'workflow', label: '生成学习路径', progress: 0, status: 'running' })
      try {
        const startRes: any = await request.post('/v1/student/learn/start')
        const sessionId = startRes.session_id
        const token = localStorage.getItem('token') || ''

        const ws = createWorkflowWebSocket(token)
        let finished = false

        ws.on('message', async (data: any) => {
          switch (data.type) {
            case 'step':
              workflowState.value = data.data
              // 喂进度给 appStore
              const detail = data.data.current_step || data.data.sub_step || ''
              const progress = Math.round((data.data.progress || 0) * 100)
              appStore.updateTask('workflow', { progress, detail })
              break
            case 'complete':
              if (finished) break
              finished = true
              appStore.updateTask('workflow', { progress: 100, detail: '完成' })
              ws.close()
              await fetchPath()
              setCurrentStage(0)
              generating.value = false
              setTimeout(() => appStore.completeTask('workflow'), 1500)
              resolve()
              break
            case 'error':
              if (finished) break
              finished = true
              ws.close()
              generating.value = false
              appStore.failTask('workflow', data.message)
              reject(new Error(data.message))
              break
          }
        })

        ws.on('error', () => {
          if (!finished) {
            finished = true
            generating.value = false
            reject(new Error('WebSocket 连接失败'))
          }
        })

        ws.on('close', () => {
          if (!finished) {
            finished = true
            generating.value = false
          }
        })

        await ws.connect(token)
        ws.send({ type: 'start', session_id: sessionId })
      } catch (e) {
        generating.value = false
        reject(e)
      }
    })
  }

  function setCurrentStage(index: number) {
    currentStage.value = index
    localStorage.setItem(STAGE_KEY, String(index))
  }

  async function completeStage() {
    if (!learningPath.value) return
    const stageId = learningPath.value.stages[currentStage.value]?.stage_id
    if (stageId === undefined) return

    // 调后端 API 持久化，返回最新的 completed_stages
    const res: any = await request.post('/v1/student/learn/stage/complete', { stage_id: stageId })

    // 直接用返回的 completed_stages 更新本地状态（不依赖 fetchPath，避免竞态）
    if (res.completed_stages) {
      completedStages.value = res.completed_stages
      learningPath.value.completed_stages = res.completed_stages

      // 计算下一个未完成阶段
      const stages = learningPath.value.stages || []
      let lastCompletedIndex = -1
      for (let i = 0; i < stages.length; i++) {
        if (completedStages.value.includes(stages[i].stage_id)) {
          lastCompletedIndex = i
        }
      }
      const nextStage = Math.min(lastCompletedIndex + 1, stages.length - 1)
      setCurrentStage(nextStage)
    }
  }

  const RESOURCE_STEP_NAMES = [
    '文档生成 Agent · 生成学习文档',
    '思维导图 Agent · 生成思维导图',
    '题库生成 Agent · 生成练习题目',
    '代码示例 Agent · 生成代码示例',
    '视频脚本 Agent · 生成教学视频脚本',
    '拓展阅读 Agent · 生成阅读材料',
    '术语词汇 Agent · 生成词汇卡片',
    '知识关联 Agent · 生成关联图',
    '学习总结 Agent · 生成总结报告',
  ]

  async function generateStageResources(stageId: number, force = false) {
    stageGenerating.value = true
    appStore.addTask({ id: 'workflow', type: 'workflow', label: '生成本阶段资源', progress: 0, status: 'running' })
    // 模拟子步骤进度（后端是同步HTTP，无法推送实时进度）
    let simIdx = 0
    const totalSteps = RESOURCE_STEP_NAMES.length
    const simTimer = setInterval(() => {
      if (simIdx < totalSteps - 1) {
        simIdx++
        const pct = Math.round((simIdx / totalSteps) * 100)
        appStore.updateTask('workflow', { progress: pct, detail: RESOURCE_STEP_NAMES[simIdx] })
      }
    }, 2000)
    try {
      const res: any = await request.post('/v1/student/learn/stage/generate', {
        stage_id: stageId,
        force,
      })
      stageResources.value = res.generated || {}

      // 同步更新 resourceStore，确保 Resources 页面能看到数据
      const { useResourceStore } = await import('@/stores/resourceStore')
      const resourceStore = useResourceStore()
      await resourceStore.loadForStage(
        learningPath.value?.stages?.findIndex((s: any) => s.stage_id === stageId) ?? 0,
        learningPath.value?.stages
      )

      appStore.updateTask('workflow', { progress: 100, detail: '完成' })
      return res.generated
    } finally {
      clearInterval(simTimer)
      stageGenerating.value = false
      setTimeout(() => appStore.completeTask('workflow'), 1500)
    }
  }

  async function fetchStageResources(stageId: number) {
    try {
      const res: any = await request.get(`/v1/student/learn/stage/resources/${stageId}`)
      stageResources.value = res.resources || {}
      // 不再自动触发生成 —— 只读取，生成由用户主动触发或工作流触发
    } catch {
      stageResources.value = {}
    }
  }

  function getStageTopic(stageIndex?: number): string {
    const idx = stageIndex ?? currentStage.value
    if (!learningPath.value?.stages?.[idx]) return ''
    const kps = learningPath.value.stages[idx].knowledge_points
    return kps?.[0] || ''
  }

  return {
    learningPath,
    currentStage,
    generating,
    workflowState,
    completedStages,
    stageResources,
    stageGenerating,
    fetchPath,
    generatePath,
    setCurrentStage,
    completeStage,
    generateStageResources,
    fetchStageResources,
    getStageTopic,
  }
})
