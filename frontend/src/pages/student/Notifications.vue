<template>
  <div class="notifications-page">
    <div class="page-header">
      <h2 class="page-title">通知中心</h2>
      <div class="header-actions">
        <el-badge :value="notificationStore.unreadCount" :max="99" :hidden="!notificationStore.unreadCount">
          <el-button :icon="Bell" @click="notificationStore.fetchNotifications()">
            刷新
          </el-button>
        </el-badge>
        <el-button
          :icon="Check"
          :disabled="!notificationStore.unreadCount"
          @click="handleMarkAllRead"
        >
          全部已读
        </el-button>
        <el-button type="danger" :icon="Delete" :disabled="!notificationStore.notifications.length" @click="handleClearAll">
          清空
        </el-button>
      </div>
    </div>

    <el-card class="content-card" shadow="never">
      <el-table
        :data="notificationStore.notifications"
        v-loading="loading"
        stripe
        style="width: 100%"
        empty-text="暂无通知"
      >
        <el-table-column label="标题" min-width="180">
          <template #default="{ row }">
            <div class="title-cell">
              <span v-if="!row.read" class="unread-dot"></span>
              <span :class="{ 'title-unread': !row.read }">{{ row.title }}</span>
            </div>
          </template>
        </el-table-column>

        <el-table-column label="内容" min-width="260">
          <template #default="{ row }">
            <span class="content-text">{{ row.content }}</span>
          </template>
        </el-table-column>

        <el-table-column label="类型" width="100" align="center">
          <template #default="{ row }">
            <el-tag :type="typeTagColor(row.type)" effect="plain" size="small">
              {{ typeLabel(row.type) }}
            </el-tag>
          </template>
        </el-table-column>

        <el-table-column label="时间" width="160" align="center">
          <template #default="{ row }">
            <span class="time-text">{{ formatTime(row.created_at) }}</span>
          </template>
        </el-table-column>

        <el-table-column label="状态" width="80" align="center">
          <template #default="{ row }">
            <el-tag :type="row.read ? 'info' : 'warning'" effect="plain" size="small">
              {{ row.read ? '已读' : '未读' }}
            </el-tag>
          </template>
        </el-table-column>

        <el-table-column label="操作" width="140" align="center" fixed="right">
          <template #default="{ row }">
            <el-button
              v-if="!row.read"
              type="primary"
              link
              size="small"
              @click="handleMarkRead(row)"
            >
              标记已读
            </el-button>
            <el-button
              type="danger"
              link
              size="small"
              @click="handleDelete(row)"
            >
              删除
            </el-button>
          </template>
        </el-table-column>

        <template #empty>
          <div class="empty-state">
            <el-icon :size="48" color="var(--color-text-muted)"><Bell /></el-icon>
            <p>暂无通知</p>
          </div>
        </template>
      </el-table>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Bell, Check, Delete } from '@element-plus/icons-vue'
import { useNotificationStore } from '@/stores/notificationStore'
import type { Notification } from '@/types'

const notificationStore = useNotificationStore()
const loading = ref(false)

/* ── Type helpers ────────────────────────────── */

function typeTagColor(type: string): '' | 'primary' | 'success' | 'warning' | 'info' | 'danger' {
  const map: Record<string, '' | 'primary' | 'success' | 'warning' | 'info' | 'danger'> = {
    learning: 'primary',
    evaluation: 'success',
    resource: 'warning',
    chat: 'info',
    system: 'info',
  }
  return map[type] || 'info'
}

function typeLabel(type: string): string {
  const map: Record<string, string> = {
    learning: '学习',
    evaluation: '评估',
    resource: '资源',
    chat: '对话',
    system: '系统',
  }
  return map[type] || '通知'
}

function formatTime(time: string): string {
  if (!time) return ''
  const date = new Date(time)
  const now = new Date()
  const diff = now.getTime() - date.getTime()

  if (diff < 60000) return '刚刚'
  if (diff < 3600000) return `${Math.floor(diff / 60000)} 分钟前`
  if (diff < 86400000) return `${Math.floor(diff / 3600000)} 小时前`
  return date.toLocaleDateString()
}

/* ── Actions ─────────────────────────────────── */

async function handleMarkRead(row: Notification) {
  try {
    await notificationStore.markRead(row.id)
    ElMessage.success('已标记为已读')
  } catch {
    ElMessage.error('标记失败')
  }
}

async function handleMarkAllRead() {
  try {
    await notificationStore.markAllRead()
    ElMessage.success('已全部标记为已读')
  } catch {
    ElMessage.error('操作失败')
  }
}

async function handleDelete(row: Notification) {
  try {
    await ElMessageBox.confirm('确定删除此通知？', '提示', {
      confirmButtonText: '删除',
      cancelButtonText: '取消',
      type: 'warning',
    })
    // The store doesn't have a single-delete, use direct mutation after API call
    const request = (await import('@/utils/axios')).default
    await request.delete(`/v1/notifications/${row.id}`)
    notificationStore.notifications = notificationStore.notifications.filter(
      (n) => n.id !== row.id
    )
    if (!row.read) {
      notificationStore.unreadCount = Math.max(0, notificationStore.unreadCount - 1)
    }
    ElMessage.success('删除成功')
  } catch (e: any) {
    if (e !== 'cancel') ElMessage.error('删除失败')
  }
}

async function handleClearAll() {
  try {
    await ElMessageBox.confirm('确定清空所有通知？此操作不可恢复。', '提示', {
      confirmButtonText: '清空',
      cancelButtonText: '取消',
      type: 'warning',
    })
    await notificationStore.clearAll()
    ElMessage.success('已清空所有通知')
  } catch (e: any) {
    if (e !== 'cancel') ElMessage.error('清空失败')
  }
}

/* ── Lifecycle ───────────────────────────────── */

let refreshTimer: ReturnType<typeof setInterval> | null = null

onMounted(async () => {
  loading.value = true
  await notificationStore.fetchNotifications()
  loading.value = false

  // Periodic poll for unread count
  refreshTimer = setInterval(() => {
    notificationStore.fetchUnreadCount()
  }, 30000)
})

onUnmounted(() => {
  if (refreshTimer) clearInterval(refreshTimer)
})
</script>

<style scoped>
.notifications-page { max-width: 1400px; }

.page-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: var(--space-section-gap);
  flex-wrap: wrap;
  gap: 12px;
}

.page-title {
  font-size: var(--text-xl);
  font-weight: 700;
  color: var(--color-text-primary);
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}

/* ── Card ──────────────────────────────────── */

.content-card {
  background: var(--color-bg-card);
  border-radius: var(--radius-lg);
  border: 1px solid var(--color-border-light);
}

/* ── Title cell ────────────────────────────── */

.title-cell {
  display: flex;
  align-items: center;
  gap: 8px;
}

.unread-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--color-error);
  flex-shrink: 0;
}

.title-unread {
  font-weight: 600;
  color: var(--color-text-primary);
}

.content-text {
  color: var(--color-text-secondary);
  font-size: var(--text-sm);
  line-height: 1.5;
}

.time-text {
  font-size: var(--text-xs);
  color: var(--color-text-muted);
}

/* ── Empty ─────────────────────────────────── */

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
  padding: 60px 24px;
}

.empty-state p {
  color: var(--color-text-muted);
  font-size: var(--text-base);
}
</style>
