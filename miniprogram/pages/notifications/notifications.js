const { request } = require('../../utils/request')
const { API } = require('../../utils/api')

Page({
  data: {
    notifications: [],
    unreadCount: 0,
    isLoading: false
  },

  onLoad() {
    this.loadNotifications()
  },

  onShow() {
    this.loadNotifications()
  },

  async loadNotifications() {
    this.setData({ isLoading: true })

    try {
      const result = await request({
        url: API.NOTIFICATION.LIST,
        method: 'GET'
      })

      const notifications = (result.items || result || []).map(notif => ({
        id: notif.id,
        title: notif.title || '系统通知',
        content: notif.content || '',
        type: notif.type || 'info',
        read: notif.read || false,
        time: notif.created_at ? this.formatTime(notif.created_at) : ''
      }))

      const unreadCount = notifications.filter(n => !n.read).length

      this.setData({ notifications, unreadCount })
    } catch (err) {
      console.error('加载通知失败:', err)
      this.setData({ notifications: [], unreadCount: 0 })
    } finally {
      this.setData({ isLoading: false })
    }
  },

  formatTime(dateStr) {
    const date = new Date(dateStr)
    const now = new Date()
    const diff = now.getTime() - date.getTime()
    const minutes = Math.floor(diff / 60000)
    const hours = Math.floor(diff / 3600000)
    const days = Math.floor(diff / 86400000)

    if (minutes < 1) return '刚刚'
    if (minutes < 60) return `${minutes}分钟前`
    if (hours < 24) return `${hours}小时前`
    if (days < 7) return `${days}天前`
    return `${date.getMonth() + 1}-${date.getDate()}`
  },

  getTypeIcon(type) {
    const icons = {
      info: 'ℹ️',
      success: '✅',
      warning: '⚠️',
      error: '❌',
      learning: '📚',
      assignment: '📝',
      system: '⚙️'
    }
    return icons[type] || '📧'
  },

  async markAsRead(e) {
    const id = e.currentTarget.dataset.id
    const notification = this.data.notifications.find(n => n.id === id)
    if (notification && !notification.read) {
      notification.read = true
      this.setData({
        notifications: [...this.data.notifications],
        unreadCount: this.data.unreadCount - 1
      })
      try {
        await request({
          url: API.NOTIFICATION.MARK_READ.replace('{notification_id}', id),
          method: 'POST'
        })
      } catch (err) {
        console.error('标记已读失败:', err)
      }
    }
  },

  async markAllRead() {
    if (this.data.unreadCount === 0) return

    wx.showLoading({ title: '标记中...' })
    try {
      await request({
        url: API.NOTIFICATION.MARK_ALL_READ,
        method: 'POST'
      })

      this.setData({
        notifications: this.data.notifications.map(n => ({ ...n, read: true })),
        unreadCount: 0
      })

      wx.hideLoading()
      wx.showToast({ title: '已全部标记为已读', icon: 'success' })
    } catch (err) {
      wx.hideLoading()
      wx.showToast({ title: '操作失败', icon: 'none' })
    }
  },

  async deleteNotification(e) {
    const id = e.currentTarget.dataset.id

    wx.showModal({
      title: '确认删除',
      content: '确定要删除这条通知吗？',
      success: async (res) => {
        if (res.confirm) {
          try {
            await request({
              url: API.NOTIFICATION.DELETE.replace('{notification_id}', id),
              method: 'DELETE'
            })

            this.setData({
              notifications: this.data.notifications.filter(n => n.id !== id)
            })

            wx.showToast({ title: '删除成功', icon: 'success' })
          } catch (err) {
            wx.showToast({ title: '删除失败', icon: 'none' })
          }
        }
      }
    })
  },

  goBack() {
    wx.navigateBack()
  }
})