<template>
  <teleport to="body">
    <div class="wf-progress-float">
      <div class="wf-card">
        <div class="wf-header">
          <el-icon class="is-loading" :size="16" color="#6366f1"><Loading /></el-icon>
          <span class="wf-title">{{ step || '正在工作...' }}</span>
        </div>
        <el-progress :percentage="percent" :stroke-width="6" :show-text="false" style="margin: 8px 0 0;" />
      </div>
    </div>
  </teleport>
</template>

<script setup lang="ts">
import { Loading } from '@element-plus/icons-vue'
defineProps<{ percent: number; step?: string }>()
</script>

<style>
.wf-progress-float {
  position: fixed;
  bottom: 24px;
  right: 24px;
  z-index: 2000;
}

.wf-card {
  width: 280px;
  background: var(--color-bg-card);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-lg);
  border: 1px solid var(--color-border);
  padding: 14px 16px;
}

.wf-header {
  display: flex;
  align-items: center;
  gap: 8px;
}

.wf-title {
  font-size: var(--text-sm);
  font-weight: 600;
  color: var(--color-text-primary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
</style>
