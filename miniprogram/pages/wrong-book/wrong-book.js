const { request } = require('../../utils/request')
const { API } = require('../../utils/api')

Page({
  data: {
    wrongQuestions: [],
    loading: false,
    selectedQuestionIdx: 0,
    showAnswer: false
  },

  onLoad() {
    this.loadWrongQuestions()
  },

  async loadWrongQuestions() {
    this.setData({ loading: true })
    try {
      const result = await request({
        url: API.STUDENT.QUESTION_ANSWERS,
        method: 'GET'
      })
      
      const answers = result?.answers || []
      const wrongQuestions = answers.filter(a => !a.correct).map(q => ({
        ...q,
        submittedDate: q.submitted_at ? q.submitted_at.slice(0, 10) : '未知'
      }))
      
      this.setData({ wrongQuestions })
    } catch (err) {
      console.error('加载错题本失败:', err)
    } finally {
      this.setData({ loading: false })
    }
  },

  selectQuestion(e) {
    const idx = e.currentTarget.dataset.index
    this.setData({ selectedQuestionIdx: idx, showAnswer: false })
  },

  toggleAnswer() {
    this.setData({ showAnswer: !this.data.showAnswer })
  },

  reviewQuestion() {
    wx.navigateTo({ url: '/pages/resource/resource' })
  },

  refresh() {
    this.loadWrongQuestions()
  }
})