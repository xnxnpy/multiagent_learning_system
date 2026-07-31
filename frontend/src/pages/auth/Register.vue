<template>
  <div class="auth-page">
    <!-- 左侧：品牌 + 角色预览 -->
    <div class="brand-panel">
      <div class="brand-grain"></div>
      <div class="brand-corner tl"></div>
      <div class="brand-corner br"></div>

      <div class="brand-content">
        <div class="brand-mark">
          <div class="brand-mark__sigil">
            <el-icon :size="24"><Reading /></el-icon>
          </div>
          <div class="brand-mark__name">
            <span class="eyebrow">EDU · MULTI-AGENT</span>
            <span class="brand-name">智学优培</span>
          </div>
        </div>

        <div class="hero-block">
          <h1 class="hero-title display-serif">
            <span class="line-1">开始</span>
            <span class="line-2">您的学习</span>
          </h1>
          <p class="hero-sub">
            注册即开通专属账号，14 个智能体将为您量身定制个性化学习方案，
            从画像到资源到辅导，一站式全流程 AI 辅助。
          </p>
        </div>

        <!-- 角色预览卡片（非玻璃拟态） -->
        <div class="role-preview">
          <div class="role-card role-card--student" :class="{ active: form.role === 'student' }"
               @click="form.role = 'student'">
            <div class="role-card__dot"></div>
            <div class="role-card__body">
              <div class="role-card__label">学生端</div>
              <div class="role-card__desc">专属学习路径 · 多模态资源 · AI 辅导</div>
            </div>
          </div>
          <div class="role-card role-card--teacher" :class="{ active: form.role === 'teacher' }"
               @click="form.role = 'teacher'">
            <div class="role-card__dot"></div>
            <div class="role-card__body">
              <div class="role-card__label">教师端</div>
              <div class="role-card__desc">课程管理 · 资源审核 · 班级学情</div>
            </div>
          </div>
        </div>

        <div class="brand-foot">
          <el-icon :size="12"><Lock /></el-icon>
          <span>全链路数据加密，隐私保障</span>
        </div>
      </div>
    </div>

    <!-- 右侧：注册表单 -->
    <div class="form-panel">
      <div class="form-veil"></div>
      <div class="form-scroll">
        <div class="form-wrap">
          <router-link to="/" class="back-home">
            <el-icon :size="14"><ArrowLeft /></el-icon>
            返回首页
          </router-link>

          <div class="form-hero">
            <div class="form-eyebrow eyebrow">ACCOUNT · 注册</div>
            <h2 class="form-title">创建您的账号</h2>
            <p class="form-sub">注册后即可开启个性化学习之旅。</p>
          </div>

          <el-form ref="formRef" :model="form" :rules="rules" label-position="top" class="auth-form" @submit.prevent="handleRegister">
            <div class="form-grid">
              <el-form-item label="用户名" prop="username" class="field-item">
                <el-input v-model="form.username" placeholder="3-50 个字符" :prefix-icon="User" class="field-input" />
              </el-form-item>
              <el-form-item label="真实姓名" prop="real_name" class="field-item">
                <el-input v-model="form.real_name" placeholder="请输入真实姓名" :prefix-icon="UserFilled" class="field-input" />
              </el-form-item>
            </div>

            <el-form-item label="邮箱" prop="email" class="field-item">
              <el-input v-model="form.email" placeholder="your@email.com" :prefix-icon="Message" class="field-input" />
            </el-form-item>

            <el-form-item label="角色选择" prop="role" class="field-item">
              <el-radio-group v-model="form.role" class="role-radio">
                <el-radio-button value="student" class="role-radio__btn role-radio__btn--student">
                  <span class="role-radio__label">
                    <span class="r-dot"></span>学生
                  </span>
                </el-radio-button>
                <el-radio-button value="teacher" class="role-radio__btn role-radio__btn--teacher">
                  <span class="role-radio__label">
                    <span class="r-dot"></span>教师
                  </span>
                </el-radio-button>
              </el-radio-group>
            </el-form-item>

            <div class="form-grid">
              <el-form-item label="密码" prop="password" class="field-item">
                <el-input v-model="form.password" type="password" placeholder="至少 6 位" :prefix-icon="Lock" show-password class="field-input" />
              </el-form-item>
              <el-form-item label="确认密码" prop="confirmPassword" class="field-item">
                <el-input v-model="form.confirmPassword" type="password" placeholder="再次输入密码" :prefix-icon="Lock" show-password class="field-input" />
              </el-form-item>
            </div>

            <el-form-item class="field-item" style="margin-top: 4px;">
              <el-button type="primary" :loading="loading" class="submit-btn" @click="handleRegister">
                <span>创建账号</span>
                <el-icon><ArrowRight /></el-icon>
              </el-button>
            </el-form-item>
          </el-form>

          <div class="form-divider">
            <span>已有账号</span>
          </div>

          <div class="form-foot">
            <p class="foot-text">
              已注册账号？
              <router-link to="/login" class="foot-link">去登录 →</router-link>
            </p>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import {
  User, UserFilled, Lock, Message, ArrowLeft, ArrowRight, Reading,
} from '@element-plus/icons-vue'
import { authAPI } from '@/api'
import type { FormInstance } from 'element-plus'

const router = useRouter()
const formRef = ref<FormInstance>()
const loading = ref(false)

const form = reactive({
  username: '',
  real_name: '',
  email: '',
  password: '',
  confirmPassword: '',
  role: 'student' as 'student' | 'teacher',
})

const validateConfirm = (_rule: any, value: string, callback: any) => {
  if (value !== form.password) {
    callback(new Error('两次输入的密码不一致'))
  } else {
    callback()
  }
}

const rules = {
  username: [
    { required: true, message: '请输入用户名', trigger: 'blur' },
    { min: 3, max: 50, message: '用户名长度在 3 到 50 个字符', trigger: 'blur' },
  ],
  real_name: [{ required: true, message: '请输入真实姓名', trigger: 'blur' }],
  email: [
    { required: true, message: '请输入邮箱', trigger: 'blur' },
    { type: 'email' as const, message: '请输入有效的邮箱地址', trigger: 'blur' },
  ],
  role: [{ required: true, message: '请选择角色', trigger: 'change' }],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 6, message: '密码长度至少 6 位', trigger: 'blur' },
  ],
  confirmPassword: [
    { required: true, message: '请再次输入密码', trigger: 'blur' },
    { validator: validateConfirm, trigger: 'blur' },
  ],
}

async function handleRegister() {
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) return

  loading.value = true
  try {
    await authAPI.register({
      username: form.username,
      password: form.password,
      real_name: form.real_name,
      email: form.email,
      role: form.role,
    })
    ElMessage.success('注册成功！请登录')
    router.push('/login')
  } catch (err: any) {
    ElMessage.error(err?.response?.data?.detail || '注册失败')
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

/* ═══════════════════ 左侧品牌区 ═══════════════════ */

.brand-panel {
  flex: 0 0 48%;
  background:
    linear-gradient(160deg, #FDFBF7 0%, #F6F1E7 40%, #F0E9DA 100%);
  position: relative;
  overflow: hidden;
  padding: 48px 52px;
  display: flex;
  flex-direction: column;
}

/* 左上柔和光晕装饰 */
.brand-panel::before {
  content: '';
  position: absolute;
  top: -15%; left: -10%;
  width: 320px; height: 320px;
  background: radial-gradient(circle, rgba(176, 81, 44, 0.07) 0%, transparent 70%);
  pointer-events: none;
}
/* 右下装饰 */
.brand-panel::after {
  content: '';
  position: absolute;
  bottom: -15%; right: -10%;
  width: 300px; height: 300px;
  background: radial-gradient(circle, rgba(61, 107, 79, 0.06) 0%, transparent 70%);
  pointer-events: none;
}

.brand-grain {
  position: absolute; inset: 0; pointer-events: none; opacity: 0.2;
  background-image: radial-gradient(rgba(43, 45, 66, 0.035) 1px, transparent 1px);
  background-size: 3px 3px;
}
.brand-corner {
  position: absolute; width: 52px; height: 52px;
  border: 1.5px solid rgba(43, 45, 66, 0.1);
  z-index: 1;
}
.brand-corner.tl { top: 28px; left: 28px; border-right: none; border-bottom: none; border-top-left-radius: 6px; }
.brand-corner.br { bottom: 28px; right: 28px; border-left: none; border-top: none; border-bottom-right-radius: 6px; }

.brand-content {
  position: relative; z-index: 1; flex: 1; display: flex; flex-direction: column;
}

.brand-mark {
  display: flex; align-items: center; gap: 14px; margin-bottom: 56px;
}
.brand-mark__sigil {
  width: 44px; height: 44px; border-radius: 12px;
  background: linear-gradient(135deg, var(--color-primary) 0%, var(--color-primary-deep) 100%);
  color: #fff; display: flex; align-items: center; justify-content: center;
  box-shadow: 0 4px 12px rgba(43, 45, 66, 0.15);
}
.brand-mark__name { display: flex; flex-direction: column; gap: 2px; }
.brand-mark__name .eyebrow { color: var(--color-text-muted); }
.brand-name {
  font-family: var(--font-serif); font-size: 22px; font-weight: 600;
  color: var(--color-text-ink); letter-spacing: 0.02em; line-height: 1;
}

/* Hero */
.hero-block { margin-bottom: 40px; max-width: 480px; }
.hero-title {
  font-size: clamp(40px, 4.8vw, 64px);
  color: var(--color-text-ink); font-weight: 600; line-height: 1.05;
  margin-bottom: 18px; display: flex; flex-direction: column; gap: 4px;
}
.hero-title .line-1 { display: block; }
.hero-title .line-2 {
  display: block;
  background: linear-gradient(90deg, #3D6B4F 0%, #2B2D42 100%);
  -webkit-background-clip: text; background-clip: text;
  -webkit-text-fill-color: transparent;
  font-style: italic;
}
.hero-sub {
  font-size: 14.5px; line-height: 1.8;
  color: var(--color-text-muted); max-width: 440px;
}

/* 角色预览卡片 */
.role-preview {
  display: flex; flex-direction: column; gap: 12px;
  max-width: 420px; margin-bottom: auto;
}
.role-card {
  display: flex; align-items: center; gap: 12px;
  padding: 14px 16px;
  background: rgba(255, 255, 255, 0.85);
  backdrop-filter: blur(8px);
  border: 1px solid var(--color-border-light);
  border-radius: 12px; cursor: pointer;
  transition: all 0.25s var(--ease-editing);
  position: relative; overflow: hidden;
}
.role-card::before {
  content: ''; position: absolute; left: 0; top: 0; bottom: 0; width: 3px;
  opacity: 0.5; transition: opacity 0.25s;
  border-radius: 3px 0 0 3px;
}
.role-card:hover {
  background: #fff; transform: translateX(3px);
  box-shadow: 0 4px 14px rgba(29, 31, 51, 0.06);
}
.role-card.active {
  border-color: var(--color-primary);
  box-shadow: 0 4px 14px rgba(29, 31, 51, 0.08);
}
.role-card.active::before { opacity: 1; }
.role-card--student::before { background: #B0512C; }
.role-card--teacher::before { background: #3D6B4F; }
.role-card__dot {
  width: 30px; height: 30px; border-radius: 9px;
  display: flex; align-items: center; justify-content: center;
  flex-shrink: 0;
}
.role-card__dot::after {
  content: ''; width: 8px; height: 8px; border-radius: 50%;
}
.role-card--student .role-card__dot {
  background: rgba(176, 81, 44, 0.12);
}
.role-card--student .role-card__dot::after { background: #B0512C; }
.role-card--teacher .role-card__dot {
  background: rgba(61, 107, 79, 0.14);
}
.role-card--teacher .role-card__dot::after { background: #3D6B4F; }

.role-card__body { flex: 1; min-width: 0; }
.role-card__label {
  font-size: 14.5px; font-weight: 600; color: var(--color-text-ink); line-height: 1.25;
}
.role-card__desc {
  font-size: 12px; color: var(--color-text-muted);
  margin-top: 3px; letter-spacing: 0.01em;
}

.brand-foot {
  display: inline-flex; align-items: center; gap: 9px;
  font-size: 12px; color: var(--color-text-muted); letter-spacing: 0.04em;
  margin-top: 32px; padding: 8px 14px;
  border: 1px solid var(--color-border-light);
  border-radius: 999px; align-self: flex-start;
  background: rgba(255, 255, 255, 0.6);
}

/* ═══════════════════ 右侧表单区 ═══════════════════ */

.form-panel {
  flex: 1; position: relative; background: var(--color-bg-page); overflow: hidden;
}
.form-veil {
  position: absolute; top: -10%; right: -5%;
  width: 520px; height: 520px;
  background: radial-gradient(circle, rgba(43, 45, 66, 0.04) 0%, transparent 70%);
  pointer-events: none;
}
.form-scroll {
  position: relative; height: 100vh; overflow-y: auto;
  display: flex; align-items: center; justify-content: center;
  padding: 40px 32px;
}
.form-wrap {
  width: 100%; max-width: 460px;
  background: #fff;
  border-radius: 20px;
  padding: 40px 36px 32px;
  box-shadow: 
    0 4px 24px rgba(29, 31, 51, 0.06),
    0 1px 3px rgba(29, 31, 51, 0.04);
  border: 1px solid var(--color-border-light);
  position: relative;
}
.form-wrap::before {
  content: '';
  position: absolute;
  top: 0; left: 28px; right: 28px;
  height: 3px;
  background: linear-gradient(90deg, #3D6B4F, #2B2D42, transparent);
  border-radius: 0 0 3px 3px;
}

.back-home {
  display: inline-flex; align-items: center; gap: 6px;
  font-size: 12.5px; color: var(--color-text-muted);
  text-decoration: none; font-weight: 500;
  padding: 6px 10px; border-radius: 8px; transition: all 0.2s;
  margin-bottom: 28px;
}
.back-home:hover { color: var(--color-primary); background: var(--color-bg-page); }

.form-hero { margin-bottom: 28px; text-align: center; }
.form-hero .form-eyebrow { margin-bottom: 12px; display: block; }
.form-title {
  font-size: 28px; font-weight: 700; color: var(--color-text-ink);
  letter-spacing: -0.02em; line-height: 1.2; margin-bottom: 10px;
  font-family: var(--font-serif);
}
.form-sub { font-size: 14px; color: var(--color-text-muted); line-height: 1.6; }

/* 表单 */
.auth-form { margin-bottom: 4px; }

.form-grid {
  display: grid; grid-template-columns: 1fr 1fr; gap: 0 20px;
}

.field-item { margin-bottom: 18px; }
.field-item :deep(.el-form-item__label) {
  font-size: 13px; font-weight: 600; color: var(--color-text-body);
  letter-spacing: 0.01em; padding-bottom: 7px !important; line-height: 1;
}

.field-input :deep(.el-input__wrapper) {
  border-radius: 12px;
  box-shadow: 0 0 0 1.5px var(--color-border) inset;
  padding: 6px 14px; background: #fff;
  transition: all 0.2s var(--ease-editing);
  font-size: 14.5px;
}
.field-input :deep(.el-input__wrapper:hover) {
  box-shadow: 0 0 0 1.5px var(--color-border-strong) inset;
}
.field-input :deep(.el-input__wrapper.is-focus) {
  box-shadow:
    0 0 0 2px rgba(43, 45, 66, 0.12) inset,
    0 0 0 1px var(--color-primary) inset;
}
.field-input :deep(.el-input__inner) {
  color: var(--color-text-ink); font-weight: 500;
}
.field-input :deep(.el-input__prefix-inner .el-icon) {
  color: var(--color-text-faint);
}

/* 角色单选（编辑风，无默认蓝） */
.role-radio {
  display: flex; width: 100%; gap: 10px;
}
.role-radio :deep(.el-radio-button__inner) {
  border-radius: 12px !important;
  padding: 12px 20px !important;
  border: 1.5px solid var(--color-border) !important;
  background: #fff !important;
  color: var(--color-text-muted) !important;
  font-size: 14px !important;
  font-weight: 500 !important;
  box-shadow: none !important;
  transition: all 0.22s var(--ease-editing);
  margin: 0 !important;
}
.role-radio :deep(.el-radio-button) { border: none !important; margin: 0 !important; }
.role-radio__btn { flex: 1; }
.role-radio__btn :deep(.el-radio-button__original-radio:checked + .el-radio-button__inner) {
  color: #fff !important;
  border-color: transparent !important;
}
.role-radio__btn--student :deep(.el-radio-button__original-radio:checked + .el-radio-button__inner) {
  background: #B0512C !important;
  box-shadow: 0 4px 14px rgba(176, 81, 44, 0.28) !important;
}
.role-radio__btn--teacher :deep(.el-radio-button__original-radio:checked + .el-radio-button__inner) {
  background: #3D6B4F !important;
  box-shadow: 0 4px 14px rgba(61, 107, 79, 0.28) !important;
}
.role-radio__label {
  display: inline-flex; align-items: center; gap: 7px;
}
.r-dot {
  width: 6px; height: 6px; border-radius: 50%;
  background: currentColor; opacity: 0.7;
}

/* 提交按钮 */
.submit-btn {
  width: 100%; height: 48px; border-radius: 12px;
  background: linear-gradient(135deg, #3D6B4F 0%, #2B2D42 100%);
  border: none;
  color: #fff; font-size: 15px; font-weight: 600;
  letter-spacing: 0.02em;
  display: flex; align-items: center; justify-content: center; gap: 8px;
  box-shadow: 0 4px 14px rgba(61, 107, 79, 0.2);
  transition: all 0.28s var(--ease-editing);
}
.submit-btn:hover {
  background: linear-gradient(135deg, #2F5440 0%, #1D1F33 100%) !important;
  transform: translateY(-2px);
  box-shadow: 0 8px 22px rgba(61, 107, 79, 0.3);
}
.submit-btn .el-icon { transition: transform 0.28s var(--ease-editing); }
.submit-btn:hover .el-icon { transform: translateX(3px); }

/* 分割线 */
.form-divider {
  margin: 24px 0 18px;
  display: flex; align-items: center; gap: 14px;
}
.form-divider::before,
.form-divider::after {
  content: ''; flex: 1; height: 1px;
  background: linear-gradient(90deg, transparent, var(--color-border), transparent);
}
.form-divider span {
  font-size: 11px; color: var(--color-text-faint);
  letter-spacing: 0.12em; text-transform: uppercase; font-weight: 600;
}

.foot-text {
  text-align: center; font-size: 14px; color: var(--color-text-muted);
}
.foot-link {
  color: var(--color-primary); font-weight: 600;
  text-decoration: none; margin-left: 4px;
  transition: all 0.2s; display: inline-block;
}
.foot-link:hover {
  color: var(--color-primary-deep); transform: translateX(2px);
}

/* 响应式 */
@media (max-width: 1100px) {
  .form-grid { grid-template-columns: 1fr; gap: 0; }
}
@media (max-width: 960px) {
  .auth-page { flex-direction: column; }
  .brand-panel {
    flex: none; padding: 36px 28px; min-height: auto;
  }
  .hero-title { font-size: 38px; }
  .hero-block { margin-bottom: 28px; }
  .brand-mark { margin-bottom: 36px; }
  .role-preview { margin-bottom: 0; }
  .brand-foot { margin-top: 24px; }
  .form-scroll { height: auto; min-height: 80vh; padding: 32px 20px; }
}
@media (max-width: 480px) {
  .brand-panel { padding: 28px 20px; }
  .hero-title { font-size: 32px; }
  .form-wrap { max-width: 100%; }
  .form-title { font-size: 28px; }
  .submit-btn { height: 48px; }
}
</style>
