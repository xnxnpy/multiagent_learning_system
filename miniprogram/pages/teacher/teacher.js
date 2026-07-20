const { request } = require('../../utils/request')
const { API } = require('../../utils/api')

Page({
  data: {
    userName: '',
    currentTab: 0,
    pendingReview: 0,
    currentTabName: '课程管理',
    tabNames: ['课程管理', '知识库', '资源审核', '作业管理', '学情分析', '统计报表'],
    
    courses: [],
    reviewResources: [],
    homeworkList: [],
    classStats: {},
    studentList: [],
    progressDistribution: []
  },

  onLoad() {
    const userInfo = wx.getStorageSync('user_info')
    const username = userInfo?.username || userInfo?.real_name || '老师'
    this.setData({ userName: username })
    this.loadTabData(0)
  },

  onShow() {
    this.loadTabData(this.data.currentTab)
  },

  async loadTabData(tabIndex) {
    wx.showLoading({ title: '加载中...' })
    
    try {
      switch (tabIndex) {
        case 0:
          await this.loadCourses()
          break
        case 1:
          wx.hideLoading()
          wx.navigateTo({ url: '/pages/teacher/knowledge' })
          return
        case 2:
          await this.loadReviewResources()
          break
        case 3:
          await this.loadHomework()
          break
        case 4:
        case 5:
          await this.loadClassStats()
          break
      }
    } catch (err) {
      console.error('加载数据失败:', err)
    }
    
    wx.hideLoading()
  },

  async loadCourses() {
    try {
      const result = await request({
        url: API.TEACHER.COURSES,
        method: 'GET',
        data: { page: 1, page_size: 20 }
      })

      const courses = (result.items || []).map(course => ({
        id: course.id,
        name: course.title,
        description: course.description || '',
        students: 0,
        duration: '',
        modules: 0,
        status: course.id ? 'active' : 'completed'
      }))

      this.setData({ courses })
    } catch (err) {
      console.error('加载课程失败:', err)
    }
  },

  async loadReviewResources() {
    try {
      const result = await request({
        url: API.TEACHER.RESOURCES_PENDING,
        method: 'GET',
        data: { page: 1, page_size: 20 }
      })

      const reviewResources = (result.items || []).map(item => ({
        id: item.id,
        type: this.getResourceTypeName(item.resource_type),
        title: item.resource_content?.substring(0, 30) || '',
        description: '',
        agent: '',
        student: '',
        time: item.created_at ? new Date(item.created_at).toLocaleString() : ''
      }))

      this.setData({ 
        reviewResources,
        pendingReview: reviewResources.length
      })
    } catch (err) {
      console.error('加载审核资源失败:', err)
    }
  },

  getResourceTypeName(type) {
    const map = {
      'document': '📄 学习文档',
      'mindmap': '🧠 思维导图',
      'question': '📝 练习题',
      'code': '💻 代码示例',
      'ppt_video': '🎬 教学视频',
      'reading_material': '📖 拓展阅读',
      'glossary': '📚 术语词汇',
      'knowledge_link': '🔗 知识关联',
      'summary': '📋 学习总结'
    }
    return map[type] || type
  },

  async loadHomework() {
    try {
      const result = await request({
        url: API.TEACHER.ASSIGNMENTS,
        method: 'GET',
        data: { page: 1, page_size: 20 }
      })

      const homeworkList = (result.items || []).map(item => {
        const status = item.status || 'pending'
        return {
          id: item.id,
          title: item.title,
          description: item.description || '',
          deadline: item.due_date || '',
          submitted: 0,
          total: item.target_students?.length || 0,
          status: status,
          statusText: status === 'published' ? '已发布' : status === 'pending' ? '待批改' : '已完成'
        }
      })

      this.setData({ homeworkList })
    } catch (err) {
      console.error('加载作业失败:', err)
    }
  },

  async loadClassStats() {
    try {
      const result = await request({
        url: API.TEACHER.CLASS_STATS,
        method: 'GET'
      })

      const classStats = {
        totalStudents: result.total_students || 0,
        avgScore: Math.round(result.average_accuracy * 100) || 0,
        completionRate: result.active_students || 0,
        activeStudents: result.active_students || 0
      }

      const studentList = (result.student_progress || []).map(sp => {
        const score = Math.round(sp.average_score) || 0
        const status = score >= 80 ? 'good' : score >= 60 ? 'normal' : 'attention'
        return {
          id: sp.student_id,
          name: sp.student_name,
          progress: Math.round(sp.total_learning_records / 10 * 100) || 0,
          score: score,
          status: status,
          statusText: status === 'good' ? '优秀' : status === 'normal' ? '正常' : '需关注'
        }
      })

      this.setData({ classStats, studentList })
    } catch (err) {
      console.error('加载班级统计失败:', err)
    }
  },

  goBack() {
    wx.navigateBack()
  },

  logout() {
    wx.showModal({
      title: '确认退出',
      content: '确定要退出登录吗？',
      success: (res) => {
        if (res.confirm) {
          const app = getApp()
          app.clearUserData()
          wx.redirectTo({ url: '/pages/index/index' })
        }
      }
    })
  },

  switchTab(e) {
    const tab = parseInt(e.currentTarget.dataset.tab)
    this.setData({ 
      currentTab: tab,
      currentTabName: this.data.tabNames[tab]
    })
    this.loadTabData(tab)
  },

  async addCourse() {
    wx.showModal({
      title: '添加课程',
      editable: true,
      placeholderText: '请输入课程名称',
      success: async (res) => {
        if (res.confirm && res.content) {
          try {
            await request({
              url: API.TEACHER.COURSES,
              method: 'POST',
              data: { title: res.content }
            })
            wx.showToast({ title: '添加成功', icon: 'success' })
            await this.loadCourses()
          } catch (err) {
            wx.showToast({ title: '添加失败', icon: 'none' })
          }
        }
      }
    })
  },

  async editCourse(e) {
    const id = e.currentTarget.dataset.id
    wx.showToast({ title: `编辑课程 ${id}`, icon: 'none' })
  },

  async viewCourse(e) {
    const id = e.currentTarget.dataset.id
    wx.showToast({ title: `查看课程 ${id}`, icon: 'none' })
  },

  async approveResource(e) {
    const id = e.currentTarget.dataset.id
    try {
      await request({
        url: `${API.TEACHER.RESOURCE_REVIEW.replace('{review_id}', id)}`,
        method: 'PUT',
        data: { action: 'approve' }
      })
      wx.showToast({ title: '审核通过', icon: 'success' })
      await this.loadReviewResources()
    } catch (err) {
      wx.showToast({ title: '审核失败', icon: 'none' })
    }
  },

  async rejectResource(e) {
    const id = e.currentTarget.dataset.id
    wx.showModal({
      title: '驳回原因',
      editable: true,
      placeholderText: '请输入驳回原因',
      success: async (res) => {
        if (res.confirm && res.content) {
          try {
            await request({
              url: `${API.TEACHER.RESOURCE_REVIEW.replace('{review_id}', id)}`,
              method: 'PUT',
              data: { action: 'reject', comment: res.content }
            })
            wx.showToast({ title: '已驳回', icon: 'success' })
            await this.loadReviewResources()
          } catch (err) {
            wx.showToast({ title: '操作失败', icon: 'none' })
          }
        }
      }
    })
  },

  async addHomework() {
    wx.showModal({
      title: '发布作业',
      editable: true,
      placeholderText: '请输入作业标题',
      success: async (res) => {
        if (res.confirm && res.content) {
          try {
            await request({
              url: API.TEACHER.ASSIGNMENTS,
              method: 'POST',
              data: { title: res.content, description: '' }
            })
            wx.showToast({ title: '发布成功', icon: 'success' })
            await this.loadHomework()
          } catch (err) {
            wx.showToast({ title: '发布失败', icon: 'none' })
          }
        }
      }
    })
  },

  async gradeHomework(e) {
    const id = e.currentTarget.dataset.id
    wx.showToast({ title: `批改作业 ${id}`, icon: 'none' })
  },

  async viewSubmissions(e) {
    const id = e.currentTarget.dataset.id
    wx.showToast({ title: `查看提交 ${id}`, icon: 'none' })
  },

  async viewStudent(e) {
    const id = e.currentTarget.dataset.id
    wx.showToast({ title: `查看学生 ${id}`, icon: 'none' })
  },

  async exportReport() {
    wx.showToast({ title: '正在导出报表...', icon: 'loading' })
    setTimeout(() => {
      wx.showToast({ title: '导出成功', icon: 'success' })
    }, 1500)
  }
})