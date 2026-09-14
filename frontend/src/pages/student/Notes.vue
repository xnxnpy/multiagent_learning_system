<template>
  <div class="notes-page">
    <div class="page-header">
      <div>
        <h2>学习笔记</h2>
        <p class="page-sub">沉淀的知识会进入个人知识库，辅导与资源生成可检索引用</p>
      </div>
      <el-button type="primary" @click="openCreate">
        <el-icon><Plus /></el-icon> 新建笔记
      </el-button>
    </div>

    <el-input
      v-model="search"
      placeholder="搜索标题或内容…"
      clearable
      class="search-input"
      @keyup.enter="load(1)"
      @clear="load(1)"
    >
      <template #prefix><el-icon><Search /></el-icon></template>
    </el-input>

    <el-card shadow="never" v-loading="loading">
      <el-empty v-if="!items.length && !loading" description="还没有笔记。把学到的关键点记下来吧。" />
      <div v-for="note in items" :key="note.id" class="note-item">
        <div class="note-header">
          <h3 class="note-title">{{ note.title }}</h3>
          <div class="note-meta">
            <el-tag size="small" effect="plain">{{ sourceLabel(note.source) }}</el-tag>
            <span class="note-time">{{ (note.updated_at || '').slice(0, 16).replace('T', ' ') }}</span>
          </div>
        </div>
        <p class="note-content">{{ note.content }}</p>
        <div class="note-actions">
          <el-button size="small" @click="openEdit(note)">编辑</el-button>
          <el-popconfirm title="删除这条笔记？" confirm-button-text="删除" cancel-button-text="取消" @confirm="handleDelete(note)">
            <template #reference>
              <el-button size="small" type="danger" text>删除</el-button>
            </template>
          </el-popconfirm>
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

    <!-- 新建/编辑对话框 -->
    <el-dialog v-model="dialogVisible" :title="editingId ? '编辑笔记' : '新建笔记'" width="560px">
      <el-form label-position="top">
        <el-form-item label="标题" required>
          <el-input v-model="form.title" maxlength="200" show-word-limit placeholder="例如：协方差与相关系数的区别" />
        </el-form-item>
        <el-form-item label="内容" required>
          <el-input v-model="form.content" type="textarea" :rows="8" placeholder="记录你的理解、易错点、公式…" />
        </el-form-item>
        <el-form-item label="标签（逗号分隔，可选）">
          <el-input v-model="form.tags" placeholder="机器学习,统计学" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="handleSave">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Plus, Search } from '@element-plus/icons-vue'
import request from '@/utils/axios'

const loading = ref(false)
const saving = ref(false)
const items = ref<any[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = 20
const search = ref('')

const dialogVisible = ref(false)
const editingId = ref<number | null>(null)
const form = reactive({ title: '', content: '', tags: '' })

async function load(p = page.value) {
  page.value = p
  loading.value = true
  try {
    const res: any = await request.get('/v1/notes', {
      params: { page: page.value, page_size: pageSize, search: search.value || undefined },
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

function openCreate() {
  editingId.value = null
  form.title = ''
  form.content = ''
  form.tags = ''
  dialogVisible.value = true
}

function openEdit(note: any) {
  editingId.value = note.id
  form.title = note.title
  form.content = note.content
  form.tags = note.tags || ''
  dialogVisible.value = true
}

async function handleSave() {
  if (!form.title.trim() || !form.content.trim()) {
    ElMessage.warning('标题和内容不能为空')
    return
  }
  saving.value = true
  try {
    if (editingId.value) {
      await request.put(`/v1/notes/${editingId.value}`, {
        title: form.title,
        content: form.content,
        tags: form.tags,
      })
      ElMessage.success('已更新')
    } else {
      await request.post('/v1/notes', {
        title: form.title,
        content: form.content,
        tags: form.tags,
        source: 'manual',
      })
      ElMessage.success('已保存，并已加入个人知识库')
    }
    dialogVisible.value = false
    await load(1)
  } catch {
    ElMessage.error('保存失败')
  } finally {
    saving.value = false
  }
}

async function handleDelete(note: any) {
  try {
    await request.delete(`/v1/notes/${note.id}`)
    ElMessage.success('已删除')
    await load(1)
  } catch {
    ElMessage.error('删除失败')
  }
}

function sourceLabel(s: string) {
  return { manual: '手写', tutor: '辅导沉淀', resource: '资源摘录' }[s] || s
}

onMounted(() => load(1))
</script>

<style scoped>
.notes-page { max-width: 900px; }
.page-header { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 16px; }
.page-header h2 { margin: 0 0 4px; }
.page-sub { color: var(--el-text-color-secondary); margin: 0; font-size: 13px; }
.search-input { margin-bottom: 16px; }
.note-item { padding: 16px 0; border-bottom: 1px solid var(--el-border-color-lighter); }
.note-item:last-child { border-bottom: none; }
.note-header { display: flex; justify-content: space-between; align-items: center; gap: 12px; flex-wrap: wrap; }
.note-title { margin: 0; font-size: 16px; }
.note-meta { display: flex; gap: 8px; align-items: center; }
.note-time { color: var(--el-text-color-secondary); font-size: 12px; }
.note-content { color: var(--el-text-color-regular); line-height: 1.7; margin: 8px 0; white-space: pre-wrap; }
.note-actions { display: flex; gap: 4px; }
.pager { margin-top: 16px; justify-content: center; }
</style>
