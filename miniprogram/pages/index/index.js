const { request } = require('../../utils/request')
const { API } = require('../../utils/api')

Page({
  data: {
    username: '',
    password: '',
    rememberMe: false
  },

  onLoad() {
    const savedUsername = wx.getStorageSync('rememberedUsername')
    if (savedUsername) {
      this.setData({
        username: savedUsername,
        rememberMe: true
      })
    }
  },

  onUsernameInput(e) {
    this.setData({ username: e.detail.value })
  },

  onPasswordInput(e) {
    this.setData({ password: e.detail.value })
  },

  toggleRemember() {
    this.setData({ rememberMe: !this.data.rememberMe })
  },

  async login() {
    const { username, password, rememberMe } = this.data
    
    if (!username || !password) {
      wx.showToast({ title: '请输入账号密码', icon: 'none' })
      return
    }

    wx.showLoading({ title: '登录中...' })

    try {
      const result = await request({
        url: API.AUTH.LOGIN,
        method: 'POST',
        data: { username, password },
        needToken: false
      })

      const { access_token, user } = result

      if (rememberMe) {
        wx.setStorageSync('rememberedUsername', username)
      } else {
        wx.removeStorageSync('rememberedUsername')
      }

      const app = getApp()
      app.saveUserData(access_token, user, user.role)

      wx.hideLoading()

      switch (user.role) {
        case 'student':
          wx.switchTab({ url: '/pages/profile/profile' })
          break
        case 'teacher':
          wx.navigateTo({ url: '/pages/teacher/teacher' })
          break
        case 'admin':
          wx.navigateTo({ url: '/pages/admin/admin' })
          break
        default:
          wx.switchTab({ url: '/pages/profile/profile' })
      }
    } catch (err) {
      wx.hideLoading()
      wx.showToast({ title: '账号或密码错误', icon: 'none' })
    }
  },

  goToRegister() {
    wx.navigateTo({ url: '/pages/register/register' })
  },

  forgotPassword() {
    wx.showModal({
      title: '忘记密码',
      content: '请联系管理员重置密码。',
      showCancel: false
    })
  }
})