<template>
  <div class="landing-page">
    <!-- 顶部导航（编辑风：细线分隔，无玻璃拟态） -->
    <header class="nav-bar" :class="{ 'nav-scrolled': isScrolled }">
      <div class="nav-inner">
        <div class="nav-logo">
          <div class="nav-logo__sigil">
            <el-icon :size="20"><Reading /></el-icon>
          </div>
          <div class="nav-logo__text">
            <span class="eyebrow">EDU · MULTI-AGENT</span>
            <span class="nav-title">智学优培</span>
          </div>
        </div>
        <nav class="nav-links">
          <a href="#features" class="nav-link">核心能力</a>
          <a href="#agents" class="nav-link">智能体</a>
          <a href="#portals" class="nav-link">三端入口</a>
          <a href="#about" class="nav-link">关于</a>
        </nav>
        <div class="nav-actions">
          <el-button text @click="$router.push('/login')" class="nav-btn nav-btn--ghost">登录</el-button>
          <el-button class="nav-btn nav-btn--ink" @click="$router.push('/register')">免费注册</el-button>
        </div>
      </div>
    </header>

    <!-- Hero 区（编辑风双栏：左侧排版叙事 + 右侧数据卡） -->
    <section class="hero">
      <div class="hero-grain"></div>
      <div class="hero-inner">
        <div class="hero-copy">
          <div class="hero-eyebrow anim-fade-up" :class="{ 'anim-visible': pageLoaded }">
            <span class="dot"></span>
            <span>MULTI-AGENT · PERSONALIZED LEARNING</span>
          </div>
          <h1
            class="hero-title anim-fade-up"
            :class="{ 'anim-visible': pageLoaded }"
            style="--delay: 0.08s"
          >
            <span class="line display-serif">让学习</span>
            <span class="line display-serif line--accent">因人而异</span>
            <span class="line line--sub">基于大模型的高校个性化学习智能体平台</span>
          </h1>
          <p
            class="hero-desc anim-fade-up"
            :class="{ 'anim-visible': pageLoaded }"
            style="--delay: 0.2s"
          >
            智学优培融合 14 个专业智能体，覆盖学习画像、路径规划、资源生成、
            智能辅导、知识图谱与学习评估全流程，为每位学生打造专属学习体验。
          </p>
          <div
            class="hero-cta anim-fade-up"
            :class="{ 'anim-visible': pageLoaded }"
            style="--delay: 0.32s"
          >
            <button class="btn-ink" @click="$router.push('/register')">
              <span>立即开始使用</span>
              <el-icon><ArrowRight /></el-icon>
            </button>
            <button class="btn-outline" @click="$router.push('/login')">
              已有账号，去登录
            </button>
          </div>
        </div>

        <!-- 右侧数据编辑卡 -->
        <div
          class="hero-stats-card anim-fade-up"
          :class="{ 'anim-visible': pageLoaded }"
          style="--delay: 0.45s"
        >
          <div class="stats-corner tl"></div>
          <div class="stats-corner br"></div>
          <div class="stats-header">
            <span class="eyebrow">PLATFORM · CAPACITY</span>
            <span class="stats-title">核心指标</span>
          </div>
          <div class="stats-body">
            <div class="stat-item">
              <div class="stat-num">
                <span class="counter">{{ animatedNumbers.agents }}</span>
              </div>
              <div class="stat-meta">
                <div class="stat-label">协同智能体</div>
                <div class="stat-sub">专业分工 · 工作流编排</div>
              </div>
            </div>
            <div class="stat-divider"></div>
            <div class="stat-item">
              <div class="stat-num">
                <span class="counter">{{ animatedNumbers.models }}</span><span class="plus">+</span>
              </div>
              <div class="stat-meta">
                <div class="stat-label">智能大模型</div>
                <div class="stat-sub">按需切换 · 深度+效率</div>
              </div>
            </div>
            <div class="stat-divider"></div>
            <div class="stat-item">
              <div class="stat-num">
                <span class="counter">{{ animatedNumbers.outputs }}</span><span class="plus">+</span>
              </div>
              <div class="stat-meta">
                <div class="stat-label">多模态产物</div>
                <div class="stat-sub">文档·导图·视频·代码</div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>

    <!-- 角色三端入口（编辑风：左侧色条 + 角色专属配色） -->
    <section class="section section--alt" id="portals" ref="portalsRef">
      <div class="section-header anim-reveal" :class="{ 'anim-visible': portalsVisible }">
        <span class="eyebrow">PORTALS · 三端协同</span>
        <h2 class="section-title">面向不同角色的专属工作台</h2>
        <p class="section-desc">学生、教师、管理员各司其职，智能体平台贯穿教学全流程</p>
      </div>
      <div class="portals-grid">
        <a
          class="portal-card portal-card--student anim-reveal"
          :class="{ 'anim-visible': portalsVisible }"
          style="--delay: 0.05s"
          @click="$router.push('/login')"
        >
          <div class="portal-accent"></div>
          <div class="portal-head">
            <div class="portal-icon">
              <el-icon><Reading /></el-icon>
            </div>

          </div>
          <h3 class="portal-title">学生学习中心</h3>
          <p class="portal-desc">
            对话式画像采集，个性化学习路径，多模态学习资源生成，
            RAG 智能辅导答疑，阶段评估报告一键生成。
          </p>
          <ul class="portal-list">
            <li><span class="tick">✓</span> 学习画像 · 多档案切换</li>
            <li><span class="tick">✓</span> 知识图谱驱动的路径规划</li>
            <li><span class="tick">✓</span> 10+ 种资源一键生成</li>
            <li><span class="tick">✓</span> 流式辅导 · 代码沙箱</li>
          </ul>
          <div class="portal-foot">
            <span>进入学生端</span>
            <el-icon><ArrowRight /></el-icon>
          </div>
        </a>

        <a
          class="portal-card portal-card--teacher anim-reveal"
          :class="{ 'anim-visible': portalsVisible }"
          style="--delay: 0.15s"
          @click="$router.push('/login')"
        >
          <div class="portal-accent"></div>
          <div class="portal-head">
            <div class="portal-icon">
              <el-icon><Notebook /></el-icon>
            </div>

          </div>
          <h3 class="portal-title">教师教研中心</h3>
          <p class="portal-desc">
            课程管理与资源审核，班级学情全景分析，智能体辅助生成教学材料，
            让备课效率成倍提升。
          </p>
          <ul class="portal-list">
            <li><span class="tick">✓</span> 课程创建 · 班级管理</li>
            <li><span class="tick">✓</span> 学生学情多维分析</li>
            <li><span class="tick">✓</span> 教学资源审核发布</li>
            <li><span class="tick">✓</span> 知识图谱构建维护</li>
          </ul>
          <div class="portal-foot">
            <span>进入教师端</span>
            <el-icon><ArrowRight /></el-icon>
          </div>
        </a>

        <a
          class="portal-card portal-card--admin anim-reveal"
          :class="{ 'anim-visible': portalsVisible }"
          style="--delay: 0.25s"
          @click="$router.push('/login')"
        >
          <div class="portal-accent"></div>
          <div class="portal-head">
            <div class="portal-icon">
              <el-icon><Management /></el-icon>
            </div>

          </div>
          <h3 class="portal-title">管理运营中心</h3>
          <p class="portal-desc">
            用户与权限管理，模型配置与切换，内容安全审核，系统日志与备份，
            全平台数据可视化大屏。
          </p>
          <ul class="portal-list">
            <li><span class="tick">✓</span> 多角色用户管理</li>
            <li><span class="tick">✓</span> 模型参数灵活配置</li>
            <li><span class="tick">✓</span> 内容安全合规审核</li>
            <li><span class="tick">✓</span> 系统监控 · 数据备份</li>
          </ul>
          <div class="portal-foot">
            <span>进入管理端</span>
            <el-icon><ArrowRight /></el-icon>
          </div>
        </a>
      </div>
    </section>

    <!-- 核心特性（学习全流程闭环） -->
    <section class="section" id="features" ref="featuresRef">
      <div class="section-header anim-reveal" :class="{ 'anim-visible': featuresVisible }">
        <span class="eyebrow">CAPABILITIES · 核心能力</span>
        <h2 class="section-title">六大核心能力 · 学习全流程闭环</h2>
        <p class="section-desc">画像 → 路径 → 资源 → 学习 → 辅导 → 评估 → 优化循环，越学越精准</p>
      </div>
      <div class="features-grid">
        <div
          v-for="(f, i) in coreFeatures"
          :key="f.title"
          class="feature-card anim-reveal"
          :class="{ 'anim-visible': featuresVisible }"
          :style="{ '--delay': `${0.08 * i}s` }"
        >
          <div class="feature-accent" :style="{ background: f.color }"></div>

          <div class="feature-icon" :style="{ background: f.bg, color: f.color }">
            <el-icon :size="26"><component :is="f.icon" /></el-icon>
          </div>
          <h3 class="feature-title">{{ f.title }}</h3>
          <p class="feature-desc">{{ f.desc }}</p>
        </div>
      </div>
    </section>

    <!-- Agent 矩阵（编辑式网格，左侧色标） -->
    <section class="section section--alt" id="agents" ref="agentsRef">
      <div class="section-header anim-reveal" :class="{ 'anim-visible': agentsVisible }">
        <span class="eyebrow">AGENTS · 智能体矩阵</span>
        <h2 class="section-title">14 个专业智能体协同工作</h2>
        <p class="section-desc">每个智能体专注一项任务，通过工作流编排实现端到端学习服务</p>
      </div>
      <div class="agents-grid">
        <div
          v-for="(a, i) in agents"
          :key="a.name"
          class="agent-item anim-reveal"
          :class="{ 'anim-visible': agentsVisible }"
          :style="{ '--delay': `${0.04 * i}s` }"
        >
          <div class="agent-accent" :style="{ background: a.color }"></div>
          <div class="agent-icon" :style="{ background: a.bg, color: a.color }">
            <el-icon><component :is="a.icon" /></el-icon>
          </div>
          <div class="agent-text">
            <div class="agent-name">{{ a.name }}</div>
            <div class="agent-desc">{{ a.desc }}</div>
          </div>

        </div>
      </div>
    </section>

    <!-- 应用介绍 + 技术栈 -->
    <section class="section" id="about" ref="aboutRef">
      <div class="section-header anim-reveal" :class="{ 'anim-visible': aboutVisible }">
        <span class="eyebrow">ABOUT · 关于平台</span>
        <h2 class="section-title">关于智学优培</h2>
        <p class="section-desc">面向高校场景的个性化学习智能体平台</p>
      </div>
      <div class="about-content">
        <div
          class="about-text anim-reveal"
          :class="{ 'anim-visible': aboutVisible }"
          style="--delay: 0.1s"
        >
          <p class="para">
            <span class="dropcap">智</span>学优培是一个基于大模型多模态生成技术构建的高校个性化学习智能体平台。
            平台采用多智能体架构，通过 LangGraph 工作流编排将「学习画像生成 → 专属路径规划 →
            多模态资源生成 → 沉浸式学习 → 智能答疑 → 效果评估 → 优化循环」
            串联为完整的闭环学习链路，越学越精准。
          </p>
          <p class="para">
            系统由 14 个专业智能体协同完成教学服务：ProfileAgent 通过对话精准刻画学生学情；
            LearningPathAgent 规划个性化学习路径；Document / Question / Mindmap / PPTVideo /
            Code / ReadingMaterial / Glossary 等多智能体基于 RAG 检索与多模态生成，
            产出文档、习题、思维导图、PPT 视频、代码沙箱实战、拓展阅读、术语表等多样化资源；
            TutorAgent 提供流式辅导答疑；KnowledgeGraphAgent 构建全局结构化知识网络；
            EvaluationAgent 生成评估报告，驱动画像与路径持续优化。
          </p>
          <p class="para">
            技术层采用 LangGraph 多智能体编排、14 Agent 专业分工、Neo4j 全局知识图谱、
            ChromaDB 向量检索、Docker 安全代码沙箱、多模态生成引擎、三端 RBAC 权限体系，
            默认采用 Spark Ultra-32K（画像 / 辅导 / 评估）与 Spark X2-Flash（其余 11 个智能体）
            双模型组合，兼顾推理深度与响应效率，为学生提供精准、高效、可追踪的个性化学习体验。
          </p>
        </div>
        <div
          class="about-side anim-reveal"
          :class="{ 'anim-visible': aboutVisible }"
          style="--delay: 0.25s"
        >
          <div class="tech-card">
            <div class="tech-card__head">
              <span class="eyebrow">TECHNOLOGY · 技术构成</span>
              <span class="tech-card__title">核心技术栈</span>
            </div>
            <div class="tech-list">
              <div v-for="(t, i) in techStack" :key="t.label" class="tech-item" :style="{ '--delay': `${0.06 * i}s` }">
                <div class="tech-icon" :style="{ background: t.bg, color: t.color }">
                  <el-icon><component :is="t.icon" /></el-icon>
                </div>
                <div class="tech-info">
                  <div class="tech-label">{{ t.label }}</div>
                  <div class="tech-desc">{{ t.desc }}</div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>

    <!-- CTA 区（深墨蓝底 + 编辑式装饰） -->
    <section class="cta-section" ref="ctaRef">
      <div class="cta-grain"></div>
      <div class="cta-corner tl"></div>
      <div class="cta-corner br"></div>
      <div class="cta-inner anim-reveal" :class="{ 'anim-visible': ctaVisible }">
        <span class="eyebrow cta-eyebrow">GET STARTED · 开启</span>
        <h2 class="cta-title display-serif">开启您的个性化学习之旅</h2>
        <p class="cta-subtitle">注册账号，让 14 个智能体为您定制专属学习方案</p>
        <div class="cta-actions">
          <button class="btn-ink btn-ink--light" @click="$router.push('/register')">
            <span>免费注册</span>
            <el-icon><ArrowRight /></el-icon>
          </button>
          <button class="btn-outline btn-outline--light" @click="$router.push('/login')">
            登录账号
          </button>
        </div>
      </div>
    </section>

    <!-- 页脚 -->
    <footer class="footer">
      <div class="footer-inner">
        <div class="footer-top">
          <div class="footer-brand">
            <div class="footer-brand__sigil">
              <el-icon :size="18"><Reading /></el-icon>
            </div>
            <div>
              <span class="footer-title">智学优培</span>
              <span class="footer-sub">EDU · MULTI-AGENT PLATFORM</span>
            </div>
          </div>
          <div class="footer-links">
            <div class="footer-col">
              <h5>产品</h5>
              <a href="#features">核心能力</a>
              <a href="#agents">智能体矩阵</a>
              <a href="#portals">三端入口</a>
            </div>
            <div class="footer-col">
              <h5>角色</h5>
              <a @click="$router.push('/login')">学生端</a>
              <a @click="$router.push('/login')">教师端</a>
              <a @click="$router.push('/login')">管理端</a>
            </div>
            <div class="footer-col">
              <h5>联系</h5>
              <a>技术支持</a>
              <a>使用文档</a>
              <a>隐私政策</a>
            </div>
          </div>
        </div>
        <div class="footer-divider"></div>
        <div class="footer-bottom">
          <p class="footer-desc">基于大模型多模态生成的高校个性化学习智能体平台</p>
          <p class="footer-copy">© {{ year }} 智学优培 · All rights reserved.</p>
        </div>
      </div>
    </footer>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, onUnmounted, reactive, ref } from 'vue'
import {
  ArrowRight,
  DataAnalysis, MapLocation, ChatDotRound, MagicStick,
  Document, Reading, EditPen,
  Connection, Histogram, Files, VideoCamera, Notebook, Collection, Monitor, Management,
} from '@element-plus/icons-vue'

const year = computed(() => new Date().getFullYear())
const pageLoaded = ref(false)
const isScrolled = ref(false)

/* ── 滚动监听 ─────────────────────────── */
function onScroll() {
  isScrolled.value = window.scrollY > 20
}

/* ── 数字递增动画 ─────────────────────── */
const animatedNumbers = reactive({ agents: 0, models: 0, outputs: 0 })
const targetNumbers = { agents: 14, models: 8, outputs: 10 }

function easeOutQuart(t: number) {
  return 1 - Math.pow(1 - t, 4)
}

function animateNumber(key: keyof typeof targetNumbers, duration = 2000) {
  const start = performance.now()
  const target = targetNumbers[key]
  function tick(now: number) {
    const elapsed = now - start
    const progress = Math.min(elapsed / duration, 1)
    const eased = easeOutQuart(progress)
    animatedNumbers[key] = Math.round(eased * target)
    if (progress < 1) requestAnimationFrame(tick)
  }
  requestAnimationFrame(tick)
}

let numberAnimated = false
function triggerNumberAnimation() {
  if (numberAnimated) return
  numberAnimated = true
  animateNumber('agents', 1800)
  setTimeout(() => animateNumber('models', 1500), 200)
  setTimeout(() => animateNumber('outputs', 1500), 400)
}

/* ── Intersection Observer 滚动触发 ──── */
const portalsRef = ref<HTMLElement>()
const featuresRef = ref<HTMLElement>()
const agentsRef = ref<HTMLElement>()
const aboutRef = ref<HTMLElement>()
const ctaRef = ref<HTMLElement>()

const portalsVisible = ref(false)
const featuresVisible = ref(false)
const agentsVisible = ref(false)
const aboutVisible = ref(false)
const ctaVisible = ref(false)

let observer: IntersectionObserver | null = null

onMounted(() => {
  setTimeout(() => { pageLoaded.value = true }, 80)
  window.addEventListener('scroll', onScroll, { passive: true })

  observer = new IntersectionObserver(
    (entries) => {
      entries.forEach((entry) => {
        if (!entry.isIntersecting) return
        const target = entry.target
        if (target === portalsRef.value) portalsVisible.value = true
        if (target === featuresRef.value) featuresVisible.value = true
        if (target === agentsRef.value) agentsVisible.value = true
        if (target === aboutRef.value) aboutVisible.value = true
        if (target === ctaRef.value) ctaVisible.value = true
        if (target === featuresRef.value || target === agentsRef.value || target === portalsRef.value) {
          triggerNumberAnimation()
        }
        observer?.unobserve(target)
      })
    },
    { threshold: 0.1, rootMargin: '0px 0px -40px 0px' }
  )

  portalsRef.value && observer.observe(portalsRef.value)
  featuresRef.value && observer.observe(featuresRef.value)
  agentsRef.value && observer.observe(agentsRef.value)
  aboutRef.value && observer.observe(aboutRef.value)
  ctaRef.value && observer.observe(ctaRef.value)
})

onUnmounted(() => {
  window.removeEventListener('scroll', onScroll)
  observer?.disconnect()
})

/* ── 数据 ─────────────────────────────── */
const coreFeatures = [
  {
    icon: DataAnalysis,
    title: '智能学习画像',
    desc: '自然对话交互精准刻画学情画像，多维识别知识薄弱点、学习风格与偏好，支持多档案切换管理。',
    color: '#B0512C',
    bg: '#FBF0E9',
  },
  {
    icon: MapLocation,
    title: '专属学习路径',
    desc: '基于学情与全局知识图谱，自动规划个性化最优学习路径，随学习进度智能动态调整。',
    color: '#3D6B4F',
    bg: '#EEF4F0',
  },
  {
    icon: MagicStick,
    title: '多模态资源生成',
    desc: '10+ 智能体协同生成文档、习题、思维导图、PPT 视频、代码、阅读材料、术语表等多样化资源。',
    color: '#70293C',
    bg: '#F5E9ED',
  },
  {
    icon: Document,
    title: '沉浸式学习',
    desc: '按路径学习文档 / 观看视频 / 在线做题 / 代码沙箱实战，多形式融合的深度学习体验。',
    color: '#4E598C',
    bg: '#EFF0F8',
  },
  {
    icon: ChatDotRound,
    title: '⑤ 智能多模态答疑',
    desc: '支持文本 / 语音 / 图片多种题型，图片经讯飞 OCR 识别转文字后传入辅导 Agent，苏格拉底式引导辅导，不直接给答案。',
    color: '#2B2D42',
    bg: '#F4F5FA',
  },
  {
    icon: Histogram,
    title: '评估 → 循环优化',
    desc: '系统评估学习效果 → 更新学习画像 → 优化学习路径，形成闭环，越学越精准。',
    color: '#8B5E3C',
    bg: '#FAF3EC',
  },
]

const agents = [
  { icon: DataAnalysis, name: '画像智能体', desc: '对话式学情画像分析', color: '#B0512C', bg: '#FBF0E9' },
  { icon: MapLocation, name: '路径智能体', desc: '个性化学习路径规划', color: '#3D6B4F', bg: '#EEF4F0' },
  { icon: Document, name: '文档智能体', desc: '学习文档自动生成', color: '#70293C', bg: '#F5E9ED' },
  { icon: EditPen, name: '习题智能体', desc: '针对性习题生成练习', color: '#B0512C', bg: '#FBF0E9' },
  { icon: Connection, name: '思维导图智能体', desc: '知识结构可视化', color: '#3D6B4F', bg: '#EEF4F0' },
  { icon: VideoCamera, name: 'PPT视频智能体', desc: 'PPT 与视频资源生成', color: '#70293C', bg: '#F5E9ED' },
  { icon: Monitor, name: '代码智能体', desc: '代码沙箱编程练习', color: '#2B2D42', bg: '#F4F5FA' },
  { icon: Histogram, name: '知识图谱智能体', desc: '结构化知识网络构建', color: '#B0512C', bg: '#FBF0E9' },
  { icon: Reading, name: '阅读材料智能体', desc: '拓展阅读材料生成', color: '#3D6B4F', bg: '#EEF4F0' },
  { icon: Notebook, name: '术语表智能体', desc: '学科术语词典整理', color: '#70293C', bg: '#F5E9ED' },
  { icon: Collection, name: '资源质量智能体', desc: '资源质量审核把控', color: '#2B2D42', bg: '#F4F5FA' },
  { icon: Files, name: '总结智能体', desc: '学习内容归纳总结', color: '#B0512C', bg: '#FBF0E9' },
  { icon: ChatDotRound, name: '辅导智能体', desc: 'RAG 流式辅导答疑', color: '#3D6B4F', bg: '#EEF4F0' },
  { icon: DataAnalysis, name: '评估智能体', desc: '学习效果评估报告', color: '#70293C', bg: '#F5E9ED' },
]

const techStack = [
  { icon: DataAnalysis, label: '多智能体工作流编排', desc: 'LangGraph · 14 Agent 协同 · 状态持久化', color: '#2B2D42', bg: '#F4F5FA' },
  { icon: Connection, label: 'Neo4j 全局知识图谱', desc: '知识点结构化关联 · 图谱驱动路径规划', color: '#3D6B4F', bg: '#EEF4F0' },
  { icon: Collection, label: 'ChromaDB 向量检索', desc: 'RAG 检索增强 · 语义匹配 · 可溯源引用', color: '#70293C', bg: '#F5E9ED' },
  { icon: Monitor, label: 'Docker 代码沙箱', desc: '安全隔离环境 · 实时代码运行 · 结果可视化', color: '#4E598C', bg: '#EFF0F8' },
  { icon: VideoCamera, label: '多模态生成引擎', desc: '文档·导图·PPT·视频·代码·术语表 · 10+ 产物', color: '#B0512C', bg: '#FBF0E9' },
  { icon: Management, label: '三端角色权限体系', desc: '学生端 · 教师端 · 管理端 · 细粒度 RBAC', color: '#8B5E3C', bg: '#FAF3EC' },
]
</script>

<style scoped>
.landing-page {
  min-height: 100vh;
  background: var(--color-bg-page);
  color: var(--color-text-body);
  overflow-x: hidden;
}

/* ── 全局动画 ────────────────────────── */
.anim-fade-up {
  opacity: 0;
  transform: translateY(28px);
  transition: opacity 0.7s var(--ease-editing), transform 0.7s var(--ease-editing);
  transition-delay: var(--delay, 0s);
}
.anim-fade-up.anim-visible { opacity: 1; transform: translateY(0); }

.anim-reveal {
  opacity: 0;
  transform: translateY(36px);
  transition: opacity 0.8s var(--ease-editing), transform 0.8s var(--ease-editing);
  transition-delay: var(--delay, 0s);
}
.anim-reveal.anim-visible { opacity: 1; transform: translateY(0); }

/* ═══════════════ 顶部导航 ═══════════════ */
.nav-bar {
  position: fixed;
  top: 0; left: 0; right: 0;
  z-index: 100;
  background: rgba(247, 245, 240, 0.82);
  backdrop-filter: saturate(160%) blur(14px);
  -webkit-backdrop-filter: saturate(160%) blur(14px);
  border-bottom: 1px solid transparent;
  transition: all 0.3s var(--ease-editing);
  transform: translateY(-100%);
  animation: navSlide 0.6s var(--ease-editing) 0.2s forwards;
}
@keyframes navSlide { to { transform: translateY(0); } }

.nav-bar.nav-scrolled {
  background: rgba(255, 253, 247, 0.94);
  border-bottom-color: var(--color-border-light);
  box-shadow: 0 1px 10px rgba(29, 31, 51, 0.05);
}

.nav-inner {
  max-width: 1280px;
  margin: 0 auto;
  padding: 0 32px;
  height: 68px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 24px;
}

.nav-logo {
  display: flex;
  align-items: center;
  gap: 12px;
  cursor: pointer;
}
.nav-logo__sigil {
  width: 36px; height: 36px;
  border-radius: 10px;
  background: linear-gradient(135deg, #2B2D42 0%, #4A4E7C 100%);
  color: #fff;
  display: flex; align-items: center; justify-content: center;
  box-shadow: 0 2px 8px rgba(43, 45, 66, 0.2);
  flex-shrink: 0;
}
.nav-logo__text { display: flex; flex-direction: column; gap: 2px; }
.nav-logo__text .eyebrow { color: var(--color-text-faint); }
.nav-title {
  font-family: var(--font-serif);
  font-size: 19px;
  font-weight: 600;
  color: var(--color-text-ink);
  letter-spacing: 0.02em;
  line-height: 1;
}

.nav-links {
  display: flex;
  align-items: center;
  gap: 8px;
}
.nav-link {
  font-size: 13.5px;
  color: var(--color-text-body);
  text-decoration: none;
  padding: 8px 14px;
  border-radius: 8px;
  font-weight: 500;
  transition: all 0.2s var(--ease-editing);
}
.nav-link:hover {
  color: var(--color-primary);
  background: var(--color-primary-faint);
}

.nav-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}
.nav-btn {
  height: 38px;
  padding: 0 18px;
  border-radius: 10px;
  font-size: 13.5px;
  font-weight: 600;
  transition: all 0.25s var(--ease-editing);
  cursor: pointer;
}
.nav-btn--ghost {
  color: var(--color-text-body);
  background: transparent;
  border: none;
}
.nav-btn--ghost:hover { color: var(--color-primary) !important; background: var(--color-primary-faint) !important; }
.nav-btn--ink {
  background: var(--color-primary);
  color: var(--color-text-inverse);
  border: none;
  box-shadow: 0 2px 8px rgba(43, 45, 66, 0.18);
}
.nav-btn--ink:hover {
  background: var(--color-primary-deep) !important;
  transform: translateY(-1px);
  box-shadow: 0 6px 16px rgba(43, 45, 66, 0.28);
}

/* ═══════════════ Hero 区 ═══════════════ */
.hero {
  position: relative;
  padding: 148px 32px 100px;
  background: var(--color-bg-page);
  overflow: hidden;
}
.hero-grain {
  position: absolute;
  inset: 0;
  pointer-events: none;
  background:
    radial-gradient(circle at 85% 10%, rgba(176, 81, 44, 0.06) 0%, transparent 38%),
    radial-gradient(circle at 8% 85%, rgba(61, 107, 79, 0.06) 0%, transparent 35%);
}

.hero-inner {
  position: relative;
  z-index: 1;
  max-width: 1280px;
  margin: 0 auto;
  display: grid;
  grid-template-columns: 1.25fr 1fr;
  gap: 80px;
  align-items: center;
}

.hero-copy { max-width: 620px; }

.hero-eyebrow {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 6px 14px;
  border: 1px solid var(--color-border);
  border-radius: 999px;
  background: var(--color-bg-card);
  margin-bottom: 28px;
}
.hero-eyebrow .dot {
  width: 6px; height: 6px;
  border-radius: 50%;
  background: var(--color-student);
  box-shadow: 0 0 8px rgba(176, 81, 44, 0.5);
}
.hero-eyebrow span:not(.dot) {
  font-size: 10.5px;
  letter-spacing: 0.14em;
  color: var(--color-text-muted);
  font-weight: 600;
}

.hero-title {
  display: flex;
  flex-direction: column;
  gap: 6px;
  margin-bottom: 22px;
}
.hero-title .line {
  font-size: clamp(40px, 5vw, 64px);
  color: var(--color-text-ink);
  font-weight: 600;
  letter-spacing: -0.03em;
  line-height: 1.05;
}
.hero-title .line--accent {
  background: linear-gradient(90deg, var(--color-text-ink) 0%, #7A6B4F 100%);
  -webkit-background-clip: text;
  background-clip: text;
  -webkit-text-fill-color: transparent;
  font-style: italic;
}
.hero-title .line--sub {
  font-size: clamp(16px, 1.5vw, 20px);
  font-weight: 500;
  letter-spacing: -0.01em;
  color: var(--color-text-muted);
  font-family: var(--font-sans);
  font-style: normal;
  margin-top: 10px;
  line-height: 1.5;
  -webkit-text-fill-color: var(--color-text-muted);
}

.hero-desc {
  font-size: 15.5px;
  line-height: 1.85;
  color: var(--color-text-muted);
  margin-bottom: 36px;
  max-width: 560px;
}

.hero-cta {
  display: flex;
  align-items: center;
  gap: 14px;
  flex-wrap: wrap;
}

.btn-ink {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  height: 50px;
  padding: 0 26px;
  border-radius: 12px;
  background: var(--color-primary);
  color: var(--color-text-inverse);
  border: none;
  font-size: 14.5px;
  font-weight: 600;
  letter-spacing: 0.01em;
  cursor: pointer;
  box-shadow: 0 4px 14px rgba(43, 45, 66, 0.22);
  transition: all 0.28s var(--ease-editing);
}
.btn-ink:hover {
  background: var(--color-primary-deep);
  transform: translateY(-2px);
  box-shadow: 0 8px 22px rgba(43, 45, 66, 0.32);
}
.btn-ink .el-icon { transition: transform 0.28s var(--ease-editing); }
.btn-ink:hover .el-icon { transform: translateX(3px); }
.btn-ink--light {
  background: var(--color-text-inverse);
  color: var(--color-primary-deep);
  box-shadow: 0 4px 14px rgba(0, 0, 0, 0.25);
}
.btn-ink--light:hover {
  background: #fff;
  color: var(--color-primary-deep);
}

.btn-outline {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  height: 50px;
  padding: 0 24px;
  border-radius: 12px;
  background: transparent;
  color: var(--color-primary);
  border: 1.5px solid var(--color-border-strong);
  font-size: 14.5px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.25s var(--ease-editing);
}
.btn-outline:hover {
  border-color: var(--color-primary);
  background: var(--color-primary-faint);
  transform: translateY(-1px);
}
.btn-outline--light {
  color: var(--color-text-inverse);
  border-color: rgba(249, 247, 242, 0.35);
}
.btn-outline--light:hover {
  border-color: var(--color-text-inverse);
  background: rgba(249, 247, 242, 0.08);
  color: var(--color-text-inverse);
}

/* ── 右侧数据卡（编辑式） ──────────── */
.hero-stats-card {
  position: relative;
  background: var(--color-bg-card);
  border: 1px solid var(--color-border-light);
  border-radius: 20px;
  padding: 32px 30px 26px;
  box-shadow: var(--shadow-card-hover);
}
.stats-corner {
  position: absolute;
  width: 36px; height: 36px;
  border: 1.5px solid var(--color-border-strong);
  opacity: 0.7;
}
.stats-corner.tl { top: 14px; left: 14px; border-right: none; border-bottom: none; border-top-left-radius: 4px; }
.stats-corner.br { bottom: 14px; right: 14px; border-left: none; border-top: none; border-bottom-right-radius: 4px; }

.stats-header {
  display: flex;
  flex-direction: column;
  gap: 6px;
  padding-bottom: 22px;
  margin-bottom: 22px;
  border-bottom: 1px solid var(--color-border-light);
}
.stats-header .eyebrow { color: var(--color-text-faint); }
.stats-title {
  font-family: var(--font-serif);
  font-size: 24px;
  font-weight: 600;
  color: var(--color-text-ink);
  letter-spacing: -0.02em;
  line-height: 1;
}

.stats-body {
  display: flex;
  flex-direction: column;
  gap: 18px;
}
.stat-item {
  display: flex;
  align-items: center;
  gap: 18px;
}
.stat-num {
  flex-shrink: 0;
  min-width: 90px;
  font-size: 44px;
  font-weight: 800;
  letter-spacing: -0.04em;
  color: var(--color-text-ink);
  line-height: 1;
  font-variant-numeric: tabular-nums;
}
.stat-num .plus {
  font-size: 28px;
  color: var(--color-student);
  margin-left: 2px;
  font-weight: 700;
}
.counter { display: inline-block; min-width: 1.1em; }
.stat-meta { flex: 1; min-width: 0; }
.stat-label {
  font-size: 14.5px;
  font-weight: 600;
  color: var(--color-text-ink);
  margin-bottom: 3px;
}
.stat-sub {
  font-size: 12px;
  color: var(--color-text-muted);
  letter-spacing: 0.01em;
}
.stat-divider {
  height: 1px;
  background: linear-gradient(90deg, transparent, var(--color-border-light), transparent);
}

.stats-foot {
  margin-top: 24px;
  padding-top: 18px;
  border-top: 1px solid var(--color-border-light);
  display: inline-flex;
  align-items: center;
  gap: 8px;
  font-size: 11.5px;
  color: var(--color-text-muted);
  letter-spacing: 0.02em;
  font-weight: 500;
}
.foot-dot {
  width: 6px; height: 6px;
  border-radius: 50%;
  background: var(--color-success);
  box-shadow: 0 0 6px rgba(63, 125, 82, 0.5);
}

/* ═══════════════ 通用 Section ═══════════════ */
.section {
  padding: 100px 32px;
  max-width: 1280px;
  margin: 0 auto;
}
.section--alt {
  max-width: none;
  background: var(--color-bg-card-soft);
  border-top: 1px solid var(--color-border-light);
  border-bottom: 1px solid var(--color-border-light);
}
.section--alt .section-header,
.section--alt > * {
  max-width: 1280px;
  margin-left: auto;
  margin-right: auto;
}

.section-header {
  text-align: center;
  margin-bottom: 56px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 10px;
}
.section-header .eyebrow { color: var(--color-text-faint); }
.section-title {
  font-family: var(--font-serif);
  font-size: clamp(26px, 2.8vw, 36px);
  font-weight: 600;
  color: var(--color-text-ink);
  letter-spacing: -0.025em;
  line-height: 1.15;
}
.section-desc {
  font-size: 15.5px;
  color: var(--color-text-muted);
  max-width: 620px;
  line-height: 1.7;
}

/* ═══════════════ 三端入口卡片 ═══════════════ */
.portals-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 24px;
}
.portal-card {
  position: relative;
  background: var(--color-bg-card);
  border: 1px solid var(--color-border-light);
  border-radius: var(--radius-2xl);
  padding: 32px 28px 26px;
  cursor: pointer;
  text-decoration: none;
  transition: all 0.35s var(--ease-editing);
  overflow: hidden;
  display: flex;
  flex-direction: column;
}
.portal-card:hover {
  transform: translateY(-6px);
  box-shadow: var(--shadow-pop);
}
.portal-accent {
  position: absolute;
  top: 0; left: 0; bottom: 0;
  width: 4px;
  opacity: 0.7;
  transition: width 0.35s var(--ease-editing), opacity 0.35s;
}
.portal-card:hover .portal-accent { width: 6px; opacity: 1; }
.portal-card--student .portal-accent { background: var(--color-student); }
.portal-card--teacher .portal-accent { background: var(--color-teacher); }
.portal-card--admin .portal-accent { background: var(--color-admin); }

.portal-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 22px;
}
.portal-icon {
  width: 48px; height: 48px;
  border-radius: 14px;
  display: flex; align-items: center; justify-content: center;
  font-size: 22px;
  transition: transform 0.35s var(--ease-editing);
}
.portal-card:hover .portal-icon { transform: scale(1.08) rotate(-4deg); }
.portal-card--student .portal-icon { background: var(--color-student-pale); color: var(--color-student); }
.portal-card--teacher .portal-icon { background: var(--color-teacher-pale); color: var(--color-teacher); }
.portal-card--admin .portal-icon { background: var(--color-admin-pale); color: var(--color-admin); }

.portal-kbd {
  font-family: var(--font-mono);
  font-size: 10.5px;
  color: var(--color-text-faint);
  letter-spacing: 0.1em;
  padding: 4px 8px;
  border: 1px solid var(--color-border-light);
  border-radius: 6px;
  font-weight: 600;
}

.portal-title {
  font-size: 22px;
  font-weight: 700;
  color: var(--color-text-ink);
  letter-spacing: -0.02em;
  margin-bottom: 10px;
  line-height: 1.2;
}
.portal-desc {
  font-size: 13.5px;
  line-height: 1.75;
  color: var(--color-text-muted);
  margin-bottom: 20px;
}

.portal-list {
  list-style: none;
  padding: 0;
  margin: 0 0 24px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.portal-list li {
  font-size: 13px;
  color: var(--color-text-body);
  display: flex;
  align-items: center;
  gap: 10px;
  line-height: 1.4;
}
.tick {
  width: 18px; height: 18px;
  border-radius: 6px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 10px;
  font-weight: 700;
  flex-shrink: 0;
}
.portal-card--student .tick { background: var(--color-student-pale); color: var(--color-student); }
.portal-card--teacher .tick { background: var(--color-teacher-pale); color: var(--color-teacher); }
.portal-card--admin .tick { background: var(--color-admin-pale); color: var(--color-admin); }

.portal-foot {
  margin-top: auto;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding-top: 18px;
  border-top: 1px solid var(--color-border-light);
  font-size: 13.5px;
  font-weight: 600;
  transition: all 0.28s var(--ease-editing);
}
.portal-card--student .portal-foot { color: var(--color-student); }
.portal-card--teacher .portal-foot { color: var(--color-teacher); }
.portal-card--admin .portal-foot { color: var(--color-admin); }
.portal-foot .el-icon { transition: transform 0.3s var(--ease-editing); }
.portal-card:hover .portal-foot .el-icon { transform: translateX(4px); }

/* ═══════════════ 核心特性卡片 ═══════════════ */
.features-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 22px;
}
.feature-card {
  position: relative;
  padding: 32px 26px;
  background: var(--color-bg-card);
  border: 1px solid var(--color-border-light);
  border-radius: var(--radius-xl);
  transition: all 0.4s var(--ease-editing);
  overflow: hidden;
}
.feature-accent {
  position: absolute;
  top: 0; left: 0; right: 0;
  height: 3px;
  transform: scaleX(0);
  transform-origin: left;
  transition: transform 0.4s var(--ease-editing);
}
.feature-card:hover {
  transform: translateY(-6px);
  box-shadow: var(--shadow-lifted);
  border-color: var(--color-border);
}
.feature-card:hover .feature-accent { transform: scaleX(1); }

.feature-index {
  position: absolute;
  top: 20px; right: 22px;
  font-family: var(--font-serif);
  font-size: 14px;
  color: var(--color-text-faint);
  font-weight: 600;
  letter-spacing: 0.05em;
}

.feature-icon {
  width: 56px; height: 56px;
  border-radius: 16px;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 22px;
  transition: all 0.4s var(--ease-editing);
}
.feature-card:hover .feature-icon {
  transform: scale(1.08) rotate(-5deg);
}

.feature-title {
  font-size: 19px;
  font-weight: 700;
  color: var(--color-text-ink);
  letter-spacing: -0.02em;
  margin-bottom: 10px;
  line-height: 1.3;
}
.feature-desc {
  font-size: 13.5px;
  line-height: 1.75;
  color: var(--color-text-muted);
}

/* ═══════════════ Agent 矩阵 ═══════════════ */
.agents-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 14px;
}
.agent-item {
  position: relative;
  display: flex;
  align-items: flex-start;
  gap: 12px;
  padding: 18px 16px 18px 22px;
  background: var(--color-bg-card);
  border: 1px solid var(--color-border-light);
  border-radius: var(--radius-lg);
  transition: all 0.32s var(--ease-editing);
  overflow: hidden;
}
.agent-accent {
  position: absolute;
  top: 0; left: 0; bottom: 0;
  width: 3px;
  opacity: 0.5;
  transition: opacity 0.3s;
}
.agent-item:hover {
  transform: translateY(-3px);
  box-shadow: var(--shadow-card-hover);
  border-color: var(--color-border);
}
.agent-item:hover .agent-accent { opacity: 1; }

.agent-icon {
  width: 38px; height: 38px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 17px;
  flex-shrink: 0;
  transition: transform 0.32s var(--ease-editing);
}
.agent-item:hover .agent-icon {
  transform: scale(1.08);
}

.agent-text { flex: 1; min-width: 0; }
.agent-name {
  font-size: 14px;
  font-weight: 600;
  color: var(--color-text-ink);
  margin-bottom: 3px;
  line-height: 1.3;
}
.agent-desc {
  font-size: 11.5px;
  color: var(--color-text-muted);
  line-height: 1.5;
}
.agent-index {
  font-family: var(--font-mono);
  font-size: 10px;
  color: var(--color-text-faint);
  letter-spacing: 0.08em;
  font-weight: 600;
  flex-shrink: 0;
  padding-top: 2px;
}

/* ═══════════════ 应用介绍 ═══════════════ */
.about-content {
  display: grid;
  grid-template-columns: 1.4fr 1fr;
  gap: 64px;
  align-items: start;
}

.about-text .para {
  font-size: 15px;
  line-height: 1.9;
  color: var(--color-text-body);
  margin-bottom: 20px;
}
.dropcap {
  float: left;
  font-family: var(--font-serif);
  font-size: 58px;
  line-height: 0.9;
  padding: 5px 12px 0 0;
  font-weight: 600;
  color: var(--color-primary);
  letter-spacing: -0.02em;
}

.tech-card {
  position: sticky;
  top: 100px;
  background: var(--color-bg-card);
  border: 1px solid var(--color-border-light);
  border-radius: var(--radius-xl);
  padding: 28px 24px;
  box-shadow: var(--shadow-card);
}
.tech-card__head {
  display: flex;
  flex-direction: column;
  gap: 6px;
  margin-bottom: 22px;
  padding-bottom: 18px;
  border-bottom: 1px solid var(--color-border-light);
}
.tech-card__head .eyebrow { color: var(--color-text-faint); }
.tech-card__title {
  font-family: var(--font-serif);
  font-size: 22px;
  font-weight: 600;
  color: var(--color-text-ink);
  letter-spacing: -0.02em;
}

.tech-list { display: flex; flex-direction: column; gap: 14px; }
.tech-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px;
  border-radius: 12px;
  transition: all 0.28s var(--ease-editing);
  animation: techFadeIn 0.6s var(--ease-editing) both;
  animation-delay: var(--delay, 0s);
  animation-play-state: paused;
}
.anim-visible ~ .about-side .tech-item,
.about-side.anim-visible .tech-item { animation-play-state: running; }
@keyframes techFadeIn {
  from { opacity: 0; transform: translateX(-8px); }
  to { opacity: 1; transform: translateX(0); }
}
.tech-item:hover {
  background: var(--color-bg-page);
  transform: translateX(3px);
}
.tech-icon {
  width: 40px; height: 40px;
  border-radius: 11px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 18px;
  flex-shrink: 0;
}
.tech-info { flex: 1; min-width: 0; }
.tech-label {
  font-size: 14px;
  font-weight: 600;
  color: var(--color-text-ink);
  line-height: 1.3;
  margin-bottom: 2px;
}
.tech-desc {
  font-size: 11.5px;
  color: var(--color-text-muted);
  line-height: 1.5;
}

/* ═══════════════ CTA 区 ═══════════════ */
.cta-section {
  position: relative;
  padding: 100px 32px;
  background:
    linear-gradient(160deg, #1A1C2E 0%, #2B2D42 55%, #35395A 100%);
  text-align: center;
  overflow: hidden;
}
.cta-grain {
  position: absolute;
  inset: 0;
  pointer-events: none;
  background-image:
    radial-gradient(rgba(255, 255, 255, 0.03) 1px, transparent 1px);
  background-size: 4px 4px;
  opacity: 0.8;
}
.cta-corner {
  position: absolute;
  width: 56px; height: 56px;
  border: 1.5px solid rgba(255, 255, 255, 0.08);
  z-index: 1;
}
.cta-corner.tl { top: 32px; left: 32px; border-right: none; border-bottom: none; border-top-left-radius: 6px; }
.cta-corner.br { bottom: 32px; right: 32px; border-left: none; border-top: none; border-bottom-right-radius: 6px; }

.cta-inner {
  position: relative;
  z-index: 2;
  max-width: 680px;
  margin: 0 auto;
  display: flex;
  flex-direction: column;
  align-items: center;
}
.cta-eyebrow {
  color: rgba(242, 239, 232, 0.45);
  margin-bottom: 16px;
}
.cta-title {
  font-size: clamp(30px, 3.6vw, 46px);
  color: #F2EFE8;
  font-weight: 600;
  letter-spacing: -0.025em;
  line-height: 1.15;
  margin-bottom: 14px;
}
.cta-subtitle {
  font-size: 16px;
  color: rgba(242, 239, 232, 0.62);
  margin-bottom: 38px;
  max-width: 520px;
  line-height: 1.7;
}
.cta-actions {
  display: flex;
  align-items: center;
  gap: 14px;
  flex-wrap: wrap;
  justify-content: center;
}

/* ═══════════════ 页脚 ═══════════════ */
.footer {
  background: #141524;
  padding: 56px 32px 32px;
}
.footer-inner {
  max-width: 1280px;
  margin: 0 auto;
}
.footer-top {
  display: grid;
  grid-template-columns: 1.2fr 2fr;
  gap: 48px;
  margin-bottom: 40px;
}
.footer-brand {
  display: flex;
  align-items: center;
  gap: 12px;
}
.footer-brand__sigil {
  width: 40px; height: 40px;
  border-radius: 11px;
  background: linear-gradient(135deg, #4A4E7C 0%, #2B2D42 100%);
  color: #F2EFE8;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}
.footer-title {
  display: block;
  font-family: var(--font-serif);
  font-size: 20px;
  font-weight: 600;
  color: #F2EFE8;
  letter-spacing: 0.02em;
  line-height: 1;
  margin-bottom: 4px;
}
.footer-sub {
  display: block;
  font-size: 10px;
  letter-spacing: 0.14em;
  color: rgba(242, 239, 232, 0.35);
  font-weight: 600;
}

.footer-links {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 32px;
}
.footer-col h5 {
  font-size: 12px;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  color: rgba(242, 239, 232, 0.4);
  font-weight: 700;
  margin-bottom: 16px;
}
.footer-col a {
  display: block;
  font-size: 13.5px;
  color: rgba(242, 239, 232, 0.65);
  text-decoration: none;
  padding: 5px 0;
  transition: color 0.2s;
  cursor: pointer;
}
.footer-col a:hover { color: #F2EFE8; }

.footer-divider {
  height: 1px;
  background: linear-gradient(90deg, transparent, rgba(255,255,255,0.08), transparent);
  margin-bottom: 24px;
}
.footer-bottom {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 24px;
  flex-wrap: wrap;
}
.footer-desc {
  font-size: 12.5px;
  color: rgba(242, 239, 232, 0.4);
  line-height: 1.6;
}
.footer-copy {
  font-size: 11.5px;
  color: rgba(242, 239, 232, 0.3);
  letter-spacing: 0.02em;
  font-family: var(--font-mono);
}

/* ═══════════════ 响应式 ═══════════════ */
@media (max-width: 1100px) {
  .hero-inner { grid-template-columns: 1fr; gap: 48px; }
  .hero-stats-card { max-width: 520px; }
  .features-grid { grid-template-columns: repeat(2, 1fr); }
  .agents-grid { grid-template-columns: repeat(2, 1fr); }
  .portals-grid { grid-template-columns: 1fr; }
  .about-content { grid-template-columns: 1fr; gap: 36px; }
  .tech-card { position: static; }
  .footer-top { grid-template-columns: 1fr; gap: 36px; }
}

@media (max-width: 768px) {
  .nav-inner { padding: 0 20px; height: 60px; }
  .nav-links { display: none; }
  .hero { padding: 116px 20px 72px; }
  .section { padding: 72px 20px; }
  .hero-title .line { font-size: 38px; }
  .hero-stats-card { padding: 24px 20px 20px; }
  .stat-num { font-size: 36px; min-width: 72px; }
  .features-grid { grid-template-columns: 1fr; }
  .agents-grid { grid-template-columns: 1fr; }
  .footer-links { grid-template-columns: repeat(2, 1fr); gap: 24px; }
  .cta-section { padding: 72px 20px; }
  .btn-ink, .btn-outline { width: 100%; justify-content: center; }
}

@media (max-width: 480px) {
  .hero-cta { flex-direction: column; }
  .hero-cta > * { width: 100%; justify-content: center; }
  .footer-links { grid-template-columns: 1fr; }
  .footer-bottom { flex-direction: column; align-items: flex-start; }
}
</style>
