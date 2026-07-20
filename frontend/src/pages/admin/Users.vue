<template>
  <div class="page-container">
    <el-card class="page-card">
      <template #header>
        <div class="card-header">
          <div class="card-header__left">
            <el-icon class="card-header__icon"><UserFilled /></el-icon>
            <h2 class="card-header__title">用户管理</h2>
          </div>
          <div class="card-header__right">
            <el-input
              v-model="searchText"
              placeholder="搜索用户名、姓名或邮箱"
              style="width: 240px"
              clearable
              @keyup.enter="handleSearch"
            >
              <template #prefix>
                <el-icon><Search /></el-icon>
              </template>
            </el-input>
            <el-button type="primary" @click="showAddModal">
              <el-icon><Plus /></el-icon> 新增用户
            </el-button>
          </div>
        </div>
      </template>

      <el-table :data="users" v-loading="loading" stripe class="data-table">
        <el-table-column prop="id" label="ID" width="70" />
        <el-table-column prop="username" label="用户名" min-width="120" />
        <el-table-column prop="real_name" label="真实姓名" min-width="120" />
        <el-table-column prop="email" label="邮箱" min-width="180">
          <template #default="{ row }">
            <span class="email-text">{{ row.email || '-' }}</span>
          </template>
        </el-table-column>
        <el-table-column label="角色" width="100" align="center">
          <template #default="{ row }">
            <el-tag :type="getRoleTagType(row.role)" effect="light" round>
              {{ getRoleText(row.role) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="创建时间" width="170">
          <template #default="{ row }">
            <span class="time-text">{{ formatDate(row.created_at) }}</span>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="150" fixed="right">
          <template #default="{ row }">
            <el-button type="primary" link size="small" @click="showEditModal(row)">
              <el-icon><Edit /></el-icon> 编辑
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
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox, type FormInstance, type FormRules } from 'element-plus'
import { adminAPI } from '@/api'
import { UserFilled, Search, Plus, Edit, Delete } from '@element-plus/icons-vue'

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

.email-text {
  color: var(--color-text-secondary);
  font-size: 13px;
}

.time-text {
  color: var(--color-text-muted);
  font-size: 13px;
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

:deep(.el-dialog) {
  border-radius: var(--radius-lg);
}
</style>
