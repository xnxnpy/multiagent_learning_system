<template>
  <div class="showcase-page">
    <div class="page-header">
      <h2 class="page-title">案例展示 - 系统功能验证</h2>
      <el-tag type="success" size="large">智学优培—基于大模型多模态生成的高校个性化学习智能体平台</el-tag>
    </div>

    <!-- 系统概览卡片 -->
    <el-row :gutter="20" class="stat-row">
      <el-col :xs="12" :sm="6" v-for="card in overviewCards" :key="card.label">
        <div class="stat-card">
          <div class="stat-value">{{ card.value }}</div>
          <div class="stat-label">{{ card.label }}</div>
        </div>
      </el-col>
    </el-row>

    <!-- 主Tab导航 -->
    <el-tabs v-model="activeMainTab" class="showcase-tabs">
      <!-- ① 画像构建案例 -->
      <el-tab-pane name="profiles">
        <template #label><span>① 画像构建 ({{ cases.profiles.length }}个案例)</span></template>
        <div class="case-grid">
          <el-card v-for="item in cases.profiles" :key="item.case_id" class="case-card" shadow="hover">
            <template #header>
              <div class="case-header">
                <span class="case-title">{{ item.title }}</span>
                <el-tag size="small" type="info">案例{{ item.case_id }}</el-tag>
              </div>
            </template>
            <p class="case-desc">{{ item.description }}</p>
            <el-descriptions :column="2" border size="small">
              <el-descriptions-item v-for="(val, key) in item.profile_data" :key="key" :label="key">
                {{ Array.isArray(val) ? val.join(', ') : val }}
              </el-descriptions-item>
            </el-descriptions>
          </el-card>
        </div>
      </el-tab-pane>

      <!-- ② 路径推荐案例 -->
      <el-tab-pane name="paths">
        <template #label><span>② 路径推荐 ({{ cases.paths.length }}个案例)</span></template>
        <div class="case-grid">
          <el-card v-for="item in cases.paths" :key="item.case_id" class="case-card" shadow="hover">
            <template #header>
              <div class="case-header">
                <span class="case-title">{{ item.title }}</span>
                <el-tag v-if="item.match_score" type="success" size="small">
                  匹配度 {{ (item.match_score * 100).toFixed(0) }}%
                </el-tag>
              </div>
            </template>
            <p class="profile-summary">学生情况：{{ item.student_profile_summary }}</p>
            <el-steps :active="item.path_stages.length" direction="vertical" finish-status="success" class="path-steps">
              <el-step v-for="(stage, idx) in item.path_stages" :key="idx"
                       :title="stage.title" :description="stage.description" />
            </el-steps>
            <div class="recommend-reason">
              推荐理由：{{ item.recommendation_reason }}
            </div>
          </el-card>
        </div>
      </el-tab-pane>

      <!-- ③ 资源生成案例（学生分组布局） -->
      <el-tab-pane name="resources">
        <template #label><span>③ 资源生成 ({{ cases.resources.length }}个案例)</span></template>
        <div v-if="!cases.resources_by_student?.length" class="empty-hint">暂无资源数据</div>
        <div v-else class="resource-layout">
          <!-- 左侧学生列表 -->
          <div class="student-sidebar">
            <div v-for="(group, idx) in cases.resources_by_student" :key="group.student_name"
                 class="student-item"
                 :class="{ 'is-active': selectedStudentIdx === idx }"
                 @click="selectedStudentIdx = idx">
              <div class="student-name">{{ group.student_name }}</div>
              <div class="student-meta">
                <el-tag size="small" type="info">{{ group.resources.length }} 个资源</el-tag>
              </div>
            </div>
          </div>
          <!-- 右侧资源内容 -->
          <div class="resource-main">
            <template v-if="selectedStudentGroup">
              <p class="student-profile-line">{{ selectedStudentGroup.student_profile }}</p>
              <!-- 按阶段分组展示 -->
              <div v-for="stageId in showcaseStages" :key="stageId" class="stage-group">
                <div class="stage-group-header">
                  <span class="stage-label">阶段 {{ stageId }}</span>
                  <el-tag size="small" type="info">{{ getShowcaseByStage(stageId).length }} 个资源</el-tag>
                </div>
                <div v-for="(res, idx) in getShowcaseByStage(stageId)" :key="`${stageId}-${res.resource_type}-${idx}`" class="resource-card">
                  <div class="res-card-header" @click="toggleResContent(`${stageId}-${idx}`)">
                    <el-tag size="small" :type="resTypeTag(res.resource_type)">{{ res.resource_type_name || res.resource_type }}</el-tag>
                    <span class="res-topic">{{ res.topic || '未知主题' }}</span>
                    <template v-if="res.quality_score?.overall_score">
                      <el-tag size="small" :type="gradeTagType(res.quality_score.overall_score)">
                        {{ res.quality_score.overall_score }}分 {{ res.quality_score.grade || getGrade(res.quality_score.overall_score) }}
                      </el-tag>
                    </template>
                    <el-tag v-else size="small" type="warning" effect="plain">未评估</el-tag>
                    <span class="res-time">{{ formatDate(res.created_at) }}</span>
                    <el-icon class="expand-icon" :class="{ expanded: expandedResIdx === `${stageId}-${idx}` }"><ArrowDown /></el-icon>
                  </div>
                  <div v-if="expandedResIdx === `${stageId}-${idx}`" class="res-expand">
                    <!-- 7维度评分 -->
                    <div v-if="res.quality_score?.overall_score" class="quality-dims">
                      <div class="dim-item"><span class="dim-label">主题相关</span><el-progress :percentage="res.quality_score.relevance || 0" :stroke-width="8" style="width:120px" /></div>
                      <div class="dim-item"><span class="dim-label">内容完整</span><el-progress :percentage="res.quality_score.completeness || 0" :stroke-width="8" style="width:120px" /></div>
                      <div class="dim-item"><span class="dim-label">个性化</span><el-progress :percentage="res.quality_score.personalization || 0" :stroke-width="8" style="width:120px" /></div>
                      <div class="dim-item"><span class="dim-label">准确性</span><el-progress :percentage="res.quality_score.accuracy || 0" :stroke-width="8" style="width:120px" /></div>
                      <div class="dim-item"><span class="dim-label">难度适配</span><el-progress :percentage="res.quality_score.difficulty_fit || 0" :stroke-width="8" style="width:120px" /></div>
                    </div>
                    <div v-else class="no-score">暂未评估</div>
                    <!-- 内容预览 -->
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
                  </div>
                </div>
              </div>
              <el-empty v-if="!selectedStudentGroup.resources?.length" description="暂无资源数据" />
            </template>
          </div>
        </div>
      </el-tab-pane>

      <!-- ④ 智能辅导案例 -->
      <el-tab-pane name="tutor">
        <template #label><span>④ 智能辅导 ({{ cases.tutor_dialogues.length }}个案例)</span></template>
        <div class="tutor-cases">
          <el-card v-for="item in cases.tutor_dialogues" :key="item.case_id" class="tutor-case-card" shadow="never">
            <div class="tutor-header">
              <el-tag :type="questionTypeTag(item.question_type)" size="small">{{ item.question_type }}</el-tag>
              <span class="tutor-title">{{ item.title }}</span>
            </div>
            <div class="dialogue">
              <div class="msg msg-user">
                <div class="msg-label">学生提问</div>
                <div class="msg-content">{{ item.question }}</div>
              </div>
              <div class="msg msg-assistant">
                <div class="msg-label">AI辅导</div>
                <div class="msg-content" v-html="renderMarkdown(item.answer)"></div>
              </div>
            </div>
            <div v-if="item.resource_type_used" class="resource-badge">
              使用资源: {{ item.resource_type_used }}
            </div>
          </el-card>
        </div>
      </el-tab-pane>

      <!-- ⑤ 学习评估案例 -->
      <el-tab-pane name="evaluations">
        <template #label><span>⑤ 学习评估 ({{ cases.evaluations.length }}个案例)</span></template>
        <div class="case-grid">
          <el-card v-for="item in cases.evaluations" :key="item.case_id" class="case-card" shadow="hover">
            <template #header>
              <div class="case-header">
                <span class="case-title">{{ item.title }}</span>
                <el-tag :type="gradeType(item.evaluation_result.overall_grade)" size="small">
                  {{ item.evaluation_result.overall_grade }}
                </el-tag>
              </div>
            </template>
            <p class="profile-summary">学生情况：{{ item.student_profile_summary }}</p>
            <el-row :gutter="16" class="eval-stats">
              <el-col :span="8">
                <div class="eval-stat">
                  <div class="eval-stat-value">{{ item.evaluation_result.total_score || 0 }}</div>
                  <div class="eval-stat-label">总分</div>
                </div>
              </el-col>
              <el-col :span="8">
                <div class="eval-stat">
                  <div class="eval-stat-value">{{ ((item.evaluation_result.accuracy_rate || 0) * 100).toFixed(0) }}%</div>
                  <div class="eval-stat-label">正确率</div>
                </div>
              </el-col>
              <el-col :span="8">
                <div class="eval-stat">
                  <div class="eval-stat-value">{{ ((item.evaluation_result.mastery_level || 0) * 100).toFixed(0) }}%</div>
                  <div class="eval-stat-label">掌握度</div>
                </div>
              </el-col>
            </el-row>
            <div v-if="item.evaluation_result.analysis" class="eval-analysis">
              <div v-if="item.evaluation_result.analysis.strengths?.length" class="analysis-section">
                <span class="analysis-label">优势：</span>
                <el-tag v-for="s in item.evaluation_result.analysis.strengths" :key="s" type="success" size="small" class="analysis-tag">{{ s }}</el-tag>
              </div>
              <div v-if="item.evaluation_result.analysis.weaknesses?.length" class="analysis-section">
                <span class="analysis-label">薄弱点：</span>
                <el-tag v-for="w in item.evaluation_result.analysis.weaknesses" :key="w" type="danger" size="small" class="analysis-tag">{{ w }}</el-tag>
              </div>
              <div v-if="item.evaluation_result.analysis.suggestions?.length" class="analysis-section">
                <span class="analysis-label">建议：</span>
                <p v-for="(s, i) in item.evaluation_result.analysis.suggestions" :key="i" class="suggestion-text">{{ s }}</p>
              </div>
            </div>
            <div v-if="item.path_adjustment" class="path-adjust">
              路径已动态调整: {{ item.path_adjustment.reason }}
            </div>
          </el-card>
        </div>
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { marked } from 'marked'
import { renderMath } from '@/utils/renderMath'
import { renderMd } from '@/utils/renderMarkdown'
import { ElMessage } from 'element-plus'
import { ArrowDown } from '@element-plus/icons-vue'
import axios from 'axios'

const activeMainTab = ref('profiles')
const cases = ref<any>({
  profiles: [], resources: [], resources_by_student: [], paths: [],
  tutor_dialogues: [], evaluations: [], system_info: {}
})

const selectedStudentIdx = ref(0)
const expandedResIdx = ref<string | null>(null)

const overviewCards = computed(() => [
  { value: cases.value.profiles.length, label: '画像案例' },
  { value: cases.value.resources.length, label: '资源生成案例' },
  { value: cases.value.paths.length, label: '路径推荐案例' },
  { value: cases.value.tutor_dialogues.length, label: '辅导对话案例' },
])

const selectedStudentGroup = computed(() => {
  const groups = cases.value.resources_by_student || []
  return groups[selectedStudentIdx.value] || null
})

const showcaseStages = computed(() => {
  if (!selectedStudentGroup.value) return []
  const stages = new Set<number>()
  ;(selectedStudentGroup.value.resources || []).forEach((r: any) => stages.add(r.stage_id || 0))
  return Array.from(stages).sort((a: number, b: number) => a - b)
})

function getShowcaseByStage(stageId: number) {
  return (selectedStudentGroup.value?.resources || []).filter((r: any) => (r.stage_id || 0) === stageId)
}

function toggleResContent(key: string) {
  expandedResIdx.value = expandedResIdx.value === key ? null : key
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

const isMarkdownType = (type: string) =>
  ['document', 'reading_material', 'summary'].includes(type)

const difficultyType = (d: string) => {
  if (d === '基础') return 'success'
  if (d === '进阶') return 'warning'
  return 'danger'
}

const renderMarkdown = (content: any) => {
  const text = typeof content === 'string' ? content : (content?.content || content?.mindmap_markdown || JSON.stringify(content))
  return renderMd(text)
}

const gradeType = (grade: string) => {
  if (!grade) return 'info'
  if (grade.startsWith('A')) return 'success'
  if (grade.startsWith('B')) return ''
  if (grade.startsWith('C')) return 'warning'
  return 'danger'
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

const questionTypeTag = (t: string) => {
  if (t?.includes('代码') || t?.includes('调试')) return 'danger'
  if (t?.includes('概念')) return ''
  return 'info'
}

async function fetchCases() {
  try {
    const token = localStorage.getItem('token')
    const res = await axios.get('/api/v1/showcase/cases', {
      headers: { Authorization: `Bearer ${token}` }
    })
    cases.value = res.data
  } catch (e: any) {
    ElMessage.error('加载案例数据失败: ' + (e.message || '未知错误'))
  }
}

onMounted(fetchCases)
</script>

<style scoped>
.showcase-page { padding: 20px; }
.page-header { display: flex; align-items: center; gap: 16px; margin-bottom: 24px; }
.page-title { margin: 0; font-size: 22px; }
.stat-row { margin-bottom: 24px; }
.stat-card { background: var(--color-bg-card); border-radius: var(--radius-lg); padding: 20px; text-align: center; border: 1px solid var(--color-border); box-shadow: var(--shadow-card); }
.stat-value { font-size: 28px; font-weight: 700; color: var(--el-color-primary); }
.stat-label { font-size: 13px; color: var(--color-text-muted); margin-top: 4px; }
.case-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(400px, 1fr)); gap: 20px; }
.case-card { border-radius: var(--radius-lg); }
.case-header { display: flex; justify-content: space-between; align-items: center; }
.case-title { font-weight: 600; }
.case-desc { color: var(--color-text-secondary); font-size: 14px; margin-bottom: 16px; }
.profile-summary { color: var(--color-text-secondary); margin-bottom: 12px; }
.path-steps { margin: 16px 0; }
.recommend-reason { margin-top: 12px; padding: 10px 14px; background: var(--color-border-light); border-radius: 8px; font-size: 14px; color: var(--color-text-secondary); }

/* 资源生成 Tab - 学生分组布局 */
.resource-layout { display: flex; gap: 20px; min-height: 480px; }
.student-sidebar {
  width: 200px; flex-shrink: 0; border: 1px solid var(--color-border); border-radius: var(--radius-lg);
  overflow-y: auto; background: var(--color-border-light);
}
.student-item {
  padding: 14px 16px; cursor: pointer; border-bottom: 1px solid var(--color-border); transition: background .15s;
}
.student-item:hover { background: var(--color-primary-lightest); }
.student-item.is-active { background: var(--color-primary-lightest); border-left: 3px solid var(--color-primary); }
.student-name { font-weight: 600; font-size: 14px; color: var(--color-text-primary); margin-bottom: 4px; }
.student-meta { font-size: 12px; color: var(--color-text-muted); }
.resource-main { flex: 1; min-width: 0; }
.student-profile-line { color: var(--color-text-secondary); font-size: 13px; margin-bottom: 12px; }
.stage-group { margin-bottom: 16px; }
.stage-group-header { display: flex; align-items: center; gap: 8px; padding: 8px 0; border-bottom: 2px solid var(--color-border); margin-bottom: 8px; }
.stage-label { font-size: 14px; font-weight: 700; color: var(--color-primary); }
.resource-card { background: var(--color-bg-card); border: 1px solid var(--color-border); border-radius: var(--radius-lg); padding: 12px 16px; margin-bottom: 8px; transition: border-color 0.15s; }
.resource-card:hover { border-color: var(--color-primary-light); }
.res-card-header { display: flex; align-items: center; gap: 10px; cursor: pointer; flex-wrap: wrap; }
.res-topic { font-weight: 600; font-size: 14px; color: var(--color-text-primary); }
.res-time { font-size: 12px; color: var(--color-text-muted); margin-left: auto; white-space: nowrap; }
.expand-icon { color: var(--color-text-muted); transition: transform 0.2s; margin-left: 8px; flex-shrink: 0; }
.expand-icon.expanded { transform: rotate(180deg); }
.res-expand { padding: 10px 0 0; }
.quality-dims { display: flex; flex-wrap: wrap; gap: 12px; padding: 10px 16px; background: var(--color-primary-lightest); border-radius: 8px; border: 1px solid var(--color-primary-lightest); margin-bottom: 10px; }
.dim-item { display: flex; align-items: center; gap: 6px; }
.dim-label { font-size: 12px; color: var(--color-text-secondary); white-space: nowrap; font-weight: 500; }
.no-score { padding: 8px 16px; color: var(--color-text-muted); font-size: 13px; }
.res-content-preview { padding: 12px 16px; background: var(--color-border-light); border-radius: 8px; border: 1px solid var(--color-border); max-height: 300px; overflow-y: auto; font-size: 13px; line-height: 1.7; color: var(--color-text-secondary); }
.code-preview { background: #1e1e2e; color: #cdd6f4; padding: 12px; border-radius: 8px; font-size: 12px; overflow-x: auto; margin: 0; white-space: pre-wrap; }
.raw-preview pre { background: var(--color-border-light); padding: 10px; border-radius: 6px; font-size: 11px; overflow-x: auto; margin: 0; white-space: pre-wrap; }
.empty-hint { padding: 40px; text-align: center; color: var(--color-text-muted); }

/* 资源内容渲染 */
.markdown-body { line-height: 1.8; }
.mindmap-content { padding: 12px; line-height: 1.8; }
.mindmap-content ul { padding-left: 20px; }
.glossary-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(260px, 1fr)); gap: 10px; }
.term-card { padding: 12px; background: var(--color-border-light); border-radius: 8px; border: 1px solid var(--color-border); }
.term-name { font-weight: 700; font-size: 15px; color: var(--el-color-primary); margin-bottom: 4px; }
.term-def { color: var(--color-text-primary); margin-bottom: 4px; }
.term-example { color: var(--color-text-secondary); font-size: 13px; }
.question-content { display: flex; flex-direction: column; gap: 16px; }
.question-item { padding: 14px; background: var(--color-border-light); border-radius: 8px; border: 1px solid var(--color-border); }
.question-header { display: flex; gap: 6px; margin-bottom: 6px; }
.question-text { font-weight: 500; margin: 0 0 8px; line-height: 1.6; }
.question-options { padding-left: 14px; margin-bottom: 8px; }
.option-item { margin: 3px 0; color: var(--color-text-secondary); }
.option-key { font-weight: 600; color: var(--el-color-primary); margin-right: 4px; }
.question-answer { font-size: 14px; color: var(--color-text-primary); margin-bottom: 4px; }
.answer-label { font-weight: 600; color: var(--el-color-success); }
.question-explain { font-size: 13px; color: var(--color-text-secondary); padding: 8px 12px; background: var(--color-primary-lightest); border-radius: 6px; }
.explain-label { font-weight: 600; }
.code-content { display: flex; flex-direction: column; gap: 16px; }
.code-example-item { padding: 14px; background: var(--color-border-light); border-radius: 8px; border: 1px solid var(--color-border); }
.code-header { display: flex; align-items: center; gap: 8px; margin-bottom: 6px; }
.code-title { font-weight: 600; font-size: 14px; }
.code-desc { color: var(--color-text-secondary); margin: 0 0 10px; font-size: 13px; }
.code-block { background: #1e1e2e; color: #cdd6f4; padding: 14px; border-radius: 8px; font-size: 13px; overflow-x: auto; margin: 0; line-height: 1.6; }
.raw-content pre { background: var(--color-border-light); padding: 14px; border-radius: 8px; font-size: 12px; overflow-x: auto; }

/* 智能辅导 */
.tutor-case-card { margin-bottom: 20px; border-radius: var(--radius-lg); }
.tutor-header { display: flex; align-items: center; gap: 10px; margin-bottom: 12px; }
.tutor-title { font-weight: 600; }
.dialogue { display: flex; flex-direction: column; gap: 12px; }
.msg { padding: 12px 16px; border-radius: var(--radius-lg); }
.msg-user { background: var(--color-primary-lightest); border: 1px solid var(--color-primary-lightest); }
.msg-assistant { background: #f0fdf4; border: 1px solid #bbf7d0; }
.msg-label { font-size: 12px; font-weight: 600; color: var(--color-text-muted); margin-bottom: 4px; }
.msg-content { line-height: 1.7; }
.resource-badge { margin-top: 12px; color: var(--color-text-muted); font-size: 13px; }

/* 学习评估 */
.eval-stats { margin-bottom: 16px; }
.eval-stat { text-align: center; }
.eval-stat-value { font-size: 24px; font-weight: 700; color: var(--el-color-primary); }
.eval-stat-label { font-size: 12px; color: var(--color-text-muted); }
.eval-analysis { margin-top: 12px; }
.analysis-section { margin-bottom: 8px; }
.analysis-label { font-weight: 600; font-size: 13px; color: var(--color-text-secondary); }
.analysis-tag { margin: 0 4px 4px 0; }
.suggestion-text { margin: 2px 0; font-size: 13px; color: var(--color-text-secondary); padding-left: 12px; border-left: 2px solid var(--color-border); }
.path-adjust { margin-top: 12px; padding: 10px; background: #fffbe6; border-radius: 8px; font-size: 14px; }

:deep(.el-tabs__header) { margin-bottom: 0; }
</style>
