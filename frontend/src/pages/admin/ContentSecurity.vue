<template>
  <div class="page-container">
    <el-card class="page-card" shadow="never">
      <template #header>
        <div class="card-header">
          <div class="card-header__left">
            <el-icon class="card-header__icon"><Flag /></el-icon>
            <h2 class="card-header__title">内容安全审核</h2>
          </div>
          <div class="card-header__right" v-if="activeTab === 'security'">
            <span class="switch-label">敏感词过滤</span>
            <el-switch v-model="enabled" @change="handleToggle" :loading="toggling" />
          </div>
        </div>
      </template>

      <el-tabs v-model="activeTab" type="border-card">
        <!-- 敏感词管理 -->
        <el-tab-pane label="敏感词管理" name="security">
          <div class="add-row">
            <el-select v-model="newCategory" placeholder="分类" style="width: 120px">
              <el-option v-for="cat in Object.keys(words)" :key="cat" :label="cat" :value="cat" />
            </el-select>
            <el-input v-model="newWordsText" placeholder="敏感词（多个用逗号分隔）" style="flex:1" @keyup.enter="handleAddWords" />
            <el-button type="primary" @click="handleAddWords" :loading="adding">添加</el-button>
          </div>
          <el-row :gutter="16">
            <el-col :span="12" v-for="(wordList, cat) in words" :key="cat">
              <div class="category-block">
                <div class="category-header">
                  <span class="category-name">{{ cat }}</span>
                  <el-tag size="small" type="info">{{ wordList.length }}</el-tag>
                </div>
                <div class="word-tags" v-if="wordList.length">
                  <el-tag v-for="w in wordList" :key="w" closable size="small" @close="handleDeleteWord(cat, w)">{{ w }}</el-tag>
                </div>
                <div v-else class="empty-words">暂无敏感词</div>
              </div>
            </el-col>
          </el-row>
        </el-tab-pane>

        <!-- 过滤记录 -->
        <el-tab-pane label="过滤记录" name="logs">
          <el-table :data="secLogs" stripe v-loading="logsLoading" size="small">
            <el-table-column prop="time" label="时间" width="170" />
            <el-table-column prop="resource_type" label="资源类型" width="100" />
            <el-table-column prop="topic" label="主题" width="140" show-overflow-tooltip />
            <el-table-column prop="hit_words" label="命中词">
              <template #default="{ row }">
                <el-tag v-for="w in row.hit_words" :key="w" size="small" type="danger" style="margin:1px">{{ w }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="user_id" label="用户" width="70" />
          </el-table>
          <el-pagination v-if="secLogsTotal > 20" layout="prev, pager, next" :total="secLogsTotal" :page-size="20"
            v-model:current-page="secLogsPage" @current-change="fetchSecLogs" style="margin-top:12px;justify-content:center" />
          <el-empty v-if="!logsLoading && secLogs.length === 0" description="暂无过滤记录" />
        </el-tab-pane>

        <!-- 内容审核 -->
        <el-tab-pane label="内容审核" name="review">
          <div style="margin-bottom:12px">
            <el-select v-model="reviewStatusFilter" placeholder="状态筛选" clearable style="width:140px" @change="fetchReview">
              <el-option label="待审核" value="pending" />
              <el-option label="已通过" value="approved" />
              <el-option label="已拒绝" value="rejected" />
            </el-select>
          </div>
          <el-table :data="reviewItems" stripe v-loading="reviewLoading" size="small">
            <el-table-column prop="id" label="ID" width="60" />
            <el-table-column prop="content_type" label="类型" width="100" />
            <el-table-column prop="content" label="内容" show-overflow-tooltip />
            <el-table-column prop="status" label="状态" width="90">
              <template #default="{ row }">
                <el-tag :type="row.status === 'approved' ? 'success' : row.status === 'rejected' ? 'danger' : 'warning'" size="small">
                  {{ { pending: '待审核', approved: '已通过', rejected: '已拒绝' }[row.status] || row.status }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="created_at" label="时间" width="160">
              <template #default="{ row }">{{ formatDate(row.created_at) }}</template>
            </el-table-column>
            <el-table-column label="操作" width="160">
              <template #default="{ row }">
                <template v-if="row.status === 'pending'">
                  <el-button type="success" link size="small" @click="handleReview(row.id, 'approve')">通过</el-button>
                  <el-button type="danger" link size="small" @click="handleReview(row.id, 'reject')">拒绝</el-button>
                </template>
                <span v-else style="color:#9ca3af;font-size:12px">{{ row.reviewer_id ? '已处理' : '-' }}</span>
              </template>
            </el-table-column>
          </el-table>
          <el-pagination v-if="reviewTotal > 10" layout="prev, pager, next" :total="reviewTotal" :page-size="10"
            v-model:current-page="reviewPage" @current-change="fetchReview" style="margin-top:12px;justify-content:center" />
          <el-empty v-if="!reviewLoading && reviewItems.length === 0" description="暂无待审核内容" />
        </el-tab-pane>
      </el-tabs>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Flag } from '@element-plus/icons-vue'
import { adminAPI } from '@/api'

const activeTab = ref('security')

// ── 敏感词管理 ──
const enabled = ref(false)
const toggling = ref(false)
const words = ref<Record<string, string[]>>({})
const newCategory = ref('自定义')
const newWordsText = ref('')
const adding = ref(false)

async function fetchSecurity() {
  try {
    const res: any = await adminAPI.getContentSecurity()
    enabled.value = res.enabled
    words.value = res.words || {}
  } catch {}
}

async function handleToggle(val: boolean) {
  toggling.value = true
  try { await adminAPI.updateContentSecurity({ enabled: val }); ElMessage.success(val ? '已开启' : '已关闭') }
  catch { enabled.value = !val; ElMessage.error('操作失败') }
  finally { toggling.value = false }
}

async function handleAddWords() {
  const text = newWordsText.value.trim()
  if (!text) return
  const list = text.split(/[,，]/).map(w => w.trim()).filter(Boolean)
  if (!list.length) return
  adding.value = true
  try {
    const res: any = await adminAPI.addSecurityWords({ category: newCategory.value, words: list })
    words.value = res.words; newWordsText.value = ''
    ElMessage.success(`添加 ${res.added?.length || 0} 个`)
  } catch { ElMessage.error('添加失败') }
  finally { adding.value = false }
}

async function handleDeleteWord(cat: string, word: string) {
  try { const res: any = await adminAPI.deleteSecurityWords({ category: cat, word }); words.value = res.words }
  catch { ElMessage.error('删除失败') }
}

// ── 过滤记录 ──
const secLogs = ref<any[]>([])
const secLogsLoading = ref(false)
const secLogsTotal = ref(0)
const secLogsPage = ref(1)
const logsLoading = ref(false)

async function fetchSecLogs() {
  logsLoading.value = true
  try {
    const res: any = await adminAPI.getSecurityLogs({ page: secLogsPage.value, page_size: 20 })
    secLogs.value = res.items || []; secLogsTotal.value = res.total || 0
  } catch {} finally { logsLoading.value = false }
}

// ── 内容审核 ──
const reviewItems = ref<any[]>([])
const reviewLoading = ref(false)
const reviewTotal = ref(0)
const reviewPage = ref(1)
const reviewStatusFilter = ref('')

async function fetchReview() {
  reviewLoading.value = true
  try {
    const params: any = { page: reviewPage.value, page_size: 10 }
    if (reviewStatusFilter.value) params.status = reviewStatusFilter.value
    const res: any = await adminAPI.getContentReview(params)
    reviewItems.value = res.items || []; reviewTotal.value = res.total || 0
  } catch {} finally { reviewLoading.value = false }
}

async function handleReview(id: number, action: string) {
  const label = action === 'approve' ? '通过' : '拒绝'
  try {
    await ElMessageBox.confirm(`确定${label}该内容？`, '确认审核', { type: 'warning' })
    await adminAPI.reviewContent(id, { action })
    ElMessage.success(`已${label}`)
    await fetchReview()
  } catch {}
}

const formatDate = (iso: string) => iso ? new Date(iso).toLocaleString('zh-CN') : '-'

onMounted(() => { fetchSecurity(); fetchSecLogs(); fetchReview() })
</script>

<style scoped>
.page-container { padding: 24px; background: var(--color-bg-page, #F4F5F7); min-height: 100%; }
.page-card { border-radius: var(--radius-lg); box-shadow: var(--shadow-card); }
.card-header { display: flex; justify-content: space-between; align-items: center; }
.card-header__left { display: flex; align-items: center; gap: 8px; }
.card-header__icon { font-size: 20px; color: var(--color-primary); }
.card-header__title { font-size: 18px; font-weight: 600; margin: 0; color: var(--color-text-primary); }
.card-header__right { display: flex; align-items: center; gap: 10px; }
.switch-label { font-size: 14px; color: var(--color-text-secondary); font-weight: 500; }
.add-row { display: flex; gap: 8px; margin-bottom: 16px; }
.category-block { background: var(--color-border-light); border: 1px solid var(--color-border); border-radius: 8px; padding: 12px; margin-bottom: 12px; }
.category-header { display: flex; align-items: center; gap: 8px; margin-bottom: 8px; }
.category-name { font-weight: 600; font-size: 14px; color: var(--color-text-secondary); }
.word-tags { display: flex; flex-wrap: wrap; gap: 4px; }
.empty-words { font-size: 12px; color: var(--color-text-muted); }
</style>
