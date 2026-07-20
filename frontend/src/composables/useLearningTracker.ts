import { onMounted, onBeforeUnmount } from 'vue'
import { studentAPI } from '@/api'

// 模块级去重：同一 key 2 秒内不重复发送初始事件
const _recentSends = new Map<string, number>()
const DEDUP_INTERVAL = 2000

/**
 * 学习行为追踪 composable
 * 自动记录页面进入/离开事件和停留时长
 *
 * @example
 * useLearningTracker({ resourceType: 'document', stageId: 1 })
 */
export function useLearningTracker(options: {
  resourceType?: string
  stageId?: number
  autoTrack?: boolean
} = {}) {
  const enterTime = Date.now()
  let totalTime = 0
  let lastResumeTime = enterTime
  let isPaused = false
  let unmountSent = false

  function getDuration(): number {
    if (isPaused) return Math.round(totalTime / 1000)
    return Math.round((totalTime + Date.now() - lastResumeTime) / 1000)
  }

  function trackEvent(eventType: string, extra?: Record<string, any>) {
    try {
      const { duration_seconds, ...metadata } = extra || {}
      studentAPI.trackEvent({
        event_type: eventType,
        resource_type: options.resourceType,
        stage_id: options.stageId,
        duration_seconds,
        metadata,
      })
    } catch { /* fire and forget */ }
  }

  function handleVisibilityChange() {
    if (document.hidden) {
      if (!isPaused) {
        totalTime += Date.now() - lastResumeTime
        isPaused = true
      }
    } else {
      lastResumeTime = Date.now()
      isPaused = false
    }
  }

  if (options.autoTrack !== false) {
    onMounted(() => {
      // 去重：同一 resourceType 2 秒内不重复发送初始事件
      const key = options.resourceType || 'default'
      const now = Date.now()
      if (!_recentSends.has(key) || now - _recentSends.get(key)! > DEDUP_INTERVAL) {
        trackEvent('resource_view', { tab: options.resourceType, start: true })
        _recentSends.set(key, now)
      }
      document.addEventListener('visibilitychange', handleVisibilityChange)
    })

    onBeforeUnmount(() => {
      document.removeEventListener('visibilitychange', handleVisibilityChange)
      // 只发送一次 unmount 事件
      if (!unmountSent) {
        unmountSent = true
        const duration = getDuration()
        if (duration > 2) {
          trackEvent('resource_view', {
            tab: options.resourceType,
            duration_seconds: duration,
            final: true,
          })
        }
      }
    })
  }

  return { trackEvent, getDuration }
}
