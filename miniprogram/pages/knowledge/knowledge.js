const { request, getToken, BASE_URL } = require('../../utils/request')

Page({
  data: {
    loading: false,
    uploading: false,
    stats: { total_documents: 0, total_chunks: 0, failed: 0 },
    documents: [],
    page: 1,
    total: 0
  },

  onShow() {
    this.setData({ page: 1 })
    this.loadAll()
  },

  async loadAll() {
    await Promise.all([this.fetchStats(), this.fetchDocs()])
  },

  async fetchStats() {
    try {
      const res = await request({ url: API_PATH.STATS, method: 'GET' })
      this.setData({ stats: res || this.data.stats })
    } catch (e) { /* ignore */ }
  },

  async fetchDocs() {
    this.setData({ loading: true })
    try {
      const res = await request({
        url: API_PATH.DOCS,
        method: 'GET',
        data: { page: this.data.page, page_size: 20 }
      })
      this.setData({
        documents: res.items || [],
        total: res.total || 0
      })
    } catch (e) {
      this.setData({ documents: [] })
    } finally {
      this.setData({ loading: false })
    }
  },

  chooseAndUpload() {
    wx.chooseMessageFile({
      count: 3,
      type: 'file',
      extension: ['txt', 'md', 'markdown', 'pdf', 'docx', 'doc'],
      success: (res) => {
        const files = res.tempFiles || []
        if (!files.length) return
        this.uploadFiles(files)
      }
    })
  },

  async uploadFiles(files) {
    this.setData({ uploading: true })
    let ok = 0
    for (const f of files) {
      // 逐个上传（wx.uploadFile 单文件）
      // eslint-disable-next-line no-await-in-loop
      const success = await new Promise((resolve) => {
        wx.uploadFile({
          url: `${BASE_URL}/knowledge/upload`,
          filePath: f.path,
          name: 'files',
          header: { Authorization: `Bearer ${getToken()}` },
          success: (res) => {
            if (res.statusCode === 200 || res.statusCode === 201) {
              ok++
              resolve(true)
            } else {
              wx.showToast({ title: '上传失败', icon: 'none' })
              resolve(false)
            }
          },
          fail: () => {
            wx.showToast({ title: '上传失败', icon: 'none' })
            resolve(false)
          }
        })
      })
      if (!success) break
    }
    this.setData({ uploading: false })
    if (ok > 0) {
      wx.showToast({ title: `已上传 ${ok} 个`, icon: 'success' })
      setTimeout(() => this.loadAll(), 800)
    }
  },

  onDelete(e) {
    const id = e.currentTarget.dataset.id
    const name = e.currentTarget.dataset.name || ''
    wx.showModal({
      title: '删除文档',
      content: `删除「${name}」及其向量索引？`,
      success: async (r) => {
        if (!r.confirm) return
        try {
          await request({ url: `${API_PATH.DOCS}/${id}`, method: 'DELETE' })
          wx.showToast({ title: '已删除', icon: 'success' })
          this.loadAll()
        } catch (e) { /* toast in request */ }
      }
    })
  },

  onPageChange(e) {
    this.setData({ page: e.detail.current || 1 }, () => this.fetchDocs())
  },

  onPrev() {
    if (this.data.page <= 1) return
    this.setData({ page: this.data.page - 1 }, () => this.fetchDocs())
  },

  onNext() {
    if (this.data.page * 20 >= this.data.total) return
    this.setData({ page: this.data.page + 1 }, () => this.fetchDocs())
  },

  formatSize(bytes) {
    if (!bytes) return '0 B'
    if (bytes < 1024) return bytes + ' B'
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
    return (bytes / 1024 / 1024).toFixed(1) + ' MB'
  }
})

const API_PATH = {
  DOCS: '/knowledge/documents',
  STATS: '/knowledge/stats'
}
