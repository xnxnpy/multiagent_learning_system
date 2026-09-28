const req = require('../../utils/request').request
const { API, replaceParams } = require('../../utils/api')

Page({
  data: {
    query: '',
    typeFilter: '',
    typeList: [
      { value: '', label: '全部' },
      { value: 'video', label: '视频' },
      { value: 'article', label: '文章' },
      { value: 'paper', label: '论文' },
      { value: 'repo', label: '仓库' }
    ],
    loading: false,
    searched: false,
    items: [],
    saved: [],
    source: 'fallback'
  },

  onShow() {
    this.loadSaved()
  },

  onInput(e) {
    this.setData({ query: e.detail.value })
  },

  onType(e) {
    this.setData({ typeFilter: e.currentTarget.dataset.value || '' })
    if (this.data.searched) this.doSearch()
  },

  async doSearch() {
    const q = (this.data.query || '').trim()
    if (!q) {
      wx.showToast({ title: '请输入检索词', icon: 'none' })
      return
    }
    this.setData({ loading: true, searched: true })
    try {
      const res = await req({
        url: API.DISCOVERY.SEARCH,
        method: 'GET',
        data: { q, ...(this.data.typeFilter ? { type: this.data.typeFilter } : {}) }
      })
      this.setData({ items: res.items || [], source: res.source || 'fallback' })
    } catch (e) {
      this.setData({ items: [] })
    } finally {
      this.setData({ loading: false })
    }
  },

  copyLink(e) {
    const url = e.currentTarget.dataset.url
    if (!url) return
    wx.setClipboardData({
      data: url,
      success: () => wx.showToast({ title: '链接已复制', icon: 'none' })
    })
  },

  async saveItem(e) {
    const item = this.data.items[e.currentTarget.dataset.index]
    if (!item) return
    const host = String(item.url || '').replace(/^https?:\/\//, '').split('/')[0]
    try {
      await req({
        url: API.DISCOVERY.SAVE_ITEM,
        method: 'POST',
        data: {
          title: item.title,
          url: item.url,
          type: item.type || 'article',
          summary: item.summary || '',
          source: host
        }
      })
      wx.showToast({ title: '已收藏', icon: 'success' })
      this.loadSaved()
    } catch (e2) { /* toast in request */ }
  },

  async loadSaved() {
    try {
      const res = await req({ url: API.DISCOVERY.SAVED, method: 'GET' })
      this.setData({ saved: res || [] })
    } catch (e) {
      this.setData({ saved: [] })
    }
  },

  removeSaved(e) {
    const id = e.currentTarget.dataset.id
    wx.showModal({
      title: '移除收藏',
      content: '确定移除？',
      success: async (r) => {
        if (!r.confirm) return
        try {
          await req({ url: replaceParams(API.DISCOVERY.UNSAVE, { item_id: id }), method: 'DELETE' })
          wx.showToast({ title: '已移除', icon: 'success' })
          this.loadSaved()
        } catch (err) { /* ignore */ }
      }
    })
  }
})
