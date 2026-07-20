import { defineStore } from 'pinia'
import { ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { tutorAPI } from '@/api'
import type { ChatMsg, SessionItem } from '@/types'
import { createTutorWebSocket } from '@/utils/websocket'
import type WebSocketClient from '@/utils/websocket'

const WELCOME_MSG = '您好！我是您的智能学习辅导助手。请随时向我提问！'
const now = () => new Date().toLocaleTimeString()

export const useTutorStore = defineStore('tutor', () => {
  // ── State ──────────────────────────────────────────────

  const messages = ref<ChatMsg[]>([
    { role: 'assistant', content: WELCOME_MSG, time: now() },
  ])
  const inputText = ref('')
  const loading = ref(false)
  const streaming = ref(false)
  const sessionId = ref<string | null>(null)
  const sessions = ref<SessionItem[]>([])
  const unreadCount = ref(0)
  const isFloatingOpen = ref(false)

  // ── Internal (non-reactive) ────────────────────────────

  let wsClient: WebSocketClient | null = null
  let pendingMessage: object | null = null

  // ── Actions ────────────────────────────────────────────

  async function loadSessions() {
    try {
      const res: any = await tutorAPI.getSessions()
      sessions.value = (res.sessions || []).map((s: any) => ({
        id: s.session_id,
        title: s.preview || '新对话',
        updated_at: s.updated_at || '',
      }))
    } catch {
      sessions.value = []
    }
  }

  async function resumeLastSession() {
    // 加载会话列表，如果有历史会话则恢复最近一个
    await loadSessions()
    if (sessions.value.length > 0 && !sessionId.value) {
      const latest = sessions.value[0]
      await switchSession(latest.id)
    }
  }

  function createNewSession() {
    sessionId.value = null
    messages.value = [{ role: 'assistant', content: WELCOME_MSG, time: now() }]
    wsClient?.close()
    wsClient = null
  }

  async function switchSession(id: string) {
    if (id === sessionId.value) return
    sessionId.value = id
    wsClient?.close()
    wsClient = null
    messages.value = [{ role: 'assistant', content: WELCOME_MSG, time: now() }]
    try {
      const res: any = await tutorAPI.getHistory(id)
      const msgs = res?.messages
      if (msgs?.length) {
        messages.value = msgs.map((m: any) => ({
          role: m.role as 'user' | 'assistant',
          content: m.content,
          time: '',
        }))
      }
    } catch { /* ignore */ }
  }

  async function deleteSession(id: string) {
    try {
      await ElMessageBox.confirm('确认删除此对话？', '删除对话', { type: 'warning' })
      await tutorAPI.deleteSession(id)
      sessions.value = sessions.value.filter(s => s.id !== id)
      if (sessionId.value === id) createNewSession()
      ElMessage.success('对话已删除')
    } catch { /* cancelled */ }
  }

  async function clearAllSessions() {
    try {
      await ElMessageBox.confirm('确认清空所有对话记录？此操作不可恢复。', '清空对话', { type: 'warning' })
      for (const s of sessions.value) {
        await tutorAPI.deleteSession(s.id).catch(() => {})
      }
      sessions.value = []
      createNewSession()
      ElMessage.success('所有对话已清空')
    } catch { /* cancelled */ }
  }

  function sendMessage(text?: string) {
    const msg = (text || inputText.value).trim()
    if (!msg || loading.value) return

    messages.value.push({ role: 'user', content: msg, time: now() })
    inputText.value = ''
    loading.value = true
    streaming.value = true

    messages.value.push({ role: 'assistant', content: '', streaming: true, time: now() } as ChatMsg)

    const queryMsg = { type: 'query', question: msg, session_id: sessionId.value }

    if (wsClient) {
      wsClient.send(queryMsg)
      pendingMessage = null
    } else {
      pendingMessage = queryMsg
      connectWebSocket()
    }
  }

  function connectWebSocket() {
    const token = localStorage.getItem('token')
    if (!token) {
      _finishLastMsg('请先登录')
      return
    }

    wsClient = createTutorWebSocket(token)

    const connectTimeout = setTimeout(() => {
      if (pendingMessage) {
        _finishLastMsg('连接超时，请检查网络后重试')
        pendingMessage = null
        wsClient = null
      }
    }, 5000)

    wsClient.on('open', () => {
      clearTimeout(connectTimeout)
      if (pendingMessage) {
        wsClient!.send(pendingMessage)
        pendingMessage = null
      }
    })

    wsClient.on('message', (data: any) => {
      const lastIdx = messages.value.length - 1
      const lastMsg = messages.value[lastIdx]
      if (!lastMsg?.streaming) return

      switch (data.type) {
        case 'chunk': {
          const newContent = lastMsg.content + String(data.content || data.data || '')
          messages.value[lastIdx] = { ...lastMsg, content: newContent }
          break
        }
        case 'end': {
          messages.value[lastIdx] = { ...lastMsg, streaming: false }
          streaming.value = false
          loading.value = false
          if (data.session_id && !sessionId.value) {
            sessionId.value = data.session_id
            loadSessions()
          }
          if (!isFloatingOpen.value) unreadCount.value++
          break
        }
        case 'error': {
          _finishLastMsg(String(data.message || data.data || '发生错误'))
          break
        }
        case 'status': break
        case 'connected':
          // 不用 WebSocket 连接 ID 覆盖辅导对话 session_id
          break
      }
    })

    wsClient.on('error', () => {
      const lastIdx = messages.value.length - 1
      const lastMsg = messages.value[lastIdx]
      if (lastMsg?.streaming && !lastMsg.content) {
        _finishLastMsg('连接出错，请稍后再试')
      }
    })

    wsClient.on('close', () => {
      const lastIdx = messages.value.length - 1
      const lastMsg = messages.value[lastIdx]
      if (lastMsg?.streaming) {
        messages.value[lastIdx] = { ...lastMsg, streaming: false }
        streaming.value = false
        loading.value = false
      }
    })

    wsClient.connect(token)
  }

  function closeWebSocket() {
    wsClient?.close()
    wsClient = null
  }

  function markRead() {
    unreadCount.value = 0
  }

  function toggleFloating() {
    isFloatingOpen.value = !isFloatingOpen.value
    if (isFloatingOpen.value) unreadCount.value = 0
  }

  // ── Internal helpers ───────────────────────────────────

  function _finishLastMsg(content: string) {
    const lastIdx = messages.value.length - 1
    const lastMsg = messages.value[lastIdx]
    if (lastMsg?.streaming) {
      messages.value[lastIdx] = { ...lastMsg, content, streaming: false }
    }
    streaming.value = false
    loading.value = false
  }

  return {
    messages,
    inputText,
    loading,
    streaming,
    sessionId,
    sessions,
    unreadCount,
    isFloatingOpen,
    loadSessions,
    resumeLastSession,
    createNewSession,
    switchSession,
    deleteSession,
    clearAllSessions,
    sendMessage,
    connectWebSocket,
    closeWebSocket,
    markRead,
    toggleFloating,
  }
})
