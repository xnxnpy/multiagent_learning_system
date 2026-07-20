App({
  globalData: {
    baseURL: 'http://localhost:8000/api/v1',
    accessToken: '',
    userInfo: null,
    userRole: ''
  },

  onLaunch() {
    this.loadUserData()
  },

  loadUserData() {
    const token = wx.getStorageSync('access_token')
    const userInfo = wx.getStorageSync('user_info')
    const role = wx.getStorageSync('user_role')

    if (token) {
      this.globalData.accessToken = token
      this.globalData.userInfo = userInfo
      this.globalData.userRole = role
    }
  },

  saveUserData(token, userInfo, role) {
    wx.setStorageSync('access_token', token)
    wx.setStorageSync('user_info', userInfo)
    wx.setStorageSync('user_role', role)
    
    this.globalData.accessToken = token
    this.globalData.userInfo = userInfo
    this.globalData.userRole = role
  },

  clearUserData() {
    wx.clearStorageSync()
    this.globalData.accessToken = ''
    this.globalData.userInfo = null
    this.globalData.userRole = ''
  },

  isLoggedIn() {
    return !!this.globalData.accessToken
  }
})