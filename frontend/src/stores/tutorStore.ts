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
  const pendingImage = ref<string | null>(null)  // 待发送的图片 base64
  const pendingImageName = ref<string>('')      // 待发送的图片文件名
  const pendingImageSize = ref<number>(0)       // 待发送的图片大小（字节）
  const pendingOcrText = ref<string>('')        // 待发送图片的 OCR 识别文本
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
    // 加载会话列表
    await loadSessions()

    // 检查 localStorage 是否有未发送消息的"新会话"标记
    const savedSessionId = localStorage.getItem('tutor_active_session')
    const isNewSession = localStorage.getItem('tutor_session_is_new') === 'true'

    if (savedSessionId && isNewSession) {
      // 用户之前点击了"新对话"但没发消息，保持空会话状态
      sessionId.value = savedSessionId
      messages.value = [{ role: 'assistant', content: WELCOME_MSG, time: now() }]
      return
    }

    // 否则恢复最近一个有消息的会话
    if (sessions.value.length > 0 && !sessionId.value) {
      const latest = sessions.value[0]
      await switchSession(latest.id)
    }
  }

  function createNewSession() {
    // 生成新的 sessionId（带 new_ 前缀表示未发送消息的新会话）
    const newSessionId = `new_${Date.now()}`
    sessionId.value = newSessionId
    messages.value = [{ role: 'assistant', content: WELCOME_MSG, time: now() }]
    wsClient?.close()
    wsClient = null
    // 持久化到 localStorage，下次进入页面时保持这个空会话
    localStorage.setItem('tutor_active_session', newSessionId)
    localStorage.setItem('tutor_session_is_new', 'true')
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
          content: m.display_content || m.content,  // 优先使用 display_content（用户原始输入），回退到 content
          time: '',
          image_base64: m.image_base64 || undefined,
          image_name: m.image_name || undefined,
          image_size: m.image_size || undefined,
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
    const imgB64 = pendingImage.value
    const imgName = pendingImageName.value
    const imgSize = pendingImageSize.value
    const ocrText = pendingOcrText.value
    const userText = (text || inputText.value).trim()

    // 前端显示的内容：用户原始输入（不包含 OCR 文本）
    const displayContent = userText || (imgB64 ? '（图片）' : '')

    // 后端查询内容：用户文本 + OCR 识别文本（拼接后发给大模型）
    let queryText = userText
    if (ocrText) {
      queryText = userText ? `${userText}\n\n${ocrText}` : ocrText
    }

    if (!queryText && !imgB64) return
    if (loading.value) return

    // 清空待发送状态
    pendingImage.value = null
    pendingImageName.value = ''
    pendingImageSize.value = 0
    pendingOcrText.value = ''

    // 前端显示：只显示用户原始输入 + 图片附件（不显示 OCR 文本）
    messages.value.push({
      role: 'user', content: displayContent, time: now(),
      image_base64: imgB64 || undefined,
      image_name: imgName || undefined,
      image_size: imgSize || undefined,
    })
    inputText.value = ''
    loading.value = true
    streaming.value = true

    messages.value.push({ role: 'assistant', content: '', streaming: true, time: now() } as ChatMsg)

    // 发送给后端：display_content（用户原始输入，用于保存）+ question（拼接 OCR 后给大模型）
    const queryMsg: Record<string, any> = {
      type: 'query',
      question: queryText || '图片',           // 拼接 OCR 后的完整查询（给大模型）
      display_content: displayContent,         // 用户原始输入（用于前端显示和保存）
      session_id: sessionId.value,
    }
    if (imgB64) {
      queryMsg.image_base64 = imgB64
      queryMsg.image_name = imgName
      queryMsg.image_size = imgSize
    }

    // 标记会话已不再是"新会话"（已发送消息）
    localStorage.removeItem('tutor_session_is_new')
    if (sessionId.value) {
      localStorage.setItem('tutor_active_session', sessionId.value)
    }

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
          // 关键修复：后端返回了真正的 session_id 时，更新前端状态
          // 条件：sessionId 为空，或者是带有 new_ 前缀的临时ID（新会话）
          if (data.session_id && (!sessionId.value || sessionId.value.startsWith('new_'))) {
            sessionId.value = data.session_id
            // 同步持久化到 localStorage
            localStorage.setItem('tutor_active_session', data.session_id)
            localStorage.removeItem('tutor_session_is_new')
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
    pendingImage,
    pendingImageName,
    pendingImageSize,
    pendingOcrText,
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
