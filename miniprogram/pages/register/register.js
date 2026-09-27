const { request } = require('../../utils/request')
const { API } = require('../../utils/api')

Page({
  data: {
    username: '',
    password: '',
    confirmPassword: '',
    email: '',
    realName: '',
    selectedRole: 'student',
    roles: [
      { value: 'student', label: '学生', icon: '📚' },
      { value: 'teacher', label: '教师', icon: '👨‍🏫' }
    ],
    agreementChecked: false,
    isSubmitting: false
  },

  onInput(e) {
    const { field } = e.currentTarget.dataset
    this.setData({ [field]: e.detail.value })
  },

  selectRole(e) {
    this.setData({ selectedRole: e.currentTarget.dataset.value })
  },

  toggleAgreement() {
    this.setData({ agreementChecked: !this.data.agreementChecked })
  },

  async register() {
    const { username, password, confirmPassword, email, realName, selectedRole, agreementChecked } = this.data

    // 表单校验（和前端一致）
    if (!username.trim()) {
      wx.showToast({ title: '请输入用户名', icon: 'none' })
      return
    }
    if (username.trim().length < 3 || username.trim().length > 50) {
      wx.showToast({ title: '用户名长度在3到50个字符', icon: 'none' })
      return
    }

    if (!realName.trim()) {
      wx.showToast({ title: '请输入真实姓名', icon: 'none' })
      return
    }

    if (!email.trim()) {
      wx.showToast({ title: '请输入邮箱', icon: 'none' })
      return
    }
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
    if (!emailRegex.test(email.trim())) {
      wx.showToast({ title: '请输入有效的邮箱地址', icon: 'none' })
      return
    }

    if (!password) {
      wx.showToast({ title: '请输入密码', icon: 'none' })
      return
    }
    if (password.length < 6) {
      wx.showToast({ title: '密码长度至少6位', icon: 'none' })
      return
    }

    if (!confirmPassword) {
      wx.showToast({ title: '请再次输入密码', icon: 'none' })
      return
    }
    if (password !== confirmPassword) {
      wx.showToast({ title: '两次输入的密码不一致', icon: 'none' })
      return
    }

    if (!agreementChecked) {
      wx.showToast({ title: '请同意用户协议', icon: 'none' })
      return
    }

    this.setData({ isSubmitting: true })
    wx.showLoading({ title: '注册中...' })

    try {
      await request({
        url: API.AUTH.REGISTER,
        method: 'POST',
        data: {
          username: username.trim(),
          password,
          real_name: realName.trim(),
          email: email.trim(),
          role: selectedRole
        },
        needToken: false
      })

      wx.hideLoading()
      wx.showToast({ title: '注册成功！请登录', icon: 'success' })

      setTimeout(() => {
        wx.navigateBack()
      }, 1500)
    } catch (err) {
      wx.hideLoading()
      this.setData({ isSubmitting: false })
      const msg = err.message || '注册失败'
      wx.showToast({ title: msg, icon: 'none' })
    }
  },

  goToLogin() {
    wx.navigateBack()
  }
})
