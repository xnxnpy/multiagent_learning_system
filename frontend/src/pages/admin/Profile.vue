<template>
  <div class="page-container">
    <el-card class="page-card profile-card">
      <template #header>
        <div class="card-header">
          <el-icon class="card-header__icon"><User /></el-icon>
          <h2 class="card-header__title">个人中心</h2>
        </div>
      </template>

      <el-tabs v-model="activeTab" class="profile-tabs">
        <!-- 基本信息 Tab -->
        <el-tab-pane label="基本信息" name="info">
          <el-form
            ref="profileFormRef"
            :model="profileForm"
            :rules="profileRules"
            @submit.prevent="handleUpdateProfile"
            label-position="top"
            class="profile-form"
          >
            <el-row :gutter="24">
              <el-col :span="12">
                <el-form-item label="用户名">
                  <el-input v-model="profileForm.username" disabled class="disabled-input" />
                </el-form-item>
              </el-col>
              <el-col :span="12">
                <el-form-item label="角色">
                  <el-input v-model="profileForm.role_text" disabled class="disabled-input" />
                </el-form-item>
              </el-col>
            </el-row>
            <el-row :gutter="24">
              <el-col :span="12">
                <el-form-item label="真实姓名" prop="real_name">
                  <el-input v-model="profileForm.real_name" placeholder="请输入真实姓名" />
                </el-form-item>
              </el-col>
              <el-col :span="12">
                <el-form-item label="邮箱" prop="email">
                  <el-input v-model="profileForm.email" placeholder="请输入邮箱" />
                </el-form-item>
              </el-col>
            </el-row>
            <el-form-item>
              <el-button type="primary" native-type="submit" :loading="loading" :disabled="!hasChanges">
                <el-icon><Check /></el-icon> 保存修改
              </el-button>
            </el-form-item>
          </el-form>
        </el-tab-pane>

        <!-- 修改密码 Tab -->
        <el-tab-pane label="修改密码" name="password">
          <el-form
            ref="passwordFormRef"
            :model="passwordForm"
            :rules="passwordRules"
            @submit.prevent="handleChangePassword"
            label-position="top"
            class="password-form"
          >
            <el-form-item label="旧密码" prop="old_password">
              <el-input
                v-model="passwordForm.old_password"
                type="password"
                placeholder="请输入旧密码"
                show-password
              />
            </el-form-item>
            <el-form-item label="新密码" prop="new_password">
              <el-input
                v-model="passwordForm.new_password"
                type="password"
                placeholder="请输入新密码（至少6个字符）"
                show-password
              />
            </el-form-item>
            <el-form-item label="确认新密码" prop="confirm_password">
              <el-input
                v-model="passwordForm.confirm_password"
                type="password"
                placeholder="请确认新密码"
                show-password
              />
            </el-form-item>
            <el-form-item>
              <el-button type="primary" native-type="submit" :loading="passwordLoading">
                <el-icon><Lock /></el-icon> 修改密码
              </el-button>
            </el-form-item>
          </el-form>
        </el-tab-pane>
      </el-tabs>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { reactive, ref, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { authAPI } from '@/api'
import { useUserStore } from '@/stores/userStore'
import { User, Check, Lock } from '@element-plus/icons-vue'

const userStore = useUserStore()

interface ProfileForm {
  username: string
  real_name: string
  email: string
  role: string
  role_text: string
}

interface PasswordForm {
  old_password: string
  new_password: string
  confirm_password: string
}

const activeTab = ref('info')
const loading = ref(false)
const passwordLoading = ref(false)
const profileFormRef = ref()
const passwordFormRef = ref()

const profileForm = reactive<ProfileForm>({
  username: '',
  real_name: '',
  email: '',
  role: '',
  role_text: ''
})

const originalProfile = reactive({
  real_name: '',
  email: ''
})

const hasChanges = computed(() => {
  return profileForm.real_name !== originalProfile.real_name ||
         profileForm.email !== originalProfile.email
})

const roleTextMap: Record<string, string> = {
  student: '学生',
  teacher: '教师',
  admin: '管理员'
}

const profileRules = {
  email: [{ type: 'email', message: '请输入有效的邮箱地址', trigger: 'blur' }]
}

const passwordForm = reactive<PasswordForm>({
  old_password: '',
  new_password: '',
  confirm_password: ''
})

const validateConfirmPassword = (_rule: any, value: string, callback: any) => {
  if (value !== passwordForm.new_password) {
    callback(new Error('两次输入的密码不一致'))
  } else {
    callback()
  }
}

const passwordRules = {
  old_password: [{ required: true, message: '请输入旧密码', trigger: 'blur' }],
  new_password: [
    { required: true, message: '请输入新密码', trigger: 'blur' },
    { min: 6, message: '密码长度至少 6 个字符', trigger: 'blur' }
  ],
  confirm_password: [
    { required: true, message: '请确认新密码', trigger: 'blur' },
    { validator: validateConfirmPassword, trigger: 'blur' }
  ]
}

onMounted(() => {
  userStore.initFromStorage()
  const user = userStore.user
  if (user) {
    profileForm.username = user.username
    profileForm.real_name = user.real_name || ''
    profileForm.email = user.email || ''
    profileForm.role = user.role
    profileForm.role_text = roleTextMap[user.role] || user.role

    originalProfile.real_name = user.real_name || ''
    originalProfile.email = user.email || ''
  }
})

const handleUpdateProfile = async () => {
  loading.value = true
  try {
    await authAPI.updateProfile({
      real_name: profileForm.real_name,
      email: profileForm.email
    })
    ElMessage.success('个人信息更新成功')
    const res: any = await authAPI.getCurrentUser()
    userStore.setUser(res)
    originalProfile.real_name = profileForm.real_name
    originalProfile.email = profileForm.email
  } catch (error) {
    ElMessage.error('更新失败')
  } finally {
    loading.value = false
  }
}

const handleChangePassword = async () => {
  passwordLoading.value = true
  try {
    await authAPI.changePassword({
      old_password: passwordForm.old_password,
      new_password: passwordForm.new_password
    })
    ElMessage.success('密码修改成功')
    passwordForm.old_password = ''
    passwordForm.new_password = ''
    passwordForm.confirm_password = ''
  } catch (error) {
    ElMessage.error('密码修改失败')
  } finally {
    passwordLoading.value = false
  }
}
</script>

<style scoped>
.page-container {
  padding: 24px;
  background: var(--color-bg-page);
  min-height: 100%;
  display: flex;
  justify-content: center;
}

.profile-card {
  width: 100%;
  max-width: 860px;
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-card);
}

.card-header {
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

.profile-tabs :deep(.el-tabs__item) {
  font-size: 15px;
  font-weight: 500;
}

.profile-tabs :deep(.el-tabs__active-bar) {
  background-color: var(--color-primary);
}

.profile-form,
.password-form {
  max-width: 600px;
  padding-top: 8px;
}

.disabled-input :deep(.el-input__wrapper) {
  background: var(--color-bg-page);
}

:deep(.el-dialog) {
  border-radius: var(--radius-lg);
}
</style>
