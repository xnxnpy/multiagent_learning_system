<template>
  <div class="wrong-book-page">
    <div class="page-header">
      <h2>错题本</h2>
      <p class="page-sub">答错的题目会自动进入这里，重练正确后自动移出</p>
    </div>

    <!-- 统计 -->
    <el-row :gutter="16" class="stats-row">
      <el-col :xs="8" :md="6">
        <el-card shadow="never" class="stat-card">
          <div class="stat-value" style="color: #ef4444">{{ stats.active }}</div>
          <div class="stat-label">待重练</div>
        </el-card>
      </el-col>
      <el-col :xs="8" :md="6">
        <el-card shadow="never" class="stat-card">
          <div class="stat-value" style="color: #22c55e">{{ stats.mastered }}</div>
          <div class="stat-label">已攻克</div>
        </el-card>
      </el-col>
      <el-col :xs="8" :md="6">
        <el-card shadow="never" class="stat-card">
          <div class="stat-value">{{ Object.keys(stats.by_knowledge_point || {}).length }}</div>
          <div class="stat-label">涉及知识点</div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 薄弱知识点 -->
    <el-card v-if="Object.keys(stats.by_knowledge_point || {}).length" shadow="never" class="kp-card">
      <template #header>薄弱知识点分布</template>
      <div class="kp-list">
        <el-tag
          v-for="(cnt, kp) in stats.by_knowledge_point"
          :key="kp"
          type="danger"
          effect="plain"
          class="kp-tag"
        >
          {{ kp }} · {{ cnt }} 题
        </el-tag>
      </div>
    </el-card>

    <!-- 错题列表 -->
    <el-card shadow="never" v-loading="loading">
      <el-empty v-if="!items.length && !loading" description="错题本是空的，继续保持！" />
      <div v-for="item in items" :key="item.id" class="q-item">
        <div class="q-header">
          <el-tag size="small" type="danger">待重练</el-tag>
          <el-tag v-if="item.knowledge_point" size="small" type="info" effect="plain">{{ item.knowledge_point }}</el-tag>
          <span class="q-meta">作答 {{ item.attempt_count }} 次 · 最近 {{ item.last_score ?? '-' }} 分</span>
        </div>
        <div class="q-body" v-html="renderQuestion(item.question_data)" />
        <div v-if="item.question_data?.answer" class="q-answer">
          <span class="answer-label">参考答案：</span>
          <code>{{ item.question_data.answer }}</code>
        </div>
        <div class="q-actions">
          <el-button size="small" type="primary" plain @click="goPractice(item)">去资源页重练</el-button>
          <el-button size="small" @click="handleRemove(item)">已掌握，移出</el-button>
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
import { ref, reactive, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { studentAPI } from '@/api'

const router = useRouter()
const loading = ref(false)
const items = ref<any[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = 20

const stats = reactive<any>({
  active: 0,
  mastered: 0,
  removed: 0,
  by_knowledge_point: {},
})

async function loadStats() {
  try {
    const res: any = await studentAPI.getWrongBookStats()
    Object.assign(stats, res || {})
  } catch { /* ignore */ }
}

async function load(p = page.value) {
  page.value = p
  loading.value = true
  try {
    const res: any = await studentAPI.getWrongBook({ page, page_size: pageSize })
    items.value = res?.items || []
    total.value = res?.total || 0
  } catch {
    items.value = []
    total.value = 0
  } finally {
    loading.value = false
  }
}

function goPractice(item: any) {
  const stageId = item.stage_id
  router.push({ path: '/student/resources', query: stageId != null ? { stage: String(stageId) } : {} })
}

async function handleRemove(item: any) {
  try {
    await ElMessageBox.confirm('确认将这道题移出错题本？', '移出确认', { type: 'warning' })
  } catch { return }
  try {
    await studentAPI.removeFromWrongBook(item.question_uid)
    ElMessage.success('已移出错题本')
    await Promise.all([load(1), loadStats()])
  } catch {
    ElMessage.error('操作失败，请重试')
  }
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

onMounted(() => {
  load(1)
  loadStats()
})
</script>

<style scoped>
.wrong-book-page { max-width: 1000px; }
.page-header h2 { margin: 0 0 4px; }
.page-sub { color: var(--el-text-color-secondary); margin: 0 0 16px; font-size: 13px; }
.stats-row { margin-bottom: 16px; }
.stat-card { text-align: center; }
.stat-value { font-size: 28px; font-weight: 600; }
.stat-label { color: var(--el-text-color-secondary); font-size: 13px; margin-top: 4px; }
.kp-card { margin-bottom: 16px; }
.kp-list { display: flex; flex-wrap: wrap; gap: 8px; }
.q-item { padding: 16px 0; border-bottom: 1px solid var(--el-border-color-lighter); }
.q-item:last-child { border-bottom: none; }
.q-header { display: flex; gap: 8px; align-items: center; flex-wrap: wrap; margin-bottom: 8px; }
.q-meta { color: var(--el-text-color-secondary); font-size: 12px; margin-left: auto; }
.q-body { line-height: 1.7; }
.q-body :deep(.opts) { margin: 8px 0 0; padding-left: 20px; color: var(--el-text-color-regular); }
.q-answer { margin-top: 8px; font-size: 13px; background: var(--el-fill-color-light); padding: 8px 12px; border-radius: 6px; }
.answer-label { color: var(--el-text-color-secondary); }
.q-actions { margin-top: 12px; display: flex; gap: 8px; }
.pager { margin-top: 16px; justify-content: center; }
</style>
