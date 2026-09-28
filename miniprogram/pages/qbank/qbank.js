const req = require('../../utils/request').request
const { API, replaceParams } = require('../../utils/api')

Page({
  data: {
    loading: false,
    items: [],
    page: 1,
    total: 0,
    status: '',
    expanded: null,
    answers: {},
    submitting: null,
    results: {}
  },

  onShow() {
    this.setData({ page: 1 })
    this.load()
  },

  async load() {
    this.setData({ loading: true })
    try {
      const res = await req({
        url: API.QBANK.LIST,
        method: 'GET',
        data: {
          page: this.data.page,
          page_size: 20,
          ...(this.data.status ? { status: this.data.status } : {})
        }
      })
      this.setData({ items: res.items || [], total: res.total || 0 })
    } catch (e) {
      this.setData({ items: [] })
    } finally {
      this.setData({ loading: false })
    }
  },

  onStatus(e) {
    this.setData({ status: e.currentTarget.dataset.value || '', page: 1 }, () => this.load())
  },

  toggleExpand(e) {
    const id = e.currentTarget.dataset.uid
    this.setData({ expanded: this.data.expanded === id ? null : id })
  },

  onAnswer(e) {
    const uid = e.currentTarget.dataset.uid
    this.setData({ [`answers.${uid}`]: e.detail.value })
  },

  pickOption(e) {
    const { uid, value } = e.currentTarget.dataset
    this.setData({ [`answers.${uid}`]: value })
  },

  async submitOne(e) {
    const uid = e.currentTarget.dataset.uid
    const item = this.data.items.find(i => i.question_uid === uid)
    if (!item) return
    const q = item.question_data || {}
    const answer = (this.data.answers[uid] || '').trim()
    if (!answer) {
      wx.showToast({ title: '请先作答', icon: 'none' })
      return
    }
    this.setData({ submitting: uid })
    try {
      const res = await req({
        url: API.STUDENT.QUESTION_SUBMIT,
        method: 'POST',
        data: {
          question_id: Number(q.question_id) || 0,
          answer,
          topic: item.knowledge_point || '',
          ...(item.stage_id != null ? { stage_id: item.stage_id } : {}),
          question_uid: uid
        }
      })
      const ev = res && res.evaluations && res.evaluations[0]
      if (ev) {
        const results = { ...this.data.results, [uid]: ev }
        item.attempt_count = (item.attempt_count || 0) + 1
        item.last_correct = ev.correct
        item.last_score = ev.score
        this.setData({ results, items: this.data.items })
        wx.showToast({ title: ev.correct ? '回答正确' : '已提交', icon: ev.correct ? 'success' : 'none' })
      }
    } catch (err) { /* toast */ } finally {
      this.setData({ submitting: null })
    }
  },

  prevPage() {
    if (this.data.page <= 1) return
    this.setData({ page: this.data.page - 1 }, () => this.load())
  },

  nextPage() {
    if (this.data.page * 20 >= this.data.total) return
    this.setData({ page: this.data.page + 1 }, () => this.load())
  },

  typeLabel(t) {
    const map = { choice: '选择', judge: '判断', blank: '填空', fill: '填空', code: '代码', case_analysis: '案例' }
    return map[t] || t || ''
  }
})
