const { request, BASE_URL } = require('../../utils/request')
const { API, replaceParams } = require('../../utils/api')
const { markdownToHtml, renderCodeBlock } = require('../../utils/markdown')

Page({
  data: {
    hasResources: false,
    isGenerating: false,
    currentAgent: '',
    currentTopic: '',
    activeTab: 0,
    tabs: [
      { icon: '📄', name: '学习文档' },
      { icon: '🎬', name: '教学视频' },
      { icon: '🧠', name: '思维导图' },
      { icon: '📝', name: '练习题目' },
      { icon: '💻', name: '代码示例' },
      { icon: '📖', name: '拓展阅读' },
      { icon: '📚', name: '术语词汇' },
      { icon: '🔗', name: '知识关联' },
      { icon: '📊', name: '学习总结' }
    ],
    documents: [],
    videos: [],
    mindmaps: [],
    exercises: [],
    codeExamples: [],
    readingMaterials: [],
    glossaries: [],
    knowledgeLinks: [],
    summaries: [],
    stageId: null,
    profileInfo: {},
    filteredResources: [],
    qualityGate: {},
    regeneratingType: '',
    answers: {},
    submittedAnswers: {},
    viewMode: 'single',
    selectedQuestionIdx: 0,
    showFloatChat: false,
    floatChatHistory: [],
    floatInputValue: '',
    floatTyping: false
  },

  onLoad(options) {
    const stageId = options?.stage_id
    this.setData({ stageId })
    this.loadResources()
  },

  onShow() {
    this.loadResources()
  },

  async loadResources() {
    const { stageId } = this.data
    const params = stageId ? { stage_id: stageId } : {}

    try {
      const [result, profileRes] = await Promise.all([
        request({ url: API.STUDENT.RESOURCES, method: 'GET', data: params }),
        request({ url: API.STUDENT.PROFILE, method: 'GET' })
      ])

      try {
        this.parseResources(result || {})
      } catch (parseErr) {
        console.error('parseResources 执行失败:', parseErr)
        this.setData({ hasResources: false })
      }
      
      if (profileRes) {
        this.setData({
          profileInfo: {
            major: profileRes.major || '',
            level: profileRes.knowledge_level || '',
            goal: profileRes.goal || '',
            weakness: profileRes.weakness || []
          },
          currentTopic: profileRes.goal || profileRes.major || ''
        })
      }

      if (result && result.filteredResources) {
        this.setData({ filteredResources: result.filteredResources })
      }
    } catch (err) {
      console.error('加载资源失败:', err)
      this.setData({ hasResources: false })
    }
  },

  parseResources(data) {
    let documents = []
    let videos = []
    let mindmaps = []
    let exercises = []
    let codeExamples = []
    let readingMaterials = []
    let glossaries = []
    let knowledgeLinks = []
    let summaries = []
    let filteredResources = []

    if (data.filteredResources && data.filteredResources.length > 0) {
      filteredResources = data.filteredResources
    }

    if (data.document) {
      try {
        const docContent = typeof data.document === 'string' ? JSON.parse(data.document) : data.document
        if (docContent.content && typeof docContent.content === 'string') {
          const processedImages = []
          if (docContent.images && Array.isArray(docContent.images)) {
            docContent.images.forEach(img => {
              if (img.base64) {
                processedImages.push({
                  src: `data:image/png;base64,${img.base64}`,
                  description: img.description || ''
                })
              } else if (img.url) {
                processedImages.push({
                  src: img.url,
                  description: img.description || ''
                })
              }
            })
          }

          // 提取 mermaid 代码块
          const mermaidBlocks = []
          const mermaidRegex = /```mermaid\n([\s\S]*?)```/g
          let match
          while ((match = mermaidRegex.exec(docContent.content)) !== null) {
            mermaidBlocks.push(match[1].trim())
          }

          documents.push({
            id: 1,
            title: docContent.topic || docContent.title || '学习文档',
            description: docContent.description || '',
            preview: docContent.content.substring(0, 100) + '...',
            difficulty: docContent.difficulty || '中等',
            content: docContent.content,
            htmlContent: (() => {
              try {
                return markdownToHtml(docContent.content)
              } catch(e) {
                console.error('markdown转换失败:', e)
                return docContent.content || ''
              }
            })(),
            images: processedImages,
            mermaidBlocks: mermaidBlocks
          })
        }
      } catch (e) {
        console.error('文档处理失败:', e)
      }
    }

    if (data.ppt_video) {
      const videoContent = typeof data.ppt_video === 'string' ? JSON.parse(data.ppt_video) : data.ppt_video
      videos.push({
        id: 1,
        title: videoContent.title || videoContent.topic || '教学视频',
        description: videoContent.description || '',
        duration: videoContent.duration || videoContent.video_duration || '',
        durationSeconds: videoContent.duration_seconds || 0,
        pagesCount: videoContent.pages_count || 0,
        video_url: videoContent.video_url || ''
      })
    }

    if (data.mindmap) {
      const mindmapData = typeof data.mindmap === 'string' ? JSON.parse(data.mindmap) : data.mindmap
      const mindmapSource = mindmapData.mindmap_markdown || mindmapData.mindmap || ''
      if (mindmapSource) {
        const mindmapContent = typeof mindmapSource === 'string' ? mindmapSource : JSON.stringify(mindmapSource)
        mindmaps.push({
          id: 1,
          title: '思维导图',
          content: mindmapContent,
          mindmapImg: ''
        })
      }
    }

    if (data.questions) {
      const questionsContent = typeof data.questions === 'string' ? JSON.parse(data.questions) : data.questions
      const qList = questionsContent.questions || questionsContent.question_list || questionsContent || []
      exercises = qList.map((q, idx) => {
        const diff = q.difficulty || 'medium'
        return {
          id: q.question_id || q.id || idx + 1,
          questionId: q.question_id || q.id || idx + 1,
          title: q.title || `题目 ${idx + 1}`,
          description: q.description || '',
          difficulty: diff,
          difficultyClass: diff === 'hard' ? 'danger' : diff === 'medium' ? 'warning' : 'success',
          question: q.question || q.content || '',
          questionHtml: markdownToHtml(q.question || q.content || ''),
          options: q.options || [],
          answer: q.answer || '',
          explanation: q.explanation || '',
          explanationHtml: markdownToHtml(q.explanation || ''),
          type: q.type || 'choice',
          score: q.score || 10,
          test_cases: q.test_cases || [],
          rubric: q.rubric || null
        }
        })
      } else {
        console.warn('data.questions 为空')
      }

    if (data.code) {
      const codeContent = typeof data.code === 'string' ? JSON.parse(data.code) : data.code
      const examples = codeContent.examples || codeContent.code_examples || []
      if (examples.length > 0) {
        codeExamples = examples.map((ex, idx) => ({
          id: idx + 1,
          title: ex.title || `代码示例 ${idx + 1}`,
          description: ex.description || '',
          language: ex.language || 'Python',
          code: ex.code || '',
          codeHtml: renderCodeBlock(ex.code || '', ex.language || 'python'),
          input_example: ex.input_example || '',
          expected_output: ex.expected_output || '',
          test_cases: ex.test_cases || []
        }))
      } else if (codeContent.code && typeof codeContent.code === 'string') {
        codeExamples.push({
          id: 1,
          title: codeContent.title || codeContent.topic || '代码示例',
          description: codeContent.description || '',
          language: codeContent.language || 'Python',
          code: codeContent.code,
          codeHtml: renderCodeBlock(codeContent.code, codeContent.language || 'python'),
          input_example: codeContent.input_example || '',
          expected_output: codeContent.expected_output || '',
          test_cases: codeContent.test_cases || []
        })
      }
    }

    if (data.reading_material) {
      const readingContent = typeof data.reading_material === 'string' ? JSON.parse(data.reading_material) : data.reading_material
      if (readingContent.content && typeof readingContent.content === 'string') {
        readingMaterials.push({
          id: 1,
          title: readingContent.title || readingContent.topic || '拓展阅读',
          description: readingContent.description || '',
          content: readingContent.content,
          htmlContent: markdownToHtml(readingContent.content),
          preview: readingContent.content.substring(0, 150) + '...'
        })
      }
    }

    if (data.glossary) {
      const glossaryContent = typeof data.glossary === 'string' ? JSON.parse(data.glossary) : data.glossary
      if (glossaryContent.terms && glossaryContent.terms.length > 0) {
        glossaries = glossaryContent.terms.map((term, idx) => ({
          id: idx + 1,
          term: term.term || '',
          definition: term.definition || '',
          definitionHtml: markdownToHtml(term.definition || ''),
          example: term.example || '',
          related_terms: term.related_terms || []
        }))
      }
    }

    if (data.knowledge_link) {
      const linkContent = typeof data.knowledge_link === 'string' ? JSON.parse(data.knowledge_link) : data.knowledge_link
      if (linkContent.nodes && linkContent.nodes.length > 0) {
        knowledgeLinks.push({
          id: 1,
          title: linkContent.title || '知识点关联图',
          nodes: linkContent.nodes,
          edges: linkContent.edges || [],
          kgImg: ''
        })
      }
    }

    if (data.summary) {
      const summaryContent = typeof data.summary === 'string' ? JSON.parse(data.summary) : data.summary
      if (summaryContent.content && typeof summaryContent.content === 'string') {
        summaries.push({
          id: 1,
          title: summaryContent.title || summaryContent.topic || '学习总结',
          description: summaryContent.description || '',
          content: summaryContent.content,
          htmlContent: markdownToHtml(summaryContent.content),
          preview: summaryContent.content.substring(0, 150) + '...'
        })
      }
    }

    const qualityGate = {}
    filteredResources.forEach(r => {
      qualityGate[r.type] = {
        hasIssue: true,
        score: r.score || '--'
      }
    })

    this.setData({
      hasResources: documents.length > 0 || videos.length > 0 || mindmaps.length > 0 || exercises.length > 0 || 
                    codeExamples.length > 0 || readingMaterials.length > 0 || glossaries.length > 0 || 
                    knowledgeLinks.length > 0 || summaries.length > 0,
      documents,
      videos,
      mindmaps,
      exercises,
      codeExamples,
      readingMaterials,
      glossaries,
      knowledgeLinks,
      summaries,
      filteredResources,
      qualityGate,
      answers: {},
      submittedAnswers: {},
      selectedQuestionIdx: 0,
      viewMode: 'single'
    })
  },

  async generateResources() {
    let { stageId } = this.data

    if (!stageId) {
      try {
        const pathResult = await request({
          url: API.STUDENT.LEARNING_PATH,
          method: 'GET'
        })
        if (pathResult.stages && pathResult.stages.length > 0) {
          stageId = pathResult.stages[0].stage_id
        } else {
          wx.showToast({ title: '请先生成学习路径', icon: 'none' })
          return
        }
      } catch (err) {
        console.error('获取学习路径失败:', err)
        wx.showToast({ title: '获取学习路径失败', icon: 'none' })
        return
      }
    }

    this.setData({ isGenerating: true, currentAgent: '文档Agent', stageId })

    const agents = ['文档Agent', '视频Agent', '题库Agent', '代码Agent', '思维导图Agent', '阅读材料Agent', '术语词汇Agent', '知识关联Agent', '学习总结Agent']
    let index = 0

    const interval = setInterval(() => {
      if (index < agents.length) {
        this.setData({ currentAgent: agents[index] })
        index++
      }
    }, 800)

    try {
      await request({
        url: API.STUDENT.GENERATE_STAGE_RESOURCES,
        method: 'POST',
        data: { stage_id: stageId }
      })

      clearInterval(interval)
      this.setData({ isGenerating: false })
      await this.loadResources()
      wx.showToast({ title: '资源生成成功', icon: 'success' })
    } catch (err) {
      clearInterval(interval)
      this.setData({ isGenerating: false })
      console.error('生成资源失败:', err)
      wx.showToast({ title: '生成资源失败', icon: 'none' })
    }
  },

  refreshResources() {
    this.generateResources()
  },

  switchTab(e) {
    const index = e.currentTarget.dataset.index
    this.setData({ activeTab: index })
    if (index === 2) {
      setTimeout(() => { this.renderMindmapCanvas() }, 300)
    } else if (index === 7) {
      setTimeout(() => { this.renderKnowledgeGraphCanvas() }, 300)
    }
  },

  goToPath() {
    wx.switchTab({ url: '/pages/path/path' })
  },

  openTutor() {
    wx.switchTab({ url: '/pages/tutor/tutor' })
  },

  toggleFloatChat() {
    if (!this.data.showFloatChat) {
      this.setData({ showFloatChat: true })
      if (this.data.floatChatHistory.length === 0) {
        this.initFloatChat()
      }
      this.connectFloatWebSocket()
    } else {
      this.setData({ showFloatChat: false })
      this.closeFloatWebSocket()
    }
  },

  closeFloatChat() {
    this.setData({ showFloatChat: false })
    this.closeFloatWebSocket()
  },

  initFloatChat() {
    this.setData({
      floatChatHistory: [{
        id: 1, role: 'ai', content: '您好！我是您的AI辅导助手，请问有什么学习问题？',
        renderedHtml: markdownToHtml('您好！我是您的AI辅导助手，请问有什么学习问题？')
      }]
    })
  },

  connectFloatWebSocket() {
    if (this._floatWs) return
    const token = wx.getStorageSync('access_token') || ''
    const wsUrl = BASE_URL.replace('http', 'ws') + '/tutor/ws/chat?token=' + token

    this._floatWs = wx.connectSocket({ url: wsUrl })

    this._floatWs.onOpen(() => {
      this._floatConnected = true
    })

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
          wx.showToast({ title: data.message || '发生错误', icon: 'none' })
        }
      } catch (e) {}
    })

    this._floatWs.onClose(() => { this._floatConnected = false })
    this._floatWs.onError(() => { this._floatConnected = false })
  },

  closeFloatWebSocket() {
    if (this._floatWs) {
      this._floatWs.close()
      this._floatWs = null
      this._floatConnected = false
    }
  },

  onFloatInput(e) {
    this.setData({ floatInputValue: e.detail.value })
  },

  sendFloatQuestion() {
    const { floatInputValue, floatChatHistory } = this.data
    if (!floatInputValue.trim()) return

    const userMsg = { id: Date.now(), role: 'user', content: floatInputValue }
    const aiMsg = { id: Date.now() + 1, role: 'ai', content: '', renderedHtml: '', _streaming: true }

    this.setData({
      floatChatHistory: [...floatChatHistory, userMsg, aiMsg],
      floatInputValue: '',
      floatTyping: true
    })

    if (this._floatWs && this._floatConnected) {
      this._floatWs.send({
        data: JSON.stringify({
          type: 'query',
          question: floatInputValue,
          session_id: this._floatSessionId || ''
        })
      })
    } else {
      this.connectFloatWebSocket()
      setTimeout(() => {
        if (this._floatWs && this._floatConnected) {
          this._floatWs.send({
            data: JSON.stringify({
              type: 'query',
              question: floatInputValue,
              session_id: ''
            })
          })
        }
      }, 500)
    }
  },

  readDocument(e) {
    const id = e.currentTarget.dataset.id
    const doc = this.data.documents.find(d => d.id === id)
    if (doc) {
      wx.showModal({
        title: doc.title,
        content: doc.content.length > 500 ? doc.content.substring(0, 500) + '...' : doc.content,
        showCancel: false,
        confirmText: '关闭'
      })
    }
  },

  playVideo(e) {
    const id = e.currentTarget.dataset.id
    const video = this.data.videos.find(v => v.id === id)
    if (video && video.video_url) {
      wx.navigateTo({ url: `/pages/video-player/video-player?url=${encodeURIComponent(video.video_url)}&title=${encodeURIComponent(video.title)}` })
    } else {
      wx.showToast({ title: '视频正在生成中', icon: 'none' })
    }
  },

  viewMindmap(e) {
    const content = e.currentTarget.dataset.content
    const title = e.currentTarget.dataset.title || '思维导图'
    if (content) {
      wx.navigateTo({ url: `/pages/mindmap/mindmap?content=${encodeURIComponent(content)}&title=${encodeURIComponent(title)}` })
    }
  },

  viewKnowledgeGraph(e) {
    const nodes = e.currentTarget.dataset.nodes
    const edges = e.currentTarget.dataset.edges
    const title = e.currentTarget.dataset.title || '知识图谱'
    if (nodes) {
      const kgData = {
        title: title,
        nodes: typeof nodes === 'string' ? JSON.parse(nodes) : nodes,
        edges: typeof edges === 'string' ? JSON.parse(edges) : edges || []
      }
      wx.navigateTo({ url: `/pages/kg/kg?data=${encodeURIComponent(JSON.stringify(kgData))}` })
    }
  },

  parseMindmapTree(markdown) {
    if (!markdown) return null
    const lines = markdown.split('\n').filter(l => l.trim())
    if (!lines.length) return null
    
    const root = { text: '', children: [] }
    const stack = [{ level: 0, children: root.children }]
    let hasHeaders = false
    
    for (const line of lines) {
      if (!line.trim()) continue
      const trimmed = line.trim()
      
      const headerMatch = trimmed.match(/^(#{1,6})\s+(.+)$/)
      if (headerMatch) {
        hasHeaders = true
        const level = headerMatch[1].length
        const text = headerMatch[2].replace(/\*\*/g, '').trim()
        if (!text) continue
        
        while (stack.length > 1 && stack[stack.length - 1].level >= level) {
          stack.pop()
        }
        
        const node = { text, children: [] }
        stack[stack.length - 1].children.push(node)
        stack.push({ level, children: node.children })
      } else {
        // 普通文本行（如 - 列表项）
        const text = trimmed.replace(/^[-*+•]\s*/, '').replace(/\*\*/g, '').trim()
        if (!text) continue
        
        const node = { text, children: [] }
        stack[stack.length - 1].children.push(node)
      }
    }
    
    // 设置根节点
    if (root.children.length > 0) {
      if (hasHeaders) {
        // 有 # 标题：第一个 # 节点作为 root
        root.text = root.children[0].text
        root.children = root.children[0].children
      }
    } else if (lines.length > 0) {
      // 无 # 标题：按缩进解析
      root.children = []
      stack.length = 0
      stack.push({ level: -1, children: root.children })
      
      for (const line of lines) {
        if (!line.trim()) continue
        const indent = line.search(/\S/)
        const text = line.trim().replace(/^[-*+•]\s*/, '').replace(/\*\*/g, '').trim()
        if (!text) continue
        const level = Math.floor(indent / 2)
        
        while (stack.length > 1 && stack[stack.length - 1].level >= level) {
          stack.pop()
        }
        
        const node = { text, children: [] }
        stack[stack.length - 1].children.push(node)
        stack.push({ level, children: node.children })
      }
      
      if (root.children.length > 0) {
        root.text = root.children[0].text
        root.children = root.children[0].children
      }
    }
    
    return root
  },

  renderMindmapCanvas() {
    const { mindmaps } = this.data
    if (!mindmaps.length || !mindmaps[0].content) return

    const tree = this.parseMindmapTree(mindmaps[0].content)
    if (!tree) return

    const colors = ['#4F46E5', '#10B981', '#F59E0B', '#EF4444', '#8B5CF6', '#EC4899']
    const nodeW = 130, nodeH = 30, hGap = 50, vGap = 25, pad = 60
    let nid = 0
    const nodes = [], conns = []

    const subH = (n) => {
      if (!n.children || !n.children.length) return nodeH
      return Math.max(nodeH, n.children.reduce((s, c) => s + subH(c), 0) + (n.children.length - 1) * vGap)
    }

    const layout = (n, cx, cy, lv) => {
      const color = colors[lv % colors.length]
      const fromIdx = nid
      nodes.push({ id: nid++, text: n.text, x: cx - nodeW / 2, y: cy - nodeH / 2, color })
      if (!n.children || !n.children.length) return
      let curY = cy - (subH(n) - nodeH) / 2
      n.children.forEach(ch => {
        const chH = subH(ch)
        const chX = cx + nodeW + hGap
        const chY = curY + chH / 2
        const toIdx = nid
        conns.push({ x1: cx + nodeW / 2, y1: cy, x2: chX - nodeW / 2, y2: chY, color, fromIdx, toIdx: -1 })
        layout(ch, chX, chY, lv + 1)
        conns[conns.length - 1].toIdx = toIdx
        curY += chH + vGap
      })
    }

    const totalH = subH(tree)
    layout(tree, pad + nodeW / 2, pad + totalH / 2, 0)

    let maxX = 0, maxY = 0
    nodes.forEach(n => { maxX = Math.max(maxX, n.x + nodeW + 20); maxY = Math.max(maxY, n.y + nodeH + 20) })
    const rawW = maxX + pad
    const rawH = maxY + pad

    const W = rawW, H = rawH

    this._mindmapNodes = nodes
    this._mindmapConns = conns
    this._mindmapW = W
    this._mindmapH = H

    const query = wx.createSelectorQuery()
    query.select('#mindmapCanvasTouch').fields({ node: true, size: true }).exec((res) => {
      if (!res[0]) return
      const { node } = res[0]
      const sysInfo = wx.getWindowInfo ? wx.getWindowInfo() : wx.getSystemInfoSync()
      const ctx = node.getContext('2d')
      const dpr = sysInfo.pixelRatio || 2
      node.width = W * dpr; node.height = H * dpr
      ctx.scale(dpr, dpr)
      this._mindmapCtx = ctx
      this._drawMindmap()
    })
  },

  _drawMindmap(highlightIdx) {
    const ctx = this._mindmapCtx
    const nodes = this._mindmapNodes
    const conns = this._mindmapConns
    const W = this._mindmapW, H = this._mindmapH
    const nodeW = 130, nodeH = 30
    if (!ctx || !nodes) return
    ctx.clearRect(0, 0, W, H)

    // 画连线
    if (conns) {
      conns.forEach(c => {
        const isHL = highlightIdx !== undefined && (c.fromIdx === highlightIdx || c.toIdx === highlightIdx)
        ctx.beginPath()
        ctx.moveTo(c.x1, c.y1)
        ctx.lineTo(c.x2, c.y2)
        ctx.strokeStyle = isHL ? '#6366F1' : '#CBD5E1'
        ctx.lineWidth = isHL ? 2.5 : 1.5
        ctx.stroke()
      })
    }

    // 画节点
    nodes.forEach((n, i) => {
      const isHL = i === highlightIdx
      ctx.fillStyle = isHL ? '#1D4ED8' : n.color
      const r = 8, x = n.x, y = n.y, w = nodeW, h = nodeH
      ctx.beginPath()
      ctx.moveTo(x + r, y); ctx.lineTo(x + w - r, y)
      ctx.arcTo(x + w, y, x + w, y + r, r); ctx.lineTo(x + w, y + h - r)
      ctx.arcTo(x + w, y + h, x + w - r, y + h, r); ctx.lineTo(x + r, y + h)
      ctx.arcTo(x, y + h, x, y + h - r, r); ctx.lineTo(x, y + r)
      ctx.arcTo(x, y, x + r, y, r); ctx.closePath(); ctx.fill()
      if (isHL) { ctx.strokeStyle = '#1D4ED8'; ctx.lineWidth = 3; ctx.stroke() }
      ctx.fillStyle = '#fff'; ctx.font = 'bold 11px sans-serif'
      ctx.textAlign = 'center'; ctx.textBaseline = 'middle'
      const txt = n.text.length > 6 ? n.text.substring(0, 6) + '..' : n.text
      ctx.fillText(txt, x + w / 2, y + h / 2)
    })
  },

  onMindmapTouch(e) {
    const t = e.touches[0]
    const nodeW = 130, nodeH = 30
    const nodes = this._mindmapNodes || []
    // 获取 Canvas 在页面中的位置
    const query = wx.createSelectorQuery()
    query.select('#mindmapCanvasTouch').boundingClientRect().exec((res) => {
      if (!res[0]) return
      const rect = res[0]
      const x = t.clientX - rect.left
      const y = t.clientY - rect.top
      for (let i = 0; i < nodes.length; i++) {
        const n = nodes[i]
        if (x >= n.x && x <= n.x + nodeW && y >= n.y && y <= n.y + nodeH) {
          this._drawMindmap(i)
          wx.showToast({ title: n.text, icon: 'none', duration: 1500 })
          break
        }
      }
    })
  },
  onMindmapMove() {},
  onMindmapEnd() {},

  renderKnowledgeGraphCanvas() {
    const { knowledgeLinks } = this.data
    if (!knowledgeLinks.length) return
    const link = knowledgeLinks[0]
    if (!link.nodes || !link.nodes.length) return

    const colors = ['#F59E0B', '#3B82F6', '#10B981', '#8B5CF6', '#EF4444', '#EC4899', '#06B6D4']
    const W = 700, H = 500

    const nodes = link.nodes.map((n, i) => ({
      id: n.id, label: n.label || n.id, level: n.level || 0,
      x: W / 2 + (Math.random() - 0.5) * W * 0.6,
      y: H / 2 + (Math.random() - 0.5) * H * 0.6,
      vx: 0, vy: 0, color: colors[i % colors.length]
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
      if (link.edges) {
        link.edges.forEach(e => {
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

    this._kgNodes = nodes
    this._kgEdges = link.edges
    this._kgNodeMap = nodeMap
    this._kgW = W
    this._kgH = H

    const query = wx.createSelectorQuery()
    query.select('#kgCanvasTouch').fields({ node: true, size: true }).exec((res) => {
      if (!res[0]) return
      const { node } = res[0]
      const sysInfo = wx.getWindowInfo ? wx.getWindowInfo() : wx.getSystemInfoSync()
      const ctx = node.getContext('2d')
      const dpr = sysInfo.pixelRatio || 2
      node.width = W * dpr; node.height = H * dpr
      ctx.scale(dpr, dpr)
      this._kgCtx = ctx
      this._drawKnowledgeGraph()
    })
  },

  _drawKnowledgeGraph(highlightId) {
    const ctx = this._kgCtx
    const nodes = this._kgNodes, edges = this._kgEdges
    const W = this._kgW, H = this._kgH
    if (!ctx || !nodes) return
    ctx.clearRect(0, 0, W, H)

    if (edges) {
      edges.forEach(e => {
        const a = this._kgNodeMap[e.source || e.from], b = this._kgNodeMap[e.target || e.to]
        if (a && b) {
          ctx.beginPath(); ctx.moveTo(a.x, a.y); ctx.lineTo(b.x, b.y)
          ctx.strokeStyle = (highlightId && (e.source === highlightId || e.target === highlightId)) ? '#374151' : '#D1D5DB'
          ctx.lineWidth = (highlightId && (e.source === highlightId || e.target === highlightId)) ? 2 : 1
          ctx.stroke()
        }
      })
    }

    nodes.forEach(n => {
      const r = Math.max(10, 18 - (n.level || 0) * 2)
      const isHighlight = n.id === highlightId
      ctx.beginPath(); ctx.arc(n.x, n.y, isHighlight ? r + 3 : r, 0, Math.PI * 2)
      ctx.fillStyle = isHighlight ? '#1D4ED8' : n.color; ctx.fill()
      if (isHighlight) { ctx.strokeStyle = '#fff'; ctx.lineWidth = 3; ctx.stroke() }
      ctx.fillStyle = '#374151'; ctx.font = '10px sans-serif'
      ctx.textAlign = 'center'; ctx.textBaseline = 'middle'
      const txt = n.label.length > 5 ? n.label.substring(0, 5) + '..' : n.label
      ctx.fillText(txt, n.x, n.y + r + 12)
    })
  },

  onKgTouch(e) {
    const t = e.touches[0]
    const nodes = this._kgNodes || []
    const query = wx.createSelectorQuery()
    query.select('#kgCanvasTouch').boundingClientRect().exec((res) => {
      if (!res[0]) return
      const rect = res[0]
      const x = t.clientX - rect.left
      const y = t.clientY - rect.top
      for (let i = 0; i < nodes.length; i++) {
        const n = nodes[i]
        const r = Math.max(10, 18 - (n.level || 0) * 2)
        const dx = x - n.x, dy = y - n.y
        if (dx * dx + dy * dy <= (r + 5) * (r + 5)) {
          this._drawKnowledgeGraph(n.id)
          wx.showToast({ title: n.label, icon: 'none', duration: 1500 })
          break
        }
      }
    })
  },
  onKgMove() {},
  onKgEnd() {},

  viewMermaid(e) {
    const code = e.currentTarget.dataset.code
    if (code) {
      wx.navigateTo({ url: `/pages/mermaid/mermaid?code=${encodeURIComponent(code)}` })
    }
  },

  viewDiagram(e) {
    const code = e.currentTarget.dataset.code
    const lang = e.currentTarget.dataset.lang || 'mermaid'
    if (code) {
      wx.navigateTo({ url: `/pages/mermaid/mermaid?code=${encodeURIComponent(code)}&lang=${encodeURIComponent(lang)}` })
    }
  },

  selectQuestion(e) {
    const idx = e.currentTarget.dataset.index
    this.setData({ selectedQuestionIdx: idx })
  },

  switchViewMode(e) {
    const mode = e.currentTarget.dataset.mode
    this.setData({ viewMode: mode })
  },

  onAnswerInput(e) {
    const questionId = e.currentTarget.dataset.questionId
    const value = e.detail.value
    const answers = { ...this.data.answers }
    answers[questionId] = value
    this.setData({ answers })
  },

  selectOption(e) {
    const questionId = e.currentTarget.dataset.questionId
    const option = e.currentTarget.dataset.option
    const answers = { ...this.data.answers }
    answers[questionId] = option
    this.setData({ answers })
  },

  async submitAnswer(e) {
    const questionId = e.currentTarget.dataset.questionId
    const question = this.data.exercises.find(q => q.questionId === questionId)
    const answer = this.data.answers[questionId]
    
    if (!question || !answer) {
      wx.showToast({ title: '请先作答', icon: 'none' })
      return
    }

    wx.showLoading({ title: '提交中...' })
    try {
      const result = await request({
        url: API.STUDENT.QUESTION_SUBMIT,
        method: 'POST',
        data: {
          question_id: questionId,
          answer: answer,
          topic: question.title
        }
      })

      wx.hideLoading()
      const submittedAnswers = { ...this.data.submittedAnswers }
      const evaluation = (result.evaluations && result.evaluations[0]) || {}
      submittedAnswers[questionId] = {
        answer: answer,
        correct: evaluation.correct || false,
        score: evaluation.score || 0,
        feedback: evaluation.feedback || ''
      }
      this.setData({ submittedAnswers })

      const isCorrect = evaluation.correct || false
      const evalScore = evaluation.score || 0
      const status = isCorrect ? 'success' : 'error'
      const message = isCorrect ? `回答正确！得分：${evalScore}/${question.score}` : (evaluation.feedback || `回答错误。正确答案：${question.answer}`)
      wx.showToast({ title: message, icon: status === 'success' ? 'success' : 'none' })
    } catch (err) {
      wx.hideLoading()
      wx.showToast({ title: '提交失败', icon: 'none' })
    }
  },

  async runCode(e) {
    const id = e.currentTarget.dataset.id
    const codeExample = this.data.codeExamples.find(c => c.id === id)
    if (!codeExample) return

    wx.showLoading({ title: '运行中...' })
    try {
      const result = await request({
        url: API.STUDENT.CODE_RUN,
        method: 'POST',
        data: {
          code: codeExample.code,
          timeout: 30
        }
      })

      wx.hideLoading()
      const output = result.stdout || result.stderr || result.error || '无输出'
      wx.showModal({
        title: codeExample.title + ' - 运行结果',
        content: output,
        showCancel: false
      })
    } catch (err) {
      wx.hideLoading()
      wx.showToast({ title: '运行失败', icon: 'none' })
    }
  },

  getFilteredInfo(resourceType) {
    const { filteredResources } = this.data
    if (!filteredResources || !filteredResources.length) return null
    const typeMap = {
      document: 'document', questions: 'questions', code: 'code',
      mindmap: 'mindmap', video: 'video', reading_material: 'reading_material',
      glossary: 'glossary', knowledge_link: 'knowledge_link', summary: 'summary'
    }
    const mappedType = typeMap[resourceType] || resourceType
    return filteredResources.find(r => r.type === mappedType)
  },

  isFiltered(resourceType) {
    return !!this.getFilteredInfo(resourceType)
  },

  async regenerateSingle(e) {
    const resourceType = e.currentTarget.dataset.type
    const { stageId } = this.data
    
    if (!stageId) {
      wx.showToast({ title: '请先选择阶段', icon: 'none' })
      return
    }

    const typeMap = {
      document: 'document', questions: 'questions', code: 'code',
      mindmap: 'mindmap', video: 'ppt_video', reading_material: 'reading_material',
      glossary: 'glossary', knowledge_link: 'knowledge_link', summary: 'summary'
    }

    wx.showModal({
      title: '确认重新生成',
      content: `确定要重新生成该类型资源吗？`,
      success: async (res) => {
        if (res.confirm) {
          this.setData({ regeneratingType: resourceType })
          try {
            const mappedType = typeMap[resourceType] || resourceType
            const url = replaceParams(API.STUDENT.REGENERATE_RESOURCE, { resource_type: mappedType })
            await request({
              url: url,
              method: 'POST',
              data: { stage_id: stageId }
            })
            await this.loadResources()
            wx.showToast({ title: '重新生成成功', icon: 'success' })
          } catch (err) {
            wx.showToast({ title: '重新生成失败', icon: 'none' })
          } finally {
            this.setData({ regeneratingType: '' })
          }
        }
      }
    })
  }
})