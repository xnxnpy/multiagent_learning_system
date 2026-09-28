<template>
  <div class="admin-analytics">
    <div class="page-header">
      <h2>学习活动分析</h2>
      <p class="page-sub">日活趋势 · 时段分布 · 需求类型 · 风险学生</p>
      <el-button size="small" type="primary" plain :loading="loading" @click="load">刷新</el-button>
    </div>

    <el-row :gutter="16" class="kpis">
      <el-col :xs="12" :md="6" v-for="k in kpis" :key="k.label">
        <el-card shadow="never" class="kpi">
          <div class="v" :style="{ color: k.color }">{{ k.value }}</div>
          <div class="l">{{ k.label }}</div>
        </el-card>
      </el-col>
    </el-row>

    <el-row :gutter="16">
      <el-col :xs="24" :lg="14">
        <el-card shadow="never" class="card">
          <template #header>近 14 天日活</template>
          <div ref="dailyRef" class="chart" />
        </el-card>
      </el-col>
      <el-col :xs="24" :lg="10">
        <el-card shadow="never" class="card">
          <template #header>学习时段分布（24h）</template>
          <div ref="hourRef" class="chart" />
        </el-card>
      </el-col>
    </el-row>

    <el-card shadow="never" class="card">
      <template #header>需求类型占比</template>
      <div class="share-list">
        <div v-for="s in typeShare" :key="s.name" class="share-row">
          <span class="name">{{ s.name }}</span>
          <el-progress :percentage="s.value" :stroke-width="10" style="flex: 1" />
        </div>
        <el-empty v-if="!typeShare.length" description="暂无数据" :image-size="60" />
      </div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onBeforeUnmount, nextTick } from 'vue'
import { adminAPI } from '@/api'
import * as echarts from 'echarts'

const loading = ref(false)
const dailyRef = ref<HTMLElement | null>(null)
const hourRef = ref<HTMLElement | null>(null)
let dailyChart: echarts.ECharts | null = null
let hourChart: echarts.ECharts | null = null

const data = ref<any>({
  total_users: 0,
  total_students: 0,
  risk_students: 0,
  daily_active: [],
  hour_distribution: [],
  type_share: [],
})

const kpis = computed(() => [
  { label: '总用户', value: data.value.total_users, color: '#2B2D42' },
  { label: '学生数', value: data.value.total_students, color: '#B0512C' },
  { label: '风险学生', value: data.value.risk_students, color: '#DC2626' },
  { label: '今日活跃', value: data.value.daily_active?.slice(-1)?.[0]?.active_users ?? 0, color: '#3D6B4F' },
])
const typeShare = computed(() => {
  const TYPE_LABELS: Record<string, string> = {
    resource_view: '资源浏览',
    question: '答题练习',
    code_execute: '代码运行',
    stage_start: '开始阶段',
    stage_complete: '完成阶段',
    chat_message: '辅导对话',
    profile_chat: '画像对话',
    resource_page: '页面访问',
    wrong_book: '错题重练',
    note: '学习笔记',
  }
  return (data.value.type_share || []).map(s => ({
    ...s,
    name: TYPE_LABELS[s.name] || s.name,
  }))
})

async function load() {
  loading.value = true
  try {
    data.value = await adminAPI.getLearningAnalytics()
    await nextTick()
    renderCharts()
  } catch {
    /* ignore */
  } finally {
    loading.value = false
  }
}

function renderCharts() {
  if (dailyRef.value) {
    if (dailyChart) dailyChart.dispose()
    dailyChart = echarts.init(dailyRef.value)
    const daily = data.value.daily_active || []
    dailyChart.setOption({
      tooltip: { trigger: 'axis' },
      grid: { left: 40, right: 16, top: 24, bottom: 30 },
      xAxis: { type: 'category', data: daily.map((d: any) => d.date.slice(5)) },
      yAxis: { type: 'value', minInterval: 1 },
      series: [{
        type: 'line',
        smooth: true,
        data: daily.map((d: any) => d.active_users),
        areaStyle: { opacity: 0.15 },
        itemStyle: { color: '#B0512C' },
      }],
    })
  }
  if (hourRef.value) {
    if (hourChart) hourChart.dispose()
    hourChart = echarts.init(hourRef.value)
    const hours = data.value.hour_distribution || []
    hourChart.setOption({
      tooltip: { trigger: 'axis' },
      grid: { left: 40, right: 8, top: 16, bottom: 30 },
      xAxis: { type: 'category', data: hours.map((h: any) => h.hour) },
      yAxis: { type: 'value' },
      series: [{
        type: 'bar',
        data: hours.map((h: any) => h.count),
        itemStyle: { color: '#4F46E5', borderRadius: [3, 3, 0, 0] },
      }],
    })
  }
}

function onResize() {
  dailyChart?.resize()
  hourChart?.resize()
}

onMounted(() => {
  load()
  window.addEventListener('resize', onResize)
})
onBeforeUnmount(() => {
  window.removeEventListener('resize', onResize)
  dailyChart?.dispose()
  hourChart?.dispose()
})
</script>

<style scoped>
.admin-analytics { max-width: 1200px; }
.page-header { display: flex; align-items: center; gap: 12px; flex-wrap: wrap; margin-bottom: 16px; }
.page-header h2 { margin: 0; }
.page-sub { color: var(--el-text-color-secondary); font-size: 13px; margin: 0; flex: 1; }
.kpis { margin-bottom: 16px; }
.kpi { text-align: center; }
.kpi .v { font-size: 28px; font-weight: 700; }
.kpi .l { font-size: 12px; color: var(--el-text-color-secondary); margin-top: 4px; }
.card { margin-bottom: 16px; }
.chart { height: 260px; width: 100%; }
.share-row { display: flex; align-items: center; gap: 12px; margin-bottom: 10px; }
.share-row .name { width: 120px; font-size: 13px; }
</style>
