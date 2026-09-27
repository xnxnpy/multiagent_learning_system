<template>
  <div class="kb-admin">
    <div class="page-header">
      <h2>知识库运维</h2>
      <p class="page-sub">分区统计 · 上传材料治理 · 按学生清理索引 · 历史无主块</p>
    </div>

    <!-- 分区统计 -->
    <el-row :gutter="16" class="stats">
      <el-col :xs="12" :md="4" v-for="s in statCards" :key="s.key">
        <el-card shadow="never" class="stat-card">
          <div class="v" :style="{ color: s.color }">{{ stats[s.key] ?? '-' }}</div>
          <div class="l">{{ s.label }}</div>
        </el-card>
      </el-col>
    </el-row>

    <el-row :gutter="16">
      <!-- 文档列表 -->
      <el-col :xs="24" :lg="14">
        <el-card shadow="never" class="card">
          <template #header>
            <div class="head">
              <span>上传材料列表</span>
              <el-button size="small" @click="loadDocs">刷新</el-button>
            </div>
          </template>
          <el-table :data="docs" v-loading="loading" size="small" max-height="420">
            <el-table-column prop="filename" label="文件名" show-overflow-tooltip />
            <el-table-column prop="uploader" label="上传者" width="110" show-overflow-tooltip />
            <el-table-column prop="file_type" label="类型" width="70">
              <template #default="{ row }"><el-tag size="small" type="info">{{ row.file_type }}</el-tag></template>
            </el-table-column>
            <el-table-column prop="chunk_count" label="分块" width="60" />
            <el-table-column label="状态" width="80">
              <template #default="{ row }">
                <el-tag v-if="row.status === 'completed'" type="success" size="small">完成</el-tag>
                <el-tag v-else-if="row.status === 'failed'" type="danger" size="small">失败</el-tag>
                <el-tag v-else type="warning" size="small" effect="plain">处理中</el-tag>
              </template>
            </el-table-column>
            <el-table-column label="操作" width="70">
              <template #default="{ row }">
                <el-button link type="danger" size="small" @click="deleteDoc(row)">删除</el-button>
              </template>
            </el-table-column>
          </el-table>
          <el-empty v-if="!loading && !docs.length" description="暂无上传材料" :image-size="60" />
          <el-pagination
            v-if="docTotal > pageSize"
            layout="prev, pager, next, total"
            :total="docTotal"
            :page-size="pageSize"
            v-model:current-page="page"
            @current-change="loadDocs"
            style="margin-top: 12px; justify-content: center"
          />
        </el-card>
      </el-col>

      <!-- 危险操作 -->
      <el-col :xs="24" :lg="10">
        <el-card shadow="never" class="card">
          <template #header>按学生清理索引</template>
          <p class="hint">清空该用户的全部向量块（资源 + 笔记 + 上传）及其上传文档记录。</p>
          <div class="row">
            <el-input v-model="clearUserId" placeholder="用户 ID（数字）" style="flex: 1" />
            <el-button type="danger" plain :loading="clearUserLoading" @click="clearUser">清理该用户</el-button>
          </div>
        </el-card>

        <el-card shadow="never" class="card">
          <template #header>批量清理</template>
          <div class="stack">
            <el-popconfirm
              title="清空全部上传材料？不影响资源与笔记索引。"
              confirm-button-text="确定"
              cancel-button-text="取消"
              @confirm="clearUploads"
            >
              <template #reference>
                <el-button type="warning" plain :loading="clearUploadsLoading" style="width: 100%">
                  清空全部上传材料
                </el-button>
              </template>
            </el-popconfirm>

            <el-popconfirm
              title="清理历史无主块（旧共享教材）？个人资源与笔记不受影响。"
              confirm-button-text="确定"
              cancel-button-text="取消"
              @confirm="clearLegacy"
            >
              <template #reference>
                <el-button type="warning" plain :loading="clearLegacyLoading" style="width: 100%">
                  清理历史无主块
                </el-button>
              </template>
            </el-popconfirm>

            <p class="hint danger">整库清空请到「数据备份」页使用 Chroma 清理（会删掉所有个人索引，慎用）。</p>
          </div>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, computed } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { adminAPI } from '@/api'

const loading = ref(false)
const docs = ref<any[]>([])
const docTotal = ref(0)
const page = ref(1)
const pageSize = 20

const stats = reactive<Record<string, number>>({
  total: 0,
  personal_resources: 0,
  personal_notes: 0,
  uploads: 0,
  legacy_shared: 0,
})

const statCards = [
  { key: 'total', label: '向量块总数', color: '#2B2D42' },
  { key: 'personal_resources', label: '个人资源', color: '#B0512C' },
  { key: 'personal_notes', label: '个人笔记', color: '#4E598C' },
  { key: 'uploads', label: '上传材料', color: '#3D6B4F' },
  { key: 'legacy_shared', label: '历史无主', color: '#70293C' },
]

const clearUserId = ref('')
const clearUserLoading = ref(false)
const clearUploadsLoading = ref(false)
const clearLegacyLoading = ref(false)

async function loadStats() {
  try {
    Object.assign(stats, await adminAPI.getKnowledgeStats())
  } catch {
    /* ignore */
  }
}

async function loadDocs() {
  loading.value = true
  try {
    const res: any = await adminAPI.getKnowledgeUploads({ page: page.value, page_size: pageSize })
    docs.value = res?.items || []
    docTotal.value = res?.total || 0
  } catch {
    docs.value = []
  } finally {
    loading.value = false
  }
}

async function deleteDoc(row: any) {
  try {
    await ElMessageBox.confirm(`删除「${row.filename}」？`, '删除确认', { type: 'warning' })
  } catch { return }
  try {
    await adminAPI.deleteKnowledgeUpload(row.id)
    ElMessage.success('已删除')
    await Promise.all([loadDocs(), loadStats()])
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || '删除失败')
  }
}

async function clearUser() {
  const id = Number(clearUserId.value)
  if (!Number.isInteger(id) || id <= 0) {
    ElMessage.warning('请输入有效的用户 ID')
    return
  }
  try {
    await ElMessageBox.confirm(`清空用户 ${id} 的全部个人索引？`, '确认清理', { type: 'warning' })
  } catch { return }
  clearUserLoading.value = true
  try {
    const res: any = await adminAPI.clearUserKnowledgeIndex(id)
    ElMessage.success(res?.message || '已清理')
    clearUserId.value = ''
    await Promise.all([loadDocs(), loadStats()])
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || '清理失败')
  } finally {
    clearUserLoading.value = false
  }
}

async function clearUploads() {
  clearUploadsLoading.value = true
  try {
    const res: any = await adminAPI.clearKnowledgeUploads()
    ElMessage.success(res?.message || '已清空')
    await Promise.all([loadDocs(), loadStats()])
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || '清空失败')
  } finally {
    clearUploadsLoading.value = false
  }
}

async function clearLegacy() {
  clearLegacyLoading.value = true
  try {
    const res: any = await adminAPI.clearLegacyShared()
    ElMessage.success(res?.message || '已清理')
    await loadStats()
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || '清理失败')
  } finally {
    clearLegacyLoading.value = false
  }
}

onMounted(() => {
  loadStats()
  loadDocs()
})
</script>

<style scoped>
.kb-admin { max-width: 1200px; }
.page-header h2 { margin: 0 0 4px; }
.page-sub { color: var(--el-text-color-secondary); margin: 0 0 16px; font-size: 13px; }
.stats { margin-bottom: 16px; }
.stat-card { text-align: center; }
.stat-card .v { font-size: 24px; font-weight: 700; }
.stat-card .l { font-size: 12px; color: var(--el-text-color-secondary); margin-top: 4px; }
.card { margin-bottom: 16px; }
.head { display: flex; justify-content: space-between; align-items: center; }
.hint { font-size: 12px; color: var(--el-text-color-secondary); line-height: 1.5; margin: 0 0 10px; }
.hint.danger { color: #b91c1c; margin-top: 10px; margin-bottom: 0; }
.row { display: flex; gap: 8px; }
.stack { display: flex; flex-direction: column; gap: 10px; }
</style>
