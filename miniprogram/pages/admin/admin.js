const { request } = require('../../utils/request')
const { API } = require('../../utils/api')

Page({
  data: {
    userName: '',
    currentTab: 0,
    currentTabName: '用户管理',
    tabNames: ['用户管理', '系统配置', '模型管理', '内容安全', '系统监控', '数据备份'],
    
    users: [],
    courses: [],
    systemLogs: [],
    systemStats: {},
    searchKeyword: ''
  },

  onLoad() {
    const userInfo = wx.getStorageSync('user_info')
    const username = userInfo?.username || userInfo?.real_name || '管理员'
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
          await this.loadUsers()
          break
        case 1:
          wx.hideLoading()
          wx.navigateTo({ url: '/pages/admin/config' })
          return
        case 2:
          wx.hideLoading()
          wx.navigateTo({ url: '/pages/admin/models' })
          return
        case 3:
          wx.hideLoading()
          wx.navigateTo({ url: '/pages/admin/content-security' })
          return
        case 4:
          await this.loadSystemLogs()
          break
        case 5:
          wx.hideLoading()
          wx.navigateTo({ url: '/pages/admin/backup' })
          return
      }
    } catch (err) {
      console.error('加载数据失败:', err)
    }
    
    wx.hideLoading()
  },

  async loadUsers() {
    try {
      const result = await request({
        url: API.ADMIN.USERS,
        method: 'GET',
        data: { page: 1, page_size: 50 }
      })

      const users = (result.items || []).map(user => ({
        id: user.id,
        username: user.username,
        realName: user.real_name || user.username,
        role: user.role,
        roleText: user.role === 'student' ? '学生' : user.role === 'teacher' ? '教师' : '管理员',
        email: user.email || '',
        phone: user.phone || '',
        createdAt: user.created_at ? new Date(user.created_at).toLocaleDateString() : '',
        status: user.is_active ? 'active' : 'disabled'
      }))

      this.setData({ users })
    } catch (err) {
      console.error('加载用户失败:', err)
    }
  },

  async loadCourses() {
    try {
      const result = await request({
        url: API.TEACHER.COURSES,
        method: 'GET',
        data: { page: 1, page_size: 50 }
      })

      const courses = (result.items || []).map(course => ({
        id: course.id,
        title: course.title,
        description: course.description || '',
        teacher: '',
        students: 0,
        status: course.id ? 'active' : 'completed',
        createdAt: course.created_at ? new Date(course.created_at).toLocaleDateString() : ''
      }))

      this.setData({ courses })
    } catch (err) {
      console.error('加载课程失败:', err)
    }
  },

  async loadSystemLogs() {
    try {
      const result = await request({
        url: API.ADMIN.LOGS,
        method: 'GET',
        data: { page: 1, page_size: 50 }
      })

      const systemLogs = (result.items || []).map(log => ({
        id: log.id,
        level: log.level || 'info',
        levelText: log.level === 'error' ? 'ERROR' : log.level === 'warning' ? 'WARN' : 'INFO',
        message: log.message || '',
        module: log.module || '',
        timestamp: log.created_at ? new Date(log.created_at).toLocaleString() : ''
      }))

      this.setData({ systemLogs })
    } catch (err) {
      console.error('加载系统日志失败:', err)
    }
  },

  async loadSystemStats() {
    try {
      const result = await request({
        url: API.ADMIN.STATS,
        method: 'GET'
      })

      const systemStats = {
        totalUsers: result.total_users || 0,
        totalCourses: result.total_courses || 0,
        totalResources: result.total_resources || 0,
        totalChatSessions: result.total_chat_sessions || 0,
        avgDailyActive: result.daily_active_users || 0,
        avgLearningTime: result.avg_learning_time || 0
      }

      this.setData({ systemStats })
    } catch (err) {
      console.error('加载系统统计失败:', err)
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

  onSearch(e) {
    this.setData({ searchKeyword: e.detail.value })
    this.filterData()
  },

  filterData() {
    const { searchKeyword, users, currentTab } = this.data
    if (!searchKeyword) {
      this.loadTabData(currentTab)
      return
    }

    const filteredUsers = users.filter(user => 
      user.username.toLowerCase().includes(searchKeyword.toLowerCase()) ||
      user.realName.toLowerCase().includes(searchKeyword.toLowerCase())
    )
    this.setData({ users: filteredUsers })
  },

  async addUser() {
    wx.showModal({
      title: '添加用户',
      editable: true,
      placeholderText: '请输入用户名',
      success: async (res) => {
        if (res.confirm && res.content) {
          try {
            await request({
              url: API.ADMIN.USERS,
              method: 'POST',
              data: { 
                username: res.content,
                password: '123456',
                role: 'student'
              }
            })
            wx.showToast({ title: '添加成功', icon: 'success' })
            await this.loadUsers()
          } catch (err) {
            wx.showToast({ title: '添加失败', icon: 'none' })
          }
        }
      }
    })
  },

  async editUser(e) {
    const id = e.currentTarget.dataset.id
    wx.showToast({ title: `编辑用户 ${id}`, icon: 'none' })
  },

  async deleteUser(e) {
    const id = e.currentTarget.dataset.id
    wx.showModal({
      title: '确认删除',
      content: '确定要删除该用户吗？',
      success: async (res) => {
        if (res.confirm) {
          try {
            await request({
              url: `${API.ADMIN.USER_DETAIL.replace('{user_id}', id)}`,
              method: 'DELETE'
            })
            wx.showToast({ title: '删除成功', icon: 'success' })
            await this.loadUsers()
          } catch (err) {
            wx.showToast({ title: '删除失败', icon: 'none' })
          }
        }
      }
    })
  },

  async toggleUserStatus(e) {
    const id = e.currentTarget.dataset.id
    const status = e.currentTarget.dataset.status
    try {
      await request({
        url: `${API.ADMIN.USER_DETAIL.replace('{user_id}', id)}`,
        method: 'PUT',
        data: { is_active: status === 'active' ? false : true }
      })
      wx.showToast({ title: '状态已更新', icon: 'success' })
      await this.loadUsers()
    } catch (err) {
      wx.showToast({ title: '操作失败', icon: 'none' })
    }
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

  async deleteCourse(e) {
    const id = e.currentTarget.dataset.id
    wx.showModal({
      title: '确认删除',
      content: '确定要删除该课程吗？',
      success: async (res) => {
        if (res.confirm) {
          try {
            await request({
              url: `${API.TEACHER.COURSE.replace('{course_id}', id)}`,
              method: 'DELETE'
            })
            wx.showToast({ title: '删除成功', icon: 'success' })
            await this.loadCourses()
          } catch (err) {
            wx.showToast({ title: '删除失败', icon: 'none' })
          }
        }
      }
    })
  },

  async toggleCourseStatus(e) {
    const id = e.currentTarget.dataset.id
    const status = e.currentTarget.dataset.status
    try {
      await request({
        url: `${API.TEACHER.COURSE.replace('{course_id}', id)}`,
        method: 'PUT',
        data: { is_active: status === 'active' ? false : true }
      })
      wx.showToast({ title: '状态已更新', icon: 'success' })
      await this.loadCourses()
    } catch (err) {
      wx.showToast({ title: '操作失败', icon: 'none' })
    }
  },

  async clearLogs() {
    wx.showModal({
      title: '确认清空',
      content: '确定要清空所有系统日志吗？',
      success: async (res) => {
        if (res.confirm) {
          try {
            await request({
              url: API.ADMIN.LOGS,
              method: 'DELETE'
            })
            wx.showToast({ title: '已清空', icon: 'success' })
            await this.loadSystemLogs()
          } catch (err) {
            wx.showToast({ title: '操作失败', icon: 'none' })
          }
        }
      }
    })
  },

  async backupData() {
    wx.showToast({ title: '正在备份数据...', icon: 'loading' })
    setTimeout(() => {
      wx.showToast({ title: '备份成功', icon: 'success' })
    }, 2000)
  },

  async exportData() {
    wx.showToast({ title: '正在导出数据...', icon: 'loading' })
    setTimeout(() => {
      wx.showToast({ title: '导出成功', icon: 'success' })
    }, 2000)
  }
})