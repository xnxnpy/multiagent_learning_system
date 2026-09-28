const req = require('../../utils/request').request
const { API, replaceParams } = require('../../utils/api')

Page({
  data: {
    loading: false,
    stats: { total: 0, personal_resources: 0, personal_notes: 0, uploads: 0, legacy_shared: 0 },
    docs: [],
    page: 1,
    total: 0
  },

  onShow() {
    this.setData({ page: 1 })
    this.loadAll()
  },

  async loadAll() {
    this.setData({ loading: true })
    try {
      const [st, docs] = await Promise.all([
        req({ url: API.ADMIN.KB_STATS, method: 'GET' }),
        req({
          url: API.ADMIN.KB_DOCUMENTS,
          method: 'GET',
          data: { page: this.data.page, page_size: 20 }
        })
      ])
      this.setData({
        stats: st || this.data.stats,
        docs: docs.items || [],
        total: docs.total || 0
      })
    } catch (e) { /* ignore */ } finally {
      this.setData({ loading: false })
    }
  },

  deleteDoc(e) {
    const id = e.currentTarget.dataset.id
    wx.showModal({
      title: '删除文档',
      content: '删除该上传材料及其向量索引？',
      success: async (r) => {
        if (!r.confirm) return
        try {
          await req({ url: replaceParams(API.ADMIN.KB_DOC, { doc_id: id }), method: 'DELETE' })
          wx.showToast({ title: '已删除', icon: 'success' })
          this.loadAll()
        } catch (err) { /* toast */ }
      }
    })
  },

  clearUploads() {
    wx.showModal({
      title: '清空上传材料',
      content: '仅清学生上传的文档索引，不动资源与笔记。确定？',
      success: async (r) => {
        if (!r.confirm) return
        try {
          const res = await req({ url: API.ADMIN.KB_CLEAR_UPLOADS, method: 'DELETE' })
          wx.showToast({ title: res.message || '已清空', icon: 'none' })
          this.loadAll()
        } catch (err) { /* toast */ }
      }
    })
  },

  clearLegacy() {
    wx.showModal({
      title: '清理历史无主块',
      content: '清理旧共享教材等无主向量，个人数据不受影响。确定？',
      success: async (r) => {
        if (!r.confirm) return
        try {
          const res = await req({ url: API.ADMIN.KB_CLEAR_LEGACY, method: 'DELETE' })
          wx.showToast({ title: res.message || '已清理', icon: 'none' })
          this.loadAll()
        } catch (err) { /* toast */ }
      }
    })
  },

  clearUser() {
    wx.showModal({
      title: '按用户清理索引',
      content: '输入学生用户 ID，清空其全部个人向量与上传文档',
      editable: true,
      placeholderText: '用户 ID',
      success: async (r) => {
        if (!r.confirm || !r.content) return
        try {
          const res = await req({
            url: replaceParams(API.ADMIN.KB_CLEAR_USER, { user_id: r.content.trim() }),
            method: 'POST'
          })
          wx.showToast({ title: res.message || '已清理', icon: 'none' })
          this.loadAll()
        } catch (err) { /* toast */ }
      }
    })
  }
})
