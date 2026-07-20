<template>
  <teleport to="body">
    <div v-if="shouldShow" class="tutor-float-wrapper">
      <!-- 折叠态：圆形按钮 -->
      <transition name="tutor-float-btn">
        <div v-if="!store.isFloatingOpen" class="tutor-float-btn" @click="store.toggleFloating()">
          <el-badge :value="store.unreadCount" :hidden="store.unreadCount === 0" :offset="[-2, -2]">
            <div class="float-btn-inner">
              <el-icon :size="24" color="#fff"><ChatDotRound /></el-icon>
            </div>
          </el-badge>
        </div>
      </transition>

      <!-- 展开态：聊天窗口 -->
      <transition name="tutor-float-panel">
        <div
          v-if="store.isFloatingOpen"
          class="tutor-float-panel"
          :style="panelStyle"
        >
          <!-- 拖拽条 -->
          <div class="panel-drag-bar" @mousedown="startDrag">
            <span class="drag-title">AI 辅导助手</span>
            <el-icon class="drag-close" @click="store.toggleFloating()"><Close /></el-icon>
          </div>

          <!-- 聊天内容 -->
          <TutorChatContainer :compact="true" :show-header="false" :show-quick-questions="false" />
        </div>
      </transition>
    </div>
  </teleport>
</template>

<script setup lang="ts">
import { ref, reactive, computed } from 'vue'
import { useRoute } from 'vue-router'
import { ChatDotRound, Close } from '@element-plus/icons-vue'
import { useTutorStore } from '@/stores/tutorStore'
import TutorChatContainer from './TutorChatContainer.vue'

const store = useTutorStore()
const route = useRoute()

const FLOATING_ROUTES = ['/student/resources', '/student/learning-path']

const shouldShow = computed(() =>
  FLOATING_ROUTES.some(r => route.path.startsWith(r))
)

// ── 拖拽逻辑 ──────────────────────────────────────────

const PANEL_W = 380
const PANEL_H = 500
const MARGIN = 24

const position = reactive({
  x: window.innerWidth - PANEL_W - MARGIN,
  y: window.innerHeight - PANEL_H - MARGIN,
})
const isDragging = ref(false)
const dragOffset = reactive({ x: 0, y: 0 })

const panelStyle = computed(() => ({
  left: `${position.x}px`,
  top: `${position.y}px`,
}))

function startDrag(e: MouseEvent) {
  isDragging.value = true
  dragOffset.x = e.clientX - position.x
  dragOffset.y = e.clientY - position.y
  document.addEventListener('mousemove', onDrag)
  document.addEventListener('mouseup', stopDrag)
}

function onDrag(e: MouseEvent) {
  if (!isDragging.value) return
  position.x = Math.max(0, Math.min(window.innerWidth - 60, e.clientX - dragOffset.x))
  position.y = Math.max(0, Math.min(window.innerHeight - 60, e.clientY - dragOffset.y))
}

function stopDrag() {
  isDragging.value = false
  document.removeEventListener('mousemove', onDrag)
  document.removeEventListener('mouseup', stopDrag)
}
</script>

<style>
/* ── Floating button ─────────────────────── */
.tutor-float-wrapper {
  position: fixed;
  bottom: 24px;
  right: 24px;
  z-index: 2000;
}

.tutor-float-btn {
  cursor: pointer;
}

.float-btn-inner {
  width: 52px;
  height: 52px;
  border-radius: 50%;
  background: linear-gradient(135deg, #2563EB, #3B82F6);
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 4px 16px rgba(37,99,235,0.4);
  transition: all var(--transition-normal);
}

.float-btn-inner:hover {
  transform: scale(1.08);
  box-shadow: 0 6px 24px rgba(37,99,235,0.5);
}

/* ── Chat panel ─────────────────────────── */
.tutor-float-panel {
  position: fixed;
  width: 380px;
  height: 500px;
  background: var(--color-bg-card);
  border-radius: var(--radius-xl);
  box-shadow: var(--shadow-lg);
  display: flex;
  flex-direction: column;
  overflow: hidden;
  border: 1px solid var(--color-border);
}

.panel-drag-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 14px;
  background: linear-gradient(135deg, #2563EB, #3B82F6);
  color: #fff;
  cursor: move;
  user-select: none;
  flex-shrink: 0;
}

.drag-title {
  font-size: var(--text-sm);
  font-weight: 600;
}

.drag-close {
  cursor: pointer;
  opacity: 0.8;
  transition: opacity var(--transition-fast);
  font-size: 18px;
}

.drag-close:hover {
  opacity: 1;
}

/* ── Override chat-messages for flex ────── */
.tutor-float-panel .chat-messages {
  flex: 1;
  overflow-y: auto;
  min-height: 0;
}

/* ── Transitions ─────────────────────────── */
.tutor-float-btn-enter-active,
.tutor-float-btn-leave-active {
  transition: all 0.3s ease;
}
.tutor-float-btn-enter-from,
.tutor-float-btn-leave-to {
  opacity: 0;
  transform: scale(0.5);
}

.tutor-float-panel-enter-active,
.tutor-float-panel-leave-active {
  transition: all 0.25s ease;
}
.tutor-float-panel-enter-from,
.tutor-float-panel-leave-to {
  opacity: 0;
  transform: scale(0.9) translateY(10px);
}
</style>
