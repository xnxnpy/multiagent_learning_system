<template>
  <el-container class="app-layout" :class="`portal-${portalType}`">
    <!-- Sidebar（深墨蓝深色底） -->
    <el-aside :width="isCollapsed ? '72px' : '256px'" class="sidebar" :class="{ collapsed: isCollapsed }">
      <!-- Logo 区 -->
      <div class="sidebar-logo" @click="isCollapsed = !isCollapsed">
        <div class="sidebar-logo__mark">
          <el-icon :size="20"><Reading /></el-icon>
        </div>
        <span v-if="!isCollapsed" class="sidebar-logo__text">智学优培</span>
      </div>

      <!-- 角色标识条（仅展开时） -->
      <div v-if="!isCollapsed" class="portal-strip">
        <span class="portal-strip__dot" :style="{ background: portalAccentColor }"></span>
        <span class="portal-strip__label">{{ portalTitle }}</span>
        <span class="portal-strip__spacer"></span>
      </div>

      <!-- 分隔细线 -->
      <div class="sidebar-divider"></div>

      <!-- 导航菜单 -->
      <el-menu
        :default-active="activeMenu"
        :collapse="isCollapsed"
        :collapse-transition="false"
        class="sidebar-menu"
        @select="handleMenuSelect"
      >
        <el-menu-item
          v-for="item in menuItemsWithIcons"
          :key="item.key"
          :index="item.key"
        >
          <el-icon class="menu-icon"><component :is="item.icon" /></el-icon>
          <template #title>{{ item.label }}</template>
        </el-menu-item>
      </el-menu>

      <div class="sidebar-grow"></div>

      <!-- 侧栏底部：用户卡 -->
      <div class="sidebar-footer">
        <el-dropdown trigger="click" @command="handleCommand" placement="top-start">
          <div class="user-card">
            <el-avatar :size="isCollapsed ? 36 : 40" :style="{ background: avatarColor }" class="user-avatar">
              {{ initial }}
            </el-avatar>
            <div v-if="!isCollapsed" class="user-meta">
              <div class="user-name">{{ displayName }}</div>
              <div class="user-role">
                <span class="role-dot" :style="{ background: portalAccentColor }"></span>
                {{ roleLabel }}
              </div>
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

    <!-- Main Container（象牙纸色） -->
    <el-container class="main-container">
      <!-- Top bar（编辑风：细线分隔，无粗线） -->
      <el-header class="top-bar" height="64px">
        <div class="top-bar-left">
          <el-button text @click="isCollapsed = !isCollapsed" class="collapse-btn">
            <el-icon :size="18"><Fold v-if="!isCollapsed" /><Expand v-else /></el-icon>
          </el-button>
          <el-breadcrumb separator="/" v-if="breadcrumbs.length > 1" class="breadcrumb-edit">
            <el-breadcrumb-item v-for="(crumb, i) in breadcrumbs" :key="i">
              {{ crumb }}
            </el-breadcrumb-item>
          </el-breadcrumb>
          <span v-else class="page-eyebrow">
            <span class="dot" :style="{ background: portalAccentColor }"></span>
            {{ portalTitle }}
          </span>
        </div>
        <div class="top-bar-right">
          <template v-if="enableNotifications">
            <el-badge :value="unreadCount" :max="99" :hidden="unreadCount === 0" class="notif-badge">
              <el-button text circle @click="router.push(`/${portalType}/notifications`)" class="notif-btn">
                <el-icon :size="18"><Bell /></el-icon>
              </el-button>
            </el-badge>
            <span class="v-sep"></span>
          </template>
          <div class="greeting-wrap">
            <span class="greeting-time">{{ greetingEmoji }}</span>
            <span class="greeting-text">{{ greetingText }}，{{ displayName }}</span>
          </div>
        </div>
      </el-header>

      <!-- Page content -->
      <el-main class="page-content">
        <slot>
          <router-view />
        </slot>
      </el-main>
    </el-container>

    <!-- 资源生成进度浮窗（编辑风：柔和阴影，顶部色条） -->
    <transition name="gen-slide">
      <div v-if="genProgress" class="gen-progress-panel" :class="`gen-progress-${portalType}`">
        <div class="gen-progress__accent"></div>
        <div class="gen-progress-header">
          <span class="gen-icon">{{ genProgress.status === 'completed' ? '✓' : '⏳' }}</span>
          <div>
            <div class="gen-title">
              {{ genProgress.status === 'completed' ? '生成完成' : '资源生成中' }}
            </div>
            <div class="gen-subtitle">{{ genProgress.stepName }}</div>
          </div>
        </div>
        <el-progress :percentage="genProgress.progress" :stroke-width="5"
                     :status="genProgress.status === 'completed' ? 'success' : undefined"
                     :show-text="false" />
      </div>
    </transition>
  </el-container>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted, onUnmounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ElMessage, ElNotification } from 'element-plus'
import {
  User, SwitchButton, Bell, Fold, Expand,
  Reading, MapLocation, Collection, ChatDotRound,
  DataAnalysis, DataLine, Document, Notebook,
  Management, View, Setting, Files, Folder,
  UserFilled, Lock, Tools, Histogram, Medal,
} from '@element-plus/icons-vue'
import type { MenuItem } from '@/types'

const ICON_MAP: Record<string, any> = {
  profile: UserFilled,
  'learning-path': MapLocation,
  resources: Collection,
  tutor: ChatDotRound,
  report: DataLine,
  notifications: Bell,
  'my-learning': Notebook,
  courses: Reading,
  assignments: Files,
  analytics: Histogram,
  knowledge: Folder,
  users: Management,
  config: Setting,
  models: Tools,
  'content-security': Lock,
  logs: Document,
  backup: View,
  showcase: Medal,
}

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

const menuItemsWithIcons = computed(() =>
  props.menuItems.map(it => ({
    ...it,
    icon: it.icon || ICON_MAP[it.key] || Document,
  }))
)

const portalAccentColor = computed(() => props.portalColor)

const genProgress = ref<{ stepName: string; progress: number; status: string } | null>(null)
let genTimer: ReturnType<typeof setTimeout> | null = null

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

const greetingEmoji = computed(() => {
  const h = new Date().getHours()
  if (h < 6) return '🌙'
  if (h < 11) return '☕'
  if (h < 14) return '🌞'
  if (h < 18) return '📖'
  return '🌆'
})

const greetingText = computed(() => {
  const h = new Date().getHours()
  if (h < 12) return '上午好'
  if (h < 18) return '下午好'
  return '晚上好'
})

const handleMenuSelect = (key: string) => {
  router.push(`/${props.portalType}/${key}`)
}

const handleCommand = (command: string) => {
  if (command === 'profile') {
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
        if (data.notification_type === 'resource_generation') {
          const d = data.data || {}
          if (d.status === 'completed') {
            genProgress.value = { stepName: '完成', progress: 100, status: 'completed' }
            if (genTimer) clearTimeout(genTimer)
            genTimer = setTimeout(() => { genProgress.value = null }, 3000)
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

/* ═══════════════════ Sidebar 纯白 + 角色辅色点缀 ═══════════════════ */

.sidebar {
  background: var(--color-bg-sidebar);
  display: flex;
  flex-direction: column;
  transition: width 0.32s var(--ease-editing);
  overflow: hidden;
  position: relative;
  border-right: 1px solid var(--color-border);
  box-shadow: 2px 0 12px rgba(29, 31, 51, 0.04);
}

/* 顶部角色色条（3px 装饰） */
.sidebar::before {
  content: '';
  position: absolute;
  top: 0; left: 0; right: 0;
  height: 3px;
  background: var(--portal-accent, var(--color-primary));
  z-index: 2;
}
.portal-student .sidebar { --portal-accent: var(--color-student); }
.portal-teacher .sidebar { --portal-accent: var(--color-teacher); }
.portal-admin   .sidebar { --portal-accent: var(--color-admin); }

.sidebar-logo {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 24px 20px 18px;
  color: var(--color-text-ink);
  cursor: pointer;
  white-space: nowrap;
  position: relative;
  z-index: 1;
}

.sidebar-logo__mark {
  width: 34px; height: 34px;
  border-radius: 10px;
  background: linear-gradient(135deg, var(--color-primary) 0%, var(--color-primary-deep) 100%);
  color: #fff;
  display: flex; align-items: center; justify-content: center;
  flex-shrink: 0;
  box-shadow: 0 3px 10px rgba(43, 45, 66, 0.18);
}

.sidebar-logo__text {
  font-family: var(--font-serif);
  font-size: 19px;
  font-weight: var(--weight-semibold);
  letter-spacing: 0.02em;
  color: var(--color-text-ink);
}

/* ── 角色标识条 ─────────────────── */

.portal-strip {
  display: flex;
  align-items: center;
  gap: 8px;
  margin: 0 16px 10px;
  padding: 9px 12px;
  background: var(--portal-accent-pale, var(--color-primary-faint));
  border: 1px solid var(--portal-accent-soft, var(--color-primary-pale));
  border-radius: 10px;
  position: relative;
  z-index: 1;
}
.portal-student .portal-strip { --portal-accent-pale: var(--color-student-pale); --portal-accent-soft: var(--color-student-soft); }
.portal-teacher .portal-strip { --portal-accent-pale: var(--color-teacher-pale); --portal-accent-soft: var(--color-teacher-soft); }
.portal-admin   .portal-strip { --portal-accent-pale: var(--color-admin-pale); --portal-accent-soft: var(--color-admin-soft); }

.portal-strip__dot {
  width: 7px; height: 7px;
  border-radius: 50%;
  flex-shrink: 0;
  box-shadow: 0 0 6px currentColor;
}

.portal-strip__label {
  font-size: var(--text-sm);
  font-weight: var(--weight-semibold);
  color: var(--color-text-body);
  letter-spacing: 0.04em;
}

.portal-strip__spacer {
  flex: 1;
}

.portal-strip__kbd {
  font-family: var(--font-mono);
  font-size: 10px;
  color: var(--color-text-muted);
  letter-spacing: 0.08em;
}

.sidebar-divider {
  height: 1px;
  margin: 8px 20px 12px;
  background: linear-gradient(90deg, transparent, var(--color-border-light), transparent);
  position: relative;
  z-index: 1;
}

/* ── Menu ───────────────────────── */

.sidebar-menu {
  flex: 1;
  border-right: none !important;
  background: transparent !important;
  padding: 4px 12px;
  position: relative;
  z-index: 1;
}

.sidebar-menu :deep(.el-menu-item) {
  color: var(--color-text-body);
  font-size: 14px;
  font-weight: var(--weight-medium);
  margin: 3px 0;
  border-radius: 10px;
  height: 42px;
  line-height: 42px;
  padding: 0 14px !important;
  transition: all 0.2s var(--ease-editing);
  position: relative;
}

.sidebar-menu :deep(.el-menu-item .menu-icon) {
  color: var(--color-text-muted);
  font-size: 17px;
  margin-right: 6px;
}

.sidebar-menu :deep(.el-menu-item:hover) {
  background: var(--color-bg-page-2);
  color: var(--color-text-ink);
}
.sidebar-menu :deep(.el-menu-item:hover .menu-icon) {
  color: var(--color-text-body);
}

/* 激活态：角色色左条 + 浅色底 */
.sidebar-menu :deep(.el-menu-item.is-active) {
  background: var(--portal-accent-pale, var(--color-primary-faint));
  color: var(--portal-accent, var(--color-primary));
  font-weight: var(--weight-semibold);
}
.sidebar-menu :deep(.el-menu-item.is-active)::before {
  content: '';
  position: absolute;
  left: 6px;
  top: 50%;
  transform: translateY(-50%);
  width: 3px;
  height: 18px;
  border-radius: 2px;
  background: var(--portal-accent, var(--color-primary));
}
.sidebar-menu :deep(.el-menu-item.is-active .menu-icon) {
  color: var(--portal-accent, var(--color-primary));
}

.portal-student .sidebar-menu :deep(.el-menu-item.is-active) { --portal-accent: var(--color-student); --portal-accent-pale: var(--color-student-pale); }
.portal-teacher .sidebar-menu :deep(.el-menu-item.is-active) { --portal-accent: var(--color-teacher); --portal-accent-pale: var(--color-teacher-pale); }
.portal-admin   .sidebar-menu :deep(.el-menu-item.is-active) { --portal-accent: var(--color-admin); --portal-accent-pale: var(--color-admin-pale); }

.sidebar-grow { flex: 0.5; }

/* ── User card ──────────────────── */

.sidebar-footer {
  padding: 12px;
  border-top: 1px solid var(--color-border-light);
  position: relative;
  z-index: 1;
}

.user-card {
  display: flex;
  align-items: center;
  gap: 11px;
  padding: 10px;
  border-radius: 12px;
  cursor: pointer;
  transition: background 0.2s;
}

.user-card:hover {
  background: var(--color-bg-page-2);
}

.user-avatar {
  font-weight: var(--weight-semibold);
  font-size: 14px;
  color: #fff;
  box-shadow: 0 2px 6px rgba(0, 0, 0, 0.1);
}

.user-meta {
  overflow: hidden;
  min-width: 0;
  flex: 1;
}

.user-name {
  color: var(--color-text-ink);
  font-size: 13.5px;
  font-weight: var(--weight-semibold);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  line-height: 1.3;
}

.user-role {
  color: var(--color-text-muted);
  font-size: 11.5px;
  margin-top: 2px;
  display: flex;
  align-items: center;
  gap: 5px;
}

.role-dot {
  width: 5px; height: 5px;
  border-radius: 50%;
  flex-shrink: 0;
}

/* ═══════════════════ Main Container ═══════════════════ */

.main-container {
  background: var(--color-bg-page);
  overflow: hidden;
}

.top-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: var(--color-bg-card);
  border-bottom: 1px solid var(--color-border-light);
  padding: 0 28px;
  position: relative;
}
.top-bar::after {
  content: '';
  position: absolute;
  top: 0; left: 0; right: 0;
  height: 3px;
  background: linear-gradient(90deg,
    transparent 0%,
    var(--portal-accent, var(--color-primary)) 20%,
    var(--color-primary) 80%,
    transparent 100%);
  opacity: 0.7;
}
.portal-student .top-bar::after { --portal-accent: var(--color-student); }
.portal-teacher .top-bar::after { --portal-accent: var(--color-teacher); }
.portal-admin   .top-bar::after { --portal-accent: var(--color-admin); }

.top-bar-left {
  display: flex;
  align-items: center;
  gap: 10px;
}

.collapse-btn {
  width: 34px; height: 34px;
  border-radius: 9px !important;
  color: var(--color-text-muted) !important;
  transition: all 0.2s !important;
}
.collapse-btn:hover {
  background: var(--color-bg-page-2) !important;
  color: var(--color-text-ink) !important;
}

.page-eyebrow {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  font-size: var(--text-xs);
  color: var(--color-text-muted);
  letter-spacing: 0.12em;
  text-transform: uppercase;
  font-weight: var(--weight-semibold);
  padding-left: 6px;
}
.page-eyebrow .dot {
  width: 6px; height: 6px;
  border-radius: 50%;
}

.top-bar-right {
  display: flex;
  align-items: center;
  gap: 14px;
}

.notif-btn {
  width: 36px; height: 36px;
  border-radius: 10px !important;
  color: var(--color-text-muted) !important;
  transition: all 0.2s !important;
}
.notif-btn:hover {
  background: var(--color-bg-page-2) !important;
  color: var(--color-text-ink) !important;
}

.notif-badge :deep(.el-badge__content) {
  background: var(--color-student);
  border-color: var(--color-student);
  font-size: 10px;
}

.v-sep {
  width: 1px;
  height: 18px;
  background: var(--color-border-light);
}

.greeting-wrap {
  display: flex;
  align-items: center;
  gap: 9px;
  padding: 6px 14px;
  background: var(--color-bg-page-2);
  border-radius: 10px;
  border: 1px solid var(--color-border-light);
}

.greeting-time {
  font-size: 16px;
  line-height: 1;
}

.greeting-text {
  font-size: 13px;
  color: var(--color-text-body);
  font-weight: var(--weight-medium);
}

.page-content {
  padding: var(--space-page-padding);
  overflow-y: auto;
  height: calc(100vh - 64px);
}

/* ═══════════════════ 资源生成浮窗 ═══════════════════ */

.gen-progress-panel {
  position: fixed;
  bottom: 28px;
  left: 284px;
  z-index: 2000;
  width: 300px;
  background: #fff;
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-lifted);
  border: 1px solid var(--color-border-light);
  padding: 16px 18px 18px;
  overflow: hidden;
}
.gen-progress__accent {
  position: absolute;
  top: 0; left: 0; right: 0;
  height: 3px;
  background: var(--color-primary);
}
.gen-progress-student .gen-progress__accent { background: var(--color-student); }
.gen-progress-teacher .gen-progress__accent { background: var(--color-teacher); }
.gen-progress-admin   .gen-progress__accent { background: var(--color-admin); }

.gen-progress-header {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  margin-bottom: 12px;
}
.gen-icon {
  width: 32px; height: 32px;
  border-radius: 9px;
  background: var(--color-primary-pale);
  color: var(--color-primary);
  display: flex; align-items: center; justify-content: center;
  font-size: 15px;
  flex-shrink: 0;
}
.gen-progress-student .gen-icon { background: var(--color-student-pale); color: var(--color-student); }
.gen-progress-teacher .gen-icon { background: var(--color-teacher-pale); color: var(--color-teacher); }
.gen-progress-admin   .gen-icon { background: var(--color-admin-pale);   color: var(--color-admin); }

.gen-title {
  font-size: 14px;
  font-weight: var(--weight-semibold);
  color: var(--color-text-ink);
  line-height: 1.2;
}
.gen-subtitle {
  font-size: 12px;
  color: var(--color-text-muted);
  margin-top: 3px;
  line-height: 1.4;
}

.gen-slide-enter-active { transition: all 0.32s var(--ease-editing); }
.gen-slide-leave-active { transition: all 0.22s var(--ease-editing); }
.gen-slide-enter-from { opacity: 0; transform: translateY(14px) scale(0.98); }
.gen-slide-leave-to { opacity: 0; transform: translateY(8px); }

/* ═══════════════════ Responsive ═══════════════════ */

@media (max-width: 768px) {
  .sidebar {
    position: fixed;
    z-index: 1000;
    height: 100vh;
    box-shadow: var(--shadow-pop);
  }
  .sidebar.collapsed {
    width: 0 !important;
  }
  .gen-progress-panel {
    left: 20px;
    right: 20px;
    width: auto;
  }
}
</style>
