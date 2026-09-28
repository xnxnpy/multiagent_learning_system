const req = require('../../utils/request').request
const { API } = require('../../utils/api')

Page({
  data: {
    loading: false,
    kpis: {
      total_users: 0,
      total_students: 0,
      risk_students: 0,
      today_active: 0
    },
    daily: [],
    hours: [],
    typeShare: []
  },

  onShow() {
    this.load()
  },

  async load() {
    this.setData({ loading: true })
    try {
      const res = await req({ url: API.ADMIN.LEARNING_ANALYTICS, method: 'GET' })
      const daily = res.daily_active || []
      const hours = res.hour_distribution || []
      const maxHour = Math.max(...hours.map(h => h.count || 0), 1)
      this.setData({
        kpis: {
          total_users: res.total_users || 0,
          total_students: res.total_students || 0,
          risk_students: res.risk_students || 0,
          today_active: daily.length ? daily[daily.length - 1].active_users : 0
        },
        daily: daily.map(d => ({
          date: String(d.date || '').slice(5),
          active: d.active_users || 0
        })),
        hours: hours.map(h => ({
          hour: h.hour,
          count: h.count || 0,
          pct: Math.round(((h.count || 0) / maxHour) * 100)
        })),
        typeShare: res.type_share || []
      })
    } catch (e) { /* ignore */ } finally {
      this.setData({ loading: false })
    }
  }
})
