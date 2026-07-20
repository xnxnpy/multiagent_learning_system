<template>
  <div class="page-container">
    <el-row :gutter="24">
      <!-- 左列：上传 + 统计 -->
      <el-col :xs="24" :lg="12">
        <el-card class="page-card" shadow="never">
          <template #header>
            <h2 class="card-header__title">上传知识库文档</h2>
          </template>
          <el-upload
            ref="uploadRef"
            :multiple="true"
            :before-upload="beforeUpload"
            :file-list="fileList"
            :auto-upload="false"
            @change="(file, list) => { fileList = list }"
            drag
            action="#"
            class="upload-area"
            accept=".txt,.md,.markdown,.pdf,.docx"
          >
            <el-icon class="upload-area__icon"><UploadFilled /></el-icon>
            <div class="upload-area__text">将文件拖到此处，或<em>点击上传</em></div>
            <template #tip>
              <div class="upload-area__tip">支持 .txt、.md、.pdf、.docx 格式，单个文件不超过 10MB，可同时选择多个文件</div>
            </template>
          </el-upload>

          <!-- 待上传文件列表 -->
          <div v-if="fileList.length > 0" class="pending-files">
            <el-tag type="info" size="small" style="margin-bottom:8px">已选择 {{ fileList.length }} 个文件</el-tag>
            <div v-for="(file, idx) in fileList" :key="idx" class="pending-file">
              <el-icon :size="14"><Document /></el-icon>
              <span class="pending-name">{{ file.name }}</span>
              <span class="pending-size">{{ formatSize(file.size) }}</span>
              <el-icon class="pending-remove" @click="removeFile(idx)"><Close /></el-icon>
            </div>
          </div>

          <el-button
            type="primary"
            :loading="uploading"
            @click="handleUpload"
            :disabled="fileList.length === 0"
            class="upload-btn"
          >
            <el-icon><Upload /></el-icon>
            {{ uploading ? `上传中 (${uploadProgress}/${uploadTotal})` : `开始上传（${fileList.length}）` }}
          </el-button>
        </el-card>

        <el-card class="page-card" shadow="never">
          <template #header>
            <h2 class="card-header__title">知识库统计</h2>
          </template>
          <el-row :gutter="16">
            <el-col :span="8">
              <div class="stat-item stat-item--primary">
                <el-icon :size="24"><Document /></el-icon>
                <div class="stat-item__value">{{ stats.total_documents }}</div>
                <div class="stat-item__label">文档数量</div>
              </div>
            </el-col>
            <el-col :span="8">
              <div class="stat-item stat-item--success">
                <el-icon :size="24"><Grid /></el-icon>
                <div class="stat-item__value">{{ stats.total_chunks }}</div>
                <div class="stat-item__label">知识碎片</div>
              </div>
            </el-col>
            <el-col :span="8">
              <div class="stat-item stat-item--warning">
                <el-icon :size="24"><Document /></el-icon>
                <div class="stat-item__value">{{ docStats.failed }}</div>
                <div class="stat-item__label">处理失败</div>
              </div>
            </el-col>
          </el-row>
        </el-card>
      </el-col>

      <!-- 右列：操作 + 文档列表 -->
      <el-col :xs="24" :lg="12">
        <el-card class="page-card" shadow="never">
          <template #header>
            <h2 class="card-header__title">知识库操作</h2>
          </template>
          <div class="action-buttons">
            <el-button class="action-btn" @click="handleRefresh">
              <el-icon><RefreshRight /></el-icon> 刷新
            </el-button>
            <el-popconfirm
              title="确定要清空知识库吗？此操作不可恢复！"
              confirm-button-text="确定"
              cancel-button-text="取消"
              @confirm="handleClear"
            >
              <template #reference>
                <el-button class="action-btn" type="danger" plain>
                  <el-icon><Delete /></el-icon> 清空知识库
                </el-button>
              </template>
            </el-popconfirm>
          </div>
        </el-card>

        <el-card class="page-card" shadow="never">
          <template #header>
            <div class="card-header">
              <h2 class="card-header__title">已上传文档</h2>
              <el-button size="small" @click="fetchDocuments">
                <el-icon><RefreshRight /></el-icon>
              </el-button>
            </div>
          </template>
          <el-table :data="documents" stripe v-loading="docsLoading" size="small" max-height="400">
            <el-table-column prop="filename" label="文件名" show-overflow-tooltip />
            <el-table-column prop="file_type" label="类型" width="70">
              <template #default="{ row }">
                <el-tag size="small" type="info">{{ row.file_type }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column label="大小" width="80">
              <template #default="{ row }">{{ formatSize(row.file_size) }}</template>
            </el-table-column>
            <el-table-column label="分块" width="60" prop="chunk_count" />
            <el-table-column label="状态" width="90">
              <template #default="{ row }">
                <el-tag v-if="row.status === 'completed'" type="success" size="small">完成</el-tag>
                <el-tag v-else-if="row.status === 'processing'" type="warning" size="small" effect="plain">
                  <el-icon class="spin"><Loading /></el-icon> 处理中
                </el-tag>
                <el-tag v-else type="danger" size="small">{{ row.error_message ? '失败' : '未知' }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column label="时间" width="140">
              <template #default="{ row }">
                {{ row.completed_at ? new Date(row.completed_at).toLocaleString() : new Date(row.created_at).toLocaleString() }}
              </template>
            </el-table-column>
          </el-table>
          <el-pagination
            v-if="docStats.total > 20"
            layout="prev, pager, next"
            :total="docStats.total"
            :page-size="20"
            v-model:current-page="docPage"
            @current-change="fetchDocuments"
            style="margin-top:12px;justify-content:center"
          />
          <el-empty v-if="!docsLoading && documents.length === 0" description="暂无文档" :image-size="60" />
        </el-card>
      </el-col>
    </el-row>

    <!-- 知识图谱 -->
    <el-card class="page-card graph-card" shadow="never">
      <template #header>
        <div class="card-header">
          <h2 class="card-header__title">知识图谱</h2>
          <el-button type="primary" :loading="graphLoading" @click="generateGraph">
            <el-icon><Share /></el-icon> 自动生成知识图谱
          </el-button>
        </div>
      </template>
      <KnowledgeGraph v-if="graphData" :graph-data="graphData" height="550px" />
      <el-empty v-else description="暂无知识图谱，请先上传文档后点击生成" />
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { teacherAPI } from '@/api'
import { UploadFilled, Upload, Document, Grid, RefreshRight, Delete, Share, Close, Loading } from '@element-plus/icons-vue'
import KnowledgeGraph from '@/components/KnowledgeGraph.vue'

interface Stats { total_documents: number; total_chunks: number; collection_name: string }
interface DocItem { id: number; filename: string; file_size: number; file_type: string; status: string; chunk_count: number; error_message: string; created_at: string; completed_at: string }

const uploading = ref(false)
const uploadRef = ref()
const fileList = ref<any[]>([])
const uploadProgress = ref(0)
const uploadTotal = ref(0)

const stats = reactive<Stats>({ total_documents: 0, total_chunks: 0, collection_name: 'knowledge_base' })
const docStats = reactive({ total: 0, failed: 0 })
const documents = ref<DocItem[]>([])
const docsLoading = ref(false)
const docPage = ref(1)

const graphData = ref<any>(null)
const graphLoading = ref(false)

function formatSize(bytes: number): string {
  if (bytes < 1024) return bytes + ' B'
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
  return (bytes / 1024 / 1024).toFixed(1) + ' MB'
}

const beforeUpload = (file: any): boolean => {
  const ok = /\.(pdf|docx?|txt|md|markdown)$/i.test(file.name) ||
    ['application/pdf', 'text/plain', 'text/markdown'].includes(file.type) ||
    file.name.endsWith('.doc') || file.name.endsWith('.docx')
  if (!ok) { ElMessage.error('不支持的文件格式'); return false }
  if (file.size > 10 * 1024 * 1024) { ElMessage.error('文件不能超过 10MB'); return false }
  fileList.value = [...fileList.value, file]
  return false
}

function removeFile(idx: number) { fileList.value.splice(idx, 1) }

const handleUpload = async () => {
  if (!fileList.value.length) { ElMessage.warning('请先选择文件'); return }
  uploading.value = true
  uploadTotal.value = fileList.value.length
  uploadProgress.value = 0

  const formData = new FormData()
  fileList.value.filter(f => f.raw).forEach(f => formData.append('files', f.raw!))

  try {
    await teacherAPI.uploadKnowledge(formData)
    ElMessage.success(`上传完成`)
    fileList.value = []
    uploadRef.value?.clearFiles()
    // 延迟刷新，等待后端处理完成
    setTimeout(async () => {
      await fetchStats()
      await fetchDocuments()
    }, 1000)
  } catch (e: any) {
    ElMessage.error('上传失败：' + (e?.message || ''))
  } finally {
    uploading.value = false
    uploadProgress.value = 0
    uploadTotal.value = 0
  }
}

const fetchStats = async () => {
  try { Object.assign(stats, await teacherAPI.getKnowledgeStats()) } catch { stats.total_documents = 0; stats.total_chunks = 0 }
}

const fetchDocuments = async () => {
  docsLoading.value = true
  try {
    const res: any = await teacherAPI.getKnowledgeDocuments({ page: docPage.value, page_size: 20 })
    documents.value = res.items || []
    docStats.total = res.total || 0
    docStats.failed = documents.value.filter(d => d.status === 'failed').length
  } catch { documents.value = [] } finally { docsLoading.value = false }
}

const handleRefresh = () => { fetchStats(); fetchDocuments(); ElMessage.success('已刷新') }

const handleClear = async () => {
  try { await teacherAPI.clearKnowledge(); ElMessage.success('知识库已清空'); fetchStats(); fetchDocuments() }
  catch { ElMessage.error('清空失败') }
}

const generateGraph = async () => {
  graphLoading.value = true
  try { graphData.value = await teacherAPI.generateKnowledgeGraph(); ElMessage.success('知识图谱生成成功') }
  catch (e: any) { ElMessage.error(e?.response?.data?.detail || '生成失败') }
  finally { graphLoading.value = false }
}

onMounted(() => { fetchStats(); fetchDocuments() })
</script>

<style scoped>
.page-container { padding: 24px; background: var(--color-bg-page, #F4F5F7); min-height: 100%; }
.page-card { border-radius: 12px; box-shadow: 0 2px 12px rgba(0, 0, 0, 0.06); margin-bottom: 20px; }
.card-header { display: flex; justify-content: space-between; align-items: center; }
.card-header__title { font-size: 14px; font-weight: 600; margin: 0; color: #1a1a2e; }
.upload-area { width: 100%; }
.upload-area__icon { font-size: 48px; color: #6b7280; margin-bottom: 8px; }
.upload-area__text { color: #1a1a2e; font-size: 14px; }
.upload-area__tip { color: #6b7280; font-size: 12px; margin-top: 8px; }
.upload-btn { width: 100%; margin-top: 12px; }
.pending-files { margin: 10px 0; max-height: 150px; overflow-y: auto; }
.pending-file { display: flex; align-items: center; gap: 8px; padding: 6px 0; font-size: 12px; color: #1a1a2e; border-bottom: 1px solid #e5e7eb; }
.pending-name { flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.pending-size { color: #6b7280; font-size: 12px; }
.pending-remove { cursor: pointer; color: #ef4444; }
.stat-item { text-align: center; padding: 16px 0; }
.stat-item__value { font-size: 28px; font-weight: 700; color: #1a1a2e; margin: 8px 0 4px; }
.stat-item__label { font-size: 12px; color: #6b7280; }
.stat-item--primary .stat-item__value { color: #4F46E5; }
.stat-item--success .stat-item__value { color: #10b981; }
.stat-item--warning .stat-item__value { color: #f59e0b; }
.action-buttons { display: flex; gap: 12px; }
.action-btn { flex: 1; }
.graph-card { margin-top: 0; }
.spin { animation: spin 1s linear infinite; }
@keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
</style>
