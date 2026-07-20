const { request } = require('../../utils/request')
const { API } = require('../../utils/api')

Page({
  data: {
    backups: [],
    isCreating: false,
    stats: {
      total_users: 0, total_students: 0, total_teachers: 0,
      total_profiles: 0, total_learning_paths: 0, total_resources: 0
    },
    systemStats: {
      cpu_percent: 0, memory_percent: 0,
      memory_used_mb: 0, memory_total_mb: 0, disk_percent: 0, disk_used_gb: 0, disk_total_gb: 0
    },
    activeTab: 0,
    tabs: ['系统统计', '备份管理', '维护操作']
  },

  onLoad() {
    this.loadAll()
  },

  onShow() {
    this.loadAll()
  },

  async loadAll() {
    wx.showLoading({ title: '加载中...' })
    await Promise.all([
      this.loadBackups(),
      this.loadStats(),
      this.loadSystemStats()
    ])
    wx.hideLoading()
  },

  async loadBackups() {
    try {
      const result = await request({ url: API.ADMIN.BACKUPS, method: 'GET' })
      const backups = (result.items || []).map(b => ({
        name: b.name || '',
        size: b.size || 0,
        created_at: b.created_at ? new Date(b.created_at).toLocaleString() : '',
        type: b.type || 'full',
        sizeText: this.formatSize(b.size || 0)
      }))
      this.setData({ backups })
    } catch (err) {
      console.error('加载备份失败:', err)
    }
  },

  async loadStats() {
    try {
      const res = await request({ url: API.ADMIN.STATS, method: 'GET' })
      this.setData({ stats: res })
    } catch (err) {
      console.error('加载统计失败:', err)
    }
  },

  async loadSystemStats() {
    try {
      const res = await request({ url: API.ADMIN.MONITORING, method: 'GET' })
      this.setData({ systemStats: res })
    } catch (err) {
      console.error('加载系统统计失败:', err)
    }
  },

  formatSize(bytes) {
    if (bytes < 1024) return bytes + ' B'
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
    if (bytes < 1024 * 1024 * 1024) return (bytes / (1024 * 1024)).toFixed(1) + ' MB'
    return (bytes / (1024 * 1024 * 1024)).toFixed(2) + ' GB'
  },

  switchTab(e) {
    this.setData({ activeTab: parseInt(e.currentTarget.dataset.index) })
  },

  async createBackup() {
    this.setData({ isCreating: true })
    wx.showLoading({ title: '创建备份中...' })
    try {
      await request({ url: API.ADMIN.BACKUP, method: 'POST' })
      wx.hideLoading()
      wx.showToast({ title: '备份成功', icon: 'success' })
      await this.loadBackups()
    } catch (err) {
      wx.hideLoading()
      wx.showToast({ title: '备份失败', icon: 'none' })
    } finally {
      this.setData({ isCreating: false })
    }
  },

  async restoreBackup(e) {
    const name = e.currentTarget.dataset.name
    wx.showModal({
      title: '确认恢复',
      content: `确定要从备份 "${name}" 恢复数据吗？这将覆盖当前数据。`,
      success: async (res) => {
        if (res.confirm) {
          wx.showLoading({ title: '恢复中...' })
          try {
            await request({ url: API.ADMIN.RESTORE, method: 'POST', data: { backup_name: name } })
            wx.hideLoading()
            wx.showToast({ title: '恢复成功', icon: 'success' })
          } catch (err) {
            wx.hideLoading()
            wx.showToast({ title: '恢复失败', icon: 'none' })
          }
        }
      }
    })
  },

  async deleteBackup(e) {
    const name = e.currentTarget.dataset.name
    wx.showModal({
      title: '确认删除',
      content: `确定要删除备份 "${name}" 吗？`,
      success: async (res) => {
        if (res.confirm) {
          try {
            await request({ url: API.ADMIN.DELETE_BACKUP.replace('{backup_name}', name), method: 'DELETE' })
            wx.showToast({ title: '删除成功', icon: 'success' })
            await this.loadBackups()
          } catch (err) {
            wx.showToast({ title: '删除失败', icon: 'none' })
          }
        }
      }
    })
  },

  async clearCache() {
    wx.showModal({
      title: '确认清空',
      content: '确定要清空系统缓存吗？',
      success: async (res) => {
        if (res.confirm) {
          wx.showLoading({ title: '清空中...' })
          try {
            await request({ url: API.ADMIN.CACHE_CLEAR, method: 'POST' })
            wx.hideLoading()
            wx.showToast({ title: '缓存已清空', icon: 'success' })
          } catch (err) {
            wx.hideLoading()
            wx.showToast({ title: '清空失败', icon: 'none' })
          }
        }
      }
    })
  },

  async cleanLogs() {
    wx.showModal({
      title: '确认清理',
      content: '确定要清理所有系统日志吗？',
      success: async (res) => {
        if (res.confirm) {
          wx.showLoading({ title: '清理中...' })
          try {
            await request({ url: API.ADMIN.LOGS_CLEAN, method: 'DELETE' })
            wx.hideLoading()
            wx.showToast({ title: '日志已清理', icon: 'success' })
          } catch (err) {
            wx.hideLoading()
            wx.showToast({ title: '清理失败', icon: 'none' })
          }
        }
      }
    })
  },

  goBack() {
    wx.navigateBack()
  }
})
