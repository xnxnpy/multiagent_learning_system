<template>
  <teleport to="body">
    <div v-if="hasTask && shouldShow" class="wf-wrap">
      <!-- 展开面板 -->
      <transition name="wf-slide">
        <div v-if="expanded" class="wf-panel">
          <div class="wf-header">
            <div class="wf-header-left">
              <span class="wf-title">工作流进度</span>
              <el-tag type="primary" size="small" effect="dark" round>{{ percent }}%</el-tag>
            </div>
            <el-icon class="wf-close" @click="expanded = false"><Close /></el-icon>
          </div>

          <div class="wf-steps">
            <div v-for="(step, i) in steps" :key="step.key + i" class="wf-step">
              <div class="wf-step-indicator">
                <div class="wf-dot" :class="step.status">
                  <el-icon v-if="step.status === 'completed'" :size="10"><Check /></el-icon>
                  <el-icon v-else-if="step.status === 'running'" class="is-loading" :size="10"><Loading /></el-icon>
                </div>
                <div v-if="i < steps.length - 1" class="wf-line" :class="{ active: step.status === 'completed' }"></div>
              </div>
              <div class="wf-step-content">
                <span class="wf-step-name" :class="step.status">{{ step.name }}</span>
                <span v-if="step.status === 'running' && currentSubStep" class="wf-step-sub">{{ currentSubStep }}</span>
              </div>
            </div>
          </div>
        </div>
      </transition>

      <!-- 浮动按钮 -->
      <div class="wf-fab" @click="expanded = !expanded">
        <div class="wf-fab-inner">
          <el-icon class="is-loading" :size="18" color="#fff"><Loading /></el-icon>
        </div>
        <svg class="wf-fab-ring" viewBox="0 0 40 40">
          <circle cx="20" cy="20" r="18" fill="none" stroke="rgba(255,255,255,0.2)" stroke-width="2.5" />
          <circle cx="20" cy="20" r="18" fill="none" stroke="#fff" stroke-width="2.5"
            :stroke-dasharray="113.1" :stroke-dashoffset="113.1 - (113.1 * percent / 100)"
            stroke-linecap="round" transform="rotate(-90 20 20)" />
        </svg>
      </div>
    </div>
  </teleport>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { useRoute } from 'vue-router'
import { Close, Loading, Check } from '@element-plus/icons-vue'
import { useAppStore } from '@/stores/appStore'

const appStore = useAppStore()
const route = useRoute()
const expanded = ref(false)

const SHOW_ROUTES = ['/student/learning-path', '/student/resources']
const shouldShow = computed(() => SHOW_ROUTES.some(r => route.path.startsWith(r)))

// 所有工作流步骤（包含子步骤）
const STEP_DEFS = [
  { key: 'build_profile', name: '画像构建', match: ['build_profile', '画像构建'] },
  { key: 'generate_path', name: '路径规划', match: ['generate_path', '路径规划'] },
  { key: 'generate_knowledge_graph', name: '知识图谱', match: ['generate_knowledge_graph', '知识图谱'] },
  { key: 'generate_document', name: '学习文档', match: ['generate_document', '文档生成', '学习文档'] },
  { key: 'generate_ppt_video', name: '教学视频', match: ['generate_ppt_video', 'PPT'] },
  { key: 'generate_mindmap', name: '思维导图', match: ['generate_mindmap', '思维导图'] },
  { key: 'generate_questions', name: '练习题目', match: ['generate_questions', '题库生成', '练习题目'] },
  { key: 'generate_code', name: '代码示例', match: ['generate_code', '代码实操', '代码示例'] },
  { key: 'generate_reading', name: '拓展阅读', match: ['generate_reading', '拓展阅读', 'reading_material'] },
  { key: 'generate_glossary', name: '术语词汇', match: ['generate_glossary', '术语词汇', 'glossary'] },
  { key: 'generate_knowledge_link', name: '知识关联', match: ['generate_knowledge_link', '知识关联', 'knowledge_link'] },
  { key: 'generate_summary', name: '学习总结', match: ['generate_summary', '学习总结', '总结报告', 'summary'] },
  { key: 'quality_evaluate', name: '质量评估', match: ['quality_evaluate', '质量评估'] },
]

const currentTask = computed(() => appStore.tasks.find(t => t.id === 'workflow'))
const hasTask = computed(() => !!currentTask.value && currentTask.value.status === 'running')
const percent = computed(() => currentTask.value?.progress || 0)

const currentSubStep = computed(() => {
  const detail = currentTask.value?.detail || ''
  if (!detail) return ''
  const parts = detail.split('·')
  return parts.length > 1 ? parts[1].trim() : ''
})

const steps = computed(() => {
  const task = currentTask.value
  if (!task) return STEP_DEFS.map(s => ({ ...s, status: 'waiting' as const }))
  const detail = task.detail || ''

  // 找当前正在运行的步骤索引
  let currentIdx = -1
  for (let i = 0; i < STEP_DEFS.length; i++) {
    const matched = STEP_DEFS[i].match.some(m => detail.includes(m))
    if (matched) { currentIdx = i; break }
  }

  return STEP_DEFS.map((s, i) => {
    let status: 'waiting' | 'running' | 'completed' = 'waiting'
    if (currentIdx >= 0) {
      if (i < currentIdx) status = 'completed'
      else if (i === currentIdx) status = 'running'
    }
    return { ...s, status }
  })
})
</script>

<style>
.wf-wrap {
  position: fixed;
  bottom: 80px;
  right: 24px;
  z-index: 2000;
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 12px;
}

/* ── FAB ───────────────────── */
.wf-fab {
  width: 44px;
  height: 44px;
  border-radius: 50%;
  position: relative;
  cursor: pointer;
  transition: transform var(--transition-fast);
}
.wf-fab:hover { transform: scale(1.08); }

.wf-fab-inner {
  position: absolute;
  inset: 0;
  border-radius: 50%;
  background: linear-gradient(135deg, var(--color-primary), var(--color-primary-soft));
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 4px 14px rgba(43, 45, 66, 0.4);
}

.wf-fab-ring {
  position: absolute;
  inset: -3px;
  width: calc(100% + 6px);
  height: calc(100% + 6px);
}

/* ── Panel ───────────────────── */
.wf-panel {
  width: 260px;
  max-height: 70vh;
  overflow-y: auto;
  background: var(--color-bg-card);
  border-radius: var(--radius-xl);
  box-shadow: var(--shadow-lg);
  border: 1px solid var(--color-border);
  overflow: hidden;
}

.wf-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 16px 10px;
  position: sticky;
  top: 0;
  background: var(--color-bg-card);
  z-index: 1;
}
.wf-header-left {
  display: flex;
  align-items: center;
  gap: 8px;
}
.wf-title {
  font-size: var(--text-sm);
  font-weight: 600;
  color: var(--color-text-primary);
}
.wf-close {
  cursor: pointer;
  color: var(--color-text-muted);
  transition: color var(--transition-fast);
}
.wf-close:hover { color: var(--color-text-secondary); }

/* ── Steps ───────────────────── */
.wf-steps {
  padding: 0 16px 16px;
}

.wf-step {
  display: flex;
  gap: 10px;
}

.wf-step-indicator {
  display: flex;
  flex-direction: column;
  align-items: center;
  width: 16px;
  flex-shrink: 0;
}

.wf-dot {
  width: 16px;
  height: 16px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  background: var(--color-border);
  transition: all var(--transition-normal);
}
.wf-dot.completed {
  background: var(--color-success);
  color: #fff;
}
.wf-dot.running {
  background: var(--color-student);
  color: #fff;
  box-shadow: 0 0 0 3px rgba(176, 81, 44, 0.15);
  animation: wf-pulse 1.5s ease infinite;
}

@keyframes wf-pulse {
  0%, 100% { box-shadow: 0 0 0 3px rgba(176, 81, 44, 0.15); }
  50% { box-shadow: 0 0 0 6px rgba(176, 81, 44, 0.05); }
}

.wf-line {
  width: 2px;
  flex: 1;
  min-height: 12px;
  background: var(--color-border);
  margin: 2px 0;
  transition: background var(--transition-normal);
}
.wf-line.active { background: var(--color-success); }

.wf-step-content {
  padding-bottom: 8px;
  min-width: 0;
}

.wf-step-name {
  font-size: 13px;
  color: var(--color-text-muted);
  transition: color var(--transition-normal);
}
.wf-step-name.completed { color: var(--color-success); font-weight: 500; }
.wf-step-name.running { color: var(--color-primary); font-weight: 600; }

.wf-step-sub {
  display: block;
  font-size: 11px;
  color: var(--color-primary);
  margin-top: 2px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

/* ── Transition ───────────────────── */
.wf-slide-enter-active { transition: all 0.25s cubic-bezier(0.34,1.56,0.64,1); }
.wf-slide-leave-active { transition: all 0.15s ease-in; }
.wf-slide-enter-from { opacity: 0; transform: translateY(8px) scale(0.95); }
.wf-slide-leave-to { opacity: 0; transform: translateY(4px) scale(0.97); }
</style>
