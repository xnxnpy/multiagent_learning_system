<template>
  <div class="tutor-page">
    <div class="page-header">
      <h2 class="page-title">智能辅导</h2>
    </div>

    <div class="tutor-layout">
      <!-- 左侧会话列表 -->
      <div class="session-sidebar" :class="{ collapsed: sidebarCollapsed }">
        <div class="sidebar-top">
          <button class="toggle-btn" @click="sidebarCollapsed = !sidebarCollapsed" :title="sidebarCollapsed ? '展开侧边栏' : '收起侧边栏'">
            <el-icon :size="18"><Fold v-if="!sidebarCollapsed" /><Expand v-else /></el-icon>
          </button>
          <transition name="fade">
            <button v-if="!sidebarCollapsed" class="new-chat-btn" @click="store.createNewSession()">
              <el-icon><Plus /></el-icon> 新对话
            </button>
          </transition>
        </div>

        <transition name="fade">
          <div v-if="!sidebarCollapsed" class="sidebar-content">
            <div class="session-list">
              <div
                v-for="s in store.sessions"
                :key="s.id"
                class="session-item"
                :class="{ active: s.id === store.sessionId }"
                @click="store.switchSession(s.id)"
              >
                <div class="session-icon">
                  <el-icon :size="14"><ChatDotRound /></el-icon>
                </div>
                <div class="session-info">
                  <div class="session-title">{{ s.title || '新对话' }}</div>
                  <div v-if="s.updated_at" class="session-time">{{ formatTimeAgo(s.updated_at) }}</div>
                </div>
                <el-icon class="session-delete" @click.stop="store.deleteSession(s.id)"><Delete /></el-icon>
              </div>
              <div v-if="!store.sessions.length" class="session-empty">
                <el-icon :size="28" color="#ccc"><ChatDotRound /></el-icon>
                <span>暂无对话</span>
              </div>
            </div>
            <button v-if="store.sessions.length" class="clear-all-btn" @click="store.clearAllSessions()">
              <el-icon><Delete /></el-icon> 清空所有对话
            </button>
          </div>
        </transition>
      </div>

      <!-- 右侧聊天区 -->
      <div class="chat-main">
        <TutorChatContainer :show-header="true" :show-quick-questions="true" />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { Plus, Delete, ChatDotRound, Fold, Expand } from '@element-plus/icons-vue'
import { useTutorStore } from '@/stores/tutorStore'
import TutorChatContainer from '@/components/tutor/TutorChatContainer.vue'

const store = useTutorStore()
const sidebarCollapsed = ref(false)

function formatTimeAgo(iso: string): string {
  if (!iso) return ''
  const date = new Date(iso)
  const now = new Date()
  const diff = Math.floor((now.getTime() - date.getTime()) / 1000)
  if (diff < 60) return '刚刚'
  if (diff < 3600) return `${Math.floor(diff / 60)} 分钟前`
  if (diff < 86400) return `${Math.floor(diff / 3600)} 小时前`
  if (diff < 604800) return `${Math.floor(diff / 86400)} 天前`
  return date.toLocaleDateString('zh-CN')
}

onMounted(() => {
  store.loadSessions()
  store.markRead()
})
</script>

<style scoped>
.tutor-page { max-width: 1400px; }
.page-header { margin-bottom: var(--space-section-gap); }
.page-title { font-size: var(--text-xl); font-weight: 700; color: var(--color-text-primary); }

/* ── Layout ─────────────────────────────── */
.tutor-layout { display: flex; gap: 16px; min-height: 600px; }

/* ── Session Sidebar ────────────────────── */
.session-sidebar {
  width: 240px;
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  background: var(--color-bg-card);
  border: 1px solid var(--color-border-light);
  border-radius: var(--radius-lg);
  overflow: hidden;
  transition: width var(--transition-normal, 0.25s ease);
}
.session-sidebar.collapsed {
  width: 48px;
}

.sidebar-top {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 10px 8px;
  border-bottom: 1px solid var(--color-border-light);
}

.toggle-btn {
  width: 32px; height: 32px; border-radius: var(--radius-sm); border: none;
  background: transparent; color: var(--color-text-muted); cursor: pointer;
  display: flex; align-items: center; justify-content: center;
  transition: all var(--transition-fast); flex-shrink: 0;
}
.toggle-btn:hover { background: var(--color-bg-page); color: var(--color-text-primary); }

.new-chat-btn {
  display: flex; align-items: center; justify-content: center; gap: 6px;
  flex: 1; padding: 8px; border: 1px dashed var(--color-border); border-radius: var(--radius-sm);
  background: transparent; color: var(--color-text-secondary);
  cursor: pointer; font-size: 13px; font-family: inherit;
  transition: all var(--transition-fast); white-space: nowrap;
}
.new-chat-btn:hover { border-color: var(--color-primary); color: var(--color-primary); }

.sidebar-content {
  display: flex;
  flex-direction: column;
  flex: 1;
  overflow: hidden;
}

.session-list {
  flex: 1; overflow-y: auto; display: flex; flex-direction: column; gap: 4px;
  padding: 8px;
}

.session-item {
  display: flex; align-items: center; gap: 10px;
  padding: 10px; border-radius: var(--radius-sm); cursor: pointer;
  font-size: 13px; color: var(--color-text-secondary);
  transition: all var(--transition-fast); border: 1px solid transparent;
}
.session-item:hover { background: var(--color-bg-page); }
.session-item.active {
  background: var(--color-primary-lightest);
  border-color: var(--color-primary);
  color: var(--color-primary);
  font-weight: 500;
}
.session-icon { color: var(--color-text-muted); flex-shrink: 0; }
.session-item.active .session-icon { color: var(--color-primary); }
.session-info { flex: 1; min-width: 0; }
.session-title { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; font-size: 13px; }
.session-time { font-size: var(--text-xs); color: var(--color-text-muted); margin-top: 2px; }
.session-delete { opacity: 0; transition: opacity var(--transition-fast); color: var(--color-text-muted); flex-shrink: 0; }
.session-item:hover .session-delete { opacity: 1; }
.session-delete:hover { color: var(--color-error); }
.session-empty {
  text-align: center; padding: 30px 0; color: var(--color-text-muted);
  font-size: 13px; display: flex; flex-direction: column; align-items: center; gap: 8px;
}

.clear-all-btn {
  display: flex; align-items: center; justify-content: center; gap: 4px;
  padding: 8px; margin: 0 8px 8px; border: none; border-radius: var(--radius-sm);
  background: transparent; color: var(--color-text-muted); cursor: pointer;
  font-size: var(--text-xs); font-family: inherit; transition: all var(--transition-fast);
}
.clear-all-btn:hover { background: #fef2f2; color: var(--color-error); }

/* ── Chat Main ──────────────────────────── */
.chat-main { flex: 1; min-width: 0; }

/* ── Transition ─────────────────────────── */
.fade-enter-active, .fade-leave-active { transition: opacity var(--transition-fast), max-width var(--transition-normal, 0.25s ease); }
.fade-enter-from, .fade-leave-to { opacity: 0; max-width: 0; overflow: hidden; }
.fade-enter-to, .fade-leave-from { opacity: 1; max-width: 300px; }
</style>
