<template>
  <div class="page-container">
    <el-card class="page-card">
      <template #header>
        <div class="card-header">
          <div class="card-header__left">
            <el-icon class="card-header__icon"><Monitor /></el-icon>
            <h2 class="card-header__title">资源审核</h2>
          </div>
          <div class="card-header__right">
            <el-select v-model="filterType" placeholder="资源类型" style="width: 140px" clearable>
              <el-option value="" label="全部类型" />
              <el-option v-for="(label, key) in TYPE_TEXT" :key="key" :value="key" :label="label" />
            </el-select>
          </div>
        </div>
      </template>

      <div v-loading="loading" class="resource-layout">
        <!-- 左侧学生列表 -->
        <div class="student-sidebar">
          <div v-if="studentGroups.length === 0 && !loading" class="empty-hint">暂无学生数据</div>
          <div v-for="group in studentGroups" :key="group.user_id"
               class="student-item"
               :class="{ 'is-active': selectedStudentId === group.user_id }"
               @click="selectStudent(group.user_id)">
            <div class="student-name">{{ group.real_name }}</div>
            <div class="student-meta">
              <el-tag size="small" type="info">{{ group.resources.length }} 个资源</el-tag>
            </div>
          </div>
        </div>

        <!-- 右侧资源详情 -->
        <div class="resource-main">
          <div v-if="!selectedGroup" class="empty-hint">
            <el-empty description="选择左侧学生查看资源" />
          </div>
          <template v-else>
            <div class="student-header">
              <h3 class="student-title">{{ selectedGroup.real_name }} 的学习资源</h3>
              <el-select v-model="filterStageId" placeholder="全部阶段" clearable size="small" style="width:140px">
                <el-option label="全部阶段" :value="0" />
                <el-option v-for="s in availableStages" :key="s" :label="`阶段 ${s}`" :value="s" />
              </el-select>
            </div>

            <!-- 资源列表 -->
            <div v-if="displayedResources.length === 0" class="empty-hint">
              <el-empty description="暂无资源" />
            </div>
            <div v-else class="resource-list">
              <!-- 按阶段分组 -->
              <div v-for="stageId in displayedStages" :key="stageId" class="stage-group">
                <div class="stage-group-header">
                  <span class="stage-label">阶段 {{ stageId }}</span>
                  <el-tag size="small" type="info">{{ getResourcesByStage(stageId).length }} 个资源</el-tag>
                </div>
                <div v-for="(res, idx) in getResourcesByStage(stageId)" :key="`${stageId}-${res.resource_type}-${idx}`" class="resource-card" :class="{ expanded: expandedIdx === `${stageId}-${idx}` }">
                  <div class="res-card-header" @click="toggleContent(String(stageId) + '-' + idx)">
                    <el-tag size="small" :type="resTypeTag(res.resource_type)">{{ res.resource_type_name || res.resource_type }}</el-tag>
                    <span class="res-topic">{{ res.topic || '未知主题' }}</span>
                    <template v-if="res.quality_score?.overall_score">
                      <el-tag size="small" :type="gradeTagType(res.quality_score.overall_score)">
                        {{ res.quality_score.overall_score }}分 {{ res.quality_score.grade || getGrade(res.quality_score.overall_score) }}
                      </el-tag>
                    </template>
                    <el-tag v-else size="small" type="warning" effect="plain">未评估</el-tag>
                    <span class="res-time">{{ formatDate(res.created_at) }}</span>
                    <el-icon class="expand-icon" :class="{ expanded: expandedIdx === `${stageId}-${idx}` }"><ArrowDown /></el-icon>
                  </div>
                  <div v-if="expandedIdx === `${stageId}-${idx}`" class="res-expand">
                    <div v-if="res.quality_score?.overall_score" class="quality-dims">
                      <div class="dim-item"><span class="dim-label">主题相关</span><el-progress :percentage="res.quality_score.relevance || 0" :stroke-width="8" style="width:120px" /></div>
                      <div class="dim-item"><span class="dim-label">内容完整</span><el-progress :percentage="res.quality_score.completeness || 0" :stroke-width="8" style="width:120px" /></div>
                      <div class="dim-item"><span class="dim-label">个性化</span><el-progress :percentage="res.quality_score.personalization || 0" :stroke-width="8" style="width:120px" /></div>
                      <div class="dim-item"><span class="dim-label">准确性</span><el-progress :percentage="res.quality_score.accuracy || 0" :stroke-width="8" style="width:120px" /></div>
                      <div class="dim-item"><span class="dim-label">难度适配</span><el-progress :percentage="res.quality_score.difficulty_fit || 0" :stroke-width="8" style="width:120px" /></div>
                    </div>
                    <div v-else class="no-score">暂未评估</div>
                    <div class="res-content-preview">
                      <div v-if="isMarkdownType(res.resource_type)" class="markdown-body" v-html="renderMarkdown(res.content)"></div>
                      <div v-else-if="res.resource_type === 'mindmap'" class="markdown-body" v-html="renderMarkdown(res.content?.mindmap_markdown)"></div>
                      <div v-else-if="res.resource_type === 'ppt_video' && res.content?.video_url">
                        <video controls style="max-width:100%;border-radius:8px" :src="res.content.video_url"></video>
                      </div>
                      <div v-else-if="res.resource_type === 'question'">
                        <div v-for="(q, qi) in (res.content?.questions || [])" :key="qi" style="padding:6px 0;border-bottom:1px solid #f0f0f0">
                          <span style="font-weight:500">{{ qi+1 }}. {{ q.question }}</span>
                        </div>
                      </div>
                      <div v-else-if="res.resource_type === 'code'">
                        <pre v-if="res.content?.code" class="code-preview"><code>{{ res.content.code.slice(0, 500) }}{{ res.content.code.length > 500 ? '...' : '' }}</code></pre>
                      </div>
                      <div v-else-if="res.resource_type === 'glossary'">
                        <div v-for="t in (res.content?.terms || []).slice(0, 5)" :key="t.term" style="padding:4px 0">
                          <strong>{{ t.term }}</strong>：{{ t.definition?.slice(0, 60) }}{{ t.definition?.length > 60 ? '...' : '' }}
                        </div>
                      </div>
                      <div v-else class="raw-preview"><pre>{{ JSON.stringify(res.content, null, 2).slice(0, 800) }}{{ JSON.stringify(res.content).length > 800 ? '...' : '' }}</pre></div>
                    </div>
                    <div class="res-actions">
                      <el-button type="warning" plain size="small"
                        :loading="regeneratingKey === `${selectedGroup.user_id}-${res.resource_type}-${res.stage_id}`"
                        @click.stop="handleRegenerate(selectedGroup.user_id, res.resource_type, res.stage_id)">重新生成</el-button>
                      <el-button type="info" plain size="small"
                        :loading="reevaluatingKey === `${selectedGroup.user_id}-${res.resource_type}-${res.stage_id}`"
                        @click.stop="handleReevaluate(selectedGroup.user_id, res.resource_type, res.stage_id)">重新评估</el-button>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </template>
        </div>
      </div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { marked } from 'marked'
import { renderMath } from '@/utils/renderMath'
import { renderMd } from '@/utils/renderMarkdown'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Monitor, ArrowDown } from '@element-plus/icons-vue'
import { teacherAPI } from '@/api'

interface StudentResource {
  resource_type: string
  resource_type_name: string
  topic: string
  stage_id: number | null
  stage_title?: string
  quality_score: any
  content: any
  created_at: string | null
}

interface StudentGroup {
  user_id: number
  username: string
  real_name: string
  resources: StudentResource[]
}

const loading = ref(false)
const studentGroups = ref<StudentGroup[]>([])
const selectedStudentId = ref<number | null>(null)
const filterStageId = ref<number>(0)

function toggleContent(key: string) {
  expandedIdx.value = expandedIdx.value === key ? null : key
}

const isMarkdownType = (type: string) => ['document', 'reading_material', 'summary'].includes(type)

const renderMarkdown = (content: any) => {
  const text = typeof content === 'string' ? content : (content?.content || content?.mindmap_markdown || JSON.stringify(content))
  return renderMd(text)
}
const filterType = ref('')
const regeneratingKey = ref('')
const reevaluatingKey = ref('')
const expandedIdx = ref<number | null>(null)

const TYPE_TEXT: Record<string, string> = {
  document: '文档',
  mindmap: '思维导图',
  code: '代码示例',
  question: '练习题',
  reading_material: '拓展阅读',
  glossary: '术语词汇',
  knowledge_link: '知识点关联',
  summary: '学习总结',
  ppt_video: 'PPT视频',
}

const selectedGroup = computed(() =>
  studentGroups.value.find(g => g.user_id === selectedStudentId.value) || null
)

const filteredResources = computed(() => {
  if (!selectedGroup.value) return []
  const list = selectedGroup.value.resources
  return filterType.value ? list.filter(r => r.resource_type === filterType.value) : list
})

function selectStudent(userId: number) {
  selectedStudentId.value = userId
  filterStageId.value = 0
  expandedIdx.value = null
}

const availableStages = computed(() => {
  if (!selectedGroup.value) return []
  const stages = new Set<number>()
  selectedGroup.value.resources.forEach((r: StudentResource) => {
    if (r.stage_id) stages.add(r.stage_id)
  })
  return Array.from(stages).sort((a, b) => a - b)
})

const displayedResources = computed(() => {
  if (!selectedGroup.value) return []
  let list = selectedGroup.value.resources
  if (filterStageId.value && filterStageId.value > 0) {
    list = list.filter((r: StudentResource) => r.stage_id === filterStageId.value)
  }
  return list
})

const displayedStages = computed(() => {
  const stages = new Set<number>()
  displayedResources.value.forEach((r: StudentResource) => stages.add(r.stage_id || 0))
  return Array.from(stages).sort((a, b) => a - b)
})

function getResourcesByStage(stageId: number) {
  return displayedResources.value.filter((r: StudentResource) => (r.stage_id || 0) === stageId)
}

const resTypeTag = (type: string) => {
  const map: Record<string, string> = {
    document: 'primary', mindmap: 'success', question: 'warning',
    code: 'danger', ppt_video: 'info', reading_material: 'info',
    glossary: 'info', knowledge_link: 'success', summary: 'info',
  }
  return (map[type] || 'info') as any
}

const formatDate = (iso: string) => {
  if (!iso) return ''
  return new Date(iso).toLocaleString('zh-CN', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })
}

const gradeTagType = (score: number): '' | 'success' | 'warning' | 'danger' | 'info' => {
  if (score >= 80) return 'success'
  if (score >= 60) return ''
  return 'danger'
}

const getGrade = (score: number) => {
  if (score >= 90) return 'A'
  if (score >= 80) return 'B'
  if (score >= 70) return 'C'
  if (score >= 60) return 'D'
  return 'F'
}

const difficultyTag = (d: string) => {
  if (d === '基础') return 'success'
  if (d === '进阶') return 'warning'
  return 'danger'
}

async function handleRegenerate(userId: number, resourceType: string, stageId: number | null) {
  if (!stageId) {
    ElMessage.error('该资源没有关联阶段，无法重新生成')
    return
  }
  await ElMessageBox.confirm(`确定要重新生成「${TYPE_TEXT[resourceType] || resourceType}」吗？旧资源将被删除。`, '确认重新生成', {
    confirmButtonText: '确定',
    cancelButtonText: '取消',
    type: 'warning',
  })

  regeneratingKey.value = `${userId}-${resourceType}`
  try {
    await teacherAPI.regenerateStudentResource(userId, resourceType, { stage_id: stageId })
    ElMessage.success('重新生成成功')
    await fetchStudentResources()
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || '重新生成失败')
  } finally {
    regeneratingKey.value = ''
  }
}

async function handleReevaluate(userId: number, resourceType: string, stageId: number | null) {
  if (!stageId) {
    ElMessage.error('该资源没有关联阶段')
    return
  }
  reevaluatingKey.value = `${userId}-${resourceType}`
  try {
    const res: any = await teacherAPI.reevaluateStudentResource(userId, resourceType, { stage_id: stageId })
    ElMessage.success(`评估完成，评分: ${res.quality_score?.overall_score || '-'}`)
    await fetchStudentResources()
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || '评估失败')
  } finally {
    reevaluatingKey.value = ''
  }
}

async function fetchStudentResources() {
  loading.value = true
  try {
    const data: any = await teacherAPI.getAllStudentResources()
    studentGroups.value = (data || []).filter((g: StudentGroup) => g.resources.length > 0)
    if (studentGroups.value.length > 0 && !selectedStudentId.value) {
      selectStudent(studentGroups.value[0].user_id)
    }
  } catch {
    ElMessage.error('获取学生资源失败')
  } finally {
    loading.value = false
  }
}

onMounted(fetchStudentResources)
</script>

<style scoped>
.page-container {
  padding: 24px;
  background: var(--color-bg-page, #F4F5F7);
  min-height: 100%;
}
.page-card {
  border-radius: 12px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.06);
}
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.card-header__left { display: flex; align-items: center; gap: 8px; }
.card-header__icon { font-size: 20px; color: var(--color-primary); }
.card-header__title { font-size: 18px; font-weight: 600; margin: 0; color: var(--color-text-primary); }

/* 双栏布局 */
.resource-layout { display: flex; gap: 20px; min-height: 520px; }

.student-sidebar {
  width: 220px;
  flex-shrink: 0;
  border: 1px solid var(--color-border);
  border-radius: 12px;
  overflow-y: auto;
  background: var(--color-bg-card);
}
.student-item {
  padding: 14px 16px;
  cursor: pointer;
  border-bottom: 1px solid #e5e7eb;
  transition: background 0.2s ease;
}
.student-item:hover { background: var(--color-primary-lightest); }
.student-item.is-active { background: var(--color-primary-lightest); border-left: 3px solid var(--color-primary); }
.student-name { font-weight: 600; font-size: 14px; color: var(--color-text-primary); margin-bottom: 4px; }
.student-meta { font-size: 12px; color: var(--color-text-muted); }

.resource-main { flex: 1; min-width: 0; }
.student-header { margin-bottom: 16px; }
.student-title { font-size: 14px; font-weight: 600; margin: 0; color: var(--color-text-secondary); }

.resource-panel {
  padding: 20px;
  border: 1px solid var(--color-border);
  border-radius: 12px;
  background: var(--color-bg-card);
}

/* 资源列表 */
.resource-list { display: flex; flex-direction: column; gap: 16px; }
.stage-group { margin-bottom: 4px; }
.stage-group-header {
  display: flex; align-items: center; gap: 8px;
  padding: 8px 0; margin-bottom: 8px;
  border-bottom: 2px solid var(--color-border);
}
.stage-label { font-size: 14px; font-weight: 700; color: var(--color-primary); }
.resource-card {
  background: var(--color-bg-card); border: 1px solid var(--color-border); border-radius: 12px;
  padding: 14px 18px; margin-bottom: 8px; transition: all 0.2s ease;
}
.resource-card:hover { border-color: var(--color-primary-lightest); }
.resource-card.expanded { border-color: var(--color-primary-light); box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08); }
.res-card-header { display: flex; align-items: center; gap: 10px; cursor: pointer; flex-wrap: wrap; }
.res-topic { font-weight: 600; font-size: 14px; color: var(--color-text-primary); }
.res-time { font-size: 12px; color: var(--color-text-muted); margin-left: auto; white-space: nowrap; }
.res-card-actions { display: flex; gap: 6px; flex-shrink: 0; }
.expand-icon { color: var(--color-text-muted); transition: transform 0.2s ease; margin-left: 8px; flex-shrink: 0; }
.expand-icon.expanded { transform: rotate(180deg); }
.res-card-header { cursor: pointer; }
.res-content-preview {
  padding: 12px 16px; margin: 8px 0 0; background: var(--color-bg-page, #F4F5F7);
  border-radius: 8px; border: 1px solid #e5e7eb; max-height: 300px; overflow-y: auto;
  font-size: 12px; line-height: 1.7; color: var(--color-text-secondary);
}
.quality-dims {
  display: flex; flex-wrap: wrap; gap: 12px;
  padding: 10px 16px; margin: 8px 0 0; background: var(--color-primary-lightest);
  border-radius: 8px; border: 1px solid var(--color-primary-lightest);
}
.dim-item { display: flex; align-items: center; gap: 6px; }
.dim-label { font-size: 12px; color: var(--color-text-secondary); white-space: nowrap; font-weight: 500; }
.no-score { padding: 8px 16px; color: var(--color-text-muted); font-size: 12px; }
.res-actions { display: flex; gap: 8px; padding-top: 10px; border-top: 1px solid #e5e7eb; margin-top: 10px; }
.code-preview {
  background: #1e1e2e; color: #cdd6f4; padding: 12px; border-radius: 8px;
  font-size: 12px; overflow-x: auto; margin: 0; white-space: pre-wrap;
}
.raw-preview pre {
  background: #e5e7eb; padding: 10px; border-radius: 4px;
  font-size: 11px; overflow-x: auto; margin: 0; white-space: pre-wrap;
}
.create-time { font-size: 12px; color: var(--color-text-muted); }

/* 内容渲染 */
.markdown-body { line-height: 1.8; }
.mindmap-content { padding: 12px; line-height: 1.8; }
.mindmap-content ul { padding-left: 20px; }
.question-content { display: flex; flex-direction: column; gap: 16px; }
.question-item { padding: 14px; background: var(--color-bg-card); border-radius: 8px; border: 1px solid var(--color-border); }
.question-header { display: flex; gap: 6px; margin-bottom: 6px; }
.question-text { font-weight: 500; margin: 0 0 8px; line-height: 1.6; }
.question-options { padding-left: 14px; margin-bottom: 8px; }
.option-item { margin: 3px 0; color: var(--color-text-primary); }
.option-key { font-weight: 600; color: var(--color-primary); margin-right: 4px; }
.question-answer { font-size: 14px; color: var(--color-text-primary); margin-bottom: 4px; }
.answer-label { font-weight: 600; color: var(--color-success); }
.question-explain { font-size: 12px; color: var(--color-text-secondary); padding: 8px 12px; background: var(--color-primary-lightest); border-radius: 4px; }
.explain-label { font-weight: 600; }
.code-content { display: flex; flex-direction: column; gap: 16px; }
.code-example-item { padding: 14px; background: var(--color-bg-card); border-radius: 8px; border: 1px solid var(--color-border); }
.code-header { display: flex; align-items: center; gap: 8px; margin-bottom: 6px; }
.code-title { font-weight: 600; font-size: 14px; }
.code-desc { color: var(--color-text-secondary); margin: 0 0 10px; font-size: 12px; }
.code-block { background: #1e1e2e; color: #cdd6f4; padding: 14px; border-radius: 8px; font-size: 12px; overflow-x: auto; margin: 0; line-height: 1.6; }
.glossary-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 10px; }
.term-card { border-radius: 8px; }
.term-name { font-weight: 700; font-size: 18px; color: var(--color-primary); margin-bottom: 4px; }
.term-def { color: var(--color-text-primary); margin-bottom: 4px; }
.term-example { color: var(--color-text-secondary); font-size: 12px; }
.raw-content pre { background: #e5e7eb; padding: 14px; border-radius: 8px; font-size: 12px; overflow-x: auto; }
.empty-hint { padding: 40px; text-align: center; color: var(--color-text-muted); }

:deep(.el-tabs__header) { margin-bottom: 0; }
</style>
