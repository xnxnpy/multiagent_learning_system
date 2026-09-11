<template>
  <div class="question-bank-page">
    <div class="page-header">
      <h2>题库</h2>
      <p class="page-sub">按阶段与知识点管理你的全部练习题</p>
    </div>

    <!-- 筛选栏 -->
    <el-card shadow="never" class="filter-card">
      <el-row :gutter="12" align="middle">
        <el-col :xs="24" :sm="8" :md="6">
          <el-select v-model="filters.status" placeholder="作答状态" clearable style="width: 100%" @change="load(1)">
            <el-option label="未作答" value="unanswered" />
            <el-option label="已答对" value="correct" />
            <el-option label="答错过" value="wrong" />
          </el-select>
        </el-col>
        <el-col :xs="24" :sm="8" :md="6">
          <el-input
            v-model="filters.knowledge_point"
            placeholder="知识点筛选"
            clearable
            @keyup.enter="load(1)"
            @clear="load(1)"
          />
        </el-col>
        <el-col :xs="24" :sm="8" :md="6">
          <el-button type="primary" plain @click="load(1)">查询</el-button>
        </el-col>
      </el-row>
    </el-card>

    <!-- 统计 -->
    <el-row :gutter="16" class="stats-row">
      <el-col :xs="12" :md="6">
        <el-card shadow="never" class="stat-card">
          <div class="stat-value">{{ total }}</div>
          <div class="stat-label">题目总数</div>
        </el-card>
      </el-col>
      <el-col :xs="12" :md="6">
        <el-card shadow="never" class="stat-card">
          <div class="stat-value" style="color: #22c55e">{{ correctCount }}</div>
          <div class="stat-label">已掌握</div>
        </el-card>
      </el-col>
      <el-col :xs="12" :md="6">
        <el-card shadow="never" class="stat-card">
          <div class="stat-value" style="color: #ef4444">{{ wrongCount }}</div>
          <div class="stat-label">答错过</div>
        </el-card>
      </el-col>
      <el-col :xs="12" :md="6">
        <el-card shadow="never" class="stat-card">
          <div class="stat-value" style="color: #f59e0b">{{ unansweredCount }}</div>
          <div class="stat-label">未作答</div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 题目列表 -->
    <el-card shadow="never" v-loading="loading">
      <el-empty v-if="!items.length && !loading" description="题库为空。进入学习阶段生成练习题后，这里会自动收录。" />
      <div v-for="item in items" :key="item.id" class="q-item">
        <div class="q-header">
          <el-tag size="small" :type="statusTagType(item)">{{ statusText(item) }}</el-tag>
          <el-tag v-if="item.knowledge_point" size="small" type="info" effect="plain">{{ item.knowledge_point }}</el-tag>
          <el-tag v-if="item.difficulty" size="small" effect="plain">{{ item.difficulty }}</el-tag>
          <span class="q-meta">作答 {{ item.attempt_count }} 次</span>
        </div>
        <div class="q-body" v-html="renderQuestion(item.question_data)" />
        <div v-if="item.last_correct !== null" class="q-result">
          最近一次：
          <el-tag size="small" :type="item.last_correct ? 'success' : 'danger'">
            {{ item.last_correct ? '正确' : '错误' }}
          </el-tag>
          <span v-if="item.last_score !== null" class="q-score">{{ item.last_score }} 分</span>
        </div>
      </div>

      <el-pagination
        v-if="total > pageSize"
        layout="prev, pager, next, total"
        :total="total"
        :page-size="pageSize"
        :current-page="page"
        class="pager"
        @current-change="load"
      />
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, computed } from 'vue'
import { studentAPI } from '@/api'

const loading = ref(false)
const items = ref<any[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = 20

const filters = reactive({
  status: '',
  knowledge_point: '',
})

const correctCount = computed(() => items.value.filter(i => i.last_correct === true).length)
const wrongCount = computed(() => items.value.filter(i => i.last_correct === false).length)
const unansweredCount = computed(() => items.value.filter(i => i.attempt_count === 0).length)

async function load(p = page.value) {
  page.value = p
  loading.value = true
  try {
    const res: any = await studentAPI.getQuestionBank({
      page,
      page_size: pageSize,
      status: filters.status || undefined,
      knowledge_point: filters.knowledge_point || undefined,
    })
    items.value = res?.items || []
    total.value = res?.total || 0
  } catch {
    items.value = []
    total.value = 0
  } finally {
    loading.value = false
  }
}

function statusText(item: any) {
  if (item.attempt_count === 0) return '未作答'
  return item.last_correct ? '已掌握' : '待重练'
}

function statusTagType(item: any) {
  if (item.attempt_count === 0) return 'info' as const
  return item.last_correct ? ('success' as const) : ('danger' as const)
}

function renderQuestion(q: any): string {
  if (!q) return ''
  const text = q.question || ''
  const options = Array.isArray(q.options) ? q.options : []
  let html = escapeHtml(text)
  if (options.length) {
    html += '<ul class="opts">' + options.map((o: any, i: number) =>
      `<li>${String.fromCharCode(65 + i)}. ${escapeHtml(String(o))}</li>`
    ).join('') + '</ul>'
  }
  return html
}

function escapeHtml(s: string) {
  return s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
}

onMounted(() => load(1))
</script>

<style scoped>
.question-bank-page { max-width: 1000px; }
.page-header h2 { margin: 0 0 4px; }
.page-sub { color: var(--el-text-color-secondary); margin: 0 0 16px; font-size: 13px; }
.filter-card { margin-bottom: 16px; }
.stats-row { margin-bottom: 16px; }
.stat-card { text-align: center; }
.stat-value { font-size: 28px; font-weight: 600; }
.stat-label { color: var(--el-text-color-secondary); font-size: 13px; margin-top: 4px; }
.q-item { padding: 16px 0; border-bottom: 1px solid var(--el-border-color-lighter); }
.q-item:last-child { border-bottom: none; }
.q-header { display: flex; gap: 8px; align-items: center; flex-wrap: wrap; margin-bottom: 8px; }
.q-meta { color: var(--el-text-color-secondary); font-size: 12px; margin-left: auto; }
.q-body { line-height: 1.7; }
.q-body :deep(.opts) { margin: 8px 0 0; padding-left: 20px; color: var(--el-text-color-regular); }
.q-result { margin-top: 8px; font-size: 13px; color: var(--el-text-color-secondary); display: flex; gap: 8px; align-items: center; }
.q-score { font-weight: 600; }
.pager { margin-top: 16px; justify-content: center; }
.empty-stage-alert { margin-bottom: 16px; }
</style>
