const { request } = require('../../utils/request')
const { API } = require('../../utils/api')

Page({
  data: {
    config: {
      app_name: '',
      debug: false,
      secret_key: '',
      jwt_expire_minutes: 1440,
      backend_host: '0.0.0.0',
      backend_port: 8000,
      quality_thresholds: {},
      ppt_video_max_pages: 10,
      tts_voice: 'x4_yezi'
    },
    thresholdLabels: {
      document: '学习文档', mindmap: '思维导图', code: '代码示例',
      question: '练习题目', reading_material: '拓展阅读', glossary: '术语词汇',
      knowledge_link: '知识关联', summary: '学习总结', ppt_video: 'PPT视频'
    },
    ttsVoices: [
      { id: 'x4_xiaoyan', name: '讯飞小燕（女）' },
      { id: 'x4_yezi', name: '讯飞小露（女）' },
      { id: 'aisjiuxu', name: '讯飞许久（男）' },
      { id: 'aisjinger', name: '讯飞小婧（女）' },
      { id: 'aisbabyxu', name: '讯飞许小宝（男）' }
    ],
    monitor: {
      cpu_percent: 0, memory_percent: 0,
      memory_used_mb: 0, memory_total_mb: 0, disk_percent: 0
    },
    stats: {
      total_users: 0, total_students: 0, total_teachers: 0,
      total_profiles: 0, total_learning_paths: 0
    },
    isSubmitting: false,
    monitorLoading: false,
    activeTab: 0,
    tabs: ['基础配置', '质量阈值', '资源生成', '系统监控']
  },

  onLoad() {
    this.fetchConfig()
    this.fetchMonitor()
    this.fetchStats()
  },

  onShow() {
    this.fetchMonitor()
  },

  async fetchConfig() {
    try {
      const res = await request({ url: API.ADMIN.CONFIG, method: 'GET' })
      const config = { ...this.data.config, ...res }
      // 确保 quality_thresholds 有默认值
      const thresholds = config.quality_thresholds || {}
      for (const key of Object.keys(this.data.thresholdLabels)) {
        if (!(key in thresholds)) thresholds[key] = 60
      }
      config.quality_thresholds = thresholds
      this.setData({ config })
    } catch (err) {
      console.error('获取配置失败:', err)
    }
  },

  async fetchMonitor() {
    this.setData({ monitorLoading: true })
    try {
      const res = await request({ url: API.ADMIN.MONITORING, method: 'GET' })
      this.setData({ monitor: res })
    } catch (err) {
      console.error('获取监控失败:', err)
    } finally {
      this.setData({ monitorLoading: false })
    }
  },

  async fetchStats() {
    try {
      const res = await request({ url: API.ADMIN.STATS, method: 'GET' })
      this.setData({ stats: res })
    } catch (err) {
      console.error('获取统计失败:', err)
    }
  },

  switchTab(e) {
    this.setData({ activeTab: parseInt(e.currentTarget.dataset.index) })
  },

  onInput(e) {
    const field = e.currentTarget.dataset.field
    const config = { ...this.data.config, [field]: e.detail.value }
    this.setData({ config })
  },

  onNumberInput(e) {
    const field = e.currentTarget.dataset.field
    const config = { ...this.data.config, [field]: parseInt(e.detail.value) || 0 }
    this.setData({ config })
  },

  onSwitch(e) {
    const field = e.currentTarget.dataset.field
    const config = { ...this.data.config, [field]: e.detail.value }
    this.setData({ config })
  },

  onThresholdChange(e) {
    const key = e.currentTarget.dataset.key
    const val = parseInt(e.detail.value)
    const config = { ...this.data.config }
    config.quality_thresholds = { ...config.quality_thresholds, [key]: val }
    this.setData({ config })
  },

  onTtsVoiceChange(e) {
    const idx = parseInt(e.detail.value)
    const config = { ...this.data.config, tts_voice: this.data.ttsVoices[idx].id }
    this.setData({ config })
  },

  onPptPagesChange(e) {
    const config = { ...this.data.config, ppt_video_max_pages: parseInt(e.detail.value) || 10 }
    this.setData({ config })
  },

  async saveConfig() {
    this.setData({ isSubmitting: true })
    wx.showLoading({ title: '保存中...' })
    try {
      const { config } = this.data
      await request({
        url: API.ADMIN.CONFIG,
        method: 'PUT',
        data: {
          app_name: config.app_name,
          debug: config.debug,
          jwt_expire_minutes: config.jwt_expire_minutes,
          backend_host: config.backend_host,
          backend_port: config.backend_port,
          quality_thresholds: config.quality_thresholds,
          ppt_video_max_pages: config.ppt_video_max_pages,
          tts_voice: config.tts_voice
        }
      })
      wx.hideLoading()
      wx.showToast({ title: '保存成功', icon: 'success' })
    } catch (err) {
      wx.hideLoading()
      wx.showToast({ title: '保存失败', icon: 'none' })
    } finally {
      this.setData({ isSubmitting: false })
    }
  },

  resetConfig() {
    wx.showModal({
      title: '确认重置',
      content: '确定要恢复默认配置吗？',
      success: async (res) => {
        if (res.confirm) {
          wx.showLoading({ title: '重置中...' })
          try {
            await request({ url: API.ADMIN.CONFIG, method: 'POST', data: { reset: true } })
            wx.hideLoading()
            await this.fetchConfig()
            wx.showToast({ title: '已重置', icon: 'success' })
          } catch (err) {
            wx.hideLoading()
            wx.showToast({ title: '重置失败', icon: 'none' })
          }
        }
      }
    })
  },

  getThresholdValue(key) {
    return this.data.config.quality_thresholds[key] || 60
  },

  getTtsVoiceIndex() {
    const { ttsVoices, config } = this.data
    const idx = ttsVoices.findIndex(v => v.id === config.tts_voice)
    return idx >= 0 ? idx : 1
  },

  goBack() {
    wx.navigateBack()
  }
})
