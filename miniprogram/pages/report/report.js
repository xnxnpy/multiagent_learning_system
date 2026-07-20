const { request } = require('../../utils/request')
const { API } = require('../../utils/api')
const { markdownToHtml } = require('../../utils/markdown')

Page({
  data: {
    loading: false,
    currentDate: '',
    reportData: {
      score: 0,
      rank: '-',
      totalQuestions: 0,
      correctRate: 0,
      studyHours: 0,
      completedModules: 0,
      suggestion: ''
    },
    knowledgePoints: [],
    overallGrade: 'N/A',
    masteryLevel: 0,
    analysis: {},
    summary: {},
    summaryStats: {
      totalStudy: '0分',
      avgDaily: 0
    },
    dailyTrend: [],
    behaviorPie: []
  },

  onLoad() {
    this.fetchReport()
  },

  onShow() {
    this.fetchReport()
  },

  async fetchReport() {
    this.setData({ loading: true })
    try {
      const [reportRes, summaryRes] = await Promise.all([
        request({ url: API.STUDENT.EVALUATION_REPORT, method: 'GET' }),
        request({ url: API.STUDENT.PROGRESS_SUMMARY, method: 'GET' }).catch(() => null)
      ])

      const date = new Date()
      const formattedDate = `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')} ${String(date.getHours()).padStart(2, '0')}:${String(date.getMinutes()).padStart(2, '0')}`

      if (reportRes) {
        const knowledgePoints = (reportRes.knowledge_points || []).map((kp, idx) => {
          const mastery = kp.mastery || 0
          const status = mastery >= 0.8 ? '掌握' : mastery >= 0.6 ? '学习中' : '薄弱'
          return {
            id: kp.topic || idx + 1,
            name: kp.topic || `知识点 ${idx + 1}`,
            score: kp.score || 0,
            total: kp.total || 100,
            mastery: mastery,
            masteryPercent: Math.round(mastery * 100),
            status: status,
            masteryClass: mastery >= 0.8 ? 'success' : mastery >= 0.6 ? 'warning' : 'exception',
            statusClass: status === '掌握' ? 'success' : status === '学习中' ? 'warning' : 'danger'
          }
        })

        const analysis = reportRes.analysis || {}

        this.setData({
          currentDate: formattedDate,
          reportData: {
            score: reportRes.total_score || 0,
            rank: '-',
            totalQuestions: reportRes.total_attempts || 0,
            correctRate: Math.round((reportRes.accuracy_rate || 0) * 100),
            studyHours: 0,
            completedModules: knowledgePoints.filter(kp => kp.status === '掌握').length,
            suggestion: reportRes.report || '',
          suggestionHtml: markdownToHtml(reportRes.report || '')
          },
          knowledgePoints,
          overallGrade: reportRes.overall_grade || 'N/A',
          masteryLevel: Math.round((reportRes.mastery_level || 0) * 100),
          analysis
        })
      }

      if (summaryRes) {
        this.setData({ summary: summaryRes })
        this.calculateSummaryStats(summaryRes)
        this.processTrendData(summaryRes)
        this.processBehaviorData(summaryRes)
      }
    } catch (err) {
      console.error('加载评估报告失败:', err)
      this.setData({ currentDate: new Date().toLocaleString() })
    } finally {
      this.setData({ loading: false })
    }
  },

  calculateSummaryStats(summary) {
    const totalSec = summary.total_study_time || 0
    const hours = Math.floor(totalSec / 3600)
    const mins = Math.floor((totalSec % 3600) / 60)
    const totalStudy = hours > 0 ? `${hours}时${mins}分` : `${mins}分`
    
    const daily = summary.daily_stats || []
    const totalDaily = daily.reduce((s, d) => s + (d.duration || 0), 0)
    const avgDaily = daily.length > 0 ? Math.round(totalDaily / daily.length / 60) : 0

    this.setData({
      summaryStats: { totalStudy, avgDaily }
    })
  },

  processTrendData(summary) {
    const daily = summary.daily_stats || []
    const trend = daily.map(d => ({
      date: d.date?.slice(5) || '',
      minutes: Math.round((d.duration || 0) / 60)
    }))
    const maxMinutes = Math.max(...trend.map(d => d.minutes), 1)
    this.setData({ dailyTrend: trend, maxTrendMinutes: maxMinutes })
  },

  processBehaviorData(summary) {
    const counts = summary.event_type_counts || {}
    const typeLabels = {
      question: '答题',
      resource_view: '资源浏览',
      code_execute: '代码运行',
      resource_page: '页面访问',
      stage_start: '阶段学习',
      stage_complete: '阶段完成',
      chat_message: '辅导对话',
      profile_chat: '画像对话'
    }
    const pieData = Object.entries(counts)
      .map(([k, v]) => ({ name: typeLabels[k] || k, value: v }))
      .filter(d => d.value > 0)
    const total = pieData.reduce((s, d) => s + d.value, 0)
    this.setData({ behaviorPie: pieData, totalBehaviorCount: total })
  },

  getPieStart(index) {
    const pie = this.data.behaviorPie || []
    let start = 0
    for (let i = 0; i < index; i++) {
      start += (pie[i].value / this.data.totalBehaviorCount) * 360
    }
    return start
  },

  getPieAngle(index) {
    const pie = this.data.behaviorPie || []
    return (pie[index].value / this.data.totalBehaviorCount) * 360
  },

  getPieColor(index) {
    const colors = ['#6366f1', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#06b6d4', '#ec4899', '#84cc16']
    return colors[index % colors.length]
  },

  progressStatus(mastery) {
    if (!mastery) return 'exception'
    if (mastery >= 0.8) return 'success'
    if (mastery >= 0.6) return 'warning'
    return 'exception'
  },

  statusClass(status) {
    const map = { '掌握': 'success', '学习中': 'warning', '薄弱': 'danger' }
    return map[status] || 'info'
  },

  async refreshReport() {
    wx.showLoading({ title: '刷新中...' })
    try {
      await this.fetchReport()
      wx.hideLoading()
      wx.showToast({ title: '报告已更新', icon: 'success' })
    } catch (err) {
      wx.hideLoading()
      wx.showToast({ title: '刷新失败', icon: 'none' })
    }
  },

  async runEvaluation() {
    wx.showLoading({ title: '评估中...' })
    try {
      await request({
        url: API.STUDENT.EVALUATION_RUN,
        method: 'POST'
      })

      wx.hideLoading()
      await this.fetchReport()
      wx.showToast({ title: '评估完成', icon: 'success' })
    } catch (err) {
      wx.hideLoading()
      wx.showToast({ title: '评估失败', icon: 'none' })
    }
  },

  updateProfile() {
    wx.switchTab({ url: '/pages/profile/profile' })
  },

  replanPath() {
    wx.switchTab({ url: '/pages/path/path' })
  },

  practiceAgain() {
    wx.switchTab({ url: '/pages/resource/resource' })
  }
})