const { request, BASE_URL } = require('../../utils/request')
const { API } = require('../../utils/api')
const { VoiceInput } = require('../../utils/voice')
const { markdownToHtml } = require('../../utils/markdown')

Page({
  data: {
    hasPath: false,
    progressPercent: 0,
    completedStages: 0,
    totalStages: 0,
    estimatedDays: 0,
    stages: [],
    recommendations: [],
    pathTitle: '',
    currentStageData: null,
    currentStageIndex: 0,
    knowledgeGraphData: null,
    kgLoading: false,
    kgImg: '',
    stageGenerating: false,
    showFloatChat: false,
    floatChatHistory: [],
    floatInputValue: '',
    floatTyping: false,
    floatPendingImage: '',
    floatPendingImageBase64: '',
    floatPendingImageName: '',
    floatPendingImageSize: 0,
    floatPendingImageOCR: '',
    floatIsRecording: false,
    floatIsVoiceLoading: false,
    floatRecordingTime: 0,
    progressTagClass: '',
    progressTagText: ''
  },

  onLoad() {
    this.loadPathData()
  },

  onShow() {
    this.loadPathData()
  },

  async loadPathData() {
    try {
      const result = await request({
        url: API.STUDENT.LEARNING_PATH,
        method: 'GET'
      })

      if (result) {
        const stagesData = result.stages || []
        const completedStages = result.completed_stages || []
        
        const resourceTypeMap = { document: '文档', video: '视频', code: '代码', mindmap: '思维导图', question: '练习题' }
        const stages = stagesData.map(stage => {
          const status = completedStages.includes(stage.stage_id) ? 'completed' : 
                        stagesData.indexOf(stage) === 0 && !completedStages.includes(stagesData[0]?.stage_id) ? 'current' : 'pending'
          const rawTypes = stage.recommended_resource_types || []
          return {
            id: stage.stage_id || stage.id,
            title: stage.title || '',
            description: stage.description || '',
            duration: stage.estimated_hours ? `${stage.estimated_hours}小时` : '',
            resources: stage.resources_count || 0,
            exercises: stage.exercises_count || 0,
            status: status,
            statusClass: status === 'completed' ? 'completed' : status === 'current' ? 'current' : '',
            clickableClass: (status === 'completed' || status === 'current') ? 'clickable' : '',
            nodeClass: status === 'completed' ? 'completed' : status === 'current' ? 'current' : 'hollow',
            tagClass: status === 'completed' ? 'success' : status === 'current' ? 'primary' : 'info',
            tagText: status === 'completed' ? '已完成' : status === 'current' ? '进行中' : '未开始',
            knowledge_points: (stage.knowledge_points || []).map(kp => typeof kp === 'string' ? { name: kp } : kp),
            recommended_resource_types: rawTypes,
            resource_type_texts: rawTypes.map(t => resourceTypeMap[t] || t)
          }
        })

        const completedCount = completedStages.length
        const totalCount = stagesData.length
        const progressPercent = totalCount > 0 ? Math.round((completedCount / totalCount) * 100) : 0
        
        const currentStageIndex = completedCount < totalCount ? completedCount : totalCount - 1
        const currentStageData = stages[currentStageIndex] || null
        
        const progressTagClass = completedCount >= totalCount ? 'success' : 'primary'
        const progressTagText = completedCount >= totalCount ? '全部完成' : `阶段 ${currentStageIndex + 1}/${totalCount}`

        this.setData({
          hasPath: true,
          stages,
          completedStages: completedCount,
          totalStages: totalCount,
          progressPercent,
          pathTitle: result.title || '个性化学习路径',
          recommendations: this.generateRecommendations(stages),
          currentStageData,
          currentStageIndex,
          progressTagClass,
          progressTagText
        })

        await this.loadKnowledgeGraph()
      } else {
        this.setData({ hasPath: false })
      }
    } catch (err) {
      console.error('加载学习路径失败:', err)
      this.setData({ hasPath: false })
    }
  },

  async loadKnowledgeGraph() {
    this.setData({ kgLoading: true })
    try {
      const result = await request({
        url: API.STUDENT.KNOWLEDGE_GRAPH,
        method: 'GET',
        data: { stage_id: 0 }
      })
      if (result && result.nodes && result.nodes.length > 0) {
        this.setData({ knowledgeGraphData: result })
        setTimeout(() => { this.renderKnowledgeGraph() }, 800)
      }
    } catch (err) {
      console.error('加载知识图谱失败:', err)
    } finally {
      this.setData({ kgLoading: false })
    }
  },

  async generateKnowledgeGraph() {
    const { pathTitle, stages } = this.data
    if (!pathTitle) {
      wx.showToast({ title: '请先生成学习路径', icon: 'none' })
      return
    }

    this.setData({ kgLoading: true })
    try {
      const result = await request({
        url: API.STUDENT.GENERATE_KNOWLEDGE_GRAPH,
        method: 'POST',
        data: { topic: pathTitle }
      })
      if (result) {
        this.setData({ knowledgeGraphData: result })
        setTimeout(() => { this.renderKnowledgeGraph() }, 800)
        wx.showToast({ title: '知识图谱生成成功', icon: 'success' })
      }
    } catch (err) {
      console.error('生成知识图谱失败:', err)
      wx.showToast({ title: '生成失败，请重试', icon: 'none' })
    } finally {
      this.setData({ kgLoading: false })
    }
  },

  renderKnowledgeGraph() {
    const { knowledgeGraphData } = this.data
    if (!knowledgeGraphData || !knowledgeGraphData.nodes || !knowledgeGraphData.nodes.length) return

    const colors = ['#F59E0B', '#3B82F6', '#10B981', '#8B5CF6', '#EF4444', '#EC4899', '#06B6D4']
    const W = 700, H = 500

    const nodes = knowledgeGraphData.nodes.map((n, i) => ({
      id: n.id, label: n.label || n.id, level: n.level || 0,
      x: W / 2 + (Math.random() - 0.5) * W * 0.6,
      y: H / 2 + (Math.random() - 0.5) * H * 0.6,
      vx: 0, vy: 0,
      color: colors[i % colors.length]
    }))

    const nodeMap = {}
    nodes.forEach(n => { nodeMap[n.id] = n })

    const repulsion = 800, attraction = 0.01, damping = 0.9, centerForce = 0.01
    for (let iter = 0; iter < 150; iter++) {
      for (let i = 0; i < nodes.length; i++) {
        for (let j = i + 1; j < nodes.length; j++) {
          let dx = nodes[j].x - nodes[i].x, dy = nodes[j].y - nodes[i].y
          let dist = Math.sqrt(dx * dx + dy * dy) || 1
          let force = repulsion / (dist * dist)
          let fx = (dx / dist) * force, fy = (dy / dist) * force
          nodes[i].vx -= fx; nodes[i].vy -= fy
          nodes[j].vx += fx; nodes[j].vy += fy
        }
      }
      if (knowledgeGraphData.edges) {
        knowledgeGraphData.edges.forEach(e => {
          const a = nodeMap[e.source || e.from], b = nodeMap[e.target || e.to]
          if (!a || !b) return
          let dx = b.x - a.x, dy = b.y - a.y
          let dist = Math.sqrt(dx * dx + dy * dy) || 1
          let force = (dist - 100) * attraction
          let fx = (dx / dist) * force, fy = (dy / dist) * force
          a.vx += fx; a.vy += fy; b.vx -= fx; b.vy -= fy
        })
      }
      nodes.forEach(n => {
        n.vx += (W / 2 - n.x) * centerForce
        n.vy += (H / 2 - n.y) * centerForce
      })
      nodes.forEach(n => {
        n.vx *= damping; n.vy *= damping
        n.x += n.vx; n.y += n.vy
        n.x = Math.max(40, Math.min(W - 40, n.x))
        n.y = Math.max(40, Math.min(H - 40, n.y))
      })
    }

    const query = wx.createSelectorQuery()
    query.select('#pathKgCanvas').fields({ node: true, size: true }).exec((res) => {
      if (!res[0]) return
      const { node } = res[0]
      const ctx = node.getContext('2d')
      const dpr = wx.getWindowInfo ? wx.getWindowInfo().pixelRatio : 2
      node.width = W * dpr; node.height = H * dpr
      ctx.scale(dpr, dpr)
      ctx.clearRect(0, 0, W, H)

      if (knowledgeGraphData.edges) {
        knowledgeGraphData.edges.forEach(e => {
          const a = nodeMap[e.source || e.from], b = nodeMap[e.target || e.to]
          if (a && b) {
            ctx.beginPath(); ctx.moveTo(a.x, a.y); ctx.lineTo(b.x, b.y)
            ctx.strokeStyle = '#D1D5DB'; ctx.lineWidth = 1; ctx.stroke()
          }
        })
      }

      nodes.forEach(n => {
        const r = Math.max(10, 18 - (n.level || 0) * 2)
        ctx.beginPath(); ctx.arc(n.x, n.y, r, 0, Math.PI * 2)
        ctx.fillStyle = n.color; ctx.fill()
        ctx.fillStyle = '#374151'; ctx.font = '10px sans-serif'
        ctx.textAlign = 'center'; ctx.textBaseline = 'middle'
        const txt = n.label.length > 5 ? n.label.substring(0, 5) + '..' : n.label
        ctx.fillText(txt, n.x, n.y + r + 12)
      })

      setTimeout(() => {
        wx.canvasToTempFilePath({
          canvas: node,
          success: (r) => { this.setData({ kgImg: r.tempFilePath }) }
        })
      }, 300)
    })
  },

  async generateStageResources() {
    const { currentStageData } = this.data
    if (!currentStageData) {
      wx.showToast({ title: '请先选择阶段', icon: 'none' })
      return
    }

    this.setData({ stageGenerating: true })
    try {
      await request({
        url: API.STUDENT.GENERATE_STAGE_RESOURCES,
        method: 'POST',
        data: { stage_id: currentStageData.id }
      })
      await this.loadPathData()
      wx.showToast({ title: '资源生成成功', icon: 'success' })
    } catch (err) {
      console.error('生成本阶段资源失败:', err)
      wx.showToast({ title: '生成失败，请重试', icon: 'none' })
    } finally {
      this.setData({ stageGenerating: false })
    }
  },

  async completeStage() {
    const { currentStageData, stages } = this.data
    if (!currentStageData || currentStageData.status === 'completed') {
      return
    }

    try {
      await request({
        url: API.STUDENT.COMPLETE_STAGE,
        method: 'POST',
        data: { stage_id: currentStageData.id }
      })
      await this.loadPathData()
      wx.showToast({ title: '阶段已完成', icon: 'success' })
    } catch (err) {
      console.error('完成阶段失败:', err)
      wx.showToast({ title: '操作失败', icon: 'none' })
    }
  },

  resourceText(rt) {
    const map = { document: '文档', video: '视频', code: '代码', mindmap: '思维导图', question: '练习题' }
    return map[rt] || rt
  },

  generateRecommendations(stages) {
    const pendingStages = stages.filter(s => s.status === 'pending')
    if (pendingStages.length === 0) return []

    return [
      {
        id: 1,
        icon: '📊',
        title: '继续下一阶段',
        description: `建议开始学习「${pendingStages[0].title}」`
      },
      {
        id: 2,
        icon: '🎯',
        title: '复习薄弱环节',
        description: '根据学习进度，建议复习已完成阶段的知识点'
      }
    ]
  },

  async generatePath() {
    wx.showLoading({ title: '生成中...' })

    try {
      const result = await request({
        url: API.STUDENT.GENERATE_PATH,
        method: 'POST'
      })

      wx.hideLoading()
      await this.loadPathData()
      wx.showToast({ title: '路径生成成功', icon: 'success' })
    } catch (err) {
      wx.hideLoading()
      wx.showToast({ title: '生成失败，请重试', icon: 'none' })
    }
  },

  refreshPath() {
    wx.showLoading({ title: '刷新中...' })
    setTimeout(async () => {
      await this.loadPathData()
      wx.hideLoading()
      wx.showToast({ title: '刷新成功', icon: 'success' })
    }, 500)
  },

  goToProfile() {
    wx.switchTab({ url: '/pages/profile/profile' })
  },

  openTutor() {
    wx.switchTab({ url: '/pages/tutor/tutor' })
  },

  toggleFloatChat() {
    if (!this.data.showFloatChat) {
      this.setData({ showFloatChat: true })
      if (this.data.floatChatHistory.length === 0) {
        this.setData({
          floatChatHistory: [{
            id: 1, role: 'ai', content: '您好！我是您的AI辅导助手，支持文字、语音、图片提问。请问有什么学习问题？',
            renderedHtml: markdownToHtml('您好！我是您的AI辅导助手，支持文字、语音、图片提问。请问有什么学习问题？')
          }]
        })
      }
      this.initFloatVoice()
      this.connectFloatWs()
    } else {
      this.setData({ showFloatChat: false })
      this.closeFloatWs()
      if (this.floatVoiceInput) this.floatVoiceInput.destroy()
    }
  },

  closeFloatChat() {
    this.setData({ showFloatChat: false })
    this.closeFloatWs()
    if (this.floatVoiceInput) this.floatVoiceInput.destroy()
  },

  /* ===================== 浮动语音输入 ===================== */

  initFloatVoice() {
    this.floatVoiceInput = new VoiceInput({
      maxDuration: 60,
      onStart: () => {
        this.setData({ floatIsRecording: true, floatIsVoiceLoading: false, floatRecordingTime: 0 })
      },
      onRecording: (time) => {
        this.setData({ floatRecordingTime: time })
      },
      onLoading: (loading) => {
        this.setData({ floatIsVoiceLoading: loading })
      },
      onResult: (text) => {
        this.setData({
          floatIsRecording: false, floatIsVoiceLoading: false, floatRecordingTime: 0,
          floatInputValue: text
        })
      },
      onError: (msg) => {
        this.setData({ floatIsRecording: false, floatIsVoiceLoading: false, floatRecordingTime: 0 })
        console.error('浮动语音错误:', msg)
      },
      onCancel: () => {
        this.setData({ floatIsRecording: false, floatIsVoiceLoading: false, floatRecordingTime: 0 })
      }
    })
    this.floatVoiceInput.init()
  },

  startFloatVoice() {
    if (this.floatVoiceInput) this.floatVoiceInput.start()
  },

  stopFloatVoice() {
    if (this.floatVoiceInput) this.floatVoiceInput.stop()
  },

  /* ===================== 浮动图片上传 ===================== */

  chooseFloatImage() {
    const that = this
    wx.chooseMedia({
      count: 1,
      mediaType: ['image'],
      sizeType: ['compressed'],
      sourceType: ['album', 'camera'],
      success: (res) => {
        const file = res.tempFiles[0]
        that.setData({
          floatPendingImage: file.tempFilePath,
          floatPendingImageName: file.tempFilePath.split('/').pop() || 'image.jpg',
          floatPendingImageSize: file.size || 0
        })
        that.uploadFloatImageAndOCR(file.tempFilePath)
      },
      fail: (err) => {
        if (err.errMsg && !err.errMsg.includes('cancel')) {
          wx.showToast({ title: '选择图片失败', icon: 'none' })
        }
      }
    })
  },

  uploadFloatImageAndOCR(tempFilePath) {
    const that = this
    wx.showLoading({ title: '识别中...', mask: true })

    wx.getFileSystemManager().readFile({
      filePath: tempFilePath,
      encoding: 'base64',
      success: (res) => {
        that.setData({ floatPendingImageBase64: res.data })
      }
    })

    const token = wx.getStorageSync('access_token') || ''
    wx.uploadFile({
      url: `${BASE_URL}/student/ocr/recognize`,
      filePath: tempFilePath,
      name: 'file',
      header: { 'Authorization': `Bearer ${token}` },
      success: (resp) => {
        wx.hideLoading()
        try {
          const data = JSON.parse(resp.data)
          if (resp.statusCode === 200 && data && data.text) {
            that.setData({ floatPendingImageOCR: data.text })
          } else {
            that.setData({ floatPendingImageOCR: '' })
          }
        } catch (e) {
          that.setData({ floatPendingImageOCR: '' })
        }
        wx.showToast({ title: '图片添加成功', icon: 'success', duration: 1500 })
      },
      fail: () => {
        wx.hideLoading()
        that.setData({ floatPendingImageOCR: '' })
        wx.showToast({ title: '图片添加成功', icon: 'success', duration: 1500 })
      }
    })
  },

  removeFloatImage() {
    this.setData({
      floatPendingImage: '',
      floatPendingImageBase64: '',
      floatPendingImageName: '',
      floatPendingImageSize: 0,
      floatPendingImageOCR: ''
    })
  },

  previewFloatImage(e) {
    const url = e.currentTarget.dataset.url
    if (url) wx.previewImage({ urls: [url], current: url })
  },

  /* ===================== 浮动 WebSocket ===================== */

  connectFloatWs() {
    if (this._floatWs) return
    const token = wx.getStorageSync('access_token') || ''
    const wsUrl = BASE_URL.replace('http', 'ws') + API.TUTOR.WS_CHAT + '?token=' + token
    this._floatWs = wx.connectSocket({ url: wsUrl })
    this._floatWs.onOpen(() => { this._floatConnected = true })
    this._floatWs.onMessage((res) => {
      try {
        const data = JSON.parse(res.data)
        if (data.type === 'chunk') {
          const msgs = [...this.data.floatChatHistory]
          const last = msgs[msgs.length - 1]
          if (last && last.role === 'ai' && last._streaming) {
            last.content += data.data
            last.renderedHtml = markdownToHtml(last.content)
            this.setData({ floatChatHistory: msgs })
          }
        } else if (data.type === 'end') {
          this.setData({ floatTyping: false })
          if (data.session_id) this._floatSessionId = data.session_id
        } else if (data.type === 'error') {
          this.setData({ floatTyping: false })
        }
      } catch (e) {}
    })
    this._floatWs.onClose(() => { this._floatConnected = false })
    this._floatWs.onError(() => { this._floatConnected = false })
  },

  closeFloatWs() {
    if (this._floatWs) { this._floatWs.close(); this._floatWs = null; this._floatConnected = false }
  },

  onFloatInput(e) { this.setData({ floatInputValue: e.detail.value }) },

  sendFloatQuestion() {
    const { floatInputValue, floatChatHistory, floatPendingImage,
      floatPendingImageBase64, floatPendingImageName, floatPendingImageSize,
      floatPendingImageOCR } = this.data

    const displayContent = floatInputValue.trim()
    const hasText = displayContent.length > 0
    const hasImage = floatPendingImageBase64 && floatPendingImageBase64.length > 0

    if (!hasText && !hasImage) return

    // 构造发给大模型的完整查询（含OCR）
    let question = displayContent
    if (floatPendingImageOCR && floatPendingImageOCR.trim().length > 0) {
      if (displayContent) {
        question = `${displayContent}\n\n[图片OCR内容]:\n${floatPendingImageOCR}`
      } else {
        question = `[图片OCR内容]:\n${floatPendingImageOCR}`
      }
    }

    // 用户消息：显示原始输入（图片+文字），不含OCR
    const userMsg = {
      id: Date.now(), role: 'user',
      content: displayContent || (hasImage ? '[图片]' : ''),
      imageUrl: floatPendingImage || undefined
    }

    const aiMsg = { id: Date.now() + 1, role: 'ai', content: '', _streaming: true }

    this.setData({
      floatChatHistory: [...floatChatHistory, userMsg, aiMsg],
      floatInputValue: '', floatTyping: true,
      floatPendingImage: '', floatPendingImageBase64: '',
      floatPendingImageName: '', floatPendingImageSize: 0,
      floatPendingImageOCR: ''
    })

    const send = () => {
      if (this._floatWs && this._floatConnected) {
        const msg = {
          type: 'query',
          question: question,
          display_content: displayContent,
          session_id: this._floatSessionId || ''
        }
        if (hasImage) {
          msg.image_base64 = floatPendingImageBase64
          msg.image_name = floatPendingImageName
          msg.image_size = floatPendingImageSize
        }
        this._floatWs.send({ data: JSON.stringify(msg) })
      }
    }

    if (this._floatWs && this._floatConnected) {
      // 立即发送（使用已缓存的变量）
      const msg = {
        type: 'query',
        question: question,
        display_content: displayContent,
        session_id: this._floatSessionId || ''
      }
      if (hasImage) {
        msg.image_base64 = floatPendingImageBase64
        msg.image_name = floatPendingImageName
        msg.image_size = floatPendingImageSize
      }
      this._floatWs.send({ data: JSON.stringify(msg) })
    } else {
      this.connectFloatWs()
      const msg = {
        type: 'query',
        question: question,
        display_content: displayContent,
        session_id: this._floatSessionId || ''
      }
      if (hasImage) {
        msg.image_base64 = floatPendingImageBase64
        msg.image_name = floatPendingImageName
        msg.image_size = floatPendingImageSize
      }
      setTimeout(() => {
        if (this._floatWs) this._floatWs.send({ data: JSON.stringify(msg) })
      }, 500)
    }
  },

  handleStageClick(e) {
    const { stageId, index } = e.currentTarget.dataset
    const stage = this.data.stages[index]
    if (!stage) return
    if (stage.status === 'completed' || stage.status === 'current') {
      this.setData({ currentStageIndex: parseInt(index), currentStageData: stage })
      wx.navigateTo({ url: `/pages/resource/resource?stage_id=${stageId}` })
    }
  },

  startStage(e) {
    const stageId = e.currentTarget.dataset.stage
    wx.navigateTo({ url: `/pages/resource/resource?stage_id=${stageId}` })
  },

  reviewStage(e) {
    const stageId = e.currentTarget.dataset.stage
    wx.navigateTo({ url: `/pages/resource/resource?stage_id=${stageId}` })
  },

  handleGenerate() {
    this.generatePath()
  },

  handleRefresh() {
    this.refreshPath()
  },

  handleCompleteStage() {
    this.completeStage()
  },

  handleGenerateStageResources() {
    this.generateStageResources()
  },

  handleGenerateKnowledgeGraph() {
    this.generateKnowledgeGraph()
  }
})