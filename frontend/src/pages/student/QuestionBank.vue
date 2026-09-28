<template>
  <div class="question-bank-page">
    <div class="page-header">
      <h2>题库</h2>
      <p class="page-sub">按阶段与知识点管理你的全部练习题</p>
    </div>

    <!-- 筛选栏 -->
    <div class="filter-bar">
      <div class="filter-chips">
        <button
          v-for="s in statusOptions"
          :key="s.value"
          class="chip"
          :class="{ active: (filters.status || '') === s.value }"
          @click="filters.status = s.value; load(1)"
        >{{ s.label }}</button>
      </div>
      <div class="filter-actions">
        <el-input
          v-model="filters.knowledge_point"
          placeholder="知识点筛选"
          clearable
          size="default"
          class="kp-input"
          @keyup.enter="load(1)"
          @clear="load(1)"
        />
        <el-button type="primary" @click="load(1)">查询</el-button>
      </div>
    </div>

    <!-- 统计 -->
    <el-row :gutter="14" class="stats-row">
      <el-col :xs="12" :md="6">
        <div class="stat-tile primary">
          <div class="stat-value">{{ total }}</div>
          <div class="stat-label">题目总数</div>
        </div>
      </el-col>
      <el-col :xs="12" :md="6">
        <div class="stat-tile success">
          <div class="stat-value">{{ correctCount }}</div>
          <div class="stat-label">本页答对</div>
        </div>
      </el-col>
      <el-col :xs="12" :md="6">
        <div class="stat-tile danger">
          <div class="stat-value">{{ wrongCount }}</div>
          <div class="stat-label">本页答错</div>
        </div>
      </el-col>
      <el-col :xs="12" :md="6">
        <div class="stat-tile warning">
          <div class="stat-value">{{ unansweredCount }}</div>
          <div class="stat-label">本页未作答</div>
        </div>
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

        <!-- 作答区 -->
        <div class="q-actions">
          <el-button
            size="small"
            :type="expandedId === item.question_uid ? 'info' : 'primary'"
            plain
            @click="toggleAnswer(item)"
          >
            {{ expandedId === item.question_uid ? '收起' : (item.attempt_count > 0 ? '再练一次' : '作答') }}
          </el-button>
        </div>

        <div v-if="expandedId === item.question_uid" class="answer-panel">
          <div v-if="qType(item) === 'choice'" class="answer-options">
            <el-radio-group v-model="answers[item.question_uid]">
              <el-radio
                v-for="(opt, oi) in (item.question_data?.options || [])"
                :key="oi"
                :value="String(opt)"
                class="option-radio"
              >
                {{ String.fromCharCode(65 + oi) }}. {{ opt }}
              </el-radio>
            </el-radio-group>
          </div>
          <div v-else-if="qType(item) === 'judge'" class="answer-options">
            <el-radio-group v-model="answers[item.question_uid]">
              <el-radio value="正确" class="option-radio">正确</el-radio>
              <el-radio value="错误" class="option-radio">错误</el-radio>
            </el-radio-group>
          </div>
          <el-input
            v-else-if="qType(item) === 'code' || qType(item) === 'case_analysis'"
            v-model="answers[item.question_uid]"
            :type="qType(item) === 'code' ? 'textarea' : 'textarea'"
            :rows="6"
            :placeholder="qType(item) === 'code' ? '请输入 Python 代码...' : '请输入你的分析...'"
          />
          <el-input
            v-else
            v-model="answers[item.question_uid]"
            placeholder="请输入答案..."
          />

          <div class="answer-submit-row">
            <el-button
              type="primary"
              size="small"
              :loading="submittingId === item.question_uid"
              @click="submitOne(item)"
            >
              提交答案
            </el-button>
          </div>

          <div v-if="results[item.question_uid]" class="answer-feedback" :class="results[item.question_uid].correct ? 'ok' : 'bad'">
            <template v-if="results[item.question_uid].code_results?.results">
              <div v-for="(r, ri) in results[item.question_uid].code_results.results" :key="ri">
                用例{{ r.test_case }}: {{ r.status === 'passed' ? '✓ 通过' : '✗ 失败' }}{{ r.error ? ' - ' + r.error : '' }}
              </div>
            </template>
            <template v-else>
              <span v-if="results[item.question_uid].correct">✓ 回答正确！得分：{{ results[item.question_uid].score }}</span>
              <span v-else>
                ✗ 回答错误。正确答案：{{ item.question_data?.answer }}，得分：{{ results[item.question_uid].score }}
              </span>
            </template>
            <div v-if="results[item.question_uid].feedback && qType(item) !== 'code'" class="fb-text">
              {{ results[item.question_uid].feedback }}
            </div>
          </div>
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
import { ElMessage } from 'element-plus'
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

const statusOptions = [
  { value: '', label: '全部' },
  { value: 'unanswered', label: '未作答' },
  { value: 'correct', label: '已答对' },
  { value: 'wrong', label: '答错过' },
]

// ── 作答状态 ──
const expandedId = ref<string | null>(null)
const answers = reactive<Record<string, string>>({})
const results = reactive<Record<string, any>>({})
const submittingId = ref<string | null>(null)

const correctCount = computed(() => items.value.filter(i => i.last_correct === true).length)
const wrongCount = computed(() => items.value.filter(i => i.last_correct === false).length)
const unansweredCount = computed(() => items.value.filter(i => i.attempt_count === 0).length)

async function load(p = page.value) {
  page.value = p
  loading.value = true
  try {
    const res: any = await studentAPI.getQuestionBank({
      page: page.value,
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

function qType(item: any): string {
  return item?.question_data?.type || 'blank'
}

function toggleAnswer(item: any) {
  const uid = item.question_uid
  if (expandedId.value === uid) {
    expandedId.value = null
    return
  }
  expandedId.value = uid
  if (!(uid in answers)) answers[uid] = ''
  delete results[uid]
}

async function submitOne(item: any) {
  const uid = item.question_uid
  const answer = (answers[uid] || '').trim()
  if (!answer) {
    ElMessage.warning('请先作答再提交')
    return
  }
  submittingId.value = uid
  try {
    const res: any = await studentAPI.submitAnswer({
      question_id: Number(item.question_data?.question_id) || 0,
      answer,
      topic: item.knowledge_point || item.question_data?.knowledge_point || '',
      ...(item.stage_id != null ? { stage_id: item.stage_id } : {}),
      question_uid: uid,
    })
    const ev = res?.evaluations?.[0]
    if (ev) {
      results[uid] = ev
      item.attempt_count = (item.attempt_count || 0) + 1
      item.last_correct = ev.correct
      item.last_score = ev.score
      if (ev.correct) ElMessage.success('回答正确！')
      else ElMessage.info('已提交，再接再厉')
    }
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || '提交失败，请重试')
  } finally {
    submittingId.value = null
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
.page-header h2 {
  margin: 0 0 4px;
  padding-left: 12px;
  border-left: 4px solid #B0512C;
  line-height: 1.2;
}
.page-sub { color: var(--el-text-color-secondary); margin: 0 0 16px; font-size: 13px; padding-left: 16px; }

.filter-bar {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  align-items: center;
  justify-content: space-between;
  background: #fff;
  border: 1px solid var(--el-border-color-lighter);
  border-radius: 12px;
  padding: 12px 16px;
  margin-bottom: 14px;
}
.filter-chips { display: flex; gap: 8px; flex-wrap: wrap; }
.chip {
  border: 1px solid var(--el-border-color);
  background: #fff;
  border-radius: 999px;
  padding: 6px 16px;
  font-size: 13px;
  cursor: pointer;
  color: var(--el-text-color-regular);
  transition: all 0.15s;
}
.chip:hover { border-color: #B0512C; color: #B0512C; }
.chip.active {
  background: #2B2D42;
  border-color: #2B2D42;
  color: #fff;
}
.filter-actions { display: flex; gap: 8px; }
.kp-input { width: 200px; }

.stats-row { margin-bottom: 16px; }
.stat-tile {
  background: #fff;
  border-radius: 12px;
  padding: 16px;
  text-align: center;
  border-top: 3px solid transparent;
  box-shadow: 0 1px 4px rgba(0,0,0,0.04);
}
.stat-tile.primary { border-top-color: #4F46E5; }
.stat-tile.success { border-top-color: #22c55e; }
.stat-tile.danger { border-top-color: #ef4444; }
.stat-tile.warning { border-top-color: #f59e0b; }
.stat-tile .stat-value { font-size: 26px; font-weight: 700; }
.stat-tile .stat-label { color: var(--el-text-color-secondary); font-size: 12px; margin-top: 4px; }

.q-item {
  padding: 16px;
  border-bottom: 1px solid var(--el-border-color-lighter);
  border-radius: 10px;
  transition: background 0.15s;
}
.q-item:hover { background: var(--el-fill-color-lighter); }
.q-item:last-child { border-bottom: none; }
.q-header { display: flex; gap: 8px; align-items: center; flex-wrap: wrap; margin-bottom: 8px; }
.q-meta { color: var(--el-text-color-secondary); font-size: 12px; margin-left: auto; }
.q-body { line-height: 1.7; }
.q-body :deep(.opts) { margin: 8px 0 0; padding-left: 20px; color: var(--el-text-color-regular); }
.q-result { margin-top: 8px; font-size: 13px; color: var(--el-text-color-secondary); display: flex; gap: 8px; align-items: center; }
.q-score { font-weight: 600; }
.q-actions { margin-top: 10px; display: flex; gap: 8px; }
.answer-panel {
  margin-top: 12px;
  padding: 14px 16px;
  background: var(--el-fill-color-light);
  border: 1px solid var(--el-border-color-lighter);
  border-radius: 8px;
}
.answer-options { display: flex; flex-direction: column; gap: 6px; }
.option-radio { margin-right: 0; height: auto; padding: 4px 0; white-space: normal; }
.answer-submit-row { margin-top: 12px; display: flex; justify-content: flex-end; }
.answer-feedback {
  margin-top: 10px;
  padding: 10px 12px;
  border-radius: 6px;
  font-size: 13px;
  line-height: 1.6;
}
.answer-feedback.ok { background: #ecfdf5; color: #047857; }
.answer-feedback.bad { background: #fef2f2; color: #b91c1c; }
.fb-text { margin-top: 4px; opacity: 0.85; }
.pager { margin-top: 16px; justify-content: center; }
.empty-stage-alert { margin-bottom: 16px; }
</style>
