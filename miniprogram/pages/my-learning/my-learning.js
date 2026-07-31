const { request } = require('../../utils/request')
const { API } = require('../../utils/api')

Page({
  data: {
    activeTab: 0,
    tabs: ['① 我的画像', '② 学习路径', '③ 学习资源', '④ 辅导对话', '⑤ 学习评估'],
    
    profile: null,
    learningPath: null,
    resources: {},
    formattedResources: {},
    evaluation: null,
    formattedEvaluation: {},
    tutorSessions: [],
    
    activeResourceTab: 0,
    resourceTabs: ['学习文档', '思维导图', '练习题目', '代码示例', '教学视频', '拓展阅读', '术语词汇', '知识关联', '学习总结']
  },

  onLoad() {
    this.loadAllData()
  },

  onShow() {
    this.loadAllData()
  },

  async loadAllData() {
    wx.showLoading({ title: '加载中...' })
    try {
      const [profileRes, pathRes, resRes, evalRes, tutorRes] = await Promise.allSettled([
        request({ url: API.STUDENT.PROFILE, method: 'GET' }),
        request({ url: API.STUDENT.LEARNING_PATH, method: 'GET' }),
        request({ url: API.STUDENT.RESOURCES, method: 'GET' }),
        request({ url: API.STUDENT.EVALUATION_REPORT, method: 'GET' }),
        request({ url: API.TUTOR.SESSIONS, method: 'GET' })
      ])

      if (profileRes.status === 'fulfilled') {
        this.setData({ profile: profileRes.value })
      }
      if (pathRes.status === 'fulfilled') {
        this.setData({ learningPath: pathRes.value })
      }
      if (resRes.status === 'fulfilled') {
        this.setData({ resources: resRes.value })
        this.formatResources(resRes.value)
      }
      if (evalRes.status === 'fulfilled') {
        this.setData({ evaluation: evalRes.value })
        this.formatEvaluation(evalRes.value)
      }
      if (tutorRes.status === 'fulfilled') {
        const sessionsData = tutorRes.value?.sessions || []
        // 逐个拉取每个会话的真实聊天历史
        const historyRequests = sessionsData.map(s =>
          request({
            url: '/tutor/history/' + s.session_id,
            method: 'GET'
          }).then(res => ({ session_id: s.session_id, messages: res?.messages || [] }))
            .catch(() => ({ session_id: s.session_id, messages: [] }))
        )
        const histories = await Promise.all(historyRequests)
        const sessions = histories
          .filter(h => h.messages.length > 0)
          .map((h, idx) => ({
            key: h.session_id,
            id: idx + 1,
            messages: h.messages.map(m => ({
              role: m.role || 'ai',
              content: m.display_content || m.content || ''
            }))
          }))
        this.setData({ tutorSessions: sessions })
      }
    } catch (err) {
      console.error('加载学习记录失败:', err)
    } finally {
      wx.hideLoading()
    }
  },

  switchTab(e) {
    const index = parseInt(e.currentTarget.dataset.index)
    this.setData({ activeTab: index })
  },

  switchResourceTab(e) {
    const index = parseInt(e.currentTarget.dataset.index)
    this.setData({ activeResourceTab: index })
  },

  viewStageDetail(e) {
    const id = e.currentTarget.dataset.id
    wx.navigateTo({ url: `/pages/resource/resource?stage_id=${id}` })
  },

  goToResources() {
    wx.switchTab({ url: '/pages/resource/resource' })
  },

  goToTutor() {
    wx.switchTab({ url: '/pages/tutor/tutor' })
  },

  goToReport() {
    wx.switchTab({ url: '/pages/report/report' })
  },

  goToProfile() {
    wx.switchTab({ url: '/pages/profile/profile' })
  },

  formatResources(data) {
    const formatted = {}
    
    if (data.document) {
      const doc = typeof data.document === 'string' ? data.document : (data.document.content || '暂无内容')
      formatted.documentText = doc.substring(0, 500) + '...'
    }
    
    if (data.mindmap_markdown) {
      formatted.mindmapText = data.mindmap_markdown
    } else if (data.mindmap) {
      formatted.mindmapText = JSON.stringify(data.mindmap)
    }
    
    if (data.questions && data.questions.questions && data.questions.questions.length > 0) {
      formatted.questionsList = data.questions.questions
    }
    
    if (data.code) {
      formatted.codeTitle = data.code.title || ''
      formatted.codeDifficulty = data.code.difficulty || ''
      formatted.codeDescription = data.code.description || ''
      formatted.codeCode = data.code.code || ''
    }
    
    if (data.video_script) {
      const vs = typeof data.video_script === 'string' ? JSON.parse(data.video_script) : data.video_script
      const script = vs.video_script || vs
      formatted.videoTitle = script.title || vs.title || '教学视频脚本'
      if (script.scenes && script.scenes.length > 0) {
        formatted.videoScenes = script.scenes
      } else if (vs.content) {
        formatted.videoContent = vs.content
      }
    }
    
    if (data.ppt_video) {
      const pv = typeof data.ppt_video === 'string' ? JSON.parse(data.ppt_video) : data.ppt_video
      formatted.videoUrl = pv.video_url || ''
      formatted.videoDuration = pv.duration || pv.video_duration || ''
      formatted.videoPages = pv.pages_count || 0
    }
    
    if (data.reading_material) {
      const content = typeof data.reading_material === 'string' ? data.reading_material : (data.reading_material.content || '暂无内容')
      formatted.readingText = content.substring(0, 500) + '...'
    }
    
    if (data.glossary && data.glossary.terms && data.glossary.terms.length > 0) {
      formatted.glossaryTerms = data.glossary.terms
    }
    
    if (data.knowledge_link) {
      const nodes = data.knowledge_link.nodes || []
      const edges = data.knowledge_link.edges || []
      formatted.knowledgeNodeCount = nodes.length
      formatted.knowledgeEdgeCount = edges.length
      formatted.knowledgeNodes = nodes
    }
    
    if (data.summary) {
      const content = typeof data.summary === 'string' ? data.summary : (data.summary.content || '暂无内容')
      formatted.summaryText = content.substring(0, 500) + '...'
    }
    
    this.setData({ formattedResources: formatted })
  },

  formatEvaluation(data) {
    const formatted = {}
    
    if (data) {
      formatted.totalScore = data.total_score || 0
      formatted.accuracyRate = Math.round((data.accuracy_rate || 0) * 100)
      formatted.masteryLevel = Math.round((data.mastery_level || 0) * 100)
      formatted.overallGrade = data.overall_grade || 'N/A'
      formatted.overallGradeFirst = data.overall_grade ? data.overall_grade.charAt(0) : ''
      
      if (data.analysis) {
        formatted.strengths = data.analysis.strengths || []
        formatted.weaknesses = data.analysis.weaknesses || []
        formatted.suggestions = data.analysis.suggestions || []
      }
    }
    
    this.setData({ formattedEvaluation: formatted })
  }
})