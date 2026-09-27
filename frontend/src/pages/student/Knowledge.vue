<template>
  <div class="kb-page">
    <div class="page-header">
      <h2>我的知识库</h2>
      <p class="page-sub">上传的材料仅本人可检索——辅导与资源生成会优先引用你的文档</p>
    </div>

    <el-row :gutter="16">
      <el-col :xs="24" :lg="10">
        <el-card shadow="never" class="card">
          <template #header>上传材料</template>
          <el-upload
            ref="uploadRef"
            :multiple="true"
            :before-upload="beforeUpload"
            :file-list="fileList"
            :auto-upload="false"
            drag
            accept=".txt,.md,.markdown,.pdf,.docx,.doc"
          >
            <el-icon class="upload-icon"><UploadFilled /></el-icon>
            <div>将文件拖到此处，或<em>点击上传</em></div>
            <template #tip>
              <div class="tip">支持 .txt / .md / .pdf / .docx，单个 ≤ 10MB</div>
            </template>
          </el-upload>

          <div v-if="fileList.length" class="pending">
            <div v-for="(f, i) in fileList" :key="i" class="pending-row">
              <span class="name">{{ f.name }}</span>
              <span class="size">{{ formatSize(f.size) }}</span>
              <el-icon class="rm" @click="removeFile(i)"><Close /></el-icon>
            </div>
          </div>

          <el-button
            type="primary"
            class="upload-btn"
            :loading="uploading"
            :disabled="!fileList.length"
            @click="handleUpload"
          >
            {{ uploading ? `上传中 (${uploadProgress}/${uploadTotal})` : `开始上传（${fileList.length}）` }}
          </el-button>
        </el-card>

        <el-card shadow="never" class="card">
          <template #header>统计</template>
          <el-row :gutter="12">
            <el-col :span="8">
              <div class="stat"><div class="v">{{ stats.total_documents }}</div><div class="l">文档</div></div>
            </el-col>
            <el-col :span="8">
              <div class="stat"><div class="v">{{ stats.total_chunks }}</div><div class="l">知识碎片</div></div>
            </el-col>
            <el-col :span="8">
              <div class="stat warn"><div class="v">{{ stats.failed }}</div><div class="l">失败</div></div>
            </el-col>
          </el-row>
        </el-card>
      </el-col>

      <el-col :xs="24" :lg="14">
        <el-card shadow="never" class="card">
          <template #header>
            <div class="card-head">
              <span>已上传文档</span>
              <el-button size="small" @click="fetchDocuments">刷新</el-button>
            </div>
          </template>
          <el-table :data="documents" v-loading="docsLoading" size="small" max-height="480">
            <el-table-column prop="filename" label="文件名" show-overflow-tooltip />
            <el-table-column label="类型" width="70">
              <template #default="{ row }">
                <el-tag size="small" type="info">{{ row.file_type }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column label="大小" width="80">
              <template #default="{ row }">{{ formatSize(row.file_size) }}</template>
            </el-table-column>
            <el-table-column prop="chunk_count" label="分块" width="60" />
            <el-table-column label="状态" width="90">
              <template #default="{ row }">
                <el-tag v-if="row.status === 'completed'" type="success" size="small">完成</el-tag>
                <el-tag v-else-if="row.status === 'processing'" type="warning" size="small" effect="plain">处理中</el-tag>
                <el-tag v-else type="danger" size="small">失败</el-tag>
              </template>
            </el-table-column>
            <el-table-column label="操作" width="70">
              <template #default="{ row }">
                <el-button size="small" link type="danger" @click="handleDelete(row)">删除</el-button>
              </template>
            </el-table-column>
          </el-table>
          <el-empty v-if="!docsLoading && !documents.length" description="还没有上传过材料" :image-size="60" />
          <el-pagination
            v-if="docStats.total > 20"
            layout="prev, pager, next"
            :total="docStats.total"
            :page-size="20"
            v-model:current-page="docPage"
            @current-change="fetchDocuments"
            style="margin-top: 12px; justify-content: center"
          />
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { studentAPI } from '@/api'
import { UploadFilled, Close } from '@element-plus/icons-vue'

interface Stats { total_documents: number; total_chunks: number; failed: number }
interface DocItem {
  id: number
  filename: string
  file_size: number
  file_type: string
  status: string
  chunk_count: number
  error_message?: string
  created_at: string
  completed_at?: string
}

const uploading = ref(false)
const uploadRef = ref()
const fileList = ref<any[]>([])
const uploadProgress = ref(0)
const uploadTotal = ref(0)

const stats = reactive<Stats>({ total_documents: 0, total_chunks: 0, failed: 0 })
const docStats = reactive({ total: 0, failed: 0 })
const documents = ref<DocItem[]>([])
const docsLoading = ref(false)
const docPage = ref(1)

function formatSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`
}

const beforeUpload = (file: any): boolean => {
  const ok = /\.(pdf|docx?|txt|md|markdown)$/i.test(file.name)
  if (!ok) {
    ElMessage.error('不支持的文件格式')
    return false
  }
  if (file.size > 10 * 1024 * 1024) {
    ElMessage.error('文件不能超过 10MB')
    return false
  }
  fileList.value = [...fileList.value, file]
  return false
}

function removeFile(idx: number) {
  fileList.value.splice(idx, 1)
}

const handleUpload = async () => {
  if (!fileList.value.length) {
    ElMessage.warning('请先选择文件')
    return
  }
  uploading.value = true
  uploadTotal.value = fileList.value.length
  uploadProgress.value = 0
  const formData = new FormData()
  fileList.value.filter(f => f.raw).forEach(f => formData.append('files', f.raw!))
  try {
    const res: any = await studentAPI.uploadKnowledge(formData)
    ElMessage.success(res?.message || '上传完成')
    fileList.value = []
    uploadRef.value?.clearFiles()
    setTimeout(async () => {
      await fetchStats()
      await fetchDocuments()
    }, 800)
  } catch (e: any) {
    ElMessage.error('上传失败：' + (e?.response?.data?.detail || e?.message || ''))
  } finally {
    uploading.value = false
    uploadProgress.value = 0
    uploadTotal.value = 0
  }
}

const fetchStats = async () => {
  try {
    Object.assign(stats, await studentAPI.getKnowledgeStats())
    docStats.total = stats.total_documents
    docStats.failed = stats.failed
  } catch {
    /* ignore */
  }
}

const fetchDocuments = async () => {
  docsLoading.value = true
  try {
    const res: any = await studentAPI.getKnowledgeDocuments({
      page: docPage.value,
      page_size: 20,
    })
    documents.value = res?.items || []
    docStats.total = res?.total || 0
  } catch {
    documents.value = []
  } finally {
    docsLoading.value = false
  }
}

const handleDelete = async (row: DocItem) => {
  try {
    await ElMessageBox.confirm(`删除「${row.filename}」？对应向量索引会一并移除。`, '删除确认', {
      type: 'warning',
    })
  } catch {
    return
  }
  try {
    await studentAPI.deleteKnowledgeDocument(row.id)
    ElMessage.success('已删除')
    await Promise.all([fetchDocuments(), fetchStats()])
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || '删除失败')
  }
}

onMounted(() => {
  fetchStats()
  fetchDocuments()
})
</script>

<style scoped>
.kb-page { max-width: 1100px; }
.page-header h2 { margin: 0 0 4px; }
.page-sub { color: var(--el-text-color-secondary); margin: 0 0 16px; font-size: 13px; }
.card { margin-bottom: 16px; }
.upload-icon { font-size: 40px; color: var(--el-color-primary); margin: 8px 0; }
.tip { color: var(--el-text-color-secondary); font-size: 12px; margin-top: 4px; }
.pending { margin-top: 10px; }
.pending-row {
  display: flex; align-items: center; gap: 8px;
  font-size: 13px; padding: 4px 0;
}
.pending-row .name { flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.pending-row .size { color: var(--el-text-color-secondary); }
.pending-row .rm { cursor: pointer; color: var(--el-text-color-secondary); }
.upload-btn { margin-top: 12px; width: 100%; }
.stat { text-align: center; padding: 8px 0; }
.stat .v { font-size: 24px; font-weight: 600; }
.stat.warn .v { color: var(--el-color-danger); }
.stat .l { font-size: 12px; color: var(--el-text-color-secondary); }
.card-head { display: flex; justify-content: space-between; align-items: center; }
</style>
