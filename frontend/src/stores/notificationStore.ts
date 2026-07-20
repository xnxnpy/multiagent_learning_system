import { defineStore } from 'pinia'
import { ref } from 'vue'
import type { Notification } from '@/types'
import request from '@/utils/axios'

export const useNotificationStore = defineStore('notification', () => {
  const notifications = ref<Notification[]>([])
  const unreadCount = ref(0)

  async function fetchNotifications() {
    try {
      const data = await request.get('/v1/notifications')
      notifications.value = data || []
      unreadCount.value = notifications.value.filter(n => !n.read).length
    } catch { /* ignore */ }
  }

  async function fetchUnreadCount() {
    try {
      const data = await request.get('/v1/notifications/unread-count')
      unreadCount.value = data?.count || 0
    } catch { /* ignore */ }
  }

  async function markRead(id: number) {
    await request.post(`/v1/notifications/mark-read/${id}`)
    const n = notifications.value.find(n => n.id === id)
    if (n && !n.read) {
      n.read = true
      unreadCount.value = Math.max(0, unreadCount.value - 1)
    }
  }

  async function markAllRead() {
    await request.post('/v1/notifications/mark-all-read')
    notifications.value.forEach(n => n.read = true)
    unreadCount.value = 0
  }

  async function clearAll() {
    await request.delete('/v1/notifications/clear')
    notifications.value = []
    unreadCount.value = 0
  }

  return {
    notifications,
    unreadCount,
    fetchNotifications,
    fetchUnreadCount,
    markRead,
    markAllRead,
    clearAll,
  }
})
