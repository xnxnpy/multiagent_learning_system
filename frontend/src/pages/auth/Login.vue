<template>
  <div class="auth-page">
    <!-- 左侧：品牌展示区（深墨蓝，编辑感） -->
    <div class="brand-panel">
      <div class="brand-grain"></div>
      <div class="brand-corner tl"></div>
      <div class="brand-corner br"></div>

      <div class="brand-content">
        <!-- Logo -->
        <div class="brand-mark">
          <div class="brand-mark__sigil">
            <el-icon :size="24"><Reading /></el-icon>
          </div>
          <div class="brand-mark__name">
            <span class="eyebrow">EDU · MULTI-AGENT</span>
            <span class="brand-name">智学优培</span>
          </div>
        </div>

        <!-- 主视觉标题（衬线+无衬线双行） -->
        <div class="hero-block">
          <h1 class="hero-title display-serif">
            <span class="line-1">让学习</span>
            <span class="line-2">因人而异</span>
          </h1>
          <p class="hero-sub">
            基于大模型多模态生成的高校个性化学习智能体平台。
            14 个智能体协同工作，为每一位学习者定制专属路径。
          </p>
        </div>

        <!-- 四个核心能力（非玻璃拟态卡片，改为编辑式列表+色标） -->
        <div class="capability-list">
          <div
            v-for="(cap, i) in capabilities"
            :key="i"
            class="cap-item"
            :style="{ '--cap-color': cap.color }"
          >
            <div class="cap-dot"></div>
            <div class="cap-body">
              <div class="cap-label">{{ cap.label }}</div>
              <div class="cap-desc">{{ cap.desc }}</div>
            </div>

          </div>
        </div>

        <!-- 底部小提示 -->
        <div class="brand-foot">
          <span class="foot-dot"></span>
          <span>支持学生端 · 教师端 · 管理端</span>
        </div>
      </div>
    </div>

    <!-- 右侧：表单区（象牙纸色） -->
    <div class="form-panel">
      <div class="form-veil"></div>

      <div class="form-scroll">
        <div class="form-wrap">
          <!-- 顶部小面包屑 -->
          <router-link to="/" class="back-home">
            <el-icon :size="14"><ArrowLeft /></el-icon>
            返回首页
          </router-link>

          <div class="form-hero">
            <div class="form-eyebrow eyebrow">ACCOUNT · 登录</div>
            <h2 class="form-title">欢迎回来</h2>
            <p class="form-sub">请登录您的账号，继续学习旅程。</p>
          </div>

          <el-form ref="formRef" :model="form" :rules="rules" label-position="top" class="auth-form" @submit.prevent="handleLogin">
            <el-form-item label="用户名" prop="username" class="field-item">
              <el-input v-model="form.username" placeholder="请输入您的用户名" :prefix-icon="User" class="field-input" />
            </el-form-item>

            <el-form-item label="密码" prop="password" class="field-item">
              <el-input
                v-model="form.password"
                type="password"
                placeholder="请输入您的密码"
                :prefix-icon="Lock"
                show-password
                class="field-input"
                @keyup.enter="handleLogin"
              />
            </el-form-item>

            <el-form-item class="field-item">
              <el-button type="primary" :loading="loading" class="submit-btn" @click="handleLogin">
                <span>登录</span>
                <el-icon><ArrowRight /></el-icon>
              </el-button>
            </el-form-item>
          </el-form>

          <div class="form-divider">
            <span>新用户</span>
          </div>

          <div class="form-foot">
            <p class="foot-text">
              还没有账号？
              <router-link to="/register" class="foot-link">立即注册 →</router-link>
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
  User, Lock, Reading, ArrowLeft, ArrowRight,
  DataAnalysis, MagicStick, ChatDotRound,
} from '@element-plus/icons-vue'
import { useUserStore } from '@/stores/userStore'
import { authAPI } from '@/api'
import type { FormInstance } from 'element-plus'

const router = useRouter()
const userStore = useUserStore()
const formRef = ref<FormInstance>()
const loading = ref(false)

const capabilities = [
  { label: '智能学习画像', desc: '对话式采集，多维建模', color: '#B0512C' },
  { label: '个性化学习路径', desc: '知识图谱驱动，量身规划', color: '#3D6B4F' },
  { label: '多模态资源生成', desc: '文档·思维导图·视频·代码', color: '#70293C' },
  { label: 'RAG 智能辅导', desc: '即时答疑，针对性讲解', color: '#2B2D42' },
]

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

/* ═══════════════════ 左侧品牌区 ═══════════════════ */

.brand-panel {
  flex: 0 0 52%;
  background:
    linear-gradient(160deg, #FDFBF7 0%, #F6F1E7 40%, #F0E9DA 100%);
  position: relative;
  overflow: hidden;
  padding: 48px 56px;
  display: flex;
  flex-direction: column;
}

/* 右侧柔和光晕装饰 */
.brand-panel::before {
  content: '';
  position: absolute;
  top: -20%; right: -15%;
  width: 380px; height: 380px;
  background: radial-gradient(circle, rgba(176, 81, 44, 0.08) 0%, transparent 70%);
  pointer-events: none;
}
/* 左下装饰 */
.brand-panel::after {
  content: '';
  position: absolute;
  bottom: -10%; left: -10%;
  width: 260px; height: 260px;
  background: radial-gradient(circle, rgba(61, 107, 79, 0.06) 0%, transparent 70%);
  pointer-events: none;
}

.brand-grain {
  position: absolute;
  inset: 0;
  pointer-events: none;
  opacity: 0.2;
  background-image:
    radial-gradient(rgba(43, 45, 66, 0.035) 1px, transparent 1px);
  background-size: 3px 3px;
}

/* 装饰角 */
.brand-corner {
  position: absolute;
  width: 52px; height: 52px;
  border: 1.5px solid rgba(43, 45, 66, 0.1);
  z-index: 1;
}
.brand-corner.tl { top: 28px; left: 28px; border-right: none; border-bottom: none; border-top-left-radius: 6px; }
.brand-corner.br { bottom: 28px; right: 28px; border-left: none; border-top: none; border-bottom-right-radius: 6px; }

.brand-content {
  position: relative;
  z-index: 1;
  flex: 1;
  display: flex;
  flex-direction: column;
}

/* ── Logo ─────────────────────── */
.brand-mark {
  display: flex;
  align-items: center;
  gap: 14px;
  margin-bottom: 72px;
}
.brand-mark__sigil {
  width: 44px; height: 44px;
  border-radius: 12px;
  background: linear-gradient(135deg, var(--color-primary) 0%, var(--color-primary-deep) 100%);
  color: #fff;
  display: flex; align-items: center; justify-content: center;
  box-shadow: 0 4px 12px rgba(43, 45, 66, 0.15);
}
.brand-mark__name {
  display: flex; flex-direction: column; gap: 2px;
}
.brand-mark__name .eyebrow {
  color: var(--color-text-muted);
}
.brand-name {
  font-family: var(--font-serif);
  font-size: 22px;
  font-weight: 600;
  color: var(--color-text-ink);
  letter-spacing: 0.02em;
  line-height: 1;
}

/* ── Hero 标题 ────────────────── */
.hero-block {
  margin-bottom: 52px;
  max-width: 480px;
}
.hero-title {
  font-size: clamp(42px, 5.2vw, 68px);
  color: var(--color-text-ink);
  font-weight: 600;
  line-height: 1.05;
  margin-bottom: 20px;
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.hero-title .line-1 { display: block; }
.hero-title .line-2 {
  display: block;
  background: linear-gradient(90deg, #B0512C 0%, #2B2D42 100%);
  -webkit-background-clip: text;
  background-clip: text;
  -webkit-text-fill-color: transparent;
  font-style: italic;
}
.hero-sub {
  font-size: 15px;
  line-height: 1.8;
  color: var(--color-text-muted);
  max-width: 440px;
}

/* ── 能力列表 ───────── */
.capability-list {
  display: flex;
  flex-direction: column;
  gap: 14px;
  max-width: 460px;
  margin-bottom: auto;
}
.cap-item {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 14px 16px;
  background: rgba(255, 255, 255, 0.85);
  backdrop-filter: blur(8px);
  border: 1px solid var(--color-border-light);
  border-radius: 12px;
  transition: all 0.25s var(--ease-editing);
  position: relative;
  overflow: hidden;
}
.cap-item::before {
  content: '';
  position: absolute;
  left: 0; top: 0; bottom: 0;
  width: 3px;
  background: var(--cap-color);
  border-radius: 3px 0 0 3px;
}
.cap-item:hover {
  background: #fff;
  transform: translateX(3px);
  box-shadow: 0 4px 14px rgba(29, 31, 51, 0.06);
}
.cap-dot {
  width: 30px; height: 30px;
  border-radius: 9px;
  background: color-mix(in srgb, var(--cap-color) 15%, transparent);
  display: flex; align-items: center; justify-content: center;
  flex-shrink: 0;
}
.cap-dot::after {
  content: '';
  width: 8px; height: 8px;
  border-radius: 50%;
  background: var(--cap-color);
}
.cap-body { flex: 1; min-width: 0; }
.cap-label {
  font-size: 14.5px;
  font-weight: 600;
  color: var(--color-text-ink);
  line-height: 1.25;
}
.cap-desc {
  font-size: 12px;
  color: var(--color-text-muted);
  margin-top: 3px;
  letter-spacing: 0.01em;
}
.cap-index {
  font-family: var(--font-mono);
  font-size: 11px;
  color: var(--color-text-faint);
  letter-spacing: 0.1em;
  flex-shrink: 0;
}

/* ── 底部小提示 ───────────────── */
.brand-foot {
  display: inline-flex;
  align-items: center;
  gap: 9px;
  font-size: 12px;
  color: var(--color-text-muted);
  letter-spacing: 0.04em;
  margin-top: 36px;
  padding: 8px 14px;
  border: 1px solid var(--color-border-light);
  border-radius: 999px;
  align-self: flex-start;
  background: rgba(255, 255, 255, 0.6);
}
.foot-dot {
  width: 6px; height: 6px;
  border-radius: 50%;
  background: var(--color-success);
  box-shadow: 0 0 8px var(--color-success);
}

/* ═══════════════════ 右侧表单区 ═══════════════════ */

.form-panel {
  flex: 1;
  position: relative;
  background: var(--color-bg-page);
  overflow: hidden;
}
.form-veil {
  position: absolute;
  top: -10%; right: -5%;
  width: 520px; height: 520px;
  background: radial-gradient(circle, rgba(43, 45, 66, 0.04) 0%, transparent 70%);
  pointer-events: none;
}
.form-scroll {
  position: relative;
  height: 100vh;
  overflow-y: auto;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 40px 32px;
}
.form-wrap {
  width: 100%;
  max-width: 440px;
  background: #fff;
  border-radius: 20px;
  padding: 44px 40px 36px;
  box-shadow: 
    0 4px 24px rgba(29, 31, 51, 0.06),
    0 1px 3px rgba(29, 31, 51, 0.04);
  border: 1px solid var(--color-border-light);
  position: relative;
}
.form-wrap::before {
  content: '';
  position: absolute;
  top: 0; left: 32px; right: 32px;
  height: 3px;
  background: linear-gradient(90deg, #B0512C, #2B2D42, transparent);
  border-radius: 0 0 3px 3px;
}

.back-home {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 12.5px;
  color: var(--color-text-muted);
  text-decoration: none;
  font-weight: 500;
  padding: 6px 10px;
  border-radius: 8px;
  transition: all 0.2s;
  margin-bottom: 32px;
}
.back-home:hover {
  color: var(--color-primary);
  background: var(--color-bg-page);
}

/* ── 头部 ─────────────────────── */
.form-hero {
  margin-bottom: 32px;
  text-align: center;
}
.form-hero .form-eyebrow {
  margin-bottom: 12px;
  display: block;
}
.form-title {
  font-size: 28px;
  font-weight: 700;
  color: var(--color-text-ink);
  letter-spacing: -0.02em;
  line-height: 1.2;
  margin-bottom: 10px;
  font-family: var(--font-serif);
}
.form-sub {
  font-size: 14px;
  color: var(--color-text-muted);
  line-height: 1.6;
}

/* ── 表单 ─────────────────────── */
.auth-form { margin-bottom: 4px; }

.field-item {
  margin-bottom: 18px;
}
.field-item :deep(.el-form-item__label) {
  font-size: 13px;
  font-weight: 600;
  color: var(--color-text-body);
  letter-spacing: 0.01em;
  padding-bottom: 6px !important;
  line-height: 1;
}

.field-input :deep(.el-input__wrapper) {
  border-radius: 12px;
  box-shadow: 0 0 0 1.5px var(--color-border) inset;
  padding: 7px 14px;
  background: #fff;
  transition: all 0.2s var(--ease-editing);
  font-size: 14.5px;
}
.field-input :deep(.el-input__wrapper:hover) {
  box-shadow: 0 0 0 1.5px var(--color-border-strong) inset;
}
.field-input :deep(.el-input__wrapper.is-focus) {
  box-shadow:
    0 0 0 2px rgba(43, 45, 66, 0.1) inset,
    0 0 0 1.5px var(--color-primary) inset;
}
.field-input :deep(.el-input__inner) {
  color: var(--color-text-ink);
  font-weight: 500;
}
.field-input :deep(.el-input__prefix-inner .el-icon) {
  color: var(--color-text-faint);
}

/* ── 提交按钮 ─────────────────── */
.submit-btn {
  width: 100%;
  height: 48px;
  border-radius: 12px;
  background: linear-gradient(135deg, #B0512C 0%, #2B2D42 100%);
  border: none;
  color: #fff;
  font-size: 15px;
  font-weight: 600;
  letter-spacing: 0.02em;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  box-shadow: 0 4px 14px rgba(176, 81, 44, 0.2);
  transition: all 0.28s var(--ease-editing);
}
.submit-btn:hover {
  background: linear-gradient(135deg, #9D4422 0%, #1D1F33 100%) !important;
  transform: translateY(-2px);
  box-shadow: 0 8px 22px rgba(176, 81, 44, 0.3);
}
.submit-btn:active {
  transform: translateY(0);
}
.submit-btn .el-icon {
  transition: transform 0.28s var(--ease-editing);
}
.submit-btn:hover .el-icon {
  transform: translateX(3px);
}

/* ── 分割线 ───────────────────── */
.form-divider {
  margin: 24px 0 18px;
  display: flex;
  align-items: center;
  gap: 14px;
}
.form-divider::before,
.form-divider::after {
  content: '';
  flex: 1;
  height: 1px;
  background: linear-gradient(90deg, transparent, var(--color-border), transparent);
}
.form-divider span {
  font-size: 11px;
  color: var(--color-text-faint);
  letter-spacing: 0.12em;
  text-transform: uppercase;
  font-weight: 600;
}

/* ── 底部链接 ─────────────────── */
.foot-text {
  text-align: center;
  font-size: 14px;
  color: var(--color-text-muted);
}
.foot-link {
  color: var(--color-primary);
  font-weight: 600;
  text-decoration: none;
  margin-left: 4px;
  transition: all 0.2s;
  display: inline-block;
}
.foot-link:hover {
  color: var(--color-primary-deep);
  transform: translateX(2px);
}

/* ── 响应式 ───────────────────── */
@media (max-width: 960px) {
  .auth-page { flex-direction: column; }
  .brand-panel {
    flex: none;
    padding: 36px 28px;
    min-height: auto;
  }
  .hero-title { font-size: 40px; }
  .hero-block { margin-bottom: 32px; }
  .brand-mark { margin-bottom: 40px; }
  .capability-list { margin-bottom: 0; }
  .brand-foot { margin-top: 28px; }
  .form-scroll { height: auto; min-height: 70vh; padding: 32px 20px; }
}
@media (max-width: 480px) {
  .brand-panel { padding: 28px 20px; }
  .hero-title { font-size: 34px; }
  .cap-item { padding: 12px 14px; }
  .form-wrap { max-width: 100%; }
  .form-title { font-size: 28px; }
  .submit-btn { height: 48px; }
}
</style>
