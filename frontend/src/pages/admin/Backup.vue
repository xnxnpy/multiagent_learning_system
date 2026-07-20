<template>
  <div class="page-container">
    <!-- 第一行：系统统计 + 创建备份 -->
    <el-row :gutter="24">
      <el-col :xs="24" :lg="10">
        <el-card class="page-card" shadow="never">
          <template #header>
            <div class="card-header">
              <div class="card-header__left">
                <el-icon class="card-header__icon"><DataAnalysis /></el-icon>
                <h2 class="card-header__title">系统数据统计</h2>
              </div>
              <el-button size="small" @click="fetchSystemStats" :loading="statsLoading">
                <el-icon><RefreshRight /></el-icon> 刷新
              </el-button>
            </div>
          </template>
          <el-row :gutter="16">
            <el-col :span="12">
              <div class="stat-item">
                <div class="stat-item__value">{{ sysStats.users_count }}</div>
                <div class="stat-item__label">用户数</div>
              </div>
            </el-col>
            <el-col :span="12">
              <div class="stat-item">
                <div class="stat-item__value">{{ sysStats.courses_count }}</div>
                <div class="stat-item__label">课程数</div>
              </div>
            </el-col>
          </el-row>
          <el-divider />
          <el-row :gutter="16">
            <el-col :span="12">
              <div class="stat-item">
                <div class="stat-item__value">{{ sysStats.learning_records_count }}</div>
                <div class="stat-item__label">学习记录</div>
              </div>
            </el-col>
            <el-col :span="12">
              <div class="stat-item">
                <div class="stat-item__value">{{ sysStats.resources_count }}</div>
                <div class="stat-item__label">资源数</div>
              </div>
            </el-col>
          </el-row>
          <el-divider />
          <el-row :gutter="16">
            <el-col :span="8">
              <div class="disk-stat">
                <span class="disk-stat__value">{{ formatBytes(sysStats.disk_usage_bytes) }}</span>
                <span class="disk-stat__label">磁盘占用</span>
              </div>
            </el-col>
            <el-col :span="8">
              <div class="disk-stat">
                <span class="disk-stat__value">{{ formatBytes(sysStats.chroma_size_bytes) }}</span>
                <span class="disk-stat__label">向量库</span>
              </div>
            </el-col>
            <el-col :span="8">
              <div class="disk-stat">
                <span class="disk-stat__value">{{ formatBytes(sysStats.logs_size_bytes) }}</span>
                <span class="disk-stat__label">日志文件</span>
              </div>
            </el-col>
          </el-row>
        </el-card>
      </el-col>

      <el-col :xs="24" :lg="14">
        <el-card class="page-card" shadow="never">
          <template #header>
            <div class="card-header">
              <div class="card-header__left">
                <el-icon class="card-header__icon"><FolderAdd /></el-icon>
                <h2 class="card-header__title">创建备份</h2>
              </div>
            </div>
          </template>
          <div class="backup-create">
            <p class="backup-create__desc">创建当前系统的完整备份，包含数据库数据和向量库数据。</p>
            <el-button type="primary" size="large" :loading="backupCreating" @click="handleCreateBackup" style="width: 100%">
              <el-icon><FolderAdd /></el-icon> 立即备份
            </el-button>
            <div v-if="lastBackupResult" class="backup-result" :class="lastBackupResult.success ? 'backup-result--success' : 'backup-result--error'">
              <el-icon v-if="lastBackupResult.success"><CircleCheck /></el-icon>
              <el-icon v-else><CircleClose /></el-icon>
              <span>{{ lastBackupResult.message }}</span>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 第二行：缓存清理 + 日志清理 + 备份列表 -->
    <el-row :gutter="24" style="margin-top: 24px;">
      <el-col :xs="24" :lg="8">
        <el-card class="page-card" shadow="never">
          <template #header>
            <div class="card-header">
              <div class="card-header__left">
                <el-icon class="card-header__icon"><DeleteFilled /></el-icon>
                <h2 class="card-header__title">缓存清理</h2>
              </div>
            </div>
          </template>
          <el-form :label-width="100" label-position="left">
            <el-form-item label="清理目标">
              <el-select v-model="cacheTarget" style="width: 100%">
                <el-option value="redis" label="Redis 缓存" />
                <el-option value="chroma" label="ChromaDB 向量库" />
                <el-option value="all" label="全部缓存" />
              </el-select>
            </el-form-item>
          </el-form>
          <el-button type="warning" :loading="cacheLoading" @click="handleClearCache" style="width: 100%">
            <el-icon><DeleteFilled /></el-icon> 清理缓存
          </el-button>
        </el-card>
      </el-col>

      <el-col :xs="24" :lg="8">
        <el-card class="page-card" shadow="never">
          <template #header>
            <div class="card-header">
              <div class="card-header__left">
                <el-icon class="card-header__icon"><Document /></el-icon>
                <h2 class="card-header__title">日志清理</h2>
              </div>
            </div>
          </template>
          <el-form :label-width="100" label-position="left">
            <el-form-item label="保留天数">
              <el-input-number v-model="logDays" :min="1" :max="365" style="width: 100%" />
            </el-form-item>
          </el-form>
          <el-button type="danger" :loading="logCleanLoading" @click="handleCleanLogs" style="width: 100%">
            <el-icon><DocumentDelete /></el-icon> 清理过期日志
          </el-button>
        </el-card>
      </el-col>

      <el-col :xs="24" :lg="8">
        <el-card class="page-card" shadow="never">
          <template #header>
            <div class="card-header">
              <div class="card-header__left">
                <el-icon class="card-header__icon"><Folder /></el-icon>
                <h2 class="card-header__title">备份列表</h2>
              </div>
              <el-button size="small" @click="fetchBackups" :loading="backupsLoading">
                <el-icon><RefreshRight /></el-icon> 刷新
              </el-button>
            </div>
          </template>
          <el-table :data="backups" v-loading="backupsLoading" stripe class="data-table" empty-text="暂无备份记录">
            <el-table-column prop="name" label="备份名称" min-width="180">
              <template #default="{ row }">
                <span class="backup-name">{{ row.name }}</span>
              </template>
            </el-table-column>
            <el-table-column label="大小" width="100" align="center">
              <template #default="{ row }">
                <span class="backup-size">{{ formatBytes(row.size) }}</span>
              </template>
            </el-table-column>
            <el-table-column label="创建时间" width="160">
              <template #default="{ row }">
                <span class="backup-time">{{ formatDate(row.created_at) }}</span>
              </template>
            </el-table-column>
            <el-table-column label="操作" width="140" align="center">
              <template #default="{ row }">
                <el-button type="primary" size="small" link :loading="restoringName === row.name" @click="handleRestore(row)">恢复</el-button>
                <el-button type="danger" size="small" link :loading="deletingName === row.name" @click="handleDeleteBackup(row)">删除</el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { adminAPI } from '@/api'
import {
  DataAnalysis, RefreshRight, DeleteFilled, Document, DocumentDelete,
  FolderAdd, Folder, CircleCheck, CircleClose,
} from '@element-plus/icons-vue'

interface Backup {
  name: string
  path: string
  size: number
  created_at: string
}

const statsLoading = ref(false)
const backupsLoading = ref(false)
const backupCreating = ref(false)
const cacheLoading = ref(false)
const logCleanLoading = ref(false)
const restoringName = ref('')
const deletingName = ref('')

const cacheTarget = ref('all')
const logDays = ref(7)

const sysStats = reactive({
  users_count: 0,
  courses_count: 0,
  learning_records_count: 0,
  resources_count: 0,
  disk_usage_bytes: 0,
  chroma_size_bytes: 0,
  logs_size_bytes: 0,
})

const backups = ref<Backup[]>([])

const lastBackupResult = ref<{ success: boolean; message: string } | null>(null)

const formatBytes = (bytes: number): string => {
  if (!bytes || bytes === 0) return '0 B'
  const units = ['B', 'KB', 'MB', 'GB', 'TB']
  const k = 1024
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + units[i]
}

const formatDate = (dateStr: string): string => {
  if (!dateStr) return '-'
  return new Date(dateStr).toLocaleString('zh-CN')
}

const fetchSystemStats = async () => {
  statsLoading.value = true
  try {
    const res: any = await adminAPI.getSystemStats()
    Object.assign(sysStats, res)
  } catch {
    ElMessage.error('获取系统统计失败')
  } finally {
    statsLoading.value = false
  }
}

const fetchBackups = async () => {
  backupsLoading.value = true
  try {
    const res: any = await adminAPI.getBackups()
    backups.value = Array.isArray(res) ? res : []
  } catch {
    ElMessage.error('获取备份列表失败')
  } finally {
    backupsLoading.value = false
  }
}

const handleCreateBackup = async () => {
  backupCreating.value = true
  lastBackupResult.value = null
  try {
    const res: any = await adminAPI.createBackup()
    lastBackupResult.value = { success: res.success, message: res.message }
    if (res.success) {
      ElMessage.success(res.message)
      fetchBackups()
    } else {
      ElMessage.error(res.message)
    }
  } catch (e: any) {
    lastBackupResult.value = { success: false, message: '备份请求失败' }
    ElMessage.error('备份请求失败')
  } finally {
    backupCreating.value = false
  }
}

const handleRestore = async (row: Backup) => {
  try {
    await ElMessageBox.confirm(
      `确定要从备份 "${row.name}" 恢复数据吗？当前数据将被覆盖，此操作不可撤销。`,
      '恢复确认',
      { type: 'warning', confirmButtonText: '确认恢复', cancelButtonText: '取消' }
    )
  } catch {
    return // user cancelled
  }

  restoringName.value = row.name
  try {
    const res: any = await adminAPI.restoreBackup(row.name)
    if (res.success) {
      ElMessage.success(res.message || '恢复成功')
    } else {
      ElMessage.error(res.message || '恢复失败')
    }
  } catch (e: any) {
    ElMessage.error('恢复请求失败')
  } finally {
    restoringName.value = ''
  }
}

const handleDeleteBackup = async (row: Backup) => {
  try {
    await ElMessageBox.confirm(
      `确定要删除备份 "${row.name}" 吗？此操作不可撤销。`,
      '删除确认',
      { type: 'warning', confirmButtonText: '确认删除', cancelButtonText: '取消' }
    )
    deletingName.value = row.name
    const res: any = await adminAPI.deleteBackup(row.name)
    if (res.success) {
      ElMessage.success(res.message || '删除成功')
      fetchBackups()
    } else {
      ElMessage.error(res.message || '删除失败')
    }
  } catch (e: any) {
    if (e !== 'cancel') ElMessage.error('删除请求失败')
  } finally {
    deletingName.value = ''
  }
}

const handleClearCache = async () => {
  cacheLoading.value = true
  try {
    const res: any = await adminAPI.clearCache(cacheTarget.value)
    if (res.success) {
      const details = (res.results || []).join('; ')
      ElMessage.success(details || '缓存清理完成')
    } else {
      ElMessage.error('缓存清理失败')
    }
  } catch {
    ElMessage.error('缓存清理请求失败')
  } finally {
    cacheLoading.value = false
  }
}

const handleCleanLogs = async () => {
  logCleanLoading.value = true
  try {
    const res: any = await adminAPI.cleanLogs(logDays.value)
    if (res.success) {
      ElMessage.success(`已清理 ${res.deleted_count} 个文件，释放 ${formatBytes(res.freed_bytes)}`)
    }
  } catch {
    ElMessage.error('日志清理请求失败')
  } finally {
    logCleanLoading.value = false
  }
}

onMounted(() => {
  fetchSystemStats()
  fetchBackups()
})
</script>

<style scoped>
.page-container {
  padding: 24px;
  background: var(--color-bg-page, #F4F5F7);
  min-height: 100%;
}

.page-card {
  border-radius: 12px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.06);
  margin-bottom: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
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
  font-size: 16px;
  font-weight: 600;
  margin: 0;
  color: var(--color-text-primary);
}

/* 统计项 */
.stat-item {
  text-align: center;
  padding: 12px 0;
}

.stat-item__value {
  font-size: 22px;
  font-weight: 700;
  color: var(--color-text-primary);
}

.stat-item__label {
  font-size: 12px;
  color: var(--color-text-muted);
  margin-top: 4px;
}

/* 磁盘统计 */
.disk-stat {
  text-align: center;
  padding: 8px 0;
}

.disk-stat__value {
  display: block;
  font-size: 16px;
  font-weight: 600;
  color: var(--color-text-secondary);
}

.disk-stat__label {
  display: block;
  font-size: 11px;
  color: var(--color-text-muted);
  margin-top: 2px;
}

/* 备份创建 */
.backup-create {
  text-align: center;
  padding: 8px 0;
}

.backup-create__desc {
  color: var(--color-text-secondary);
  font-size: 13px;
  margin: 0 0 16px;
  line-height: 1.6;
}

.backup-result {
  margin-top: 12px;
  padding: 8px 12px;
  border-radius: 8px;
  font-size: 13px;
  display: flex;
  align-items: center;
  gap: 6px;
}

.backup-result--success {
  background: #f0fdf4;
  color: #16a34a;
  border: 1px solid #bbf7d0;
}

.backup-result--error {
  background: #fef2f2;
  color: #dc2626;
  border: 1px solid #fecaca;
}

/* 备份列表 */
.backup-name {
  font-weight: 500;
  color: var(--color-text-primary);
  font-size: 13px;
}

.backup-size {
  color: var(--color-text-secondary);
  font-size: 13px;
}

.backup-time {
  color: var(--color-text-muted);
  font-size: 13px;
}

/* 通用 */
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
