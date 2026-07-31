<template>
  <div class="teacher-page">
    <div class="page-header">
      <h2 class="page-title">课程管理</h2>
      <p class="page-subtitle">管理课程内容、知识结构与教学资源</p>
    </div>

    <!-- 统计条 -->
    <div class="stat-strip">
      <div class="stat-item">
        <span class="stat-num tabular">{{ courses.length }}</span>
        <span class="stat-label">门课程</span>
      </div>
      <div class="stat-divider"></div>
      <div class="stat-item">
        <span class="stat-num tabular">{{ totalKnowledgeNodes }}</span>
        <span class="stat-label">个知识点</span>
      </div>
      <div class="stat-divider"></div>
      <div class="stat-item">
        <span class="stat-num tabular">{{ thisMonthNew }}</span>
        <span class="stat-label">本月新增</span>
      </div>
    </div>

    <el-card class="page-card" shadow="never">
      <template #header>
        <div class="card-header">
          <div class="card-header__left">
            <div class="card-header__mark">
              <el-icon class="card-header__icon"><Reading /></el-icon>
            </div>
            <div>
              <h3 class="card-header__title">课程列表</h3>
              <span class="card-header__subtitle">共 {{ pagination.total }} 条记录</span>
            </div>
          </div>
          <div class="card-header__right">
            <el-input
              v-model="searchText"
              placeholder="搜索课程名称"
              class="search-input"
              clearable
              @keyup.enter="handleSearch"
            >
              <template #prefix>
                <el-icon><Search /></el-icon>
              </template>
            </el-input>
            <el-button class="create-btn" @click="showAddDialog">
              <el-icon><Plus /></el-icon>
              创建课程
            </el-button>
          </div>
        </div>
      </template>

      <el-table :data="courses" v-loading="loading" class="data-table">
        <el-table-column prop="id" label="ID" width="70">
          <template #default="{ row }">
            <span class="cell-id">#{{ row.id }}</span>
          </template>
        </el-table-column>
        <el-table-column label="课程标题" min-width="180">
          <template #default="{ row }">
            <div class="course-title-cell">
              <span class="course-title-link" @click="showDetail(row)">{{ row.title }}</span>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="课程描述" min-width="260">
          <template #default="{ row }">
            <p class="truncate-text">{{ row.description || '暂无课程描述' }}</p>
          </template>
        </el-table-column>
        <el-table-column label="知识结构" width="120" align="center">
          <template #default="{ row }">
            <span class="knowledge-count">
              <el-icon class="kc-icon"><Connection /></el-icon>
              {{ countKnowledgeNodes(row.knowledge_tree) }}
            </span>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="创建时间" width="180">
          <template #default="{ row }">
            <span class="time-text">{{ formatDate(row.created_at) }}</span>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="220" fixed="right" align="right">
          <template #default="{ row }">
            <div class="action-group">
              <el-button class="action-btn edit" link size="small" @click="showEditDialog(row)">
                <el-icon><Edit /></el-icon> 编辑
              </el-button>
              <el-button class="action-btn export" link size="small" @click="handleExport(row)">
                <el-icon><Download /></el-icon> 导出
              </el-button>
              <el-button class="action-btn delete" link size="small" @click="handleDelete(row)">
                <el-icon><Delete /></el-icon> 删除
              </el-button>
            </div>
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
import { ref, reactive, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Reading, Search, Plus, Edit, Download, Delete, Connection } from '@element-plus/icons-vue'
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

/* ── 计算属性 ────────────────────────────────── */

const totalKnowledgeNodes = computed(() => {
  return courses.value.reduce((acc, c) => acc + countKnowledgeNodes(c.knowledge_tree), 0)
})

const thisMonthNew = computed(() => {
  const now = new Date()
  const y = now.getFullYear()
  const m = now.getMonth()
  return courses.value.filter(c => {
    if (!c.created_at) return false
    const d = new Date(c.created_at)
    return d.getFullYear() === y && d.getMonth() === m
  }).length
})

function countKnowledgeNodes(tree: any): number {
  if (!tree?.nodes?.length) return 0
  return tree.nodes.length
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
/* ── 页面基础 ────────────────────────────────── */

.teacher-page {
  max-width: 1440px;
  margin: 0 auto;
}

.page-header {
  margin-bottom: var(--space-5);
}

.page-title {
  font-family: var(--font-serif);
  font-size: var(--text-2xl);
  font-weight: 700;
  color: var(--color-text-ink);
  letter-spacing: 0.02em;
  margin: 0;
  position: relative;
  display: inline-block;
  padding-left: 16px;
  line-height: 1.2;
}
.page-title::before {
  content: '';
  position: absolute;
  left: 0; top: 15%;
  width: 5px; height: 70%;
  background: linear-gradient(180deg, var(--color-teacher), var(--color-teacher-soft));
  border-radius: 5px;
}

.page-subtitle {
  margin: 8px 0 0 0;
  padding-left: 16px;
  font-size: var(--text-sm);
  color: var(--color-text-muted);
  letter-spacing: 0.01em;
}

/* ── 统计条 ──────────────────────────────────── */

.stat-strip {
  display: flex;
  align-items: center;
  gap: 28px;
  padding: 18px 28px;
  background: var(--color-teacher-pale);
  border: 1px solid var(--color-teacher-soft);
  border-radius: var(--radius-lg);
  margin-bottom: var(--space-card-gap);
  position: relative;
  overflow: hidden;
}
.stat-strip::after {
  content: '';
  position: absolute;
  right: 0; top: 0; bottom: 0;
  width: 120px;
  background: linear-gradient(90deg, transparent, rgba(61,107,79,0.06));
  pointer-events: none;
}

.stat-item {
  display: flex;
  align-items: baseline;
  gap: 8px;
  z-index: 1;
}

.stat-num {
  font-family: var(--font-serif);
  font-size: var(--text-2xl);
  font-weight: 700;
  color: var(--color-teacher);
  line-height: 1;
}
.tabular { font-variant-numeric: tabular-nums; }

.stat-label {
  font-size: var(--text-sm);
  color: var(--color-text-muted);
  font-weight: 500;
}

.stat-divider {
  width: 1px;
  height: 28px;
  background: var(--color-teacher-soft);
}

/* ── 卡片与头部 ──────────────────────────────── */

.page-card {
  background: var(--color-bg-card);
  border-radius: var(--radius-lg);
  border: 1px solid var(--color-border-light);
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
  gap: 12px;
}

.card-header__mark {
  width: 38px; height: 38px;
  border-radius: 10px;
  background: linear-gradient(135deg, var(--color-teacher), #5A8E6E);
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 2px 8px rgba(61,107,79,0.18);
  flex-shrink: 0;
}

.card-header__icon {
  font-size: 18px;
  color: #fff;
}

.card-header__title {
  font-family: var(--font-serif);
  font-size: var(--text-lg);
  font-weight: 600;
  margin: 0;
  color: var(--color-text-ink);
  line-height: 1.2;
}

.card-header__subtitle {
  font-size: var(--text-xs);
  color: var(--color-text-muted);
  display: block;
  margin-top: 3px;
}

.card-header__right {
  display: flex;
  align-items: center;
  gap: 12px;
}

.search-input {
  width: 260px;
}
.search-input :deep(.el-input__wrapper) {
  border-radius: 10px;
  box-shadow: 0 0 0 1px var(--color-border);
  transition: all var(--transition-fast);
}
.search-input :deep(.el-input__wrapper:hover) {
  box-shadow: 0 0 0 1px var(--color-teacher-soft);
}
.search-input :deep(.el-input__wrapper.is-focus) {
  box-shadow: 0 0 0 1px var(--color-teacher);
}

.create-btn {
  background: var(--color-teacher);
  border: none;
  font-weight: 500;
  padding: 0 20px;
  border-radius: 10px;
  transition: all var(--transition-fast);
  color: #fff;
}
.create-btn:hover {
  background: #2F5440 !important;
  transform: translateY(-1px);
  box-shadow: 0 4px 14px rgba(61,107,79,0.28);
  color: #fff !important;
}

/* ── 表格 ────────────────────────────────────── */

.cell-id {
  font-family: var(--font-mono);
  font-size: var(--text-sm);
  color: var(--color-text-muted);
  font-weight: 500;
}

.course-title-cell {
  display: flex;
  align-items: center;
}

.course-title-link {
  color: var(--color-teacher);
  cursor: pointer;
  font-weight: 600;
  font-size: var(--text-base);
  transition: all var(--transition-fast);
  position: relative;
}
.course-title-link::after {
  content: '';
  position: absolute;
  bottom: -2px; left: 0;
  width: 0; height: 1.5px;
  background: var(--color-teacher);
  transition: width var(--transition-normal);
}
.course-title-link:hover::after {
  width: 100%;
}

.truncate-text {
  color: var(--color-text-body);
  font-size: var(--text-sm);
  line-height: 1.6;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.knowledge-count {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  padding: 4px 10px;
  background: var(--color-teacher-pale);
  color: var(--color-teacher);
  border-radius: var(--radius-sm);
  font-size: var(--text-sm);
  font-weight: 500;
}
.kc-icon {
  font-size: 13px;
}

.time-text {
  color: var(--color-text-muted);
  font-size: var(--text-sm);
  font-family: var(--font-mono);
  font-size: var(--text-xs);
}

.action-group {
  display: inline-flex;
  gap: 4px;
}

.action-btn {
  font-weight: 500;
  padding: 4px 8px;
  border-radius: 6px;
  transition: all var(--transition-fast);
}
.action-btn.edit { color: var(--color-teacher); }
.action-btn.edit:hover { background: var(--color-teacher-pale); }
.action-btn.export { color: var(--color-info); }
.action-btn.export:hover { background: var(--color-info-soft); }
.action-btn.delete { color: var(--color-error); }
.action-btn.delete:hover { background: var(--color-error-soft); }

.pagination-wrap {
  margin-top: 24px;
  display: flex;
  justify-content: flex-end;
}

:deep(.el-table) {
  border-radius: var(--radius-md);
  overflow: hidden;
}

:deep(.el-table th.el-table__cell) {
  background: var(--color-bg-page-2);
  color: var(--color-text-body);
  font-weight: 600;
  font-size: var(--text-sm);
  font-family: var(--font-serif);
  border-bottom: 2px solid var(--color-teacher-soft);
}

:deep(.el-table tr:hover > td) {
  background: var(--color-teacher-pale) !important;
}

:deep(.el-dialog) {
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-pop);
}

/* ── 知识树编辑器 ────────────────────────────── */

.knowledge-tree-editor {
  width: 100%;
  padding: 14px;
  background: var(--color-bg-card-soft);
  border: 1px dashed var(--color-border);
  border-radius: var(--radius-md);
}

.knowledge-tree-item {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 10px;
  padding: 8px 12px;
  background: var(--color-bg-card);
  border-radius: var(--radius-sm);
  border: 1px solid var(--color-border-light);
  transition: all var(--transition-fast);
}
.knowledge-tree-item:hover {
  border-color: var(--color-teacher-soft);
}

.knowledge-tree-empty {
  color: var(--color-text-muted);
  font-size: var(--text-sm);
  padding: 16px 0;
  text-align: center;
  font-style: italic;
}
</style>
