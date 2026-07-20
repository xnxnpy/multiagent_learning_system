const { request } = require('../../utils/request')
const { API, replaceParams } = require('../../utils/api')

Page({
  data: {
    securityConfig: { enabled: false },
    securityWords: [],
    securityLogs: [],
    reviewItems: [],
    reviewTotal: 0,
    newWord: '',
    wordCategory: 'black',
    activeTab: 0,
    tabs: ['安全配置', '敏感词管理', '审核日志', '内容审核'],
    isSubmitting: false,
    reviewLoading: false,
    reviewStatus: '',
    statusOptions: ['全部', 'pending', 'approved', 'rejected']
  },

  onLoad() {
    this.loadSecurityConfig()
    this.loadSecurityWords()
    this.loadSecurityLogs()
    this.loadReviewItems()
  },

  switchTab(e) {
    this.setData({ activeTab: parseInt(e.currentTarget.dataset.index) })
  },

  // ── 安全配置 ──
  async loadSecurityConfig() {
    try {
      const result = await request({ url: API.ADMIN.CONTENT_SECURITY, method: 'GET' })
      this.setData({ securityConfig: result })
    } catch (err) {
      console.error('加载安全配置失败:', err)
    }
  },

  onSwitch(e) {
    const securityConfig = { ...this.data.securityConfig, enabled: e.detail.value }
    this.setData({ securityConfig })
  },

  async saveConfig() {
    this.setData({ isSubmitting: true })
    wx.showLoading({ title: '保存中...' })
    try {
      await request({
        url: API.ADMIN.CONTENT_SECURITY,
        method: 'PUT',
        data: { enabled: this.data.securityConfig.enabled }
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

  // ── 敏感词管理 ──
  async loadSecurityWords() {
    try {
      const result = await request({ url: API.ADMIN.SECURITY_WORDS, method: 'GET' })
      const words = (result.items || []).map(w => ({
        id: w.id, word: w.word || '', category: w.category || 'black',
        created_at: w.created_at ? new Date(w.created_at).toLocaleString() : ''
      }))
      this.setData({ securityWords: words })
    } catch (err) {
      console.error('加载敏感词失败:', err)
    }
  },

  onWordInput(e) {
    this.setData({ newWord: e.detail.value })
  },

  selectCategory(e) {
    this.setData({ wordCategory: e.currentTarget.dataset.value })
  },

  async addWord() {
    const { newWord, wordCategory } = this.data
    if (!newWord.trim()) {
      wx.showToast({ title: '请输入敏感词', icon: 'none' })
      return
    }
    try {
      await request({
        url: API.ADMIN.SECURITY_WORDS,
        method: 'POST',
        data: { category: wordCategory, words: [newWord.trim()] }
      })
      wx.showToast({ title: '添加成功', icon: 'success' })
      this.setData({ newWord: '' })
      await this.loadSecurityWords()
    } catch (err) {
      wx.showToast({ title: '添加失败', icon: 'none' })
    }
  },

  async deleteWord(e) {
    const { id, word } = e.currentTarget.dataset
    wx.showModal({
      title: '确认删除', content: `确定要删除敏感词 "${word}" 吗？`,
      success: async (res) => {
        if (res.confirm) {
          try {
            await request({ url: API.ADMIN.SECURITY_WORDS, method: 'DELETE', data: { category: 'black', word } })
            wx.showToast({ title: '删除成功', icon: 'success' })
            await this.loadSecurityWords()
          } catch (err) {
            wx.showToast({ title: '删除失败', icon: 'none' })
          }
        }
      }
    })
  },

  // ── 审核日志 ──
  async loadSecurityLogs() {
    try {
      const result = await request({ url: API.ADMIN.SECURITY_LOGS, method: 'GET', data: { page: 1, page_size: 50 } })
      const logs = (result.items || []).map(l => ({
        id: l.id, message: l.message || '', category: l.category || '',
        timestamp: l.created_at ? new Date(l.created_at).toLocaleString() : ''
      }))
      this.setData({ securityLogs: logs })
    } catch (err) {
      console.error('加载审核日志失败:', err)
    }
  },

  // ── 内容审核 ──
  async loadReviewItems() {
    this.setData({ reviewLoading: true })
    try {
      const params = { page: 1, page_size: 50 }
      if (this.data.reviewStatus && this.data.reviewStatus !== '全部') {
        params.status = this.data.reviewStatus
      }
      const result = await request({ url: API.ADMIN.CONTENT_REVIEW, method: 'GET', data: params })
      const items = (result.items || []).map(r => ({
        id: r.id, content_type: r.content_type || '',
        content: r.content || '', status: r.status || 'pending',
        reviewer_id: r.reviewer_id || null,
        review_comment: r.review_comment || '',
        created_at: r.created_at ? new Date(r.created_at).toLocaleString() : '',
        statusText: r.status === 'approved' ? '已通过' : r.status === 'rejected' ? '已拒绝' : '待审核',
        statusClass: r.status === 'approved' ? 'success' : r.status === 'rejected' ? 'danger' : 'warning'
      }))
      this.setData({ reviewItems: items, reviewTotal: result.total || 0 })
    } catch (err) {
      console.error('加载审核内容失败:', err)
    } finally {
      this.setData({ reviewLoading: false })
    }
  },

  onReviewStatusChange(e) {
    const idx = parseInt(e.detail.value)
    this.setData({ reviewStatus: this.data.statusOptions[idx] })
    this.loadReviewItems()
  },

  async approveReview(e) {
    const id = e.currentTarget.dataset.id
    wx.showModal({
      title: '确认通过', content: '确定要通过该内容审核吗？',
      success: async (res) => {
        if (res.confirm) {
          try {
            await request({
              url: replaceParams(API.ADMIN.CONTENT_REVIEW_ACTION, { content_id: id }),
              method: 'PUT', data: { action: 'approve' }
            })
            wx.showToast({ title: '已通过', icon: 'success' })
            await this.loadReviewItems()
          } catch (err) {
            wx.showToast({ title: '操作失败', icon: 'none' })
          }
        }
      }
    })
  },

  async rejectReview(e) {
    const id = e.currentTarget.dataset.id
    wx.showModal({
      title: '驳回原因', editable: true, placeholderText: '请输入驳回原因',
      success: async (res) => {
        if (res.confirm) {
          try {
            await request({
              url: replaceParams(API.ADMIN.CONTENT_REVIEW_ACTION, { content_id: id }),
              method: 'PUT', data: { action: 'reject', comment: res.content || '' }
            })
            wx.showToast({ title: '已拒绝', icon: 'success' })
            await this.loadReviewItems()
          } catch (err) {
            wx.showToast({ title: '操作失败', icon: 'none' })
          }
        }
      }
    })
  },

  goBack() {
    wx.navigateBack()
  }
})
