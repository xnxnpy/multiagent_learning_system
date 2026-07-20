const { request } = require('../../utils/request')
const { API } = require('../../utils/api')

Page({
  data: {
    documents: [],
    stats: {
      total_documents: 0,
      total_chunks: 0,
      total_tokens: 0
    },
    isUploading: false,
    uploadProgress: 0,
    searchKeyword: ''
  },

  onLoad() {
    this.loadDocuments()
    this.loadStats()
  },

  async loadDocuments() {
    try {
      const result = await request({
        url: API.TEACHER.KNOWLEDGE_DOCUMENTS,
        method: 'GET',
        data: { page: 1, page_size: 50 }
      })

      const documents = (result.items || []).map(doc => ({
        id: doc.id,
        filename: doc.filename || doc.name || '',
        size: doc.size || 0,
        size_kb: doc.size ? (doc.size / 1024).toFixed(1) : '0',
        chunks: doc.chunks || 0,
        status: doc.status || 'processed',
        uploaded_at: doc.created_at ? new Date(doc.created_at).toLocaleString() : ''
      }))

      this.setData({ documents })
    } catch (err) {
      console.error('加载文档失败:', err)
    }
  },

  async loadStats() {
    try {
      const result = await request({
        url: API.TEACHER.KNOWLEDGE_STATS,
        method: 'GET'
      })

      this.setData({ 
        stats: {
          ...result,
          total_tokens_k: result.total_tokens ? (result.total_tokens / 1000).toFixed(1) : 0
        }
      })
    } catch (err) {
      console.error('加载统计失败:', err)
    }
  },

  onSearch(e) {
    this.setData({ searchKeyword: e.detail.value })
  },

  uploadFile() {
    wx.chooseMessageFile({
      count: 1,
      type: 'file',
      success: async (res) => {
        const file = res.tempFiles[0]
        this.setData({ isUploading: true, uploadProgress: 0 })

        wx.showLoading({ title: '上传中...' })

        try {
          const uploadResult = await wx.uploadFile({
            url: `${API.TEACHER.KNOWLEDGE_UPLOAD}`,
            filePath: file.path,
            name: 'file',
            header: {
              'Authorization': `Bearer ${wx.getStorageSync('access_token')}`
            },
            success: (uploadRes) => {
              wx.hideLoading()
              this.setData({ isUploading: false })
              wx.showToast({ title: '上传成功', icon: 'success' })
              this.loadDocuments()
              this.loadStats()
            },
            fail: (err) => {
              wx.hideLoading()
              this.setData({ isUploading: false })
              wx.showToast({ title: '上传失败', icon: 'none' })
            }
          })
        } catch (err) {
          wx.hideLoading()
          this.setData({ isUploading: false })
          wx.showToast({ title: '上传失败', icon: 'none' })
        }
      },
      fail: () => {
        wx.showToast({ title: '取消选择', icon: 'none' })
      }
    })
  },

  async generateKnowledgeGraph() {
    wx.showLoading({ title: '生成中...' })
    try {
      await request({
        url: API.TEACHER.KNOWLEDGE_GRAPH_GENERATE,
        method: 'POST'
      })

      wx.hideLoading()
      wx.showToast({ title: '知识图谱已生成', icon: 'success' })
    } catch (err) {
      wx.hideLoading()
      wx.showToast({ title: '生成失败', icon: 'none' })
    }
  },

  async clearKnowledge() {
    wx.showModal({
      title: '确认清空',
      content: '确定要清空所有知识库吗？此操作不可恢复。',
      success: async (res) => {
        if (res.confirm) {
          wx.showLoading({ title: '清空中...' })
          try {
            await request({
              url: API.TEACHER.KNOWLEDGE_CLEAR,
              method: 'DELETE'
            })

            wx.hideLoading()
            wx.showToast({ title: '已清空', icon: 'success' })
            this.loadDocuments()
            this.loadStats()
          } catch (err) {
            wx.hideLoading()
            wx.showToast({ title: '操作失败', icon: 'none' })
          }
        }
      }
    })
  },

  async deleteDocument(e) {
    const id = e.currentTarget.dataset.id
    wx.showModal({
      title: '确认删除',
      content: '确定要删除该文档吗？',
      success: async (res) => {
        if (res.confirm) {
          try {
            await request({
              url: `${API.TEACHER.KNOWLEDGE_DOCUMENTS}/${id}`,
              method: 'DELETE'
            })

            wx.showToast({ title: '删除成功', icon: 'success' })
            this.loadDocuments()
            this.loadStats()
          } catch (err) {
            wx.showToast({ title: '删除失败', icon: 'none' })
          }
        }
      }
    })
  },

  goBack() {
    wx.navigateBack()
  }
})