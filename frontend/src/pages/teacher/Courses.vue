<template>
  <div class="page-container">
    <el-card class="page-card">
      <template #header>
        <div class="card-header">
          <div class="card-header__left">
            <el-icon class="card-header__icon"><Reading /></el-icon>
            <h2 class="card-header__title">课程管理</h2>
          </div>
          <div class="card-header__right">
            <el-input
              v-model="searchText"
              placeholder="搜索课程名称"
              style="width: 240px"
              clearable
              @keyup.enter="handleSearch"
            >
              <template #prefix>
                <el-icon><Search /></el-icon>
              </template>
            </el-input>
            <el-button type="primary" @click="showAddDialog">
              <el-icon><Plus /></el-icon>
              创建课程
            </el-button>
          </div>
        </div>
      </template>

      <el-table :data="courses" v-loading="loading" stripe class="data-table">
        <el-table-column prop="id" label="ID" width="70" />
        <el-table-column label="课程标题" min-width="160">
          <template #default="{ row }">
            <span class="link-text" @click="showDetail(row)">{{ row.title }}</span>
          </template>
        </el-table-column>
        <el-table-column label="课程描述" min-width="220">
          <template #default="{ row }">
            <span class="truncate-text">{{ row.description ? row.description.substring(0, 50) + '...' : '-' }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="创建时间" width="170">
          <template #default="{ row }">
            <span class="time-text">{{ formatDate(row.created_at) }}</span>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="200" fixed="right">
          <template #default="{ row }">
            <el-button type="primary" link size="small" @click="showEditDialog(row)">
              <el-icon><Edit /></el-icon> 编辑
            </el-button>
            <el-button type="success" link size="small" @click="handleExport(row)">
              <el-icon><Download /></el-icon> 导出
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

    <!-- 创建/编辑对话框 -->
    <el-dialog
      v-model="dialogVisible"
      :title="isEdit ? '编辑课程' : '创建课程'"
      width="600px"
      class="custom-dialog"
    >
      <el-form :model="formData" :rules="formRules" ref="formRef" label-width="100px">
        <el-form-item label="课程标题" prop="title">
          <el-input v-model="formData.title" placeholder="请输入课程标题" />
        </el-form-item>
        <el-form-item label="课程描述">
          <el-input v-model="formData.description" type="textarea" :rows="4" placeholder="请输入课程描述" />
        </el-form-item>
        <el-form-item label="知识结构">
          <div class="knowledge-tree-editor">
            <div
              v-for="(item, index) in knowledgeTreeItems"
              :key="index"
              class="knowledge-tree-item"
            >
              <el-input
                v-model="item.name"
                placeholder="知识点名称"
                style="width: 260px"
              />
              <el-select
                v-model="item.level"
                placeholder="层级"
                style="width: 140px; margin-left: 8px"
              >
                <el-option :value="1" label="一级知识点" />
                <el-option :value="2" label="二级知识点" />
                <el-option :value="3" label="三级知识点" />
              </el-select>
              <el-button
                type="danger"
                link
                @click="removeKnowledgeNode(index)"
                style="margin-left: 8px"
              >
                <el-icon><Delete /></el-icon>
              </el-button>
            </div>
            <div v-if="knowledgeTreeItems.length === 0" class="knowledge-tree-empty">
              暂无知识点，点击下方按钮添加
            </div>
            <el-button type="primary" link @click="addKnowledgeNode" style="margin-top: 8px">
              <el-icon><Plus /></el-icon> 添加知识点
            </el-button>
          </div>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitLoading" @click="handleSubmit">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Reading, Search, Plus, Edit, Download, Delete } from '@element-plus/icons-vue'
import { teacherAPI } from '@/api'

interface Course {
  id: number
  teacher_id: number
  title: string
  description?: string
  knowledge_tree?: any
  created_at: string
}

const loading = ref(false)
const submitLoading = ref(false)
const dialogVisible = ref(false)
const isEdit = ref(false)
const editingId = ref<number | null>(null)
const searchText = ref('')
const courses = ref<Course[]>([])
const formRef = ref()
const knowledgeTreeItems = ref<{ name: string; level: number }[]>([])

const addKnowledgeNode = () => {
  knowledgeTreeItems.value.push({ name: '', level: 1 })
}

const removeKnowledgeNode = (index: number) => {
  knowledgeTreeItems.value.splice(index, 1)
}

const buildKnowledgeTree = () => {
  const items = knowledgeTreeItems.value.filter(item => item.name.trim())
  if (!items.length) return null

  const nodes = items.map((item, i) => {
    const nodeId = `node_${i}`
    const node: Record<string, any> = {
      id: nodeId,
      label: item.name.trim(),
      level: item.level,
    }
    for (let j = i - 1; j >= 0; j--) {
      if (items[j].level < item.level) {
        node.parent = `node_${j}`
        break
      }
    }
    return node
  })

  const edges: { source: string; target: string }[] = []
  for (const node of nodes) {
    if (node.parent) {
      edges.push({ source: node.parent, target: node.id })
    }
  }

  return { nodes, edges }
}

const parseKnowledgeTree = (tree: any) => {
  if (!tree?.nodes?.length) {
    knowledgeTreeItems.value = []
    return
  }
  knowledgeTreeItems.value = tree.nodes.map((node: any) => ({
    name: node.label || '',
    level: node.level || 1,
  }))
}

const pagination = reactive({
  current: 1,
  pageSize: 10,
  total: 0
})

const formData = reactive({
  title: '',
  description: ''
})

const formRules = {
  title: [{ required: true, message: '请输入课程标题', trigger: 'blur' }]
}

const formatDate = (dateStr: string) => {
  if (!dateStr) return '-'
  return new Date(dateStr).toLocaleString('zh-CN')
}

const fetchCourses = async () => {
  loading.value = true
  try {
    const response: any = await teacherAPI.getCourses({
      page: pagination.current,
      page_size: pagination.pageSize,
      search: searchText.value || undefined
    })
    courses.value = response.items || response
    pagination.total = response.total || courses.value.length
  } catch (error) {
    ElMessage.error('获取课程列表失败')
  } finally {
    loading.value = false
  }
}

const handleSearch = () => {
  pagination.current = 1
  fetchCourses()
}

const handlePageChange = () => {
  fetchCourses()
}

const handleSizeChange = () => {
  pagination.current = 1
  fetchCourses()
}

const showAddDialog = () => {
  isEdit.value = false
  editingId.value = null
  Object.assign(formData, { title: '', description: '' })
  knowledgeTreeItems.value = []
  dialogVisible.value = true
}

const showEditDialog = (row: Course) => {
  isEdit.value = true
  editingId.value = row.id
  Object.assign(formData, {
    title: row.title,
    description: row.description
  })
  parseKnowledgeTree(row.knowledge_tree)
  dialogVisible.value = true
}

const showDetail = (row: Course) => {
  ElMessageBox.info({
    title: row.title,
    message: `<p>${row.description || '暂无描述'}</p><p style="color:#999;margin-top:8px">创建时间: ${formatDate(row.created_at)}</p>`,
    confirmButtonText: '关闭'
  })
}

const handleSubmit = async () => {
  try {
    await formRef.value.validate()
    submitLoading.value = true

    const knowledgeTree = buildKnowledgeTree()

    const submitData = {
      title: formData.title,
      description: formData.description,
      knowledge_tree: knowledgeTree
    }

    if (isEdit.value && editingId.value) {
      await teacherAPI.updateCourse(editingId.value, submitData)
      ElMessage.success('课程更新成功')
    } else {
      await teacherAPI.createCourse(submitData)
      ElMessage.success('课程创建成功')
    }

    dialogVisible.value = false
    fetchCourses()
  } catch (error: any) {
    if (error.errorFields) return
    ElMessage.error(isEdit.value ? '更新失败' : '创建失败')
  } finally {
    submitLoading.value = false
  }
}

const handleDelete = (row: Course) => {
  ElMessageBox.confirm(`确定要删除课程 "${row.title}" 吗？`, '确认删除', {
    confirmButtonText: '确定',
    cancelButtonText: '取消',
    type: 'warning'
  }).then(async () => {
    try {
      await teacherAPI.deleteCourse(row.id)
      ElMessage.success('删除成功')
      fetchCourses()
    } catch (error) {
      ElMessage.error('删除失败')
    }
  }).catch(() => {})
}

const handleExport = async (row: Course) => {
  try {
    const response: any = await teacherAPI.exportCourseReport(row.id)
    const blob = new Blob([response])
    const url = window.URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = `course_${row.id}_report.csv`
    link.click()
    window.URL.revokeObjectURL(url)
    ElMessage.success('报表导出成功')
  } catch (error) {
    ElMessage.error('导出失败')
  }
}

onMounted(() => {
  fetchCourses()
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

.link-text {
  color: var(--color-primary);
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
  color: var(--color-text-muted);
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

.knowledge-tree-editor {
  width: 100%;
}

.knowledge-tree-item {
  display: flex;
  align-items: center;
  margin-bottom: 8px;
}

.knowledge-tree-empty {
  color: var(--color-text-muted);
  font-size: 12px;
  padding: 12px 0;
}
</style>
