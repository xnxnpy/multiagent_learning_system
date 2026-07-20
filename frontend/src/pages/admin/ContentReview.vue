<template>
  <div class="page-container">
    <el-card class="page-card">
      <template #header>
        <div class="card-header">
          <div class="card-header__left">
            <el-icon class="card-header__icon"><CircleCheck /></el-icon>
            <h2 class="card-header__title">内容安全审核</h2>
          </div>
          <div class="card-header__right">
            <el-select v-model="filterStatus" placeholder="状态筛选" style="width: 140px" @change="handleFilterChange" clearable>
              <el-option value="" label="全部状态" />
              <el-option value="pending" label="待审核" />
              <el-option value="approved" label="已通过" />
              <el-option value="rejected" label="已拒绝" />
            </el-select>
          </div>
        </div>
      </template>

      <el-table :data="contents" v-loading="loading" stripe class="data-table">
        <el-table-column prop="id" label="ID" width="70" />
        <el-table-column label="类型" width="110" align="center">
          <template #default="{ row }">
            <el-tag effect="light" round>{{ getTypeText(row.content_type) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="内容预览" min-width="260">
          <template #default="{ row }">
            <span class="truncate-text" :title="row.content">{{ row.content?.substring(0, 80) }}...</span>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="100" align="center">
          <template #default="{ row }">
            <el-tag :type="getStatusTagType(row.status)" effect="light" round>
              {{ getStatusText(row.status) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="提交时间" width="170">
          <template #default="{ row }">
            <span class="time-text">{{ formatDate(row.created_at) }}</span>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="180" fixed="right">
          <template #default="{ row }">
            <el-button type="primary" link size="small" @click="showDetail(row)">查看</el-button>
            <template v-if="row.status === 'pending'">
              <el-button type="success" link size="small" @click="handleApprove(row)">通过</el-button>
              <el-button type="danger" link size="small" @click="handleReject(row)">拒绝</el-button>
            </template>
          </template>
        </el-table-column>
      </el-table>

      <div class="pagination-wrap">
        <el-pagination
          v-model:current-page="pagination.current"
          v-model:page-size="pagination.pageSize"
          :total="pagination.total"
          :page-sizes="[10, 20, 50, 100]"
          layout="total, sizes, prev, pager, next, jumper"
          @size-change="handleSizeChange"
          @current-change="handleCurrentChange"
        />
      </div>
    </el-card>

    <!-- 审核详情对话框 -->
    <el-dialog
      v-model="detailModalVisible"
      title="内容详情"
      width="800px"
      class="custom-dialog"
    >
      <el-descriptions :column="2" border class="detail-desc">
        <el-descriptions-item label="内容类型">
          <el-tag effect="light" round>{{ getTypeText(currentContent?.content_type) }}</el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="状态">
          <el-tag :type="getStatusTagType(currentContent?.status)" effect="light" round>
            {{ getStatusText(currentContent?.status) }}
          </el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="提交时间">
          {{ formatDate(currentContent?.created_at) }}
        </el-descriptions-item>
        <el-descriptions-item label="审核时间" v-if="currentContent?.reviewed_at">
          {{ formatDate(currentContent.reviewed_at) }}
        </el-descriptions-item>
        <el-descriptions-item label="内容" :span="2">
          <pre class="content-pre">{{ currentContent?.content }}</pre>
        </el-descriptions-item>
        <el-descriptions-item label="审核意见" :span="2" v-if="currentContent?.review_comment">
          {{ currentContent.review_comment }}
        </el-descriptions-item>
      </el-descriptions>

      <el-divider content-position="center">审核操作</el-divider>
      <el-form :label-width="80" v-if="currentContent?.status === 'pending'">
        <el-form-item label="审核意见">
          <el-input v-model="reviewComment" placeholder="请输入审核意见（拒绝必填）" type="textarea" :rows="2" />
        </el-form-item>
      </el-form>

      <template #footer v-if="currentContent?.status === 'pending'">
        <el-button @click="detailModalVisible = false">关闭</el-button>
        <el-button type="danger" @click="doReject">拒绝</el-button>
        <el-button type="primary" @click="doApprove">通过</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { adminAPI } from '@/api'
import { CircleCheck } from '@element-plus/icons-vue'

interface Content {
  id: number
  content_type: string
  content: string
  status: string
  created_at: string
  reviewed_at?: string
  review_comment?: string
}

const loading = ref(false)
const detailModalVisible = ref(false)
const currentContent = ref<Content | null>(null)
const reviewComment = ref('')
const filterStatus = ref('')

const contents = ref<Content[]>([])
const pagination = reactive({
  current: 1,
  pageSize: 10,
  total: 0
})

const getTypeText = (type: string | undefined): string => {
  const texts: Record<string, string> = {
    document: '文档',
    mindmap: '思维导图',
    video: '视频',
    code: '代码'
  }
  return texts[type || ''] || type || '未知'
}

const getStatusTagType = (status: string | undefined): '' | 'info' | 'primary' | 'success' | 'warning' | 'danger' | 'text' => {
  const types: Record<string, '' | 'info' | 'primary' | 'success' | 'warning' | 'danger' | 'text'> = {
    pending: 'warning',
    approved: 'success',
    rejected: 'danger'
  }
  return types[status || ''] || ''
}

const getStatusText = (status: string | undefined): string => {
  const texts: Record<string, string> = {
    pending: '待审核',
    approved: '已通过',
    rejected: '已拒绝'
  }
  return texts[status || ''] || status || '未知'
}

const formatDate = (dateStr: string | undefined): string => {
  if (!dateStr) return '-'
  return new Date(dateStr).toLocaleString('zh-CN')
}

const fetchContents = async () => {
  loading.value = true
  try {
    const params: Record<string, any> = {
      page: pagination.current,
      page_size: pagination.pageSize
    }
    if (filterStatus.value) {
      params.status = filterStatus.value
    }
    const response: any = await adminAPI.getContentReview(params)
    contents.value = response.items || response
    pagination.total = response.total || contents.value.length
  } catch (error) {
    ElMessage.error('获取内容列表失败')
  } finally {
    loading.value = false
  }
}

const handleFilterChange = () => {
  pagination.current = 1
  fetchContents()
}

const handleSizeChange = (size: number) => {
  pagination.pageSize = size
  pagination.current = 1
  fetchContents()
}

const handleCurrentChange = (current: number) => {
  pagination.current = current
  fetchContents()
}

const showDetail = (record: Content) => {
  currentContent.value = record
  reviewComment.value = ''
  detailModalVisible.value = true
}

const handleApprove = (record: Content) => {
  ElMessageBox.confirm('确定要通过此内容的审核吗？', '确认通过', {
    confirmButtonText: '确定',
    cancelButtonText: '取消',
    type: 'info'
  }).then(() => {
    doApproveById(record.id)
  }).catch(() => {})
}

const handleReject = (record: Content) => {
  ElMessageBox.prompt('请输入拒绝原因', '确认拒绝', {
    confirmButtonText: '确定',
    cancelButtonText: '取消',
    type: 'warning',
    inputPlaceholder: '请输入拒绝原因'
  }).then(({ value }) => {
    reviewComment.value = value || ''
    doRejectById(record.id, value || '')
  }).catch(() => {})
}

const doApprove = async () => {
  if (currentContent.value) {
    await doApproveById(currentContent.value.id)
    detailModalVisible.value = false
  }
}

const doReject = async () => {
  if (!reviewComment.value) {
    ElMessage.error('请输入拒绝原因')
    return
  }
  if (currentContent.value) {
    await doRejectById(currentContent.value.id, reviewComment.value)
    detailModalVisible.value = false
  }
}

const doApproveById = async (id: number) => {
  try {
    await adminAPI.reviewContent(id, {
      action: 'approve',
      comment: reviewComment.value
    })
    ElMessage.success('已通过审核')
    fetchContents()
  } catch (error) {
    ElMessage.error('操作失败')
  }
}

const doRejectById = async (id: number, comment: string) => {
  try {
    await adminAPI.reviewContent(id, {
      action: 'reject',
      comment
    })
    ElMessage.success('已拒绝')
    fetchContents()
  } catch (error) {
    ElMessage.error('操作失败')
  }
}

onMounted(() => {
  fetchContents()
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
  color: #1a1a2e;
}

.card-header__right {
  display: flex;
  align-items: center;
  gap: 12px;
}

.truncate-text {
  color: #374151;
  font-size: 13px;
  line-height: 1.6;
}

.time-text {
  color: #6b7280;
  font-size: 13px;
}

.content-pre {
  white-space: pre-wrap;
  max-height: 300px;
  overflow-y: auto;
  background: #e5e7eb;
  padding: 12px 16px;
  border-radius: 8px;
  font-size: 13px;
  line-height: 1.6;
  color: #374151;
  margin: 0;
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
  background: #e5e7eb;
  color: #374151;
  font-weight: 600;
  font-size: 13px;
}

:deep(.el-dialog) {
  border-radius: 12px;
}
</style>
