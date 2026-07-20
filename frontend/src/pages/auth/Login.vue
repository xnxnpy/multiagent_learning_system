<template>
  <div class="auth-page">
    <!-- Left brand panel -->
    <div class="brand-panel">
      <div class="brand-content">
        <div class="brand-icon">
          <el-icon :size="48"><Cpu /></el-icon>
        </div>
        <h1 class="brand-title">智学优培</h1>
        <p class="brand-subtitle">基于大模型多模态生成的高校个性化学习智能体平台</p>
        <div class="brand-features">
          <div class="feature-item">
            <el-icon><DataAnalysis /></el-icon>
            <span>智能画像分析</span>
          </div>
          <div class="feature-item">
            <el-icon><MapLocation /></el-icon>
            <span>个性化学习路径</span>
          </div>
          <div class="feature-item">
            <el-icon><MagicStick /></el-icon>
            <span>AI 个性化学习资源生成</span>
          </div>
          <div class="feature-item">
            <el-icon><ChatDotRound /></el-icon>
            <span>RAG 智能辅导</span>
          </div>
        </div>
      </div>
    </div>

    <!-- Right form panel -->
    <div class="form-panel">
      <div class="form-container">
        <div class="form-header">
          <h2>欢迎回来</h2>
          <p>登录您的账号以继续学习</p>
        </div>

        <el-form ref="formRef" :model="form" :rules="rules" label-position="top" size="large" @submit.prevent="handleLogin">
          <el-form-item label="用户名" prop="username">
            <el-input v-model="form.username" placeholder="请输入用户名" :prefix-icon="User" />
          </el-form-item>
          <el-form-item label="密码" prop="password">
            <el-input v-model="form.password" type="password" placeholder="请输入密码" :prefix-icon="Lock" show-password @keyup.enter="handleLogin" />
          </el-form-item>
          <el-form-item>
            <el-button type="primary" :loading="loading" class="submit-btn" @click="handleLogin">
              登录
            </el-button>
          </el-form-item>
        </el-form>

        <p class="form-footer">
          还没有账号？<router-link to="/register">立即注册</router-link>
        </p>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { User, Lock, Cpu, DataAnalysis, MapLocation, MagicStick, ChatDotRound } from '@element-plus/icons-vue'
import { useUserStore } from '@/stores/userStore'
import { authAPI } from '@/api'
import type { FormInstance } from 'element-plus'

const router = useRouter()
const userStore = useUserStore()
const formRef = ref<FormInstance>()
const loading = ref(false)

const form = reactive({
  username: '',
  password: '',
})

const rules = {
  username: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
  password: [{ required: true, message: '请输入密码', trigger: 'blur' }],
}

async function handleLogin() {
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) return

  loading.value = true
  try {
    const res = await authAPI.login(form)
    userStore.login(res.access_token, res.user)
    ElMessage.success('登录成功')

    const roleRedirects: Record<string, string> = {
      student: '/student',
      teacher: '/teacher',
      admin: '/admin',
    }
    router.push(roleRedirects[res.user.role] || '/student')
  } catch (err: any) {
    ElMessage.error(err?.response?.data?.detail || '登录失败，请检查用户名和密码')
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.auth-page {
  display: flex;
  min-height: 100vh;
  background: var(--color-bg-page);
}

/* ── 品牌面板 ─────────────────────────── */
.brand-panel {
  flex: 0 0 50%;
  background: linear-gradient(135deg, #0F172A 0%, #1E3A5F 50%, #1E40AF 100%);
  display: flex;
  flex-direction: column;
  justify-content: center;
  padding: 60px 48px;
  position: relative;
  overflow: hidden;
}

.brand-panel::before {
  content: '';
  position: absolute;
  top: -20%;
  right: -10%;
  width: 400px;
  height: 400px;
  background: radial-gradient(circle, rgba(59, 130, 246, 0.15) 0%, transparent 70%);
  border-radius: 50%;
}

.brand-icon {
  width: 80px;
  height: 80px;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.12);
  backdrop-filter: blur(12px);
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 24px;
  box-shadow: 0 0 40px rgba(59, 130, 246, 0.2);
}

.brand-icon .el-icon {
  color: #fff;
}

.brand-title {
  font-size: 32px;
  font-weight: 800;
  color: #fff;
  margin-bottom: 12px;
  letter-spacing: -0.5px;
}

.brand-subtitle {
  font-size: var(--text-lg);
  color: rgba(255, 255, 255, 0.7);
  line-height: 1.6;
  margin-bottom: 40px;
}

.brand-features {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.feature-item {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 14px 18px;
  color: #fff;
  background: rgba(255, 255, 255, 0.08);
  border-radius: 10px;
  backdrop-filter: blur(10px);
}

.feature-icon {
  font-size: 28px;
  flex-shrink: 0;
}

.feature-text {
  display: flex;
  flex-direction: column;
}

.feature-label {
  font-size: 15px;
  font-weight: 600;
  color: #fff;
}

.feature-desc {
  font-size: var(--text-xs);
  color: rgba(255, 255, 255, 0.6);
  margin-top: 2px;
}

/* ── 表单面板 ─────────────────────────── */
.form-panel {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 40px;
  background: linear-gradient(180deg, #FAFBFC 0%, #FFFFFF 100%);
}

.form-container {
  width: 100%;
  max-width: 380px;
}

.form-header {
  margin-bottom: 32px;
}

.form-header h2 {
  font-size: 24px;
  font-weight: 700;
  color: var(--color-text-primary);
  margin-bottom: 8px;
}

.form-header p {
  font-size: var(--text-base);
  color: var(--color-text-muted);
}

.login-form {
  margin-bottom: 24px;
}

.login-form :deep(.el-form-item__label) {
  font-weight: 500;
  color: var(--color-text-secondary);
  font-size: var(--text-sm);
}

.login-form :deep(.el-input__wrapper) {
  border-radius: 8px;
  box-shadow: 0 0 0 1px var(--color-border);
  padding: 4px 12px;
  transition: all 0.2s;
}

.login-form :deep(.el-input__wrapper:hover) {
  box-shadow: 0 0 0 1px var(--color-border);
}

.login-form :deep(.el-input__wrapper.is-focus) {
  box-shadow: 0 0 0 2px rgba(30, 64, 175, 0.2);
}

.login-btn {
  width: 100%;
  height: 44px;
  font-size: 15px;
  font-weight: 600;
  border-radius: 10px;
  letter-spacing: 0.5px;
  background: linear-gradient(135deg, var(--color-primary), var(--color-primary-dark));
  border: none;
  box-shadow: 0 4px 14px rgba(30, 64, 175, 0.3);
  transition: all var(--transition-fast);
}

.login-btn:hover {
  transform: translateY(-1px);
  box-shadow: 0 6px 20px rgba(30, 64, 175, 0.4);
}

.form-footer {
  text-align: center;
  font-size: var(--text-sm);
  color: var(--color-text-muted);
}

.form-footer a {
  color: var(--color-primary);
  text-decoration: none;
  font-weight: 500;
  transition: color 0.2s;
}

.form-footer a:hover {
  color: var(--color-primary-dark);
}

/* ── 响应式 ───────────────────────────── */
@media (max-width: 768px) {
  .brand-panel {
    display: none;
  }
  .form-panel {
    padding: 24px;
  }
}
</style>
