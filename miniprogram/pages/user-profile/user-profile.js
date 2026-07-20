const { request } = require('../../utils/request')
const { API } = require('../../utils/api')

Page({
  data: {
    userInfo: {},
    profileData: {
      major: '',
      grade: '',
      goal: '',
      knowledge_level: '',
      learning_style: '',
      coding_ability: '',
      interests: [],
      weakness: []
    },
    activeTab: 0,
    tabs: ['基本信息', '学习画像', '修改密码'],
    oldPassword: '',
    newPassword: '',
    confirmPassword: '',
    isSubmitting: false
  },

  onLoad() {
    this.loadUserInfo()
    this.loadProfile()
  },

  async loadUserInfo() {
    try {
      const result = await request({
        url: API.AUTH.ME,
        method: 'GET'
      })
      result.roleText = result.role === 'student' ? '学生' : result.role === 'teacher' ? '教师' : '管理员'
      this.setData({ userInfo: result })
    } catch (err) {
      console.error('加载用户信息失败:', err)
    }
  },

  async loadProfile() {
    try {
      const result = await request({
        url: API.STUDENT.PROFILE,
        method: 'GET'
      })
      this.setData({
        profileData: {
          major: result.major || '',
          grade: result.grade || '',
          goal: result.goal || '',
          knowledge_level: result.knowledge_level || '',
          learning_style: result.learning_style || '',
          coding_ability: result.coding_ability || '',
          interests: result.interests || [],
          weakness: result.weakness || []
        }
      })
    } catch (err) {
      console.error('加载学习画像失败:', err)
    }
  },

  switchTab(e) {
    const index = parseInt(e.currentTarget.dataset.index)
    this.setData({ activeTab: index })
  },

  onInput(e) {
    const { field } = e.currentTarget.dataset
    this.setData({ [field]: e.detail.value })
  },

  onProfileInput(e) {
    const { field } = e.currentTarget.dataset
    const { profileData } = this.data
    this.setData({
      profileData: { ...profileData, [field]: e.detail.value }
    })
  },

  async updateProfile() {
    this.setData({ isSubmitting: true })
    wx.showLoading({ title: '更新中...' })

    try {
      const { profileData } = this.data
      await request({
        url: API.STUDENT.PROFILE,
        method: 'PUT',
        data: profileData
      })

      wx.hideLoading()
      wx.showToast({ title: '更新成功', icon: 'success' })
    } catch (err) {
      wx.hideLoading()
      this.setData({ isSubmitting: false })
      wx.showToast({ title: '更新失败', icon: 'none' })
    }
  },

  async updateBasicInfo() {
    const { userInfo } = this.data
    this.setData({ isSubmitting: true })
    wx.showLoading({ title: '更新中...' })

    try {
      await request({
        url: API.AUTH.UPDATE_ME,
        method: 'PUT',
        data: {
          real_name: userInfo.real_name || '',
          email: userInfo.email || ''
        }
      })

      wx.hideLoading()
      wx.showToast({ title: '更新成功', icon: 'success' })
    } catch (err) {
      wx.hideLoading()
      this.setData({ isSubmitting: false })
      wx.showToast({ title: '更新失败', icon: 'none' })
    }
  },

  async changePassword() {
    const { oldPassword, newPassword, confirmPassword } = this.data

    if (!oldPassword) {
      wx.showToast({ title: '请输入旧密码', icon: 'none' })
      return
    }

    if (!newPassword) {
      wx.showToast({ title: '请输入新密码', icon: 'none' })
      return
    }

    if (newPassword.length < 6) {
      wx.showToast({ title: '新密码至少6位', icon: 'none' })
      return
    }

    if (newPassword !== confirmPassword) {
      wx.showToast({ title: '两次密码不一致', icon: 'none' })
      return
    }

    this.setData({ isSubmitting: true })
    wx.showLoading({ title: '修改中...' })

    try {
      await request({
        url: API.AUTH.CHANGE_PASSWORD,
        method: 'POST',
        data: {
          old_password: oldPassword,
          new_password: newPassword
        }
      })

      wx.hideLoading()
      wx.showToast({ title: '密码修改成功', icon: 'success' })
      this.setData({ oldPassword: '', newPassword: '', confirmPassword: '' })
    } catch (err) {
      wx.hideLoading()
      this.setData({ isSubmitting: false })
      wx.showToast({ title: '修改失败', icon: 'none' })
    }
  },

  goBack() {
    wx.navigateBack()
  }
})