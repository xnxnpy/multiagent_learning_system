<template>
  <div class="report-page">
    <div class="page-header">
      <h2 class="page-title">学习报告</h2>
      <el-button type="primary" :icon="Refresh" :loading="loading" @click="fetchReport">
        刷新报告
      </el-button>
    </div>

    <!-- Stat cards -->
    <el-row :gutter="20" class="stat-row">
      <el-col :xs="12" :sm="6" v-for="card in statCards" :key="card.label">
        <div class="stat-card">
          <div class="stat-icon" :style="{ background: card.bg }">
            <el-icon :size="24" :color="card.color"><component :is="card.icon" /></el-icon>
          </div>
          <div class="stat-info">
            <span class="stat-value">{{ card.value }}</span>
            <span class="stat-label">{{ card.label }}</span>
          </div>
        </div>
      </el-col>
    </el-row>

    <!-- Radar chart + Suggestions -->
    <el-row :gutter="24" class="section-row">
      <el-col :xs="24" :lg="12">
        <el-card class="content-card" shadow="never">
          <template #header>
            <div class="card-header">
              <span class="card-title">知识点掌握雷达图</span>
            </div>
          </template>
          <div ref="radarRef" class="chart-container"></div>
        </el-card>
      </el-col>

      <el-col :xs="24" :lg="12">
        <el-card class="content-card" shadow="never">
          <template #header>
            <div class="card-header">
              <span class="card-title">学习建议</span>
            </div>
          </template>
          <div v-if="report.analysis?.suggestions?.length" class="suggestion-list">
            <div
              v-for="(s, i) in report.analysis.suggestions"
              :key="i"
              class="suggestion-item"
            >
              <el-icon color="var(--color-warning)"><Warning /></el-icon>
              <span>{{ s }}</span>
            </div>
          </div>
          <el-empty v-else description="暂无建议" :image-size="80" />
        </el-card>
      </el-col>
    </el-row>

    <!-- Knowledge points detail -->
    <el-card class="content-card section-row" shadow="never">
      <template #header>
        <div class="card-header">
          <span class="card-title">各知识点详情</span>
        </div>
      </template>
      <el-table :data="report.knowledge_points" stripe style="width: 100%">
        <el-table-column prop="topic" label="知识点" min-width="160" />
        <el-table-column label="得分" width="80" align="center">
          <template #default="{ row }">
            <span v-if="row.total > 0">{{ row.score }}</span>
            <span v-else class="text-muted">-</span>
          </template>
        </el-table-column>
        <el-table-column label="满分" width="80" align="center">
          <template #default="{ row }">
            <span v-if="row.total > 0">{{ row.total }}</span>
            <span v-else class="text-muted">-</span>
          </template>
        </el-table-column>
        <el-table-column label="掌握度" width="200">
          <template #default="{ row }">
            <el-progress
              v-if="row.total > 0"
              :percentage="Math.round(row.mastery * 100)"
              :status="progressStatus(row.mastery)"
              :stroke-width="8"
            />
            <span v-else class="text-muted">未评分</span>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="100" align="center">
          <template #default="{ row }">
            <el-tag :type="statusTagType(row.status)" effect="plain" size="small">
              {{ row.status }}
            </el-tag>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 学习趋势 + 资源分布 -->
    <el-row :gutter="24" class="section-row">
      <el-col :xs="24" :lg="14">
        <el-card class="content-card" shadow="never">
          <template #header>
            <div class="card-header">
              <span class="card-title">近7天学习趋势</span>
              <el-tag size="small" type="info">日均 {{ summaryStats.avgDaily }} 分钟</el-tag>
            </div>
          </template>
          <div ref="trendRef" class="chart-container" style="height: 260px;"></div>
          <div v-if="!summary.daily_stats?.length" class="chart-empty">暂无学习数据</div>
        </el-card>
      </el-col>
      <el-col :xs="24" :lg="10">
        <el-card class="content-card" shadow="never">
          <template #header>
            <div class="card-header">
              <span class="card-title">行为分布</span>
            </div>
          </template>
          <div ref="pieRef" class="chart-container" style="height: 260px;"></div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 学习行为统计卡片 -->
    <el-row :gutter="20" class="stat-row">
      <el-col :xs="12" :sm="6">
        <div class="stat-card">
          <div class="stat-info">
            <span class="stat-value">{{ summaryStats.totalStudy }}</span>
            <span class="stat-label">总学习时长</span>
          </div>
        </div>
      </el-col>
      <el-col :xs="12" :sm="6">
        <div class="stat-card">
          <div class="stat-info">
            <span class="stat-value">{{ summary.resource_access_count || 0 }}</span>
            <span class="stat-label">资源访问次数</span>
          </div>
        </div>
      </el-col>
      <el-col :xs="12" :sm="6">
        <div class="stat-card">
          <div class="stat-info">
            <span class="stat-value">{{ summary.avg_session_duration || 0 }}分钟</span>
            <span class="stat-label">平均单次时长</span>
          </div>
        </div>
      </el-col>
      <el-col :xs="12" :sm="6">
        <div class="stat-card">
          <div class="stat-info">
            <span class="stat-value">{{ summary.learning_streak || 0 }}天</span>
            <span class="stat-label">连续学习</span>
          </div>
        </div>
      </el-col>
    </el-row>

    <!-- Detailed report text -->
    <el-card v-if="report.report" class="content-card section-row" shadow="never">
      <template #header>
        <div class="card-header">
          <span class="card-title">详细评估报告</span>
        </div>
      </template>
      <div class="report-text">{{ report.report }}</div>
    </el-card>

    <!-- Loop improvement -->
    <el-card class="content-card loop-card section-row" shadow="never">
      <template #header>
        <div class="card-header">
          <el-icon :size="20" color="var(--color-primary)"><DataAnalysis /></el-icon>
          <span class="card-title">循环提升</span>
        </div>
      </template>
      <p class="loop-desc">根据评估结果，您可以采取以下行动来持续提升学习效果：</p>
      <div class="loop-actions">
        <el-button type="primary" :icon="Edit" @click="router.push('/student/profile')">
          更新画像
        </el-button>
        <el-button type="success" :icon="RefreshRight" :loading="regenerating" @click="regeneratePath">
          重新规划路径
        </el-button>
        <el-button :icon="Document" @click="router.push('/student/resources')">
          继续学习
        </el-button>
      </div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted, onBeforeUnmount, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import {
  Refresh,
  Warning,
  Edit,
  RefreshRight,
  Document,
  DataAnalysis,
  Trophy,
  Timer,
  Aim,
  TrendCharts,
} from '@element-plus/icons-vue'
import * as echarts from 'echarts'
import { studentAPI } from '@/api'
import request from '@/utils/axios'
import type { EvaluationReport } from '@/types'

const router = useRouter()

/* ── Report state ────────────────────────────── */

const loading = ref(false)
const regenerating = ref(false)

const report = reactive<EvaluationReport>({
  overall_grade: '',
  total_score: 0,
  total_attempts: 0,
  accuracy_rate: 0,
  mastery_level: 0,
  analysis: { strengths: [], weaknesses: [], suggestions: [] },
  knowledge_points: [],
  report: '',
})

/* ── Stat cards computed ─────────────────────── */

const statCards = computed(() => [
  {
    label: '评估等级',
    value: report.overall_grade || '--',
    icon: Trophy,
    color: 'var(--color-warning)',
    bg: 'var(--color-warning-light)',
  },
  {
    label: '总分',
    value: report.total_score || 0,
    icon: TrendCharts,
    color: 'var(--color-primary)',
    bg: 'var(--color-primary-lightest)',
  },
  {
    label: '答题数',
    value: report.total_attempts || 0,
    icon: Timer,
    color: 'var(--color-info)',
    bg: 'var(--color-info-light)',
  },
  {
    label: '正确率',
    value: `${((report.accuracy_rate || 0) * 100).toFixed(1)}%`,
    icon: Aim,
    color: 'var(--color-success)',
    bg: 'var(--color-success-light)',
  },
])

/* ── Helpers ─────────────────────────────────── */

function progressStatus(mastery: number): 'success' | 'warning' | 'exception' | '' {
  if (mastery <= 0) return '' // el-progress 不支持 'info'，未评分用默认状态
  if (mastery >= 0.7) return 'success'
  if (mastery >= 0.5) return 'warning'
  return 'exception'
}

function statusTagType(status: string): '' | 'success' | 'warning' | 'danger' | 'info' {
  const map: Record<string, '' | 'success' | 'warning' | 'danger' | 'info'> = {
    掌握: 'success',
    学习中: 'warning',
    薄弱: 'danger',
    未学习: 'info',
  }
  return map[status] || ''
}

/* ── ECharts radar ───────────────────────────── */

const radarRef = ref<HTMLElement | null>(null)
let chartInstance: echarts.ECharts | null = null

function initRadarChart() {
  if (!radarRef.value) return

  if (chartInstance) {
    chartInstance.dispose()
  }
  chartInstance = echarts.init(radarRef.value)

  const kps = report.knowledge_points || []
  const indicators = kps.length
    ? kps.map((kp) => ({ name: kp.topic, max: 1 }))
    : [{ name: '暂无数据', max: 1 }]

  chartInstance.setOption({
    tooltip: { trigger: 'item' },
    radar: {
      indicator: indicators,
      radius: '65%',
      axisName: { fontSize: 12, color: 'var(--color-text-secondary)' },
      splitArea: {
        areaStyle: {
          color: ['rgba(79,70,229,0.02)', 'rgba(79,70,229,0.05)'],
        },
      },
    },
    series: [
      {
        type: 'radar',
        data: [
          {
            value: kps.map((kp) => kp.mastery),
            name: '掌握度',
            areaStyle: { color: 'rgba(79,70,229,0.18)' },
            lineStyle: { color: '#4F46E5', width: 2 },
            itemStyle: { color: '#4F46E5' },
          },
        ],
      },
    ],
  })
}

function handleResize() {
  chartInstance?.resize()
  trendChart?.resize()
  pieChart?.resize()
}

/* ── Fetch report ────────────────────────────── */

const summary = ref<any>({})
const trendRef = ref<HTMLElement | null>(null)
const pieRef = ref<HTMLElement | null>(null)
let trendChart: echarts.ECharts | null = null
let pieChart: echarts.ECharts | null = null

const summaryStats = computed(() => {
  const totalSec = summary.value.total_study_time || 0
  const hours = Math.floor(totalSec / 3600)
  const mins = Math.floor((totalSec % 3600) / 60)
  const totalStudy = hours > 0 ? `${hours}小时${mins}分钟` : `${mins}分钟`
  const daily = summary.value.daily_stats || []
  const totalDaily = daily.reduce((s: number, d: any) => s + (d.duration || 0), 0)
  const avgDaily = daily.length > 0 ? Math.round(totalDaily / daily.length / 60) : 0
  return { totalStudy, avgDaily }
})

function initTrendChart() {
  const data = summary.value.daily_stats || []
  if (!trendRef.value || !data.length) return
  if (trendChart) trendChart.dispose()
  trendChart = echarts.init(trendRef.value)
  trendChart.setOption({
    tooltip: { trigger: 'axis', formatter: '{b}<br/>学习时长: {c} 分钟' },
    grid: { top: 10, right: 20, bottom: 30, left: 50 },
    xAxis: {
      type: 'category',
      data: data.map((d: any) => d.date?.slice(5) || ''),
      axisLabel: { fontSize: 11 },
    },
    yAxis: {
      type: 'value',
      name: '分钟',
      axisLabel: { fontSize: 11 },
    },
    series: [{
      type: 'bar',
      data: data.map((d: any) => Math.round((d.duration || 0) / 60)),
      itemStyle: {
        color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
          { offset: 0, color: '#6366f1' },
          { offset: 1, color: '#a78bfa' },
        ]),
        borderRadius: [4, 4, 0, 0],
      },
      barWidth: '40%',
    }],
  })
}

function initPieChart() {
  if (!pieRef.value) return
  const counts = summary.value.event_type_counts || {}
  const typeLabels: Record<string, string> = {
    question: '答题', resource_view: '资源浏览', code_execute: '代码运行',
    resource_page: '页面访问', stage_start: '阶段学习', stage_complete: '阶段完成',
    chat_message: '辅导对话', profile_chat: '画像对话',
  }
  const pieData = Object.entries(counts)
    .map(([k, v]) => ({ name: typeLabels[k] || k, value: v }))
    .filter((d: any) => d.value > 0)
  if (!pieData.length) return
  if (pieChart) pieChart.dispose()
  pieChart = echarts.init(pieRef.value)
  pieChart.setOption({
    tooltip: { trigger: 'item', formatter: '{b}: {c} ({d}%)' },
    series: [{
      type: 'pie',
      radius: ['40%', '70%'],
      data: pieData,
      label: { fontSize: 12 },
      itemStyle: { borderRadius: 6 },
    }],
  })
}

async function fetchReport() {
  loading.value = true
  try {
    const [reportRes, summaryRes] = await Promise.all([
      studentAPI.getReport(),
      request.get('/v1/student/progress/summary').catch(() => null),
    ])
    if (reportRes) {
      Object.assign(report, reportRes)
    }
    if (summaryRes) {
      summary.value = summaryRes
    }
    await nextTick()
    initRadarChart()
    initTrendChart()
    initPieChart()
  } catch {
    ElMessage.error('获取报告失败')
  } finally {
    loading.value = false
  }
}

/* ── Regenerate path ─────────────────────────── */

async function regeneratePath() {
  regenerating.value = true
  try {
    localStorage.removeItem('learning_path_current_stage')

    const startRes: any = await request.post('/v1/student/learn/start')
    const sessionId = startRes.session_id

    ElMessage.info('正在重新规划学习路径...')

    const { createWorkflowWebSocket } = await import('@/utils/websocket')
    const token = localStorage.getItem('token') || ''
    const ws = createWorkflowWebSocket(token)

    await new Promise<void>((resolve, reject) => {
      let finished = false

      ws.on('message', (data: any) => {
        if (data.type === 'complete') {
          if (finished) return
          finished = true
          ws.close()
          resolve()
        } else if (data.type === 'error') {
          if (finished) return
          finished = true
          ws.close()
          reject(new Error(data.message))
        }
      })

      ws.on('error', () => {
        if (!finished) {
          finished = true
          reject(new Error('WebSocket 连接失败'))
        }
      })

      ws.connect(token).then(() => {
        ws.send({ type: 'start', session_id: sessionId })
      }).catch(reject)
    })

    ElMessage.success('学习路径已重新规划！')
    router.push('/student/learning-path')
  } catch {
    ElMessage.error('重新规划失败，请重试')
  } finally {
    regenerating.value = false
  }
}

/* ── Lifecycle ───────────────────────────────── */

onMounted(() => {
  fetchReport()
  window.addEventListener('resize', handleResize)
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', handleResize)
  chartInstance?.dispose()
  trendChart?.dispose()
  pieChart?.dispose()
})
</script>

<style scoped>
.report-page { max-width: 1400px; }

.text-muted { color: var(--color-text-placeholder, #c0c4cc); font-size: 12px; }

.page-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: var(--space-section-gap);
}

.page-title {
  font-size: var(--text-xl);
  font-weight: 700;
  color: var(--color-text-primary);
}

/* ── Stat cards ─────────────────────────────── */

.stat-row {
  margin-bottom: var(--space-card-gap);
}

.stat-card {
  display: flex;
  align-items: center;
  gap: 16px;
  background: var(--color-bg-card);
  border-radius: var(--radius-lg);
  padding: 20px;
  box-shadow: var(--shadow-card);
  border: 1px solid var(--color-border-light);
  transition: box-shadow var(--transition-fast);
}

.stat-card:hover {
  box-shadow: var(--shadow-card-hover);
}

.stat-icon {
  width: 48px;
  height: 48px;
  border-radius: var(--radius-md);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.stat-info {
  display: flex;
  flex-direction: column;
}

.stat-value {
  font-size: var(--text-2xl);
  font-weight: 800;
  color: var(--color-text-primary);
  font-variant-numeric: tabular-nums;
  letter-spacing: -0.02em;
}

.stat-label {
  font-size: var(--text-sm);
  color: var(--color-text-muted);
  margin-top: 2px;
}

/* ── Content cards ──────────────────────────── */

.content-card {
  background: var(--color-bg-card);
  border-radius: var(--radius-lg);
  border: 1px solid var(--color-border-light);
}

.section-row {
  margin-bottom: var(--space-card-gap);
}

.card-header {
  display: flex;
  align-items: center;
  gap: 8px;
}

.card-title {
  font-weight: 600;
  font-size: var(--text-lg);
  color: var(--color-text-primary);
}

.chart-container {
  width: 100%;
  height: 380px;
  position: relative;
}

.chart-empty {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--color-text-muted);
  font-size: 13px;
}

/* ── Suggestions ────────────────────────────── */

.suggestion-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.suggestion-item {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  font-size: var(--text-base);
  color: var(--color-text-primary);
  line-height: 1.6;
}

.suggestion-item .el-icon {
  margin-top: 3px;
  flex-shrink: 0;
}

/* ── Report text ────────────────────────────── */

.report-text {
  white-space: pre-wrap;
  line-height: 1.8;
  color: var(--color-text-primary);
  font-size: var(--text-base);
  background: var(--color-bg-page);
  padding: 16px;
  border-radius: var(--radius-md);
}

/* ── Loop card ──────────────────────────────── */

.loop-card {
  background: linear-gradient(135deg, var(--color-primary-lightest) 0%, #E8F5E9 100%);
  border: none;
}

.loop-desc {
  color: var(--color-text-secondary);
  margin-bottom: 16px;
  font-size: var(--text-base);
}

.loop-actions {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
}
</style>
