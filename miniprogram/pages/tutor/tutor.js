const { request, BASE_URL } = require('../../utils/request')
const { API, replaceParams } = require('../../utils/api')
const { VoiceInput } = require('../../utils/voice')
const { markdownToPlainText, markdownToSimpleText } = require('../../utils/markdown')

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
    pendingImage: '',           // 待发送的图片本地路径
    pendingImageBase64: '',     // 待发送图片的base64
    pendingImageName: '',       // 图片文件名
    pendingImageSize: 0,        // 图片大小
    pendingImageSizeText: '',   // 格式化的图片大小
    pendingImageOCR: '',        // 图片的OCR识别文本
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

  /* ===================== 文件格式化工具 ===================== */

  formatFileSize(bytes) {
    if (!bytes) return '0 B'
    if (bytes < 1024) return bytes + ' B'
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
    return (bytes / 1024 / 1024).toFixed(1) + ' MB'
  },

  getFileExt(name) {
    if (!name) return 'PNG'
    const parts = name.split('.')
    return parts.length > 1 ? parts[parts.length - 1].toUpperCase() : 'PNG'
  },

  /* ===================== 图片上传相关 ===================== */

  chooseImage() {
    const that = this
    wx.chooseMedia({
      count: 1,
      mediaType: ['image'],
      sizeType: ['compressed'],
      sourceType: ['album', 'camera'],
      success: (res) => {
        const file = res.tempFiles[0]
        that.setData({
          pendingImage: file.tempFilePath,
          pendingImageName: file.tempFilePath.split('/').pop() || 'image.jpg',
          pendingImageSize: file.size || 0,
          pendingImageSizeText: that.formatFileSize(file.size || 0)
        })
        that.uploadImageAndOCR(file.tempFilePath)
      },
      fail: (err) => {
        if (err.errMsg && !err.errMsg.includes('cancel')) {
          wx.showToast({ title: '选择图片失败', icon: 'none' })
        }
      }
    })
  },

  uploadImageAndOCR(tempFilePath) {
    const that = this
    wx.showLoading({ title: '识别中...', mask: true })

    // 先读取图片为 base64（发送WS消息时需要）
    wx.getFileSystemManager().readFile({
      filePath: tempFilePath,
      encoding: 'base64',
      success: (res) => {
        that.setData({ pendingImageBase64: res.data })
      }
    })

    // 调用后端OCR接口（文件上传）
    const token = wx.getStorageSync('access_token') || ''
    wx.uploadFile({
      url: `${BASE_URL}/student/ocr/recognize`,
      filePath: tempFilePath,
      name: 'file',
      header: {
        'Authorization': `Bearer ${token}`
      },
      success: (resp) => {
        wx.hideLoading()
        try {
          const data = JSON.parse(resp.data)
          if (resp.statusCode === 200 && data && data.text) {
            that.setData({ pendingImageOCR: data.text })
          } else {
            that.setData({ pendingImageOCR: '' })
          }
        } catch (e) {
          that.setData({ pendingImageOCR: '' })
        }
        // 无论OCR成功与否，都提示图片添加成功（简洁消息）
        wx.showToast({ title: '图片添加成功', icon: 'success', duration: 1500 })
      },
      fail: () => {
        wx.hideLoading()
        // OCR失败，仍保留图片，仅提示添加成功
        that.setData({ pendingImageOCR: '' })
        wx.showToast({ title: '图片添加成功', icon: 'success', duration: 1500 })
      }
    })
  },

  removePendingImage() {
    this.setData({
      pendingImage: '',
      pendingImageBase64: '',
      pendingImageName: '',
      pendingImageSize: 0,
      pendingImageSizeText: '',
      pendingImageOCR: ''
    })
  },

  previewImage(e) {
    const url = e.currentTarget.dataset.url
    if (url) {
      wx.previewImage({ urls: [url], current: url })
    }
  },

  async loadSessions() {
    try {
      const result = await request({
        url: API.TUTOR.SESSIONS,
        method: 'GET'
      })
      const sessionsData = result?.sessions || []
      const sessions = sessionsData.map((s, idx) => ({
        key: s.session_id,
        id: idx + 1,
        preview: s.preview || '暂无消息',
        time: s.updated_at ? this.formatTimeAgo(s.updated_at) : ''
      }))
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
    const welcomeText = '您好！我是您的智能学习辅导助手。我会根据您的学习内容为您提供个性化的指导。您可以输入文字、发送语音，或上传题目图片来提问！'
    const welcomeMsg = {
      id: 1,
      role: 'ai',
      type: 'text',
      content: this.cleanText(welcomeText),
      tokens: markdownToPlainText(welcomeText),
      showAvatar: true
    }
    this.setData({
      chatHistory: [welcomeMsg],
      pendingImage: '',
      pendingImageBase64: '',
      pendingImageName: '',
      pendingImageSize: 0,
      pendingImageSizeText: '',
      pendingImageOCR: ''
    })
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
        if (msgData && msgData.session_id) {
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
      lastMsg.content = this.cleanText(lastMsg.content + chunk)
      lastMsg.tokens = markdownToPlainText(lastMsg.content)
      this.setData({ chatHistory: [...chatHistory] })
    }
  },

  // 清理文本中多余的空行
  cleanText(text) {
    if (!text) return ''
    return text.replace(/\n{3,}/g, '\n\n').trim()
  },

  onInput(e) {
    this.setData({ inputValue: e.detail.value })
  },

  sendQuestion() {
    const { inputValue, chatHistory, pendingImage, pendingImageBase64,
      pendingImageName, pendingImageSize, pendingImageOCR } = this.data

    const hasText = inputValue.trim().length > 0
    const hasImage = pendingImageBase64 && pendingImageBase64.length > 0

    if (!hasText && !hasImage) return

    // display_content 是用户看到的原始输入（不含OCR）
    const displayContent = this.cleanText(inputValue.trim())
    // question 是发给大模型的完整查询（包含OCR文本）
    let question = displayContent
    if (pendingImageOCR && pendingImageOCR.trim().length > 0) {
      if (displayContent) {
        question = `${displayContent}\n\n[图片OCR内容]:\n${pendingImageOCR}`
      } else {
        question = `[图片OCR内容]:\n${pendingImageOCR}`
      }
    }

    const userMsg = {
      id: chatHistory.length + 1,
      role: 'user',
      type: hasImage ? 'image_text' : 'text',
      content: displayContent,
      imageUrl: pendingImage || undefined,
      imageName: pendingImageName || '',
      imageSize: pendingImageSize || 0,
      imageExt: this.getFileExt(pendingImageName),
      imageSizeText: this.formatFileSize(pendingImageSize)
    }

    // 显示内容：如果有图片但没文字，就显示图片提示
    if (hasImage && !displayContent) {
      userMsg.content = '[图片]'
    }

    this.setData({
      chatHistory: [...chatHistory, userMsg, {
        id: chatHistory.length + 2,
        role: 'ai',
        type: 'text',
        content: '',
        tokens: [],
        isTyping: true,
        showAvatar: false
      }],
      inputValue: '',
      isTyping: true,
      // 发送后清空待发送图片
      pendingImage: '',
      pendingImageBase64: '',
      pendingImageName: '',
      pendingImageSize: 0,
      pendingImageSizeText: '',
      pendingImageOCR: ''
    })

    if (this.socket && this.data.isConnected) {
      const msg = {
        type: 'query',
        question: question,
        display_content: displayContent,
        session_id: this.data.sessionId
      }
      if (hasImage) {
        msg.image_base64 = pendingImageBase64
        msg.image_name = pendingImageName
        msg.image_size = pendingImageSize
      }
      this.socket.send({
        data: JSON.stringify(msg)
      })
    } else {
      this.fallbackSendQuestion(question)
    }
  },

  async fallbackSendQuestion(question) {
    try {
      this.setData({ isTyping: false })
      const responseContent = '抱歉，连接暂不可用。请检查网络后重试：' + question

      const newMessages = this.data.chatHistory.slice(0, -1)
      newMessages.push({
        id: this.data.chatHistory.length,
        role: 'ai',
        type: 'text',
        content: responseContent,
        tokens: markdownToPlainText(responseContent),
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
      content: '确定要清空当前对话记录吗？',
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

  async selectSession(e) {
    const idx = e.currentTarget.dataset.index
    const session = this.data.tutorSessions[idx]
    if (!session) return

    wx.showLoading({ title: '加载中...', mask: true })
    try {
      const url = replaceParams(API.TUTOR.CHAT_HISTORY, { session_id: session.key })
      const result = await request({ url, method: 'GET' })
      const messages = result?.messages || []

      this.setData({
        chatHistory: messages.map((msg, mIdx) => {
          const role = msg.role === 'assistant' ? 'ai' : msg.role
          const displayContent = this.cleanText(msg.display_content || msg.content || '')
          const imageUrl = msg.image_base64 ? `data:image/jpeg;base64,${msg.image_base64}` : ''
          const imageName = msg.image_name || ''
          const imageSize = msg.image_size || 0
          return {
            id: mIdx + 1,
            role: role,
            type: imageUrl ? 'image_text' : 'text',
            content: displayContent || (imageUrl ? '[图片]' : ''),
            tokens: role === 'ai' ? markdownToPlainText(msg.content) : [],
            showAvatar: role === 'ai' && mIdx === 0,
            imageUrl: imageUrl || undefined,
            imageName: imageName,
            imageSize: imageSize,
            imageExt: this.getFileExt(imageName),
            imageSizeText: this.formatFileSize(imageSize)
          }
        }),
        showSessionList: false,
        sessionId: session.key
      })
    } catch (err) {
      console.error('加载会话历史失败:', err)
      wx.showToast({ title: '加载失败', icon: 'none' })
    } finally {
      wx.hideLoading()
    }
  }
})
