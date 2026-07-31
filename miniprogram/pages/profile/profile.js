const { request, BASE_URL } = require('../../utils/request')
const { API, replaceParams } = require('../../utils/api')
const { VoiceInput } = require('../../utils/voice')

Page({
  data: {
    userName: '',
    inputValue: '',
    messages: [],
    profileCompleted: false,
    profileComplete: false,
    profileData: {
      major: '',
      grade: '',
      goal: '',
      level: '',
      style: '',
      coding: '',
      interests: [],
      weakness: []
    },
    sessionId: '',
    unreadCount: 0,
    workflowRunning: false,
    workflowProgress: 0,
    workflowStep: '',
    hasPath: false,
    profiles: [],
    activeProfileId: null,
    showProfileList: false,
    showNewProfileDialog: false,
    newProfileName: '',
    editingProfileId: null,
    editingProfileName: '',
    submitting: false,
    sending: false,
    currentProfileName: '我的画像',
    showProfileDropdown: false,
    activeProfiles: [],
    needsWorkflow: false,
    currentAgentName: '准备中',
    isRecording: false,
    isVoiceLoading: false,
    recordingTime: 0,
    showEditDialog: false,
    editData: {
      major: '',
      grade: '',
      goal: '',
      level: '',
      style: '',
      coding: '',
      interests: []
    },
    newInterestTag: ''
  },

  onLoad() {
    const userInfo = wx.getStorageSync('user_info')
    const username = userInfo?.username || userInfo?.real_name || '同学'
    this.setData({ userName: username })
    this.loadProfile()
    this.loadUnreadCount()
    this.fetchProfiles()
    this.checkInitStatus()
  },

  onShow() {
    this.loadUnreadCount()
  },

  onReady() {
    this.initVoiceInput()
  },

  onUnload() {
    if (this.voiceInput) {
      this.voiceInput.destroy()
    }
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
          isRecording: false,
          isVoiceLoading: false, 
          recordingTime: 0,
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
    if (this.voiceInput) {
      this.voiceInput.start()
    }
  },

  stopVoiceInput() {
    if (this.voiceInput) {
      this.voiceInput.stop()
    }
  },

  cancelVoiceInput() {
    if (this.voiceInput) {
      this.voiceInput.cancel()
    }
  },

  async loadUnreadCount() {
    try {
      const result = await request({
        url: API.NOTIFICATION.UNREAD_COUNT,
        method: 'GET'
      })
      this.setData({ unreadCount: result.count || 0 })
    } catch (err) {
      console.error('加载通知失败:', err)
    }
  },

  async loadChatHistory() {
    try {
      let url
      if (this.data.activeProfileId) {
        url = replaceParams(API.STUDENT.PROFILE_CHAT_HISTORY, { profile_id: this.data.activeProfileId })
      } else {
          // 回退到旧路径（后端也能工作：student.py:453 的 /chat/history（GET）
        url = '/student/chat/history'
      }
      const result = await request({
        url: url,
        method: 'GET'
      })

      const messages = (result.messages || []).map(msg => ({
        id: msg.id,
        role: msg.role === 'assistant' ? 'ai' : msg.role,
        content: msg.content,
        isThinking: false,
        streaming: false,
        time: msg.time || ''
      }))

      this.setData({ messages })
    } catch (err) {
      console.error('加载聊天历史失败:', err)
      this.initChat()
    }
  },

  async loadProfile() {
    try {
      const result = await request({
        url: API.STUDENT.PROFILE,
        method: 'GET'
      })

      const profileData = {
        major: result.major || '',
        grade: result.grade || '',
        goal: result.goal || '',
        level: result.knowledge_level || '',
        style: result.learning_style || '',
        coding: result.coding_ability || '',
        interests: result.interests || [],
        weakness: result.weakness || []
      }

      const completedFields = Object.keys(profileData).filter(key => {
        const val = profileData[key]
        return (Array.isArray(val) && val.length > 0) || (typeof val === 'string' && val.length > 0)
      }).length

      const profileComplete = profileData.major && profileData.grade && profileData.goal && profileData.level && 
        (profileData.interests?.length > 0) && (profileData.weakness?.length > 0) && profileData.style && profileData.coding

      this.setData({
        profileData,
        profileCompleted: completedFields >= 6,
        profileComplete: profileComplete
      })
    } catch (err) {
      console.error('加载画像失败:', err)
    }
  },

  initChat() {
    const initialMsg = {
      id: 1,
      role: 'ai',
      content: '您好！我是您的学习顾问。为了给您制定个性化的学习方案，请先告诉我您的专业方向和年级？',
      isThinking: false,
      streaming: false,
      time: new Date().toLocaleTimeString()
    }
    this.setData({ messages: [initialMsg] })
  },

  scrollToBottom() {
    setTimeout(() => {
      const query = wx.createSelectorQuery()
      query.select('.chat-box').boundingClientRect()
      query.exec((res) => {
        if (res[0]) {
          const scrollHeight = res[0].height || 500
          wx.pageScrollTo({
            selector: '.chat-box',
            scrollTop: scrollHeight * 10,
            duration: 300
          })
        }
      })
    }, 100)
  },

  onInput(e) {
    this.setData({ inputValue: e.detail.value })
  },

  async sendMessage() {
    const { inputValue, messages, activeProfileId, profileData, sending } = this.data
    if (!inputValue.trim() || sending) return

    const now = new Date().toLocaleTimeString()
    const userMsg = {
      id: messages.length + 1,
      role: 'user',
      content: inputValue,
      isThinking: false,
      streaming: false,
      time: now
    }

    this.setData({
      messages: [...messages, userMsg],
      inputValue: '',
      sending: true
    })
    this.scrollToBottom()

    await this.persistMessage('user', inputValue)

    const chatHistory = messages.slice(-10).map(m => ({ role: m.role, content: m.content }))
    
    const token = wx.getStorageSync('access_token') || ''
    const wsUrl = BASE_URL.replace('http', 'ws') + '/profile-chat/ws/chat' + `?token=${token}`
    
    const ws = wx.connectSocket({ url: wsUrl })
    let currentAssistantMsg = null
    let finished = false

    const sendTimeout = setTimeout(() => {
      if (!finished && sending) {
        finished = true
        ws.close()
        this.setData({ sending: false })
        const newMessages = this.data.messages
        newMessages.push({
          id: newMessages.length + 1,
          role: 'ai',
          content: '响应超时，请重试。',
          isThinking: false,
          streaming: false,
          time: new Date().toLocaleTimeString()
        })
        this.setData({ messages: newMessages })
      }
    }, 30000)

    ws.onOpen(() => {
      ws.send({
        data: JSON.stringify({
          type: 'query',
          question: inputValue,
          session_id: `profile_${wx.getStorageSync('user_info')?.id || 'unknown'}`,
          chat_history: chatHistory,
          profile: { ...profileData },
          profile_id: activeProfileId
        })
      })
    })

    ws.onMessage((res) => {
      try {
        const data = JSON.parse(res.data)
        switch (data.type) {
          case 'chunk':
            if (!currentAssistantMsg) {
              currentAssistantMsg = {
                id: this.data.messages.length + 1,
                role: 'ai',
                content: '',
                isThinking: false,
                streaming: true,
                time: new Date().toLocaleTimeString()
              }
              this.setData({ messages: [...this.data.messages, currentAssistantMsg] })
            this.scrollToBottom()
            }
            currentAssistantMsg.content += data.content
            currentAssistantMsg.streaming = true
            const idx = this.data.messages.findIndex(m => m.id === currentAssistantMsg.id)
            if (idx !== -1) {
              const newMessages = [...this.data.messages]
              newMessages[idx] = { ...currentAssistantMsg }
              this.setData({ messages: newMessages })
            }
            break
          case 'end':
            finished = true
            clearTimeout(sendTimeout)
            // 不立即关闭 WebSocket，因为后台可能还要发送 profile_update / check_workflow
            // 等 check_workflow 处理完成后再由工作流 WebSocket 接管，或页面卸载时关闭
            if (currentAssistantMsg) {
              currentAssistantMsg.streaming = false
              const idx = this.data.messages.findIndex(m => m.id === currentAssistantMsg.id)
              if (idx !== -1) {
                const newMessages = [...this.data.messages]
                newMessages[idx] = { ...currentAssistantMsg }
                this.setData({ messages: newMessages })
              }
              this.persistMessage('assistant', currentAssistantMsg.content)
            }
            this.setData({ sending: false })
            this.loadProfile()
            break
          case 'profile_update':
            this.loadProfile()
            break
          case 'check_workflow':
            this.setData({ needsWorkflow: true })
            this.startAutoWorkflow()
            break
          case 'error':
            finished = true
            clearTimeout(sendTimeout)
            ws.close()
            const errMsg = {
              id: this.data.messages.length + 1,
              role: 'ai',
              content: data.message || '生成回答失败，请稍后重试',
              isThinking: false,
              streaming: false,
              time: new Date().toLocaleTimeString()
            }
            this.setData({ messages: [...this.data.messages, errMsg], sending: false })
            break
        }
      } catch (err) {
        console.error('解析消息失败:', err)
      }
    })

    ws.onError(() => {
      if (!finished) {
        finished = true
        clearTimeout(sendTimeout)
        this.setData({ sending: false })
        const errMsg = {
          id: this.data.messages.length + 1,
          role: 'ai',
          content: '连接失败，请重试。',
          isThinking: false,
          streaming: false,
          time: new Date().toLocaleTimeString()
        }
        this.setData({ messages: [...this.data.messages, errMsg] })
      }
    })

    ws.onClose(() => {
      if (!finished) {
        finished = true
        clearTimeout(sendTimeout)
        this.setData({ sending: false })
      }
    })
  },

  async persistMessage(role, content) {
    try {
      await request({
        url: API.STUDENT.PROFILE_CHAT_MESSAGE,
        method: 'POST',
        data: {
          role: role,
          content: content,
          profile_id: this.data.activeProfileId
        }
      })
    } catch (err) {
      console.error('保存消息失败:', err)
    }
  },

  goToPath() {
    wx.switchTab({ url: '/pages/path/path' })
  },

  goToUserProfile() {
    wx.navigateTo({ url: '/pages/user-profile/user-profile' })
  },

  goToMyLearning() {
    wx.navigateTo({ url: '/pages/my-learning/my-learning' })
  },

  goToNotifications() {
    wx.navigateTo({ url: '/pages/notifications/notifications' })
  },

  logout() {
    wx.showModal({
      title: '确认退出',
      content: '确定要退出登录吗？',
      success: (res) => {
        if (res.confirm) {
          const app = getApp()
          app.clearUserData()
          wx.reLaunch({ url: '/pages/index/index' })
        }
      }
    })
  },

  async checkInitStatus() {
    try {
      const result = await request({
        url: API.STUDENT.INIT_STATUS,
        method: 'GET'
      })
      if (result.has_path) {
        this.setData({ hasPath: true })
      } else if (result.needs_workflow) {
        this.startAutoWorkflow()
      }
    } catch (err) {
      console.error('检查初始化状态失败:', err)
    }
  },

  async startAutoWorkflow() {
    this.setData({ workflowRunning: true, workflowProgress: 0, workflowStep: '准备中...', currentAgentName: '准备中' })
    
    try {
      const startRes = await request({
        url: API.STUDENT.LEARN_START,
        method: 'POST'
      })
      const sessionId = startRes.session_id
      
      const token = wx.getStorageSync('access_token') || ''
      const wsUrl = BASE_URL.replace('http', 'ws') + API.STUDENT.WORKFLOW_WS + `?token=${token}`
      
      const ws = wx.connectSocket({ url: wsUrl })
      let finished = false
      
      ws.onOpen(() => {
        ws.send({ data: JSON.stringify({ type: 'start', session_id: sessionId }) })
      })
      
      ws.onMessage((res) => {
        try {
          const data = JSON.parse(res.data)
          switch (data.type) {
            case 'step':
              const stepName = this.getStepName(data.data.current_step)
              const subStep = data.data.sub_step || ''
              const displayStep = subStep.includes('·') ? subStep.split('·')[0] : stepName
              const currentAgentName = this.getCurrentAgentName()
              this.setData({
                workflowStep: displayStep,
                workflowProgress: Math.round((data.data.progress || 0) * 100),
                currentAgentName: currentAgentName
              })
              break
            case 'complete':
              if (finished) break
              finished = true
              ws.close()
              this.setData({ workflowRunning: false, hasPath: true })
              this.loadProfile()
              const successMsg = {
                id: this.data.messages.length + 1,
                role: 'ai',
                content: '✅ 学习路径和学习资源已准备就绪！\n\n请前往「学习路径」页面查看并开始学习。',
                isThinking: false,
                streaming: false,
                time: new Date().toLocaleTimeString()
              }
              this.setData({ messages: [...this.data.messages, successMsg] })
              wx.showToast({ title: '学习路径已生成！', icon: 'success' })
              break
            case 'error':
              if (finished) break
              finished = true
              ws.close()
              this.setData({ workflowRunning: false })
              const errorMsg = {
                id: this.data.messages.length + 1,
                role: 'ai',
                content: '资源生成遇到问题，您可以稍后在「学习路径」页面手动触发生成。',
                isThinking: false,
                streaming: false,
                time: new Date().toLocaleTimeString()
              }
              this.setData({ messages: [...this.data.messages, errorMsg] })
              wx.showToast({ title: '生成失败，请重试', icon: 'none' })
              break
          }
        } catch (err) {
          console.error('解析工作流消息失败:', err)
        }
      })
      
      ws.onError(() => {
        if (!finished) {
          finished = true
          this.setData({ workflowRunning: false })
          const errorMsg = {
            id: this.data.messages.length + 1,
            role: 'ai',
            content: '资源生成遇到问题，您可以稍后在「学习路径」页面手动触发生成。',
            isThinking: false,
            streaming: false,
            time: new Date().toLocaleTimeString()
          }
          this.setData({ messages: [...this.data.messages, errorMsg] })
          wx.showToast({ title: '连接工作流服务失败', icon: 'none' })
        }
      })
      
      ws.onClose(() => {
        if (!finished) {
          finished = true
          this.setData({ workflowRunning: false })
        }
      })
    } catch (err) {
      this.setData({ workflowRunning: false })
      const errorMsg = {
        id: this.data.messages.length + 1,
        role: 'ai',
        content: '资源生成遇到问题，您可以稍后在「学习路径」页面手动触发生成。',
        isThinking: false,
        streaming: false,
        time: new Date().toLocaleTimeString()
      }
      this.setData({ messages: [...this.data.messages, errorMsg] })
      wx.showToast({ title: '启动工作流失败', icon: 'none' })
    }
  },

  getStepName(step) {
    const map = {
      build_profile: '画像构建 Agent',
      generate_path: '路径规划 Agent',
      generate_knowledge_graph: '知识图谱 Agent',
      generate_document: '文档生成 Agent',
      generate_ppt_video: 'PPT 视频 Agent',
      generate_mindmap: '思维导图 Agent',
      generate_questions: '题库生成 Agent',
      generate_code: '代码实操 Agent',
      generate_reading: '拓展阅读 Agent',
      generate_glossary: '术语词汇 Agent',
      generate_knowledge_link: '知识关联 Agent',
      generate_summary: '学习总结 Agent',
      quality_evaluate: '质量评估 Agent'
    }
    return map[step] || step
  },

  getCurrentAgentName() {
    const step = this.data.workflowStep || ''
    const subStepKeywords = {
      '知识图谱': '知识图谱 Agent',
      '思维导图': '思维导图 Agent',
      '拓展阅读': '拓展阅读 Agent',
      '术语词汇': '术语词汇 Agent',
      '知识关联': '知识关联 Agent',
      '学习总结': '学习总结 Agent',
      '总结报告': '学习总结 Agent',
      'PPT': '教学视频 Agent',
      'ppt': '教学视频 Agent',
      'synthesizing_tts': '教学视频 Agent',
      'tts': '教学视频 Agent',
      'rendering': '教学视频 Agent',
      'rendering_html': '教学视频 Agent',
      'uploading': '教学视频 Agent',
      'generating_ppt': '教学视频 Agent',
      'generating_pages': '教学视频 Agent',
      'generating_subtitles': '教学视频 Agent',
      'composing_video': '教学视频 Agent',
      'combining': '教学视频 Agent'
    }
    for (const [keyword, name] of Object.entries(subStepKeywords)) {
      if (step.includes(keyword)) return name.split('·')[0].trim()
    }
    const parts = step.split('·')
    return (parts[0] || '准备中').trim()
  },

  async fetchProfiles() {
    try {
      const result = await request({
        url: API.STUDENT.PROFILES,
        method: 'GET'
      })
      const profiles = result || []
      const active = profiles.find(p => p.is_active)
      const currentProfileName = active?.profile_name || '我的画像'
      const activeProfiles = profiles.filter(p => !p.is_archived)
      this.setData({
        profiles,
        activeProfiles,
        activeProfileId: active?.id || null,
        currentProfileName: currentProfileName
      }, () => {
        this.loadChatHistory()
      })
    } catch (err) {
      console.error('获取画像列表失败:', err)
    }
  },

  handleProfileCommand(e) {
    const action = e.currentTarget.dataset.action
    if (action === 'new') {
      this.setData({ showNewProfileDialog: true })
    } else if (action === 'manage') {
      this.setData({ showProfileList: true })
    } else if (action === 'dropdown') {
      this.setData({ showProfileDropdown: !this.data.showProfileDropdown })
    }
  },

  closeProfileDropdown() {
    this.setData({ showProfileDropdown: false })
  },

  async handleCreateProfile() {
    const { newProfileName } = this.data
    if (!newProfileName.trim()) {
      wx.showToast({ title: '请输入画像名称', icon: 'none' })
      return
    }
    
    try {
      await request({
        url: API.STUDENT.PROFILES,
        method: 'POST',
        data: { profile_name: newProfileName.trim() }
      })
      this.setData({ newProfileName: '', showNewProfileDialog: false })
      await this.fetchProfiles()
      await this.loadProfile()
      await this.loadChatHistory()
      wx.showToast({ title: '新画像创建成功', icon: 'success' })
    } catch (err) {
      wx.showToast({ title: '创建失败', icon: 'none' })
    }
  },

  async handleActivateProfile(e) {
    const id = e.currentTarget.dataset.id
    try {
      await request({
        url: `${API.STUDENT.PROFILES}/${id}/activate`,
        method: 'POST'
      })
      await this.fetchProfiles()
      await this.loadProfile()
      await this.loadChatHistory()
      this.setData({ showProfileList: false, showProfileDropdown: false })
      const pathResult = await request({ url: API.STUDENT.INIT_STATUS, method: 'GET' })
      this.setData({ 
        hasPath: !!pathResult?.has_path,
        needsWorkflow: false,
        workflowRunning: false
      })
      wx.showToast({ title: '已切换画像', icon: 'success' })
    } catch (err) {
      wx.showToast({ title: '切换失败', icon: 'none' })
    }
  },

  async handleArchiveProfile(e) {
    const id = e.currentTarget.dataset.id
    wx.showModal({
      title: '确认归档',
      content: '确定要归档该画像吗？',
      success: async (res) => {
        if (res.confirm) {
          try {
            await request({
              url: `${API.STUDENT.PROFILES}/${id}/archive`,
              method: 'POST'
            })
            await this.fetchProfiles()
            wx.showToast({ title: '已归档', icon: 'success' })
          } catch (err) {
            wx.showToast({ title: '归档失败', icon: 'none' })
          }
        }
      }
    })
  },

  async handleRestoreProfile(e) {
    const id = e.currentTarget.dataset.id
    try {
      await request({
        url: `${API.STUDENT.PROFILES}/${id}/restore`,
        method: 'POST'
      })
      await this.fetchProfiles()
      wx.showToast({ title: '已恢复', icon: 'success' })
    } catch (err) {
      wx.showToast({ title: '恢复失败', icon: 'none' })
    }
  },

  startEditProfileName(e) {
    const { id, name } = e.currentTarget.dataset
    this.setData({
      editingProfileId: parseInt(id),
      editingProfileName: name
    })
  },

  async saveProfileName(e) {
    const { editingProfileId, editingProfileName } = this.data
    if (!editingProfileId || !editingProfileName.trim()) {
      this.setData({ editingProfileId: null })
      return
    }
    
    try {
      await request({
        url: `${API.STUDENT.PROFILES}/${editingProfileId}`,
        method: 'PUT',
        data: { profile_name: editingProfileName.trim() }
      })
      this.setData({ editingProfileId: null })
      await this.fetchProfiles()
      await this.loadProfile()
    } catch (err) {
      wx.showToast({ title: '修改失败', icon: 'none' })
    }
  },

  closeProfileList() {
    this.setData({ showProfileList: false })
  },

  closeNewProfileDialog() {
    this.setData({ showNewProfileDialog: false, newProfileName: '' })
  },

  openEditDialog() {
    const { profileData } = this.data
    this.setData({
      showEditDialog: true,
      editData: {
        major: profileData.major || '',
        grade: profileData.grade || '',
        goal: profileData.goal || '',
        level: profileData.level || '',
        style: profileData.style || '',
        coding: profileData.coding || '',
        interests: [...(profileData.interests || [])]
      },
      newInterestTag: ''
    })
  },

  cancelProfileEdit() {
    this.setData({ showEditDialog: false })
  },

  onEditInput(e) {
    const field = e.currentTarget.dataset.field
    this.setData({
      [`editData.${field}`]: e.detail.value
    })
  },

  onNewInterestInput(e) {
    this.setData({ newInterestTag: e.detail.value })
  },

  addTag(e) {
    const type = e.currentTarget.dataset.type
    const { editData, newInterestTag } = this.data
    const tagValue = newInterestTag
    const trimmed = (tagValue || '').trim()
    if (!trimmed) {
      wx.showToast({ title: '请输入标签内容', icon: 'none' })
      return
    }
    const list = [...(editData[type] || [])]
    if (list.includes(trimmed)) {
      wx.showToast({ title: '标签已存在', icon: 'none' })
      return
    }
    list.push(trimmed)
    this.setData({
      [`editData.${type}`]: list,
      newInterestTag: ''
    })
  },

  removeTag(e) {
    const { type, index } = e.currentTarget.dataset
    const list = [...(this.data.editData[type] || [])]
    list.splice(index, 1)
    this.setData({ [`editData.${type}`]: list })
  },

  async saveProfileEdit() {
    const { editData, activeProfileId } = this.data
    const data = {
      major: (editData.major || '').trim(),
      grade: (editData.grade || '').trim(),
      goal: (editData.goal || '').trim(),
      learning_style: (editData.style || '').trim(),
      coding_ability: (editData.coding || '').trim(),
      interests: editData.interests || []
    }
    try {
      const url = activeProfileId
        ? `${API.STUDENT.PROFILES}/${activeProfileId}`
        : API.STUDENT.PROFILE
      await request({
        url: url,
        method: 'PUT',
        data
      })
      this.setData({ showEditDialog: false })
      await this.loadProfile()
      wx.showToast({ title: '画像已更新', icon: 'success' })
    } catch (err) {
      wx.showToast({ title: '更新失败', icon: 'none' })
    }
  }
})