import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

export interface BackgroundTask {
  id: string
  type: 'workflow' | 'stage_generation' | 'resource_generation'
  label: string
  progress: number
  status: 'running' | 'completed' | 'failed'
  detail?: string
}

export const useAppStore = defineStore('app', () => {
  const tasks = ref<BackgroundTask[]>([])
  const expanded = ref(false)

  const activeTasks = computed(() => tasks.value.filter(t => t.status === 'running'))
  const activeCount = computed(() => activeTasks.value.length)

  function addTask(task: BackgroundTask) {
    const existing = tasks.value.find(t => t.id === task.id)
    if (existing) {
      Object.assign(existing, task)
    } else {
      tasks.value.push({ ...task })
    }
  }

  function updateTask(id: string, updates: Partial<BackgroundTask>) {
    const task = tasks.value.find(t => t.id === id)
    if (task) Object.assign(task, updates)
  }

  function completeTask(id: string) {
    const task = tasks.value.find(t => t.id === id)
    if (task) {
      task.status = 'completed'
      task.progress = 100
      setTimeout(() => {
        tasks.value = tasks.value.filter(t => t.id !== id)
      }, 2000)
    }
  }

  function failTask(id: string, detail?: string) {
    const task = tasks.value.find(t => t.id === id)
    if (task) {
      task.status = 'failed'
      task.detail = detail || '失败'
      setTimeout(() => {
        tasks.value = tasks.value.filter(t => t.id !== id)
      }, 3000)
    }
  }

  function toggleExpand() {
    expanded.value = !expanded.value
  }

  return {
    tasks,
    expanded,
    activeTasks,
    activeCount,
    addTask,
    updateTask,
    completeTask,
    failTask,
    toggleExpand,
  }
})
