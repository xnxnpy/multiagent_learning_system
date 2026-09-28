<template>
  <div class="plaza-page">
    <div class="page-header">
      <h2>学习广场</h2>
      <p class="page-sub">分享笔记与速查表，点赞互动，把好内容收进自己的库</p>
    </div>

    <el-card shadow="never" class="card">
      <el-form @submit.prevent="submitPost">
        <el-form-item>
          <el-input v-model="form.title" maxlength="200" placeholder="标题，如：Python 函数速查表（可打印版）" />
        </el-form-item>
        <el-form-item>
          <el-input
            v-model="form.content"
            type="textarea"
            :rows="3"
            maxlength="5000"
            placeholder="分享内容：总结、踩坑、可打印资料说明…"
          />
        </el-form-item>
        <el-form-item>
          <el-input v-model="form.tags" maxlength="200" placeholder="标签，逗号分隔，如：Python,速查表" />
        </el-form-item>
        <el-button type="primary" :loading="posting" :disabled="!form.title || !form.content" @click="submitPost">
          发布分享
        </el-button>
      </el-form>
    </el-card>

    <el-card shadow="never" class="card" v-loading="loading">
      <template #header>
        <div class="head">
          <span>最新分享</span>
          <el-button size="small" @click="load">刷新</el-button>
        </div>
      </template>
      <el-empty v-if="!posts.length" description="还没有分享，来发第一帖" :image-size="70" />
      <div v-for="p in posts" :key="p.id" class="post">
        <div class="post-head">
          <span class="author">{{ p.author }}</span>
          <span class="time">{{ fmt(p.created_at) }}</span>
        </div>
        <h3 class="post-title">{{ p.title }}</h3>
        <p class="post-content">{{ p.content }}</p>
        <div class="post-tags" v-if="p.tags">
          <el-tag v-for="t in p.tags.split(/[,，]/).filter(Boolean)" :key="t" size="small" effect="plain">
            {{ t.trim() }}
          </el-tag>
        </div>
        <div class="post-actions">
          <el-button
            size="small"
            :type="p.liked ? 'primary' : 'default'"
            plain
            :loading="likingId === p.id"
            @click="toggleLike(p)"
          >
            👍 {{ p.like_count }}
          </el-button>
          <el-button v-if="p.mine || isAdmin" size="small" type="danger" link @click="removePost(p)">删除</el-button>
        </div>
      </div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import request from '@/utils/axios'

interface Post {
  id: number
  title: string
  content: string
  tags: string
  like_count: number
  author: string
  liked: boolean
  created_at?: string
  mine?: boolean
}

const loading = ref(false)
const posting = ref(false)
const likingId = ref<number | null>(null)
const posts = ref<Post[]>([])
const form = reactive({ title: '', content: '', tags: '' })
const isAdmin = ref(false)

function fmt(s?: string) {
  if (!s) return ''
  try { return new Date(s).toLocaleString() } catch { return s }
}

async function load() {
  loading.value = true
  try {
    const list: any[] = await request.get('/v1/plaza/posts')
    let myId: number | null = null
    try {
      const me: any = await request.get('/v1/student/profile').catch(() => null)
      // profile 不一定有 user id；从 localStorage
    } catch { /* ignore */ }
    try {
      const u = JSON.parse(localStorage.getItem('user') || '{}')
      myId = u.id ?? null
      isAdmin.value = u.role === 'admin'
    } catch { /* ignore */ }
    posts.value = (list || []).map(p => ({ ...p, mine: myId != null && p.user_id === myId }))
  } catch {
    posts.value = []
  } finally {
    loading.value = false
  }
}

async function submitPost() {
  if (!form.title.trim() || !form.content.trim()) return
  posting.value = true
  try {
    await request.post('/v1/plaza/posts', {
      title: form.title.trim(),
      content: form.content.trim(),
      tags: form.tags.trim(),
    })
    ElMessage.success('已发布')
    form.title = ''
    form.content = ''
    form.tags = ''
    await load()
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || '发布失败')
  } finally {
    posting.value = false
  }
}

async function toggleLike(p: Post) {
  likingId.value = p.id
  try {
    const res: any = await request.post(`/v1/plaza/posts/${p.id}/like`)
    p.liked = res.liked
    p.like_count = res.like_count
  } catch {
    ElMessage.error('点赞失败')
  } finally {
    likingId.value = null
  }
}

async function removePost(p: Post) {
  try {
    await ElMessageBox.confirm('删除这条分享？', '删除确认', { type: 'warning' })
  } catch { return }
  try {
    await request.delete(`/v1/plaza/posts/${p.id}`)
    ElMessage.success('已删除')
    await load()
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || '删除失败')
  }
}

onMounted(load)
</script>

<style scoped>
.plaza-page { max-width: 800px; }
.page-header h2 { margin: 0 0 4px; padding-left: 12px; border-left: 4px solid #70293C; line-height: 1.2; }
.page-sub { color: var(--el-text-color-secondary); margin: 0 0 16px; font-size: 13px; padding-left: 16px; }
.card { margin-bottom: 16px; }
.head { display: flex; justify-content: space-between; align-items: center; }
.post { padding: 16px; border-bottom: 1px solid var(--el-border-color-lighter); border-radius: 12px; transition: box-shadow 0.15s; }
.post:hover { box-shadow: 0 2px 10px rgba(0,0,0,0.05); }
.post:last-child { border-bottom: none; }
.post:last-child { border-bottom: none; }
.post-head { display: flex; gap: 10px; font-size: 12px; color: var(--el-text-color-secondary); }
.author { font-weight: 600; color: var(--el-text-color-primary); }
.post-title { margin: 6px 0; font-size: 16px; }
.post-content { margin: 0 0 8px; font-size: 14px; line-height: 1.6; white-space: pre-wrap; color: var(--el-text-color-regular); }
.post-tags { display: flex; gap: 6px; flex-wrap: wrap; margin-bottom: 8px; }
.post-actions { display: flex; gap: 8px; align-items: center; }
</style>
