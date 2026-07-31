<template>
  <div class="agent-collab">
    <div class="collab-header">
      <h3 class="collab-title">多智能体协作</h3>
      <el-tag :type="isRunning ? 'warning' : 'success'" effect="plain" size="small">
        {{ isRunning ? '协作中...' : '已完成' }}
      </el-tag>
    </div>

    <div class="agent-list">
      <div
        v-for="agent in agents"
        :key="agent.key"
        class="agent-item"
        :class="agent.status"
      >
        <div class="agent-icon">
          <el-icon v-if="agent.status === 'completed'" :size="20" color="#059669"><CircleCheck /></el-icon>
          <el-icon v-else-if="agent.status === 'running'" :size="20" color="#4F46E5" class="spin"><Loading /></el-icon>
          <el-icon v-else-if="agent.status === 'failed'" :size="20" color="#DC2626"><CircleClose /></el-icon>
          <el-icon v-else :size="20" color="#9CA3AF"><Clock /></el-icon>
        </div>
        <div class="agent-info">
          <span class="agent-name">{{ agent.name }}</span>
          <span class="agent-desc">{{ agent.description }}</span>
        </div>
        <div class="agent-status-tag">
          <el-tag :type="statusTagType(agent.status)" size="small" effect="plain">
            {{ statusText(agent.status) }}
          </el-tag>
        </div>
      </div>
    </div>

    <!-- 整体进度 -->
    <div class="progress-bar">
      <el-progress
        :percentage="progress"
        :stroke-width="8"
        :status="progress === 100 ? 'success' : undefined"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { CircleCheck, CircleClose, Clock, Loading } from '@element-plus/icons-vue'

interface AgentStatus {
  key: string
  name: string
  description: string
  status: 'waiting' | 'running' | 'completed' | 'failed' | 'skipped'
}

const props = defineProps<{
  agents: AgentStatus[]
  isRunning: boolean
}>()

const progress = computed(() => {
  if (!props.agents.length) return 0
  const done = props.agents.filter(a => a.status === 'completed' || a.status === 'skipped').length
  return Math.round((done / props.agents.length) * 100)
})

function statusTagType(status: string) {
  const map: Record<string, string> = {
    completed: 'success',
    running: 'primary',
    failed: 'danger',
    skipped: 'info',
    waiting: 'info',
  }
  return (map[status] || 'info') as any
}

function statusText(status: string) {
  const map: Record<string, string> = {
    completed: '完成',
    running: '生成中',
    failed: '失败',
    skipped: '跳过',
    waiting: '等待',
  }
  return map[status] || status
}
</script>

<style scoped>
.agent-collab {
  background: var(--color-bg-card);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-card);
  padding: 20px;
}

.collab-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;
}

.collab-title {
  font-size: var(--text-lg);
  font-weight: 700;
  margin: 0;
  color: var(--color-text-primary);
}

.agent-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.agent-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 16px;
  border-radius: var(--radius-md);
  background: var(--color-border-light);
  border: 1px solid transparent;
  transition: all var(--transition-normal);
}

.agent-item.running {
  background: var(--color-primary-faint);
  border-color: var(--color-primary-pale);
}

.agent-item.completed {
  background: var(--color-success-soft);
  border-color: var(--color-success);
}

.agent-item.failed {
  background: var(--color-error-soft);
  border-color: var(--color-error);
}

.agent-icon {
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: center;
}

.spin {
  animation: spin 1s linear infinite;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

.agent-info {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.agent-name {
  font-weight: 600;
  font-size: var(--text-sm);
  color: var(--color-text-primary);
}

.agent-desc {
  font-size: var(--text-xs);
  color: var(--color-text-muted);
}

.progress-bar {
  margin-top: 16px;
}
.progress-bar :deep(.el-progress-bar__inner) {
  background: linear-gradient(90deg, var(--color-student), #D17A52);
}
</style>
