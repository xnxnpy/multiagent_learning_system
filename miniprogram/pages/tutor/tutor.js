const { request, BASE_URL } = require('../../utils/request')
const { API, replaceParams } = require('../../utils/api')
const { VoiceInput } = require('../../utils/voice')
const { markdownToHtml } = require('../../utils/markdown')

Page({
  data: {
    chatHistory: [],
    inputValue: '',
    isTyping: false,
    isConnected: false,
    sessionId: '',
    isRecording: false,
    isVoiceLoading: false,
    recordingTime: 0,
    tutorSessions: [],
    showSessionList: false,
    quickQuestions: [
      { id: 1, icon: '❓', text: '什么是神经网络？' },
      { id: 2, icon: '💡', text: '梯度下降怎么理解？' },
      { id: 3, icon: '📐', text: '矩阵乘法有什么用？' },
      { id: 4, icon: '🔍', text: 'ReLU激活函数特点' },
      { id: 5, icon: '⚡', text: '反向传播原理' }
    ]
  },

  onLoad() {
    this.initChat()
    this.loadSessions()
    this.connectWebSocket()
    this.initVoiceInput()
  },

  onShow() {
    this.loadSessions()
  },

  onUnload() {
    this.closeWebSocket()
    if (this.voiceInput) this.voiceInput.destroy()
  },

  onReady() {
    if (this.voiceInput) this.voiceInput.init()
  },

  initVoiceInput() {
    this.voiceInput = new VoiceInput({
      maxDuration: 60,
      onStart: () => {
        this.setData({ isRecording: true, isVoiceLoading: false, recordingTime: 0 })
      },
      onRecording: (time) => {
        this.setData({ recordingTime: time })
      },
      onLoading: (loading) => {
        this.setData({ isVoiceLoading: loading })
      },
      onResult: (text) => {
        this.setData({
          isRecording: false, isVoiceLoading: false, recordingTime: 0,
          inputValue: text
        })
      },
      onError: (msg) => {
        this.setData({ isRecording: false, isVoiceLoading: false, recordingTime: 0 })
        console.error('语音输入错误:', msg)
      },
      onCancel: () => {
        this.setData({ isRecording: false, isVoiceLoading: false, recordingTime: 0 })
      }
    })
  },

  startVoiceInput() {
    if (this.voiceInput) this.voiceInput.start()
  },

  stopVoiceInput() {
    if (this.voiceInput) this.voiceInput.stop()
  },

  cancelVoiceInput() {
    if (this.voiceInput) this.voiceInput.cancel()
  },

  async loadSessions() {
    try {
      const result = await request({
        url: API.STUDENT.TUTOR_CHATS,
        method: 'GET'
      })
      const sessionsData = result?.sessions || {}
      const sessions = Object.keys(sessionsData).map((key, idx) => {
        const msgs = sessionsData[key]
        const lastMsg = msgs.length > 0 ? msgs[msgs.length - 1] : null
        return {
          key: key,
          id: idx + 1,
          messages: msgs,
          preview: lastMsg?.content?.substring(0, 30) + '...' || '暂无消息',
          time: lastMsg?.time ? this.formatTimeAgo(lastMsg.time) : ''
        }
      })
      this.setData({ tutorSessions: sessions })
    } catch (err) {
      console.error('加载会话列表失败:', err)
    }
  },

  formatTimeAgo(iso) {
    if (!iso) return ''
    const date = new Date(iso)
    const now = new Date()
    const diff = Math.floor((now.getTime() - date.getTime()) / 1000)
    if (diff < 60) return '刚刚'
    if (diff < 3600) return `${Math.floor(diff / 60)}分钟前`
    if (diff < 86400) return `${Math.floor(diff / 3600)}小时前`
    if (diff < 604800) return `${Math.floor(diff / 86400)}天前`
    return date.toLocaleDateString('zh-CN')
  },

  createNewSession() {
    this.initChat()
    this.setData({ sessionId: '', showSessionList: false })
    wx.showToast({ title: '已创建新对话', icon: 'success' })
  },

  deleteSession(e) {
    const idx = e.currentTarget.dataset.index
    const session = this.data.tutorSessions[idx]
    if (!session) return

    wx.showModal({
      title: '确认删除',
      content: '确定要删除这个对话吗？',
      success: async (res) => {
        if (res.confirm) {
          try {
            await request({
              url: replaceParams(API.TUTOR.DELETE_SESSION, { session_id: session.key }),
              method: 'DELETE'
            })
            await this.loadSessions()
            if (this.data.tutorSessions.length === 0) {
              this.initChat()
            }
            wx.showToast({ title: '已删除', icon: 'success' })
          } catch (err) {
            console.error('删除会话失败:', err)
            wx.showToast({ title: '删除失败', icon: 'none' })
          }
        }
      }
    })
  },

  clearAllSessions() {
    wx.showModal({
      title: '确认清空',
      content: '确定要清空所有对话记录吗？',
      success: async (res) => {
        if (res.confirm) {
          try {
            await request({
              url: API.TUTOR.SESSIONS,
              method: 'DELETE'
            })
            this.initChat()
            this.loadSessions()
            wx.showToast({ title: '已清空', icon: 'success' })
          } catch (err) {
            console.error('清空会话失败:', err)
            wx.showToast({ title: '清空失败', icon: 'none' })
          }
        }
      }
    })
  },

  initChat() {
    const welcomeMsg = {
      id: 1,
      role: 'ai',
      type: 'text',
      content: '您好！我是您的智能学习辅导助手。我会根据您的学习内容为您提供个性化的指导，请随时向我提问！',
      renderedHtml: markdownToHtml('您好！我是您的智能学习辅导助手。我会根据您的学习内容为您提供个性化的指导，请随时向我提问！'),
      showAvatar: true
    }
    this.setData({ chatHistory: [welcomeMsg] })
  },

  connectWebSocket() {
    const token = wx.getStorageSync('access_token')
    const wsUrl = BASE_URL.replace('http', 'ws') + API.TUTOR.WS_CHAT + `?token=${token}`

    this.socket = wx.connectSocket({
      url: wsUrl,
      success: () => {},
      fail: (err) => {
        console.error('WebSocket 连接失败:', err)
        wx.showToast({ title: '连接辅导服务失败', icon: 'none' })
      }
    })

    this.socket.onOpen(() => {
      this.setData({ isConnected: true })
    })

    this.socket.onMessage((res) => {
      try {
        const data = JSON.parse(res.data)
        this.handleSocketMessage(data)
      } catch (err) {
        console.error('解析 WebSocket 消息失败:', err)
      }
    })

    this.socket.onClose(() => {
      this.setData({ isConnected: false })
    })

    this.socket.onError((err) => {
      console.error('WebSocket 错误:', err)
      this.setData({ isConnected: false })
    })
  },

  closeWebSocket() {
    if (this.socket) {
      this.socket.close()
      this.socket = null
    }
  },

  handleSocketMessage(data) {
    const { type, message, data: msgData } = data

    switch (type) {
      case 'connected':
        break
      case 'status':
        wx.showToast({ title: message, icon: 'none', duration: 1500 })
        break
      case 'chunk':
        this.appendChatContent(msgData)
        break
      case 'end':
        this.setData({ isTyping: false })
        if (msgData.session_id) {
          this.setData({ sessionId: msgData.session_id })
        }
        this.loadSessions()
        break
      case 'error':
        wx.showToast({ title: message || '发生错误', icon: 'none' })
        this.setData({ isTyping: false })
        break
    }
  },

  appendChatContent(chunk) {
    const { chatHistory } = this.data
    const lastMsg = chatHistory[chatHistory.length - 1]

    if (lastMsg && lastMsg.role === 'ai' && lastMsg.isTyping !== false) {
      lastMsg.content += chunk
      lastMsg.renderedHtml = markdownToHtml(lastMsg.content)
      this.setData({ chatHistory: [...chatHistory] })
    }
  },

  onInput(e) {
    this.setData({ inputValue: e.detail.value })
  },

  sendQuestion() {
    const { inputValue, chatHistory } = this.data
    if (!inputValue.trim()) return

    const userMsg = {
      id: chatHistory.length + 1,
      role: 'user',
      type: 'text',
      content: inputValue
    }

    this.setData({
      chatHistory: [...chatHistory, userMsg, {
        id: chatHistory.length + 2,
        role: 'ai',
        type: 'text',
        content: '',
        renderedHtml: '',
        isTyping: true,
        showAvatar: false
      }],
      inputValue: '',
      isTyping: true
    })

    if (this.socket && this.data.isConnected) {
      this.socket.send({
        data: JSON.stringify({
          type: 'query',
          question: inputValue,
          session_id: this.data.sessionId
        })
      })
    } else {
      this.fallbackSendQuestion(inputValue)
    }
  },

  async fallbackSendQuestion(question) {
    try {
      const result = await request({
        url: API.TUTOR.SESSIONS,
        method: 'GET'
      })

      this.setData({ isTyping: false })
      const responseContent = '抱歉，WebSocket 连接不可用。这是一个离线响应：' + question

      const newMessages = this.data.chatHistory.slice(0, -1)
      newMessages.push({
        id: this.data.chatHistory.length,
        role: 'ai',
        type: 'text',
        content: responseContent,
        renderedHtml: markdownToHtml(responseContent),
        isTyping: false,
        showAvatar: false
      })
      this.setData({ chatHistory: newMessages })
    } catch (err) {
      this.setData({ isTyping: false })
    }
  },

  sendQuickQuestion(e) {
    const question = e.currentTarget.dataset.question
    this.setData({ inputValue: question })
    this.sendQuestion()
  },

  clearChat() {
    wx.showModal({
      title: '确认清空',
      content: '确定要清空所有对话记录吗？',
      success: (res) => {
        if (res.confirm) {
          this.initChat()
          wx.showToast({ title: '已清空', icon: 'success' })
        }
      }
    })
  },

  toggleSessionList() {
    this.setData({ showSessionList: !this.data.showSessionList })
  },

  selectSession(e) {
    const idx = e.currentTarget.dataset.index
    const session = this.data.tutorSessions[idx]
    if (session) {
      this.setData({
        chatHistory: session.messages.map((msg, mIdx) => {
          const role = msg.role === 'assistant' ? 'ai' : msg.role
          return {
            id: mIdx + 1,
            role: role,
            type: 'text',
            content: msg.content,
            renderedHtml: role === 'ai' ? markdownToHtml(msg.content) : '',
            showAvatar: role === 'ai' && mIdx === 0
          }
        }),
        showSessionList: false
      })
    }
  }
})