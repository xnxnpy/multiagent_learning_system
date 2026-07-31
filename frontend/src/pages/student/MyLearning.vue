<template>
  <div class="my-learning-page">
    <div class="page-header">
      <h2 class="page-title">我的学习记录</h2>
      <el-tag type="success" size="large">智学优培——基于大模型多模态生成的高校个性化学习智能体平台</el-tag>
    </div>

    <el-tabs v-model="activeTab" class="learning-tabs">
      <!-- ① 我的画像 -->
      <el-tab-pane name="profile">
        <template #label><span>① 我的画像</span></template>
        <div v-if="profile" class="profile-card">
          <el-card shadow="hover">
            <template #header>
              <div class="card-header">
                <span class="card-title">{{ profile.real_name || '我的学习画像' }}</span>
                <el-tag size="small" type="info">{{ profile.major || '待完善' }}</el-tag>
              </div>
            </template>
            <el-descriptions :column="2" border size="small">
              <el-descriptions-item label="专业">{{ profile.major || '-' }}</el-descriptions-item>
              <el-descriptions-item label="年级">{{ profile.grade || '-' }}</el-descriptions-item>
              <el-descriptions-item label="学习目标" :span="2">{{ profile.goal || '-' }}</el-descriptions-item>
              <el-descriptions-item label="知识水平">{{ profile.knowledge_level || '-' }}</el-descriptions-item>
              <el-descriptions-item label="学习风格">{{ profile.learning_style || '-' }}</el-descriptions-item>
              <el-descriptions-item label="编程能力">{{ profile.coding_ability || '-' }}</el-descriptions-item>
              <el-descriptions-item label="兴趣方向">
                <el-tag v-for="item in (profile.interests || [])" :key="item" size="small" style="margin-right:4px">{{ item }}</el-tag>
              </el-descriptions-item>
              <el-descriptions-item label="薄弱点" :span="2">
                <el-tag v-for="item in (profile.weakness || [])" :key="item" type="warning" size="small" style="margin-right:4px">{{ item }}</el-tag>
              </el-descriptions-item>
            </el-descriptions>
          </el-card>
        </div>
        <el-empty v-else description="暂无画像数据，请先完成画像构建" />
      </el-tab-pane>

      <!-- ② 学习路径 -->
      <el-tab-pane name="path">
        <template #label><span>② 学习路径</span></template>
        <div v-if="learningPath" class="path-content">
          <h3>{{ learningPath.title }}</h3>
          <el-steps :active="learningPath.completed_stages?.length || 0" direction="vertical" finish-status="success" class="path-steps">
            <el-step v-for="(stage, idx) in (learningPath.stages || [])" :key="idx"
                     :title="stage.title" :description="stage.description" />
          </el-steps>
        </div>
        <el-empty v-else description="暂无学习路径，请先生成学习路径" />
      </el-tab-pane>

      <!-- ③ 学习资源 -->
      <el-tab-pane name="resources">
        <template #label><span>③ 学习资源</span></template>
        <div v-if="hasResources">
          <el-tabs v-model="activeResourceTab" tab-position="left" class="resource-sub-tabs">
            <!-- 学习文档 -->
            <el-tab-pane v-if="resources.document" name="document" label="学习文档">
              <div class="markdown-body" v-html="renderMarkdown(resources.document.content)"></div>
            </el-tab-pane>
            <!-- 教学视频 -->
            <el-tab-pane v-if="resources.ppt_video?.video_url" name="ppt_video" label="教学视频">
              <div class="video-player-wrap">
                <video :src="resources.ppt_video.video_url" controls style="width:100%;max-height:500px;border-radius:8px"></video>
                <div v-if="resources.ppt_video.duration_seconds" style="margin-top:8px;color:#909399;font-size:13px">
                  时长: {{ Math.floor(resources.ppt_video.duration_seconds / 60) }}:{{ String(resources.ppt_video.duration_seconds % 60).padStart(2, '0') }}
                  <span v-if="resources.ppt_video.pages_count"> · {{ resources.ppt_video.pages_count }} 页</span>
                </div>
              </div>
            </el-tab-pane>
            <!-- 思维导图 -->
            <el-tab-pane v-if="resources.mindmap_markdown || resources.mindmap" name="mindmap" label="思维导图">
              <div class="markdown-body" v-html="renderMarkdown(resources.mindmap_markdown || resources.mindmap?.mindmap_markdown)"></div>
            </el-tab-pane>
            <!-- 练习题目 -->
            <el-tab-pane v-if="resources.questions" name="questions" label="练习题目">
              <div v-for="(q, qi) in (resources.questions.questions || [])" :key="qi" class="question-item">
                <div class="question-header">
                  <el-tag :type="q.type === '编程题' ? 'danger' : 'info'" size="small">{{ q.type }}</el-tag>
                  <el-tag size="small" :type="difficultyType(q.difficulty)">{{ q.difficulty }}</el-tag>
                </div>
                <p class="question-text">{{ qi + 1 }}. {{ q.question }}</p>
                <div v-if="q.options" class="question-options">
                  <div v-for="(val, key) in q.options" :key="key" class="option-item">
                    <span class="option-key">{{ key }}.</span> {{ val }}
                  </div>
                </div>
                <div class="question-answer"><span class="answer-label">答案：</span>{{ q.answer }}</div>
                <div v-if="q.explanation" class="question-explain"><span class="explain-label">解析：</span>{{ q.explanation }}</div>
              </div>
            </el-tab-pane>
            <!-- 代码示例 -->
            <el-tab-pane v-if="resources.code" name="code" label="代码示例">
              <div class="code-example-item">
                <div class="code-header">
                  <span class="code-title">{{ resources.code.title || '代码示例' }}</span>
                  <el-tag v-if="resources.code.difficulty" size="small" :type="difficultyType(resources.code.difficulty)">{{ resources.code.difficulty }}</el-tag>
                </div>
                <p v-if="resources.code.description" class="code-desc">{{ resources.code.description }}</p>
                <pre class="code-block"><code v-html="highlightedCode"></code></pre>
                <div v-if="resources.code.test_cases?.length" class="test-cases">
                  <p style="font-size:13px;color:#909399;margin:8px 0 4px">测试用例：</p>
                  <div v-for="(tc, ti) in resources.code.test_cases" :key="ti" style="font-size:12px;color:#606266;margin:2px 0">
                    输入: <code>{{ tc.input }}</code> → 期望: <code>{{ tc.expected }}</code>
                  </div>
                </div>
              </div>
            </el-tab-pane>
            <!-- 拓展阅读 -->
            <el-tab-pane v-if="resources.reading_material" name="reading_material" label="拓展阅读">
              <div class="markdown-body" v-html="renderMarkdown(resources.reading_material.content)"></div>
            </el-tab-pane>
            <!-- 术语词汇 -->
            <el-tab-pane v-if="resources.glossary" name="glossary" label="术语词汇">
              <div class="glossary-grid">
                <el-card v-for="term in (resources.glossary.terms || [])" :key="term.term" class="term-card" shadow="never">
                  <div class="term-name">{{ term.term }}</div>
                  <div class="term-def">{{ term.definition }}</div>
                  <div class="term-example">例：{{ term.example }}</div>
                </el-card>
              </div>
            </el-tab-pane>
            <!-- 知识关联图 -->
            <el-tab-pane v-if="resources.knowledge_link" name="knowledge_link" label="知识关联图">
              <p>节点数: {{ resources.knowledge_link.nodes?.length || 0 }}，边数: {{ resources.knowledge_link.edges?.length || 0 }}</p>
              <div class="node-list">
                <el-tag v-for="node in (resources.knowledge_link.nodes || [])" :key="node.id" class="node-tag">{{ node.label }}</el-tag>
              </div>
            </el-tab-pane>
            <!-- 学习总结 -->
            <el-tab-pane v-if="resources.summary" name="summary" label="学习总结">
              <div class="markdown-body" v-html="renderMarkdown(resources.summary.content)"></div>
            </el-tab-pane>
          </el-tabs>
        </div>
        <el-empty v-else description="暂无学习资源" />
      </el-tab-pane>

      <!-- ④ 辅导对话 -->
      <el-tab-pane name="tutor-chat">
        <template #label><span>④ 辅导对话</span></template>
        <div v-if="tutorSessions.length" class="tutor-sessions">
          <div v-for="(msgs, si) in tutorSessions" :key="si" class="tutor-session">
            <h4 class="session-title">会话 {{ si + 1 }}</h4>
            <div v-for="(msg, mi) in msgs" :key="mi" :class="['chat-msg', msg.role === 'user' ? 'msg-user' : 'msg-assistant']">
              <div class="msg-label">{{ msg.role === 'user' ? '我' : 'AI辅导' }}</div>
              <div class="msg-content" v-html="msg.role === 'assistant' ? renderMarkdown(msg.content) : msg.content"></div>
            </div>
          </div>
        </div>
        <el-empty v-else description="暂无辅导对话记录" />
      </el-tab-pane>

      <!-- ⑤ 学习评估 -->
      <el-tab-pane name="evaluation">
        <template #label><span>⑤ 学习评估</span></template>
        <div v-if="evaluation" class="eval-content">
          <el-row :gutter="20" class="eval-stats">
            <el-col :span="8">
              <div class="eval-stat"><div class="eval-stat-value">{{ evaluation.total_score || 0 }}</div><div class="eval-stat-label">总分</div></div>
            </el-col>
            <el-col :span="8">
              <div class="eval-stat"><div class="eval-stat-value">{{ ((evaluation.accuracy_rate || 0) * 100).toFixed(0) }}%</div><div class="eval-stat-label">正确率</div></div>
            </el-col>
            <el-col :span="8">
              <div class="eval-stat"><div class="eval-stat-value">{{ ((evaluation.mastery_level || 0) * 100).toFixed(0) }}%</div><div class="eval-stat-label">掌握度</div></div>
            </el-col>
          </el-row>
          <el-tag :type="gradeType(evaluation.overall_grade)" size="large" style="margin-bottom:16px">
            综合等级：{{ evaluation.overall_grade }}
          </el-tag>
          <div v-if="evaluation.analysis" class="eval-analysis">
            <div v-if="evaluation.analysis.strengths?.length" class="analysis-section">
              <span class="analysis-label">优势：</span>
              <el-tag v-for="s in evaluation.analysis.strengths" :key="s" type="success" size="small" class="analysis-tag">{{ s }}</el-tag>
            </div>
            <div v-if="evaluation.analysis.weaknesses?.length" class="analysis-section">
              <span class="analysis-label">薄弱点：</span>
              <el-tag v-for="w in evaluation.analysis.weaknesses" :key="w" type="danger" size="small" class="analysis-tag">{{ w }}</el-tag>
            </div>
            <div v-if="evaluation.analysis.suggestions?.length" class="analysis-section">
              <span class="analysis-label">建议：</span>
              <p v-for="(s, i) in evaluation.analysis.suggestions" :key="i" class="suggestion-text">{{ s }}</p>
            </div>
          </div>
        </div>
        <el-empty v-else description="暂无评估数据" />
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { marked } from 'marked'
import hljs from 'highlight.js'
import 'highlight.js/styles/github.css'
import { renderMath } from '@/utils/renderMath'
import { renderMd } from '@/utils/renderMarkdown'
import { ElMessage } from 'element-plus'
import axios from 'axios'

const activeTab = ref('profile')
const activeResourceTab = ref('document')
const profile = ref<any>(null)
const learningPath = ref<any>(null)
const resources = ref<any>({})
const evaluation = ref<any>(null)
const tutorSessions = ref<any[]>([])

const hasResources = computed(() => {
  const r = resources.value
  return r.document || r.mindmap_markdown || r.mindmap || r.questions ||
         r.code || r.video_script || r.reading_material || r.glossary ||
         r.knowledge_link || r.summary
})

const renderMarkdown = (content: any) => {
  const text = typeof content === 'string' ? content : (content?.content || content?.mindmap_markdown || JSON.stringify(content))
  return renderMd(text)
}

const gradeType = (grade: string) => {
  if (!grade) return 'info'
  if (grade.startsWith('A')) return 'success'
  if (grade.startsWith('B')) return 'primary'
  if (grade.startsWith('C')) return 'warning'
  return 'danger'
}

const difficultyType = (d: string) => {
  if (d === '基础') return 'success'
  if (d === '进阶') return 'warning'
  return 'danger'
}

const highlightedCode = computed(() => {
  if (!resources.value.code?.code) return ''
  try {
    return hljs.highlight(resources.value.code.code, { language: 'python' }).value
  } catch {
    return resources.value.code.code
  }
})

onMounted(async () => {
  const token = localStorage.getItem('token')
  const headers = { Authorization: `Bearer ${token}` }

  try {
    // 并行获取画像/路径/资源/评估/辅导会话元数据
    const [profileRes, pathRes, resRes, evalRes, tutorRes] = await Promise.allSettled([
      axios.get('/api/v1/student/profile', { headers }),
      axios.get('/api/v1/student/learning-path', { headers }),
      axios.get('/api/v1/student/resources', { headers }),
      axios.get('/api/v1/student/evaluation/report', { headers }),
      axios.get('/api/v1/tutor/sessions', { headers }),
    ])

    if (profileRes.status === 'fulfilled') profile.value = profileRes.value.data
    if (pathRes.status === 'fulfilled') learningPath.value = pathRes.value.data
    if (resRes.status === 'fulfilled') resources.value = resRes.value.data
    if (evalRes.status === 'fulfilled') evaluation.value = evalRes.value.data
    if (tutorRes.status === 'fulfilled') {
      const sessionMetas: any[] = tutorRes.value.data?.sessions || []
      // 逐个拉取每个会话的真实聊天历史消息
      const histories = await Promise.allSettled(
        sessionMetas.map((m: any) =>
          axios.get(`/api/v1/tutor/history/${m.session_id}`, { headers })
        )
      )
      tutorSessions.value = histories
        .map((r: any) => (r.status === 'fulfilled' ? r.value.data?.messages ?? [] : []))
        .filter((msgs: any[]) => msgs.length > 0)
    }
  } catch (e: any) {
    ElMessage.error('加载学习记录失败: ' + (e.message || '未知错误'))
  }
})
</script>

<style scoped>
.my-learning-page { max-width: 1400px; }

.page-header {
  display: flex;
  align-items: center;
  gap: 16px;
  margin-bottom: var(--space-section-gap, 24px);
}

.page-title {
  margin: 0;
  font-size: var(--text-xl);
  font-weight: 700;
  color: var(--color-text-primary);
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.card-title {
  font-weight: 600;
  font-size: var(--text-lg);
  color: var(--color-text-primary);
}

.path-content h3 {
  margin-top: 0;
  color: var(--color-text-primary);
}

.path-steps { margin: 16px 0; }

.markdown-body {
  line-height: 1.8;
  padding: 16px;
  color: var(--color-text-primary);
  word-wrap: break-word;
}
.markdown-body :deep(h1) { font-size: 24px; margin: 20px 0 12px; font-weight: 700; }
.markdown-body :deep(h2) { font-size: 20px; margin: 18px 0 10px; font-weight: 700; }
.markdown-body :deep(h3) { font-size: 17px; margin: 14px 0 8px; font-weight: 600; }
.markdown-body :deep(h4) { font-size: 16px; margin: 12px 0 6px; font-weight: 600; }
.markdown-body :deep(p) { margin: 8px 0; }
.markdown-body :deep(strong) { font-weight: 600; }
.markdown-body :deep(ul), .markdown-body :deep(ol) { margin: 8px 0; padding-left: 24px; }
.markdown-body :deep(li) { margin: 4px 0; line-height: 1.8; }
.markdown-body :deep(blockquote) { margin: 12px 0; padding: 12px 16px; border-left: 4px solid var(--color-primary); background: var(--color-bg-page); border-radius: 0 8px 8px 0; }
.markdown-body :deep(hr) { margin: 16px 0; border: none; border-top: 1px solid var(--color-border); }
.markdown-body :deep(table) { width: 100%; border-collapse: collapse; margin: 12px 0; font-size: 14px; }
.markdown-body :deep(th), .markdown-body :deep(td) { border: 1px solid var(--color-border); padding: 8px 12px; text-align: left; }
.markdown-body :deep(th) { background: var(--color-bg-page); font-weight: 600; }
.markdown-body :deep(pre) { background: #fff; color: var(--color-text-primary); padding: 16px; border-radius: 8px; overflow-x: auto; font-size: 13px; line-height: 1.6; margin: 12px 0; }
.markdown-body :deep(code) { font-family: var(--font-mono); font-size: 13px; }
.markdown-body :deep(p > code), .markdown-body :deep(li > code) { background: var(--color-bg-page); padding: 2px 6px; border-radius: 4px; color: var(--color-primary); }
.markdown-body :deep(pre > code) { background: transparent; padding: 0; color: inherit; }
.markdown-body :deep(img) { max-width: 100%; border-radius: 8px; margin: 8px 0; }
.markdown-body :deep(a) { color: var(--color-primary); text-decoration: none; }

.question-item {
  padding: 16px;
  background: var(--color-bg-card);
  border-radius: var(--radius-md);
  border: 1px solid var(--color-border-light);
  border-left: 3px solid var(--color-primary);
  margin-bottom: 16px;
}

.question-header {
  display: flex;
  gap: 8px;
  margin-bottom: 8px;
}

.question-text {
  font-weight: 500;
  margin: 0 0 10px;
  line-height: 1.6;
  color: var(--color-text-primary);
}

.question-options {
  padding-left: 16px;
  margin-bottom: 10px;
}

.option-item {
  margin: 4px 0;
  color: var(--color-text-secondary);
}

.option-key {
  font-weight: 600;
  color: var(--color-primary);
  margin-right: 4px;
}

.question-answer {
  font-size: 14px;
  color: var(--color-text-primary);
  margin-bottom: 4px;
}

.answer-label {
  font-weight: 600;
  color: var(--color-success);
}

.question-explain {
  font-size: 13px;
  color: var(--color-text-secondary);
  padding: 8px 12px;
  background: var(--color-primary-faint);
  border-radius: var(--radius-sm);
}

.explain-label { font-weight: 600; }

.code-example-item {
  padding: 16px;
  background: var(--color-bg-card);
  border-radius: var(--radius-md);
  border: 1px solid var(--color-border-light);
  border-left: 3px solid var(--color-student);
  margin-bottom: 16px;
}

.code-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
}

.code-title {
  font-weight: 600;
  font-size: var(--text-base);
  color: var(--color-text-primary);
}

.code-desc {
  color: var(--color-text-secondary);
  margin: 0 0 12px;
  font-size: 14px;
}

.code-block {
  background: #fff;
  padding: 16px;
  border-radius: var(--radius-md);
  font-size: 13px;
  overflow-x: auto;
  margin: 0;
  line-height: 1.6;
}

.code-block code {
  font-family: var(--font-mono);
}

.video-script h4 {
  margin: 0 0 8px;
  color: var(--color-text-primary);
}

.scene-card {
  padding: 14px;
  margin: 12px 0;
  background: var(--color-bg-page);
  border-radius: var(--radius-md);
  border-left: 3px solid var(--color-primary);
}

.scene-header {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 8px;
}

.scene-num {
  font-weight: 700;
  color: var(--color-primary);
  font-size: 13px;
}

.scene-title {
  font-weight: 600;
  color: var(--color-text-primary);
}

.scene-visual {
  color: var(--color-text-muted);
  font-size: 13px;
  margin: 4px 0;
}

.scene-narration {
  color: var(--color-text-primary);
  font-size: 14px;
  margin: 6px 0 0;
  line-height: 1.7;
}

.glossary-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 12px;
}

.term-card {
  border-radius: var(--radius-md);
  border: 1px solid var(--color-border-light);
}

.term-name {
  font-weight: 700;
  font-size: var(--text-lg);
  color: var(--color-primary);
  margin-bottom: 6px;
}

.term-def {
  color: var(--color-text-primary);
  margin-bottom: 6px;
}

.term-example {
  color: var(--color-text-muted);
  font-size: 13px;
}

.node-list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 12px;
}

.node-tag { font-size: 14px; }

.eval-stats { margin-bottom: 16px; }

.eval-stat {
  text-align: center;
  background: var(--color-bg-card);
  padding: 20px;
  border-radius: var(--radius-md);
  border: 1px solid var(--color-border-light);
}

.eval-stat:nth-child(1) { border-top: 3px solid var(--color-primary); }
.eval-stat:nth-child(2) { border-top: 3px solid var(--color-success); }
.eval-stat:nth-child(3) { border-top: 3px solid var(--color-student); }

.eval-stat-value {
  font-size: 28px;
  font-weight: 700;
}

.eval-stat:nth-child(1) .eval-stat-value { color: var(--color-primary); }
.eval-stat:nth-child(2) .eval-stat-value { color: var(--color-success); }
.eval-stat:nth-child(3) .eval-stat-value { color: var(--color-student); }

.eval-stat-label {
  font-size: var(--text-xs);
  color: var(--color-text-muted);
  margin-top: 4px;
}

.eval-analysis { margin-top: 16px; }

.analysis-section { margin-bottom: 12px; }

.analysis-label {
  font-weight: 600;
  font-size: 13px;
  color: var(--color-text-secondary);
}

.analysis-tag { margin: 0 4px 4px 0; }

.suggestion-text {
  margin: 4px 0;
  font-size: 14px;
  color: var(--color-text-secondary);
  padding-left: 12px;
  border-left: 2px solid var(--color-primary);
}

.tutor-sessions {
  display: flex;
  flex-direction: column;
  gap: 24px;
  max-width: 700px;
}

.session-title {
  margin: 0 0 12px;
  font-size: 14px;
  color: var(--color-text-muted);
}

.chat-msg {
  padding: 12px 16px;
  border-radius: var(--radius-md);
  max-width: 85%;
  margin-bottom: 10px;
}

.msg-user {
  background: var(--color-student-pale);
  border: 1px solid var(--color-student-soft);
  align-self: flex-end;
}

.msg-assistant {
  background: var(--color-primary-faint);
  border: 1px solid var(--color-primary-pale);
  align-self: flex-start;
}

.msg-label {
  font-size: var(--text-xs);
  font-weight: 600;
  margin-bottom: 4px;
}

.msg-user .msg-label {
  color: var(--color-student);
}

.msg-assistant .msg-label {
  color: var(--color-primary-soft);
}

.msg-content {
  line-height: 1.7;
  color: var(--color-text-primary);
}
</style>
