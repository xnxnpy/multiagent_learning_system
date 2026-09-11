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
    'Supervisor · 分析画像与阶段',
    '文档生成 · 个性化讲解',
    '题库生成 · 摸底练习',
    '质量评估 · 守门员审核',
    '资源入库 · 双写完成',
  ]

  async function generateStageResources(stageId: number, _force = false) {
    stageGenerating.value = true
    appStore.addTask({ id: 'workflow', type: 'workflow', label: 'Supervisor 正在编排本阶段资源', progress: 5, status: 'running' })

    // 后端为同步 HTTP，无法推送节点级进度；用轮询文案模拟 Supervisor 思考过程
    let simIdx = 0
    const simTimer = setInterval(() => {
      if (simIdx < RESOURCE_STEP_NAMES.length - 1) {
        simIdx++
        const pct = Math.min(5 + Math.round((simIdx / RESOURCE_STEP_NAMES.length) * 90), 95)
        appStore.updateTask('workflow', { progress: pct, detail: RESOURCE_STEP_NAMES[simIdx] })
      }
    }, 8000)

    try {
      const res: any = await request.post('/v1/student/learn/stage/generate', {
        stage_id: stageId,
      }, { timeout: 600000 })
      stageResources.value = res.generated || {}

      // 同步更新 resourceStore，确保 Resources 页面能看到数据
      const { useResourceStore } = await import('@/stores/resourceStore')
      const resourceStore = useResourceStore()
      await resourceStore.loadForStage(
        learningPath.value?.stages?.findIndex((s: any) => s.stage_id === stageId) ?? 0,
        learningPath.value?.stages
      )

      appStore.updateTask('workflow', { progress: 100, detail: '完成' })
      return res
    } catch (e) {
      appStore.failTask('workflow', '资源生成失败')
      throw e
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
