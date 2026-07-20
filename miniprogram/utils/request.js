const BASE_URL = 'http://localhost:8000/api/v1'

function getToken() {
  return wx.getStorageSync('access_token') || ''
}

function request(options) {
  const { url, method = 'GET', data = {}, header = {}, needToken = true } = options

  const defaultHeader = {
    'content-type': 'application/json',
  }

  if (needToken) {
    const token = getToken()
    if (token) {
      defaultHeader['Authorization'] = `Bearer ${token}`
    }
  }

  return new Promise((resolve, reject) => {
    wx.request({
      url: `${BASE_URL}${url}`,
      method: method.toUpperCase(),
      data: data,
      header: { ...defaultHeader, ...header },
      success: (res) => {
        if (res.statusCode === 200 || res.statusCode === 201) {
          resolve(res.data)
        } else if (res.statusCode === 401) {
          wx.showToast({ title: '登录已过期', icon: 'none' })
          wx.clearStorageSync()
          wx.reLaunch({ url: '/pages/index/index' })
          reject(new Error('Unauthorized'))
        } else {
          const msg = res.data?.detail || res.data?.message || `请求失败 ${res.statusCode}`
          wx.showToast({ title: msg, icon: 'none' })
          reject(new Error(msg))
        }
      },
      fail: (err) => {
        const msg = err.errMsg || '网络连接失败'
        if (msg.includes('not in the request valid domain list')) {
          wx.showModal({
            title: '域名未配置',
            content: '请在微信开发者工具中勾选"不校验合法域名"，或在小程序后台配置合法域名。',
            showCancel: false
          })
        } else {
          wx.showToast({ title: msg, icon: 'none' })
        }
        reject(err)
      }
    })
  })
}

module.exports = {
  request,
  getToken,
  BASE_URL
}