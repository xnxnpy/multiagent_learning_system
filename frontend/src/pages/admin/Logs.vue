<template>
  <div class="page-container">
    <el-card class="page-card">
      <template #header>
        <div class="card-header">
          <div class="card-header__left">
            <el-icon class="card-header__icon"><Document /></el-icon>
            <h2 class="card-header__title">系统日志</h2>
          </div>
          <div class="card-header__right">
            <el-select v-model="filterLevel" placeholder="级别筛选" style="width: 130px" @change="handleFilterChange">
              <el-option value="INFO" label="INFO" />
              <el-option value="WARNING" label="WARNING" />
              <el-option value="ERROR" label="ERROR" />
            </el-select>
            <el-button @click="handleRefresh">
              <el-icon><RefreshRight /></el-icon> 刷新
            </el-button>
            <el-button type="success" @click="handleExport">
              <el-icon><Download /></el-icon> 导出日志
            </el-button>
          </div>
        </div>
      </template>

      <el-table :data="logs" v-loading="loading" stripe class="data-table">
        <el-table-column prop="timestamp" label="时间" width="170">
          <template #default="{ row }">
            <span class="time-text">{{ formatDate(row.timestamp) }}</span>
          </template>
        </el-table-column>
        <el-table-column label="级别" width="100" align="center">
          <template #default="{ row }">
            <el-tag :type="getLevelTagType(row.level)" effect="light" round size="small">
              {{ row.level }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="module" label="模块" width="140">
          <template #default="{ row }">
            <span class="module-text">{{ row.module || '-' }}</span>
          </template>
        </el-table-column>
        <el-table-column label="日志内容" min-width="300">
          <template #default="{ row }">
            <code class="log-message">{{ row.message }}</code>
          </template>
        </el-table-column>
      </el-table>

      <div class="pagination-wrap">
        <el-pagination
          v-model:current-page="pagination.current"
          v-model:page-size="pagination.pageSize"
          :total="pagination.total"
          :page-sizes="[20, 50, 100, 200]"
          layout="total, sizes, prev, pager, next, jumper"
          @size-change="handleSizeChange"
          @current-change="handleCurrentChange"
        />
      </div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { adminAPI } from '@/api'
import { Document, RefreshRight, Download } from '@element-plus/icons-vue'

interface Log {
  id: number
  timestamp: string
  level: string
  module?: string
  message: string
}

const loading = ref(false)
const filterLevel = ref('INFO')

const logs = ref<Log[]>([])
const pagination = reactive({
  current: 1,
  pageSize: 50,
  total: 0
})

const getLevelTagType = (level: string): '' | 'info' | 'primary' | 'success' | 'warning' | 'danger' | 'text' => {
  const types: Record<string, '' | 'info' | 'primary' | 'success' | 'warning' | 'danger' | 'text'> = {
    INFO: 'info',
    WARNING: 'warning',
    ERROR: 'danger',
    DEBUG: ''
  }
  return types[level] || ''
}

const formatDate = (dateStr: string): string => {
  if (!dateStr) return '-'
  return new Date(dateStr).toLocaleString('zh-CN')
}

const fetchLogs = async () => {
  loading.value = true
  try {
    const response: any = await adminAPI.getLogs({
      level: filterLevel.value,
      page: pagination.current,
      page_size: pagination.pageSize,
    })
    logs.value = response.items || []
    pagination.total = response.total || 0
  } catch (error) {
    ElMessage.error('获取日志失败')
  } finally {
    loading.value = false
  }
}

const handleFilterChange = () => {
  pagination.current = 1
  fetchLogs()
}

const handleSizeChange = (size: number) => {
  pagination.pageSize = size
  fetchLogs()
}

const handleCurrentChange = (current: number) => {
  pagination.current = current
  fetchLogs()
}

const handleRefresh = () => {
  fetchLogs()
  ElMessage.success('已刷新')
}

const handleExport = () => {
  try {
    let csvContent = '﻿时间,级别,模块,日志内容\n'
    logs.value.forEach(log => {
      csvContent += `"${log.timestamp}","${log.level}","${log.module || ''}","${log.message.replace(/"/g, '""')}"\n`
    })

    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' })
    const url = window.URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = `system_logs_${new Date().toISOString().split('T')[0]}.csv`
    link.click()
    window.URL.revokeObjectURL(url)
    ElMessage.success('日志导出成功')
  } catch (error) {
    ElMessage.error('导出失败')
  }
}

onMounted(() => {
  fetchLogs()
})
</script>

<style scoped>
.page-container {
  padding: 24px;
  background: var(--color-bg-page);
  min-height: 100%;
}

.page-card {
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-card);
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 12px;
}

.card-header__left {
  display: flex;
  align-items: center;
  gap: 8px;
}

.card-header__icon {
  font-size: 20px;
  color: var(--color-primary);
}

.card-header__title {
  font-size: 18px;
  font-weight: 600;
  margin: 0;
  color: var(--color-text-primary);
}

.card-header__right {
  display: flex;
  align-items: center;
  gap: 12px;
}

.time-text {
  color: var(--color-text-muted);
  font-size: 13px;
}

.module-text {
  color: var(--color-text-secondary);
  font-size: 13px;
  font-weight: 500;
}

.log-message {
  font-family: 'SFMono-Regular', 'Consolas', 'Liberation Mono', 'Menlo', monospace;
  font-size: 12px;
  color: var(--color-text-secondary);
  background: var(--color-bg-page);
  padding: 4px 8px;
  border-radius: 4px;
  line-height: 1.6;
  word-break: break-all;
}

.pagination-wrap {
  margin-top: 20px;
  display: flex;
  justify-content: flex-end;
}

:deep(.el-table) {
  border-radius: 8px;
  overflow: hidden;
}

:deep(.el-table th.el-table__cell) {
  background: var(--color-border-light);
  color: var(--color-text-secondary);
  font-weight: 600;
  font-size: 13px;
}
</style>
