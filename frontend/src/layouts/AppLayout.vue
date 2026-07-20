<template>
  <el-container class="app-layout">
    <!-- Sidebar -->
    <el-aside :width="isCollapsed ? '64px' : '240px'" class="sidebar" :class="{ collapsed: isCollapsed }">
      <!-- Logo -->
      <div class="sidebar-logo" @click="isCollapsed = !isCollapsed">
        <el-icon :size="24"><Cpu /></el-icon>
        <span v-if="!isCollapsed" class="logo-text">智学优培</span>
      </div>

      <!-- Portal badge -->
      <div v-if="!isCollapsed" class="portal-badge" :style="{ backgroundColor: portalColor }">
        {{ portalTitle }}
      </div>

      <!-- Navigation -->
      <el-menu
        :default-active="activeMenu"
        :collapse="isCollapsed"
        :collapse-transition="false"
        class="sidebar-menu"
        @select="handleMenuSelect"
      >
        <el-menu-item
          v-for="item in menuItems"
          :key="item.key"
          :index="item.key"
        >
          <el-icon v-if="item.icon">
            <component :is="item.icon" />
          </el-icon>
          <template #title>{{ item.label }}</template>
        </el-menu-item>
      </el-menu>

      <!-- User info at bottom -->
      <div class="sidebar-footer">
        <el-dropdown trigger="click" @command="handleCommand" placement="top-start">
          <div class="user-card">
            <el-avatar :size="32" :style="{ backgroundColor: avatarColor }">
              {{ initial }}
            </el-avatar>
            <div v-if="!isCollapsed" class="user-meta">
              <div class="user-name">{{ displayName }}</div>
              <div class="user-role">{{ roleLabel }}</div>
            </div>
          </div>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item command="profile">
                <el-icon><User /></el-icon>个人中心
              </el-dropdown-item>
              <el-dropdown-item command="logout" divided>
                <el-icon><SwitchButton /></el-icon>退出登录
              </el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
      </div>
    </el-aside>

    <!-- Main Content -->
    <el-container class="main-container">
      <!-- Top bar -->
      <el-header class="top-bar" height="56px">
        <div class="top-bar-left">
          <el-button text @click="isCollapsed = !isCollapsed">
            <el-icon :size="20"><Fold v-if="!isCollapsed" /><Expand v-else /></el-icon>
          </el-button>
          <el-breadcrumb separator="/" v-if="breadcrumbs.length > 1">
            <el-breadcrumb-item v-for="(crumb, i) in breadcrumbs" :key="i">
              {{ crumb }}
            </el-breadcrumb-item>
          </el-breadcrumb>
        </div>
        <div class="top-bar-right">
          <!-- Notification bell (student only) -->
          <template v-if="enableNotifications">
            <el-badge :value="unreadCount" :max="99" :hidden="unreadCount === 0">
              <el-button text circle @click="router.push(`/${portalType}/notifications`)">
                <el-icon :size="20"><Bell /></el-icon>
              </el-button>
            </el-badge>
            <el-divider direction="vertical" />
          </template>
          <span class="greeting">{{ greetingText }}，{{ displayName }}</span>
        </div>
      </el-header>

      <!-- Page content -->
      <el-main class="page-content">
        <slot>
          <router-view />
        </slot>
      </el-main>
    </el-container>

    <!-- 资源生成进度浮窗 -->
    <transition name="gen-slide">
      <div v-if="genProgress" class="gen-progress-panel">
        <div class="gen-progress-header">
          <span class="gen-icon">📚</span>
          <span class="gen-title">{{ genProgress.status === 'completed' ? '生成完成' : '资源生成中' }}</span>
        </div>
        <div class="gen-progress-body">
          <span class="gen-step">{{ genProgress.stepName }}</span>
          <el-progress :percentage="genProgress.progress" :stroke-width="6"
                       :status="genProgress.status === 'completed' ? 'success' : undefined"
                       style="flex: 1;" />
        </div>
      </div>
    </transition>
  </el-container>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted, onUnmounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ElMessage, ElNotification } from 'element-plus'
import {
  Cpu, User, SwitchButton, Bell, Fold, Expand,
  Reading, MapLocation, Collection, ChatDotRound,
  DataAnalysis, Bell as BellIcon, UserFilled,
  Management, View, Setting, Document
} from '@element-plus/icons-vue'
import type { MenuItem } from '@/types'

const props = withDefaults(defineProps<{
  menuItems: (MenuItem & { icon?: any })[]
  portalTitle: string
  portalType: 'student' | 'teacher' | 'admin'
  portalColor: string
  avatarColor: string
  enableNotifications?: boolean
}>(), {
  enableNotifications: false
})

const router = useRouter()
const route = useRoute()
const isCollapsed = ref(false)
const unreadCount = ref(0)
let ws: any = null

// ── 资源生成进度浮窗 ──────────────────────────────────────────
const genProgress = ref<{ stepName: string; progress: number; status: string } | null>(null)
let genTimer: ReturnType<typeof setTimeout> | null = null

// ── Computed ──────────────────────────────────────────────────

const activeMenu = computed(() => {
  const parts = route.path.split('/')
  return parts[parts.length - 1] || ''
})

const displayName = computed(() => {
  try {
    const user = JSON.parse(localStorage.getItem('user') || '{}')
    return user.real_name || user.username || '用户'
  } catch { return '用户' }
})

const initial = computed(() => displayName.value.charAt(0).toUpperCase())

const roleLabel = computed(() => {
  const labels: Record<string, string> = { student: '学生', teacher: '教师', admin: '管理员' }
  return labels[props.portalType] || ''
})

const breadcrumbs = computed(() => {
  const current = props.menuItems.find(m => m.key === activeMenu.value)
  return current ? [props.portalTitle.replace('智学优培 - ', ''), current.label] : []
})

const greetingText = computed(() => {
  const h = new Date().getHours()
  if (h < 12) return '上午好'
  if (h < 18) return '下午好'
  return '晚上好'
})

// ── Handlers ──────────────────────────────────────────────────

const handleMenuSelect = (key: string) => {
  router.push(`/${props.portalType}/${key}`)
}

const handleCommand = (command: string) => {
  if (command === 'profile') {
    // 学生端个人中心走独立路由 /profile，其他端走 /{portalType}/profile
    if (props.portalType === 'student') {
      router.push('/profile')
    } else {
      router.push(`/${props.portalType}/profile`)
    }
  } else if (command === 'logout') {
    localStorage.removeItem('token')
    localStorage.removeItem('user')
    localStorage.removeItem('userRole')
    if (ws) ws.close()
    ElMessage.success('已退出登录')
    router.push('/login')
  }
}

// ── Notifications WebSocket ───────────────────────────────────

const initNotifications = async () => {
  if (!props.enableNotifications) return
  try {
    const { createNotificationWebSocket } = await import('@/utils/websocket')
    const token = localStorage.getItem('token')
    if (!token) return

    ws = createNotificationWebSocket(token)
    ws.on('open', () => fetchUnread())
    ws.on('message', (data: any) => {
      if (data.type === 'notification') {
        fetchUnread()
        // 评估结果弹窗
        if (data.notification_type === 'evaluation_result') {
          const summary = data.content || data.data?.summary || '评估已完成'
          ElNotification({
            title: data.title || '📊 阶段学习评估',
            message: summary,
            type: 'info',
            duration: 8000,
            position: 'top-right',
          })
        }
        // 资源生成进度浮窗
        if (data.notification_type === 'resource_generation') {
          const d = data.data || {}
          if (d.status === 'completed') {
            genProgress.value = { stepName: '完成', progress: 100, status: 'completed' }
            if (genTimer) clearTimeout(genTimer)
            genTimer = setTimeout(() => { genProgress.value = null }, 3000)
            // 通知 Resources 页面刷新数据
            window.dispatchEvent(new CustomEvent('resource-generated', { detail: d }))
          } else {
            genProgress.value = {
              stepName: d.step_name || '生成中',
              progress: d.progress || 0,
              status: 'running',
            }
          }
        }
      }
    })
    ws.connect(token)
  } catch (e) { /* ignore */ }
}

const fetchUnread = async () => {
  try {
    const { default: axios } = await import('@/utils/axios')
    const res = await axios.get('/v1/notifications/unread-count')
    unreadCount.value = res?.count || 0
  } catch { /* ignore */ }
}

watch(() => route.path, () => { if (props.enableNotifications) fetchUnread() })

onMounted(() => { initNotifications() })
onUnmounted(() => {
  if (ws) ws.close()
  if (genTimer) clearTimeout(genTimer)
})
</script>

<style scoped>
.app-layout {
  height: 100vh;
  overflow: hidden;
}

/* ── Sidebar ───────────────────────────────────── */

.sidebar {
  background: #fafafa;
  border-right: 1px solid #eeeeee;
  display: flex;
  flex-direction: column;
  transition: width 0.28s ease;
  overflow: hidden;
}

.sidebar-logo {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 20px 20px 12px;
  color: #1a1a1a;
  cursor: pointer;
  white-space: nowrap;
}

.sidebar-logo .el-icon {
  background: linear-gradient(135deg, #1E88E5, #42A5F5);
  color: #fff;
  border-radius: 6px;
  padding: 4px;
}

.logo-text {
  font-size: 20px;
  font-weight: 700;
  letter-spacing: 0.5px;
  color: #1a1a1a;
}

.portal-badge {
  margin: 0 16px 12px;
  padding: 4px 12px;
  border-radius: 6px;
  color: #fff;
  font-size: 15px;
  font-weight: 600;
  text-align: center;
  letter-spacing: 1px;
}

.sidebar-menu {
  flex: 1;
  border-right: none !important;
  background: transparent !important;
}

.sidebar-menu :deep(.el-menu-item) {
  color: #666;
  font-size: 16px;
  margin: 2px 8px;
  border-radius: 8px;
  height: 42px;
  line-height: 42px;
}

.sidebar-menu :deep(.el-menu-item:hover) {
  background: #f0f0f0;
  color: #333;
}

.sidebar-menu :deep(.el-menu-item.is-active) {
  background: #e8f0fe;
  color: #1E88E5;
}

.sidebar-menu :deep(.el-menu-item .el-icon) {
  color: #999;
}

.sidebar-menu :deep(.el-menu-item.is-active .el-icon) {
  color: #1E88E5;
}

.sidebar-footer {
  padding: 12px;
  border-top: 1px solid #eee;
}

.user-card {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px;
  border-radius: 8px;
  cursor: pointer;
  transition: background 0.2s;
}

.user-card:hover {
  background: #f0f0f0;
}

.user-meta {
  overflow: hidden;
}

.user-name {
  color: #333;
  font-size: 13px;
  font-weight: 600;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.user-role {
  color: #bbb;
  font-size: 11px;
}

/* ── Main Container ────────────────────────────── */

.main-container {
  background: var(--color-bg-page, #F4F5F7);
  overflow: hidden;
}

.top-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: #fff;
  border-bottom: 1px solid #E5E7EB;
  padding: 0 24px;
}

.top-bar-left {
  display: flex;
  align-items: center;
  gap: 8px;
}

.top-bar-right {
  display: flex;
  align-items: center;
  gap: 12px;
}

.greeting {
  font-size: 13px;
  color: var(--color-text-secondary, #6B7280);
}

.page-content {
  padding: var(--space-page-padding, 24px);
  overflow-y: auto;
  height: calc(100vh - 56px);
}

/* ── Transitions ───────────────────────────────── */

.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.15s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}

/* ── Responsive ────────────────────────────────── */

@media (max-width: 768px) {
  .sidebar {
    position: fixed;
    z-index: 1000;
    height: 100vh;
  }
  .sidebar.collapsed {
    width: 0 !important;
  }
}

/* ── 资源生成进度浮窗 ─────────────────────────────── */
.gen-progress-panel {
  position: fixed;
  bottom: 24px;
  left: 260px;
  z-index: 2000;
  width: 280px;
  background: #fff;
  border-radius: 12px;
  box-shadow: 0 6px 24px rgba(0, 0, 0, 0.12);
  border: 1px solid #e5e7eb;
  padding: 14px 16px;
}
.gen-progress-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 10px;
}
.gen-icon { font-size: 16px; }
.gen-title { font-size: 13px; font-weight: 600; color: #374151; }
.gen-progress-body {
  display: flex;
  align-items: center;
  gap: 10px;
}
.gen-step {
  font-size: 12px;
  color: #6b7280;
  white-space: nowrap;
  min-width: 70px;
}

.gen-slide-enter-active { transition: all 0.3s ease-out; }
.gen-slide-leave-active { transition: all 0.2s ease-in; }
.gen-slide-enter-from { opacity: 0; transform: translateY(12px); }
.gen-slide-leave-to { opacity: 0; transform: translateY(8px); }
</style>
