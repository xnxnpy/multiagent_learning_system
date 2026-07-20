<template>
  <div class="page-container">
    <el-card class="page-card">
      <template #header>
        <div class="card-header">
          <div class="card-header__left">
            <el-icon class="card-header__icon"><Notebook /></el-icon>
            <h2 class="card-header__title">作业管理</h2>
          </div>
          <div class="card-header__right">
            <el-radio-group v-model="statusFilter" @change="handleFilterChange">
              <el-radio-button value="">全部</el-radio-button>
              <el-radio-button value="draft">草稿</el-radio-button>
              <el-radio-button value="published">已发布</el-radio-button>
              <el-radio-button value="closed">已关闭</el-radio-button>
            </el-radio-group>
            <el-button type="primary" @click="showCreateDialog">
              <el-icon><Plus /></el-icon>
              新建作业
            </el-button>
          </div>
        </div>
      </template>

      <el-table :data="assignments" v-loading="loading" stripe class="data-table">
        <el-table-column prop="id" label="ID" width="70" />
        <el-table-column label="标题" min-width="180">
          <template #default="{ row }">
            <span class="link-text" @click="showDetail(row)">{{ row.title }}</span>
          </template>
        </el-table-column>
        <el-table-column label="截止日期" width="180">
          <template #default="{ row }">
            <span class="time-text">{{ formatDate(row.due_date) }}</span>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="110">
          <template #default="{ row }">
            <el-tag :type="statusTagType(row.status)" size="small">
              {{ statusLabel(row.status) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="分配人数" width="100" align="center">
          <template #default="{ row }">
            <span>{{ row.target_students?.length || 0 }}</span>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="280" fixed="right">
          <template #default="{ row }">
            <el-button type="primary" link size="small" @click="showEditDialog(row)">
              <el-icon><Edit /></el-icon> 编辑
            </el-button>
            <el-button type="warning" link size="small" @click="showAssignDialog(row)">
              <el-icon><User /></el-icon> 分配
            </el-button>
            <el-button type="success" link size="small" @click="showSubmissions(row)">
              <el-icon><Document /></el-icon> 提交
            </el-button>
            <el-button type="danger" link size="small" @click="handleDelete(row)">
              <el-icon><Delete /></el-icon> 删除
            </el-button>
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
          @current-change="handlePageChange"
        />
      </div>
    </el-card>

    <!-- 创建/编辑作业对话框 -->
    <el-dialog
      v-model="formDialogVisible"
      :title="isEdit ? '编辑作业' : '新建作业'"
      width="600px"
      class="custom-dialog"
    >
      <el-form :model="formData" :rules="formRules" ref="formRef" label-width="100px">
        <el-form-item label="作业标题" prop="title">
          <el-input v-model="formData.title" placeholder="请输入作业标题" />
        </el-form-item>
        <el-form-item label="作业描述" prop="description">
          <el-input
            v-model="formData.description"
            type="textarea"
            :rows="4"
            placeholder="请输入作业描述"
          />
        </el-form-item>
        <el-form-item label="截止日期">
          <el-date-picker
            v-model="formData.due_date"
            type="datetime"
            placeholder="选择截止日期"
            value-format="YYYY-MM-DDTHH:mm:ss"
            style="width: 100%"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="formDialogVisible = false">取消</el-button>
        <el-button @click="handleSubmitAsDraft" :loading="submitLoading">保存为草稿</el-button>
        <el-button type="primary" @click="handlePublish" :loading="submitLoading">直接发布</el-button>
      </template>
    </el-dialog>

    <!-- 分配学生对话框 -->
    <el-dialog
      v-model="assignDialogVisible"
      title="分配学生"
      width="500px"
      class="custom-dialog"
    >
      <div v-loading="assignLoading">
        <el-input
          v-model="studentSearch"
          placeholder="搜索学生姓名"
          clearable
          style="margin-bottom: 16px"
        >
          <template #prefix>
            <el-icon><Edit /></el-icon>
          </template>
        </el-input>
        <el-checkbox-group v-model="selectedStudentIds">
          <div
            v-for="student in filteredStudents"
            :key="student.id"
            class="student-checkbox-item"
          >
            <el-checkbox :value="student.id">
              {{ student.real_name || student.username }}
            </el-checkbox>
          </div>
        </el-checkbox-group>
        <div v-if="filteredStudents.length === 0" class="empty-tip">
          暂无学生数据
        </div>
      </div>
      <template #footer>
        <span class="assign-count">已选 {{ selectedStudentIds.length }} 名学生</span>
        <el-button @click="assignDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleAssign" :loading="assignLoading">确认分配</el-button>
      </template>
    </el-dialog>

    <!-- 提交记录对话框 -->
    <el-dialog
      v-model="submissionsDialogVisible"
      title="提交记录"
      width="800px"
      class="custom-dialog"
    >
      <el-table :data="submissions" v-loading="submissionsLoading" stripe>
        <el-table-column prop="student_id" label="学生ID" width="80" />
        <el-table-column label="提交时间" width="180">
          <template #default="{ row }">
            <span class="time-text">{{ formatDate(row.submitted_at) }}</span>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="110">
          <template #default="{ row }">
            <el-tag :type="submissionStatusType(row.status)" size="small">
              {{ submissionStatusLabel(row.status) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="score" label="分数" width="80" />
        <el-table-column label="反馈" min-width="200">
          <template #default="{ row }">
            <span class="truncate-text">{{ row.feedback || '-' }}</span>
          </template>
        </el-table-column>
      </el-table>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Notebook, Plus, Edit, Delete, User, Document } from '@element-plus/icons-vue'
import { teacherAPI } from '@/api'

interface Assignment {
  id: number
  title: string
  description: string
  due_date?: string
  target_students?: number[]
  status: string
  created_at: string
}

interface Student {
  id: number
  username: string
  real_name?: string
}

const loading = ref(false)
const submitLoading = ref(false)
const assignLoading = ref(false)
const submissionsLoading = ref(false)
const statusFilter = ref('')
const formDialogVisible = ref(false)
const assignDialogVisible = ref(false)
const submissionsDialogVisible = ref(false)
const isEdit = ref(false)
const editingId = ref<number | null>(null)
const formRef = ref()
const currentAssignment = ref<Assignment | null>(null)

const assignments = ref<Assignment[]>([])
const students = ref<Student[]>([])
const selectedStudentIds = ref<number[]>([])
const studentSearch = ref('')
const submissions = ref<any[]>([])

const pagination = reactive({ current: 1, pageSize: 10, total: 0 })

const formData = reactive({
  title: '',
  description: '',
  due_date: '',
})

const formRules = {
  title: [{ required: true, message: '请输入作业标题', trigger: 'blur' }],
  description: [{ required: true, message: '请输入作业描述', trigger: 'blur' }],
}

const filteredStudents = computed(() => {
  if (!studentSearch.value) return students.value
  const keyword = studentSearch.value.toLowerCase()
  return students.value.filter(s =>
    (s.real_name || s.username).toLowerCase().includes(keyword)
  )
})

const statusLabel = (status: string) => ({ draft: '草稿', published: '已发布', closed: '已关闭' }[status] || status)
const statusTagType = (status: string) => ({ draft: 'info', published: 'success', closed: 'danger' }[status] || 'info')
const submissionStatusLabel = (s: string) => ({ submitted: '已提交', graded: '已评分', returned: '已退回' }[s] || s)
const submissionStatusType = (s: string) => ({ submitted: 'warning', graded: 'success', returned: 'info' }[s] || 'info')
const formatDate = (dateStr: string) => dateStr ? new Date(dateStr).toLocaleString('zh-CN') : '-'

const fetchAssignments = async () => {
  loading.value = true
  try {
    const params: any = {
      page: pagination.current,
      page_size: pagination.pageSize,
    }
    if (statusFilter.value) {
      params.status = statusFilter.value
    }
    const response: any = await teacherAPI.getAssignments(params)
    assignments.value = response.items || response
    pagination.total = response.total || assignments.value.length
  } catch (error) {
    ElMessage.error('获取作业列表失败')
  } finally {
    loading.value = false
  }
}

const fetchStudents = async () => {
  assignLoading.value = true
  try {
    const response: any = await teacherAPI.getStudentProgress()
    const list = Array.isArray(response) ? response : (response.student_progress || response.items || [])
    students.value = list.map((item: any) => ({
      id: item.student_id,
      username: item.student_name || item.username || String(item.student_id),
      real_name: item.student_name || item.real_name || '',
    }))
  } catch (error) {
    ElMessage.error('获取学生列表失败')
    students.value = []
  } finally {
    assignLoading.value = false
  }
}

const handleFilterChange = () => {
  pagination.current = 1
  fetchAssignments()
}

const handlePageChange = () => {
  fetchAssignments()
}

const handleSizeChange = () => {
  pagination.current = 1
  fetchAssignments()
}

const showCreateDialog = () => {
  isEdit.value = false
  editingId.value = null
  Object.assign(formData, { title: '', description: '', due_date: '' })
  formDialogVisible.value = true
}

const showEditDialog = (row: Assignment) => {
  isEdit.value = true
  editingId.value = row.id
  Object.assign(formData, {
    title: row.title,
    description: row.description,
    due_date: row.due_date || '',
  })
  formDialogVisible.value = true
}

const showDetail = (row: Assignment) => {
  ElMessageBox.alert(
    `<p>${row.description || '暂无描述'}</p>
     <p style="color:#999;margin-top:8px">截止日期: ${formatDate(row.due_date)}</p>
     <p style="color:#999;margin-top:4px">状态: ${statusLabel(row.status)}</p>`,
    row.title,
    {
      confirmButtonText: '关闭',
      dangerouslyUseHTMLString: true,
    }
  )
}

const showAssignDialog = (row: Assignment) => {
  currentAssignment.value = row
  selectedStudentIds.value = Array.isArray(row.target_students) ? [...row.target_students] : []
  studentSearch.value = ''
  if (students.value.length === 0) {
    fetchStudents()
  }
  assignDialogVisible.value = true
}

const showSubmissions = async (row: Assignment) => {
  currentAssignment.value = row
  submissions.value = []
  submissionsLoading.value = true
  submissionsDialogVisible.value = true
  try {
    const response: any = await teacherAPI.getAssignmentSubmissions(row.id)
    submissions.value = Array.isArray(response) ? response : (response.items || response.data || [])
  } catch (error) {
    ElMessage.error('获取提交记录失败')
    submissions.value = []
  } finally {
    submissionsLoading.value = false
  }
}

const handleSubmit = async (status: 'draft' | 'published') => {
  try {
    await formRef.value.validate()
    submitLoading.value = true

    const payload: any = {
      title: formData.title,
      description: formData.description,
      due_date: formData.due_date || undefined,
      status,
    }

    if (isEdit.value && editingId.value) {
      await teacherAPI.updateAssignment(editingId.value, payload)
      ElMessage.success('作业更新成功')
    } else {
      await teacherAPI.createAssignment(payload)
      ElMessage.success('作业创建成功')
    }

    formDialogVisible.value = false
    fetchAssignments()
  } catch (error: any) {
    if (error.errorFields) return
    ElMessage.error(isEdit.value ? '更新失败' : '创建失败')
  } finally {
    submitLoading.value = false
  }
}

const handleSubmitAsDraft = () => {
  handleSubmit('draft')
}

const handlePublish = () => {
  handleSubmit('published')
}

const handleAssign = async () => {
  if (!currentAssignment.value) return
  assignLoading.value = true
  try {
    await teacherAPI.assignStudents(currentAssignment.value.id, selectedStudentIds.value)
    ElMessage.success('分配成功')
    assignDialogVisible.value = false
    fetchAssignments()
  } catch (error) {
    ElMessage.error('分配失败')
  } finally {
    assignLoading.value = false
  }
}

const handleDelete = (row: Assignment) => {
  ElMessageBox.confirm(`确定要删除作业 "${row.title}" 吗？`, '确认删除', {
    confirmButtonText: '确定',
    cancelButtonText: '取消',
    type: 'warning',
  }).then(async () => {
    try {
      await teacherAPI.deleteAssignment(row.id)
      ElMessage.success('删除成功')
      fetchAssignments()
    } catch (error) {
      ElMessage.error('删除失败')
    }
  }).catch(() => {})
}

onMounted(() => {
  fetchAssignments()
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
  color: #4F46E5;
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

.link-text {
  color: #4F46E5;
  cursor: pointer;
  font-weight: 500;
}

.link-text:hover {
  text-decoration: underline;
}

.truncate-text {
  color: #374151;
  font-size: 12px;
  line-height: 1.6;
}

.time-text {
  color: #6b7280;
  font-size: 12px;
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
  background: var(--color-bg-page, #F4F5F7);
  color: #374151;
  font-weight: 600;
  font-size: 12px;
}

:deep(.el-dialog) {
  border-radius: 12px;
}

.student-checkbox-item {
  padding: 8px 0;
  border-bottom: 1px solid #e5e7eb;
}

.student-checkbox-item:last-child {
  border-bottom: none;
}

.empty-tip {
  color: #6b7280;
  font-size: 12px;
  text-align: center;
  padding: 24px 0;
}

.assign-count {
  color: #374151;
  font-size: 12px;
  margin-right: auto;
}
</style>
