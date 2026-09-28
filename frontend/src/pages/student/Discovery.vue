<template>
  <div class="discovery-page">
    <div class="page-header">
      <h2>学习发现</h2>
      <p class="page-sub">搜索外部视频、文章、论文与代码仓库，一键收藏进我的学习库</p>
    </div>

    <el-card shadow="never" class="card">
      <div class="search-row">
        <el-input
          v-model="query"
          placeholder="例如：Python 装饰器 / Transformer 论文 / React 状态管理"
          clearable
          @keyup.enter="doSearch"
        >
          <template #append>
            <el-button type="primary" :loading="loading" @click="doSearch">发现</el-button>
          </template>
        </el-input>
      </div>
      <div class="type-filter">
        <el-radio-group v-model="typeFilter" size="small" @change="doSearch">
          <el-radio-button value="">全部</el-radio-button>
          <el-radio-button value="video">视频</el-radio-button>
          <el-radio-button value="article">文章</el-radio-button>
          <el-radio-button value="paper">论文</el-radio-button>
          <el-radio-button value="repo">代码仓库</el-radio-button>
        </el-radio-group>
      </div>
    </el-card>

    <el-card v-if="items.length" shadow="never" class="card">
      <template #header>
        <div class="head">
          <span>检索结果 · {{ items.length }}</span>
          <el-tag size="small" effect="plain">{{ source === 'ddg' ? '联网检索' : '快捷入口' }}</el-tag>
        </div>
      </template>
      <div v-for="(item, i) in items" :key="i" class="res-item">
        <div class="res-main">
          <div class="res-title-row">
            <el-tag size="small" :type="typeTag(item.type)">{{ typeLabel(item.type) }}</el-tag>
            <a class="res-title" :href="item.url" target="_blank" rel="noopener">{{ item.title }}</a>
          </div>
          <p class="res-summary">{{ item.summary || '暂无简介' }}</p>
          <div class="res-url">{{ item.url }}</div>
        </div>
        <div class="res-actions">
          <el-button size="small" type="primary" plain @click="openLink(item.url)">打开</el-button>
          <el-button size="small" :loading="savingKey === item.url" @click="saveItem(item)">收藏</el-button>
        </div>
      </div>
    </el-card>
    <el-empty v-else-if="searched && !loading" description="没有找到结果，换个关键词试试" />

    <el-card shadow="never" class="card">
      <template #header>
        <div class="head">
          <span>我的收藏</span>
          <el-button size="small" @click="loadSaved">刷新</el-button>
        </div>
      </template>
      <el-empty v-if="!saved.length" description="还没有收藏，先搜点什么吧" :image-size="70" />
      <div v-for="item in saved" :key="item.id" class="res-item">
        <div class="res-main">
          <div class="res-title-row">
            <el-tag size="small" :type="typeTag(item.type)">{{ typeLabel(item.type) }}</el-tag>
            <a class="res-title" :href="item.url" target="_blank" rel="noopener">{{ item.title }}</a>
          </div>
          <p class="res-summary">{{ item.summary }}</p>
        </div>
        <div class="res-actions">
          <el-button size="small" type="primary" plain @click="openLink(item.url)">打开</el-button>
          <el-button size="small" type="danger" plain @click="removeSaved(item)">移除</el-button>
        </div>
      </div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import request from '@/utils/axios'

interface ResItem {
  title: string
  url: string
  type: string
  summary?: string
  id?: number
}

const query = ref('')
const typeFilter = ref('')
const loading = ref(false)
const searched = ref(false)
const items = ref<ResItem[]>([])
const source = ref('fallback')
const savingKey = ref('')
const saved = ref<ResItem[]>([])

function typeLabel(t: string) {
  return ({ video: '视频', article: '文章', paper: '论文', repo: '仓库' } as any)[t] || t
}
function typeTag(t: string) {
  return ({ video: 'warning', article: 'info', paper: 'success', repo: 'primary' } as any)[t] || 'info'
}

function openLink(url: string) {
  window.open(url, '_blank', 'noopener')
}

async function doSearch() {
  const q = query.value.trim()
  if (!q) {
    ElMessage.warning('请输入检索词')
    return
  }
  loading.value = true
  searched.value = true
  try {
    const res: any = await request.get('/v1/discovery/search', {
      params: { q, ...(typeFilter.value ? { type: typeFilter.value } : {}) },
      timeout: 20000,
    })
    items.value = res?.items || []
    source.value = res?.source || 'fallback'
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || '检索失败')
    items.value = []
  } finally {
    loading.value = false
  }
}

async function loadSaved() {
  try {
    saved.value = await request.get('/v1/discovery/saved')
  } catch {
    saved.value = []
  }
}

async function saveItem(item: ResItem) {
  savingKey.value = item.url
  try {
    await request.post('/v1/discovery/save', {
      title: item.title,
      url: item.url,
      type: item.type,
      summary: item.summary || '',
      source: new URL(item.url).hostname || '',
    })
    ElMessage.success('已加入我的学习库')
    await loadSaved()
  } catch (e: any) {
    if (String(e?.message || '').includes('Invalid URL')) {
      // 兜底 hostname
      await request.post('/v1/discovery/save', {
        title: item.title, url: item.url, type: item.type, summary: item.summary || '', source: '',
      })
      ElMessage.success('已加入我的学习库')
      await loadSaved()
    } else {
      ElMessage.error(e?.response?.data?.detail || '收藏失败')
    }
  } finally {
    savingKey.value = ''
  }
}

async function removeSaved(item: ResItem) {
  try {
    await ElMessageBox.confirm(`移除「${item.title}」？`, '移除收藏', { type: 'warning' })
  } catch { return }
  try {
    await request.delete(`/v1/discovery/saved/${item.id}`)
    ElMessage.success('已移除')
    await loadSaved()
  } catch {
    ElMessage.error('移除失败')
  }
}

onMounted(loadSaved)
</script>

<style scoped>
.discovery-page { max-width: 960px; }
.page-header h2 { margin: 0 0 4px; padding-left: 12px; border-left: 4px solid #3D6B4F; line-height: 1.2; }
.page-sub { color: var(--el-text-color-secondary); margin: 0 0 16px; font-size: 13px; padding-left: 16px; }
.card { margin-bottom: 16px; }
.search-row { margin-bottom: 10px; }
.type-filter { display: flex; justify-content: flex-start; }
.head { display: flex; justify-content: space-between; align-items: center; }
.res-item {
  display: flex;
  gap: 12px;
  align-items: flex-start;
  padding: 12px;
  border-bottom: 1px solid var(--el-border-color-lighter);
  border-radius: 10px;
  transition: box-shadow 0.15s, transform 0.15s, background 0.15s;
}
.res-item:hover {
  box-shadow: 0 4px 12px rgba(0,0,0,0.06);
  transform: translateY(-1px);
  background: var(--el-fill-color-lighter);
}
.res-item:last-child { border-bottom: none; }
.res-main { flex: 1; min-width: 0; }
.res-title-row { display: flex; gap: 8px; align-items: center; flex-wrap: wrap; }
.res-title {
  color: var(--el-color-primary);
  font-weight: 600;
  text-decoration: none;
  word-break: break-all;
}
.res-title:hover { text-decoration: underline; }
.res-summary {
  margin: 6px 0 4px;
  font-size: 13px;
  color: var(--el-text-color-regular);
  line-height: 1.5;
}
.res-url {
  font-size: 11px;
  color: var(--el-text-color-secondary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.res-actions { display: flex; flex-direction: column; gap: 6px; flex-shrink: 0; }
</style>
