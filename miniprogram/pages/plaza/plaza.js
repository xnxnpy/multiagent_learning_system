const req = require('../../utils/request').request
const { API, replaceParams } = require('../../utils/api')

Page({
  data: {
    loading: false,
    posting: false,
    posts: [],
    form: { title: '', content: '', tags: '' },
    likingId: null,
    myId: null
  },

  onShow() {
    try {
      const u = JSON.parse(wx.getStorageSync('user') || '{}')
      this.setData({ myId: u.id ?? null })
    } catch (e) { /* ignore */ }
    this.load()
  },

  onField(e) {
    const f = e.currentTarget.dataset.field
    this.setData({ [`form.${f}`]: e.detail.value })
  },

  async load() {
    this.setData({ loading: true })
    try {
      const res = await req({ url: API.PLAZA.POSTS, method: 'GET' })
      this.setData({ posts: res || [] })
    } catch (e) {
      this.setData({ posts: [] })
    } finally {
      this.setData({ loading: false })
    }
  },

  async submitPost() {
    const { title, content, tags } = this.data.form
    if (!title.trim() || !content.trim()) {
      wx.showToast({ title: '请填写标题和内容', icon: 'none' })
      return
    }
    this.setData({ posting: true })
    try {
      await req({
        url: API.PLAZA.POSTS,
        method: 'POST',
        data: { title: title.trim(), content: content.trim(), tags: (tags || '').trim() }
      })
      wx.showToast({ title: '已发布', icon: 'success' })
      this.setData({ form: { title: '', content: '', tags: '' } })
      this.load()
    } catch (e) { /* toast */ } finally {
      this.setData({ posting: false })
    }
  },

  async toggleLike(e) {
    const id = e.currentTarget.dataset.id
    this.setData({ likingId: id })
    try {
      const res = await req({ url: replaceParams(API.PLAZA.LIKE, { post_id: id }), method: 'POST' })
      const posts = this.data.posts.map(p => p.id === id
        ? { ...p, liked: res.liked, like_count: res.like_count }
        : p)
      this.setData({ posts })
    } catch (e) { /* ignore */ } finally {
      this.setData({ likingId: null })
    }
  },

  removePost(e) {
    const id = e.currentTarget.dataset.id
    wx.showModal({
      title: '删除分享',
      content: '确定删除？',
      success: async (r) => {
        if (!r.confirm) return
        try {
          await req({ url: replaceParams(API.PLAZA.DELETE, { post_id: id }), method: 'DELETE' })
          wx.showToast({ title: '已删除', icon: 'success' })
          this.load()
        } catch (err) { /* ignore */ }
      }
    })
  }
})
