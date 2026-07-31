<template>
  <div class="admin-page">
    <div class="page-header">
      <h2 class="page-title">用户管理</h2>
      <p class="page-subtitle">管理平台用户账户、角色权限与账号状态</p>
    </div>

    <!-- 角色分布统计卡 -->
    <div class="role-stats">
      <div class="role-stat-card student">
        <div class="role-stat-icon">
          <el-icon><User /></el-icon>
        </div>
        <div class="role-stat-info">
          <span class="role-stat-num tabular">{{ roleCount.student }}</span>
          <span class="role-stat-label">学生</span>
        </div>
      </div>
      <div class="role-stat-card teacher">
        <div class="role-stat-icon">
          <el-icon><Reading /></el-icon>
        </div>
        <div class="role-stat-info">
          <span class="role-stat-num tabular">{{ roleCount.teacher }}</span>
          <span class="role-stat-label">教师</span>
        </div>
      </div>
      <div class="role-stat-card admin">
        <div class="role-stat-icon">
          <el-icon><Reading /></el-icon>
        </div>
        <div class="role-stat-info">
          <span class="role-stat-num tabular">{{ roleCount.admin }}</span>
          <span class="role-stat-label">管理员</span>
        </div>
      </div>
      <div class="role-stat-card total">
        <div class="role-stat-icon">
          <el-icon><UserFilled /></el-icon>
        </div>
        <div class="role-stat-info">
          <span class="role-stat-num tabular">{{ pagination.total || users.length }}</span>
          <span class="role-stat-label">总用户</span>
        </div>
      </div>
    </div>

    <el-card class="page-card" shadow="never">
      <template #header>
        <div class="card-header">
          <div class="card-header__left">
            <div class="card-header__mark">
              <el-icon class="card-header__icon"><UserFilled /></el-icon>
            </div>
            <div>
              <h3 class="card-header__title">用户列表</h3>
              <span class="card-header__subtitle">共 {{ pagination.total }} 条记录</span>
            </div>
          </div>
          <div class="card-header__right">
            <el-input
              v-model="searchText"
              placeholder="搜索用户名、姓名或邮箱"
              class="search-input"
              clearable
              @keyup.enter="handleSearch"
            >
              <template #prefix>
                <el-icon><Search /></el-icon>
              </template>
            </el-input>
            <el-button class="create-btn" @click="showAddModal">
              <el-icon><Plus /></el-icon> 新增用户
            </el-button>
          </div>
        </div>
      </template>

      <el-table :data="users" v-loading="loading" class="data-table">
        <el-table-column prop="id" label="ID" width="70">
          <template #default="{ row }">
            <span class="cell-id">#{{ row.id }}</span>
          </template>
        </el-table-column>
        <el-table-column label="用户" min-width="180">
          <template #default="{ row }">
            <div class="user-cell">
              <div class="user-avatar" :class="row.role">
                <span>{{ (row.real_name || row.username).charAt(0) }}</span>
              </div>
              <div class="user-meta">
                <span class="user-name">{{ row.real_name || row.username }}</span>
                <span class="user-username">@{{ row.username }}</span>
              </div>
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="email" label="邮箱" min-width="200">
          <template #default="{ row }">
            <span class="email-text">{{ row.email || '— 未填写 —' }}</span>
          </template>
        </el-table-column>
        <el-table-column label="角色" width="130" align="center">
          <template #default="{ row }">
            <span :class="['role-badge', row.role]">
              <span class="role-dot"></span>
              {{ getRoleText(row.role) }}
            </span>
          </template>
        </el-table-column>
        <el-table-column label="创建时间" width="180">
          <template #default="{ row }">
            <span class="time-text">{{ formatDate(row.created_at) }}</span>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="180" fixed="right" align="right">
          <template #default="{ row }">
            <div class="action-group">
              <el-button class="action-btn edit" link size="small" @click="showEditModal(row)">
                <el-icon><Edit /></el-icon> 编辑
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
          @current-change="handleCurrentChange"
        />
      </div>
    </el-card>

    <!-- 新增/编辑对话框 -->
    <el-dialog
      v-model="modalVisible"
      :title="isEdit ? '编辑用户' : '新增用户'"
      width="520px"
      class="custom-dialog"
    >
      <el-form
        ref="formRef"
        :model="formData"
        :rules="formRules"
        :label-width="80"
        label-position="left"
      >
        <el-form-item label="用户名" prop="username">
          <el-input v-model="formData.username" :disabled="isEdit" placeholder="请输入用户名" />
        </el-form-item>
        <el-form-item v-if="!isEdit" label="密码" prop="password">
          <el-input v-model="formData.password" placeholder="请输入密码" show-password />
        </el-form-item>
        <el-form-item label="真实姓名" prop="real_name">
          <el-input v-model="formData.real_name" placeholder="请输入真实姓名" />
        </el-form-item>
        <el-form-item label="邮箱" prop="email">
          <el-input v-model="formData.email" placeholder="请输入邮箱" />
        </el-form-item>
        <el-form-item label="角色" prop="role">
          <el-select v-model="formData.role" style="width: 100%">
            <el-option value="student" label="学生" />
            <el-option value="teacher" label="教师" />
            <el-option value="admin" label="管理员" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="modalVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitLoading" @click="handleSubmit">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox, type FormInstance, type FormRules } from 'element-plus'
import { adminAPI } from '@/api'
import { UserFilled, Search, Plus, Edit, Delete, User, Reading } from '@element-plus/icons-vue'

interface User {
  id: number
  username: string
  real_name: string
  email: string
  role: string
  created_at: string
}

interface FormData {
  username: string
  password: string
  real_name: string
  email: string
  role: string
}

const loading = ref(false)
const submitLoading = ref(false)
const modalVisible = ref(false)
const isEdit = ref(false)
const editingId = ref<number | null>(null)

const searchText = ref('')
const users = ref<User[]>([])
const pagination = reactive({
  current: 1,
  pageSize: 10,
  total: 0
})

const formRef = ref<FormInstance>()
const formData = reactive<FormData>({
  username: '',
  password: '',
  real_name: '',
  email: '',
  role: 'student'
})

const formRules: FormRules = {
  username: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
  password: [{
    required: true,
    validator: (_rule: any, _value: any, callback: any) => {
      if (!formData.password && !isEdit.value) {
        callback(new Error('请输入密码'))
      } else {
        callback()
      }
    },
    trigger: 'blur'
  }],
  role: [{ required: true, message: '请选择角色', trigger: 'change' }]
}

/* ── 计算属性 ────────────────────────────────── */

const roleCount = computed(() => {
  const count = { student: 0, teacher: 0, admin: 0 }
  for (const u of users.value) {
    if (u.role in count) (count as any)[u.role]++
  }
  return count
})

const getRoleText = (role: string): string => {
  const map: Record<string, string> = { student: '学生', teacher: '教师', admin: '管理员' }
  return map[role] || role
}

const getRoleTagType = (role: string): '' | 'info' | 'primary' | 'success' | 'warning' | 'danger' | 'text' => {
  const types: Record<string, '' | 'info' | 'primary' | 'success' | 'warning' | 'danger' | 'text'> = {
    student: 'info',
    teacher: 'success',
    admin: 'danger'
  }
  return types[role] || ''
}

const formatDate = (dateStr: string): string => {
  if (!dateStr) return '-'
  return new Date(dateStr).toLocaleString('zh-CN')
}

const fetchUsers = async () => {
  loading.value = true
  try {
    const response: any = await adminAPI.getUsers({
      page: pagination.current,
      page_size: pagination.pageSize,
      search: searchText.value || undefined
    })
    users.value = response.items
    pagination.total = response.total
  } catch (error) {
    ElMessage.error('获取用户列表失败')
  } finally {
    loading.value = false
  }
}

const handleSearch = () => {
  pagination.current = 1
  fetchUsers()
}

const handleSizeChange = (size: number) => {
  pagination.pageSize = size
  pagination.current = 1
  fetchUsers()
}

const handleCurrentChange = (current: number) => {
  pagination.current = current
  fetchUsers()
}

const showAddModal = () => {
  isEdit.value = false
  editingId.value = null
  Object.assign(formData, {
    username: '',
    password: '',
    real_name: '',
    email: '',
    role: 'student'
  })
  modalVisible.value = true
}

const showEditModal = (record: User) => {
  isEdit.value = true
  editingId.value = record.id
  Object.assign(formData, {
    username: record.username,
    password: '',
    real_name: record.real_name || '',
    email: record.email || '',
    role: record.role
  })
  modalVisible.value = true
}

const handleSubmit = async () => {
  if (!formRef.value) return

  try {
    await formRef.value.validate()
    submitLoading.value = true

    const submitData: Record<string, any> = { ...formData }
    if (!submitData.password) {
      delete submitData.password
    }

    if (isEdit.value && editingId.value) {
      await adminAPI.updateUser(editingId.value, submitData)
      ElMessage.success('用户更新成功')
    } else {
      await adminAPI.createUser(submitData)
      ElMessage.success('用户创建成功')
    }

    modalVisible.value = false
    fetchUsers()
  } catch (error: any) {
    if (!error.errorFields) {
      ElMessage.error(isEdit.value ? '更新失败' : '创建失败')
    }
  } finally {
    submitLoading.value = false
  }
}

const handleDelete = (record: User) => {
  ElMessageBox.confirm(
    `确定要删除用户 "${record.username}" 吗？`,
    '确认删除',
    {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    }
  ).then(async () => {
    try {
      await adminAPI.deleteUser(record.id)
      ElMessage.success('删除成功')
      fetchUsers()
    } catch (error) {
      ElMessage.error('删除失败')
    }
  }).catch(() => {})
}

onMounted(() => {
  fetchUsers()
})
</script>

<style scoped>
/* ── 页面基础 ────────────────────────────────── */

.admin-page {
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
  background: linear-gradient(180deg, var(--color-admin), var(--color-admin-soft));
  border-radius: 5px;
}

.page-subtitle {
  margin: 8px 0 0 0;
  padding-left: 16px;
  font-size: var(--text-sm);
  color: var(--color-text-muted);
  letter-spacing: 0.01em;
}

/* ── 角色统计卡 ──────────────────────────────── */

.role-stats {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
  margin-bottom: var(--space-card-gap);
}

.role-stat-card {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 18px 20px;
  background: var(--color-bg-card);
  border-radius: var(--radius-lg);
  border: 1px solid var(--color-border-light);
  box-shadow: var(--shadow-card);
  transition: all var(--transition-normal);
  position: relative;
  overflow: hidden;
}
.role-stat-card::before {
  content: '';
  position: absolute;
  left: 0; top: 0; bottom: 0;
  width: 4px;
}
.role-stat-card:hover {
  transform: translateY(-2px);
  box-shadow: var(--shadow-card-hover);
}

.role-stat-card.student::before { background: var(--color-student); }
.role-stat-card.teacher::before { background: var(--color-teacher); }
.role-stat-card.admin::before   { background: var(--color-admin); }
.role-stat-card.total::before   { background: var(--color-primary); }

.role-stat-icon {
  width: 44px; height: 44px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  font-size: 20px;
  color: #fff;
}
.role-stat-card.student .role-stat-icon { background: linear-gradient(135deg, var(--color-student), #D17A52); }
.role-stat-card.teacher .role-stat-icon { background: linear-gradient(135deg, var(--color-teacher), #5A8E6E); }
.role-stat-card.admin   .role-stat-icon { background: linear-gradient(135deg, var(--color-admin), #9C4458); }
.role-stat-card.total   .role-stat-icon { background: linear-gradient(135deg, var(--color-primary-deep), var(--color-primary-soft)); }

.role-stat-info {
  display: flex;
  flex-direction: column;
  line-height: 1.2;
}

.role-stat-num {
  font-family: var(--font-serif);
  font-size: var(--text-3xl);
  font-weight: 700;
  color: var(--color-text-ink);
}
.tabular { font-variant-numeric: tabular-nums; }

.role-stat-label {
  font-size: var(--text-sm);
  color: var(--color-text-muted);
  font-weight: 500;
  margin-top: 4px;
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
  background: linear-gradient(135deg, var(--color-admin), #9C4458);
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 2px 8px rgba(112, 41, 60, 0.2);
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
  width: 280px;
}
.search-input :deep(.el-input__wrapper) {
  border-radius: 10px;
  box-shadow: 0 0 0 1px var(--color-border);
  transition: all var(--transition-fast);
}
.search-input :deep(.el-input__wrapper:hover) {
  box-shadow: 0 0 0 1px var(--color-admin-soft);
}
.search-input :deep(.el-input__wrapper.is-focus) {
  box-shadow: 0 0 0 1px var(--color-admin);
}

.create-btn {
  background: var(--color-admin);
  border: none;
  font-weight: 500;
  padding: 0 20px;
  border-radius: 10px;
  transition: all var(--transition-fast);
  color: #fff;
}
.create-btn:hover {
  background: #581E2E !important;
  transform: translateY(-1px);
  box-shadow: 0 4px 14px rgba(112, 41, 60, 0.3);
  color: #fff !important;
}

/* ── 表格 ────────────────────────────────────── */

.cell-id {
  font-family: var(--font-mono);
  font-size: var(--text-sm);
  color: var(--color-text-muted);
  font-weight: 500;
}

.user-cell {
  display: flex;
  align-items: center;
  gap: 10px;
}

.user-avatar {
  width: 36px; height: 36px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  font-weight: 600;
  font-size: var(--text-md);
  flex-shrink: 0;
  box-shadow: 0 2px 6px rgba(0,0,0,0.08);
}
.user-avatar.student { background: linear-gradient(135deg, var(--color-student), #D17A52); }
.user-avatar.teacher { background: linear-gradient(135deg, var(--color-teacher), #5A8E6E); }
.user-avatar.admin   { background: linear-gradient(135deg, var(--color-admin), #9C4458); }

.user-meta {
  display: flex;
  flex-direction: column;
  line-height: 1.3;
}
.user-name {
  font-weight: 600;
  color: var(--color-text-body);
  font-size: var(--text-base);
}
.user-username {
  font-size: var(--text-xs);
  color: var(--color-text-muted);
  font-family: var(--font-mono);
}

.email-text {
  color: var(--color-text-muted);
  font-size: var(--text-sm);
}

.role-badge {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 5px 12px;
  border-radius: var(--radius-full);
  font-size: var(--text-xs);
  font-weight: 600;
  letter-spacing: 0.02em;
}
.role-badge .role-dot {
  width: 6px; height: 6px;
  border-radius: 50%;
}
.role-badge.student {
  background: var(--color-student-pale);
  color: var(--color-student);
}
.role-badge.student .role-dot { background: var(--color-student); }
.role-badge.teacher {
  background: var(--color-teacher-pale);
  color: var(--color-teacher);
}
.role-badge.teacher .role-dot { background: var(--color-teacher); }
.role-badge.admin {
  background: var(--color-admin-pale);
  color: var(--color-admin);
}
.role-badge.admin .role-dot { background: var(--color-admin); }

.time-text {
  color: var(--color-text-muted);
  font-size: var(--text-xs);
  font-family: var(--font-mono);
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
.action-btn.edit   { color: var(--color-admin); }
.action-btn.edit:hover   { background: var(--color-admin-pale); }
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
  border-bottom: 2px solid var(--color-admin-soft);
}

:deep(.el-table tr:hover > td) {
  background: var(--color-admin-pale) !important;
}

:deep(.el-dialog) {
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-pop);
}

/* ── 响应式 ──────────────────────────────────── */

@media (max-width: 960px) {
  .role-stats {
    grid-template-columns: repeat(2, 1fr);
  }
}
@media (max-width: 560px) {
  .role-stats {
    grid-template-columns: 1fr;
  }
}
</style>
