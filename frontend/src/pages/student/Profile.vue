<template>
  <div class="profile-page">
    <div class="page-header">
      <h2 class="page-title">学习画像</h2>
    </div>

    <el-row :gutter="24">
      <!-- 左：对话式画像采集 -->
      <el-col :xs="24" :lg="16">
        <el-card class="chat-card" shadow="never">
          <template #header>
            <div class="card-header">
              <div class="header-left">
                <div class="ai-avatar">
                  <el-icon :size="18" color="#fff"><ChatDotRound /></el-icon>
                </div>
                <div>
                  <span class="card-title">对话式画像采集</span>
                  <span class="card-subtitle">通过对话了解您的学习背景</span>
                </div>
              </div>
              <div class="status-dot" :class="{ active: sending }"></div>
            </div>
          </template>

          <div class="chat-messages" ref="chatRef">
            <div
              v-for="(msg, idx) in messages"
              :key="idx"
              class="chat-message"
              :class="msg.role"
            >
              <div v-if="msg.role === 'assistant'" class="msg-avatar ai">
                <el-icon :size="14" color="#fff"><ChatDotRound /></el-icon>
              </div>

              <div class="bubble-wrap">
                <div class="bubble">
                  <span style="white-space: pre-wrap;">{{ msg.content }}</span>
                </div>

                <!-- 流式输出指示器 -->
                <div v-if="msg.streaming" class="typing-indicator">
                  <span class="dot"></span>
                  <span class="dot"></span>
                  <span class="dot"></span>
                </div>

                <div class="msg-meta">
                  <span class="msg-time">{{ msg.time }}</span>
                </div>
              </div>

              <div v-if="msg.role === 'user'" class="msg-avatar user">
                <span>我</span>
              </div>
            </div>
          </div>

          <div v-if="profileComplete && !workflowRunning && !hasPath" class="profile-complete-tip">
            ✅ 画像已采集完成，您可以继续修改或查看学习路径
          </div>

          <div class="chat-input-area">
            <div class="input-wrap">
              <el-input
                v-model="inputText"
                type="textarea"
                :rows="2"
                :autosize="{ minRows: 1, maxRows: 4 }"
                placeholder="请描述您的学习背景、目标、兴趣等..."
                resize="none"
                class="chat-textarea"
                @keydown.enter.exact.prevent="sendMessage"
              />
              <VoiceInputButton @result="(t) => inputText = t" />
              <button
                class="send-btn"
                :class="{ active: inputText.trim() && !sending }"
                :disabled="!inputText.trim() || sending"
                @click="sendMessage"
              >
                <el-icon :size="18"><Promotion /></el-icon>
              </button>
            </div>
          </div>
        </el-card>
      </el-col>

      <!-- 右：实时画像展示 -->
      <el-col :xs="24" :lg="8">
        <el-card class="profile-card" shadow="never">
          <template #header>
            <div class="card-header">
              <div class="header-left">
                <div class="ai-avatar" style="background: linear-gradient(135deg, #10b981, #059669);">
                  <el-icon :size="18" color="#fff"><User /></el-icon>
                </div>
                <span class="card-title">我的画像</span>
              </div>
            </div>
          </template>

          <div class="profile-header-bar">
            <div class="profile-name-display">
              <el-dropdown @command="handleProfileCommand" trigger="click">
                <span class="profile-name-text">
                  {{ currentProfileName }}
                  <el-icon class="el-icon--right"><ArrowDown /></el-icon>
                </span>
                <template #dropdown>
                  <el-dropdown-menu>
                    <el-dropdown-item
                      v-for="p in nonArchivedProfiles"
                      :key="p.id"
                      :command="{ action: 'switch', id: p.id }"
                    >
                      {{ p.profile_name }}
                      <el-tag v-if="p.is_active" size="small" type="success" style="margin-left: 8px">当前</el-tag>
                    </el-dropdown-item>
                    <el-dropdown-item divided :command="{ action: 'new' }">+ 新建画像</el-dropdown-item>
                    <el-dropdown-item :command="{ action: 'manage' }">管理画像</el-dropdown-item>
                  </el-dropdown-menu>
                </template>
              </el-dropdown>
            </div>
          </div>

          <div class="profile-fields">
            <div class="field-row">
              <span class="field-label">专业</span>
              <el-tag type="primary" effect="plain" size="small">{{ profile.major || '待完善' }}</el-tag>
            </div>
            <div class="field-row">
              <span class="field-label">年级</span>
              <el-tag type="success" effect="plain" size="small">{{ profile.grade || '待完善' }}</el-tag>
            </div>
            <div class="field-row">
              <span class="field-label">学习目标</span>
              <span class="field-value">{{ profile.goal || '待完善' }}</span>
            </div>
            <div class="field-row">
              <span class="field-label">知识水平</span>
              <el-tag :type="levelTagType(profile.knowledge_level)" effect="plain" size="small">
                {{ profile.knowledge_level || '待评估' }}
              </el-tag>
            </div>
            <div class="field-row">
              <span class="field-label">学习风格</span>
              <span class="field-value">{{ profile.learning_style || '待评估' }}</span>
            </div>
            <div class="field-row">
              <span class="field-label">编程能力</span>
              <span class="field-value">{{ profile.coding_ability || '待评估' }}</span>
            </div>
          </div>

          <div class="profile-section">
            <h4 class="section-title">兴趣方向</h4>
            <div class="tag-list">
              <el-tag v-for="tag in profile.interests" :key="tag" type="info" effect="plain" size="small" class="tag-item">
                {{ tag }}
              </el-tag>
              <span v-if="!profile.interests?.length" class="empty-hint">暂无</span>
            </div>
          </div>

          <div class="profile-section">
            <h4 class="section-title">薄弱环节</h4>
            <div class="tag-list">
              <el-tag v-for="tag in profile.weakness" :key="tag" type="danger" effect="plain" size="small" class="tag-item">
                {{ tag }}
              </el-tag>
              <span v-if="!profile.weakness?.length" class="empty-hint">暂无</span>
            </div>
          </div>

          <div v-if="workflowRunning" class="workflow-progress">
            <div class="workflow-progress-header">
              <el-icon class="is-loading" :size="14" color="#4F46E5"><Loading /></el-icon>
              <span class="workflow-progress-label">{{ currentAgentName }}</span>
              <span class="workflow-progress-pct">{{ workflowProgress }}%</span>
            </div>
            <el-progress :percentage="workflowProgress" :stroke-width="6" :show-text="false" color="#4F46E5" />
          </div>

          <el-button
            v-if="!workflowRunning && profile.major && profile.grade && profile.goal && profile.knowledge_level && hasPath"
            type="success"
            class="workflow-btn"
            :icon="DataAnalysis"
            @click="router.push('/student/learning-path')"
          >
            查看学习路径
          </el-button>
        </el-card>
      </el-col>
    </el-row>

    <!-- 画像管理对话框 -->
    <el-dialog v-model="showProfileList" title="画像管理" width="600px" class="custom-dialog">
      <el-button type="primary" @click="showNewProfileDialog = true" style="margin-bottom: 16px">
        + 新建画像
      </el-button>
      <el-table :data="profiles" stripe>
        <el-table-column label="画像名称" min-width="160">
          <template #default="{ row }">
            <template v-if="editingProfileId === row.id">
              <el-input v-model="editingProfileName" size="small" @keyup.enter="saveProfileName" @blur="saveProfileName" autofocus style="width: 200px" />
            </template>
            <template v-else>
              <span class="link-text" @click="handleActivateProfile(row.id)">{{ row.profile_name }}</span>
              <el-button link type="primary" size="small" @click.stop="startEditProfileName(row)" style="margin-left: 8px">
                <el-icon><Edit /></el-icon>
              </el-button>
            </template>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="100">
          <template #default="{ row }">
            <el-tag v-if="row.is_active" type="success" size="small">活跃</el-tag>
            <el-tag v-else-if="row.is_archived" type="info" size="small">归档</el-tag>
            <el-tag v-else type="info" size="small">-</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="140">
          <template #default="{ row }">
            <el-button v-if="!row.is_active && !row.is_archived" type="primary" link size="small" @click="handleActivateProfile(row.id)">切换</el-button>
            <el-button v-if="!row.is_active && !row.is_archived" type="warning" link size="small" @click="handleArchiveProfile(row.id)">归档</el-button>
            <el-button v-if="row.is_archived" type="success" link size="small" @click="handleRestoreProfile(row.id)">恢复</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-dialog>

    <!-- 新建画像对话框 -->
    <el-dialog v-model="showNewProfileDialog" title="新建画像" width="400px" class="custom-dialog">
      <el-input v-model="newProfileName" placeholder="输入画像名称（如：考研方向）" @keyup.enter="handleCreateProfile" autofocus />
      <template #footer>
        <el-button @click="showNewProfileDialog = false">取消</el-button>
        <el-button type="primary" @click="handleCreateProfile">创建</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted, onUnmounted, nextTick, watch } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { ChatDotRound, User, Promotion, DataAnalysis, Loading, ArrowDown, Edit } from '@element-plus/icons-vue'
import { studentAPI } from '@/api'
import VoiceInputButton from '@/components/VoiceInputButton.vue'
import { useUserStore } from '@/stores/userStore'
import { useAppStore } from '@/stores/appStore'
import { useLearningPathStore } from '@/stores/learningPathStore'
import { createProfileChatWebSocket } from '@/utils/websocket'
import type { StudentProfile } from '@/types'
import type WebSocketClient from '@/utils/websocket'
import request from '@/utils/axios'

const router = useRouter()
const userStore = useUserStore()
const appStore = useAppStore()

/* ── Chat state ──────────────────────────────── */

interface ChatMsg {
  role: 'user' | 'assistant'
  content: string
  time: string
  streaming?: boolean
}

const now = () => new Date().toLocaleTimeString()

const messages = ref<ChatMsg[]>([
  {
    role: 'assistant',
    content: '您好！我是您的学习顾问。为了给您制定个性化的学习方案，请先告诉我您的专业方向和年级？',
    time: now(),
  },
])
const inputText = ref('')
const sending = ref(false)
const chatRef = ref<HTMLElement | null>(null)
const needsWorkflow = ref(false)
const workflowRunning = ref(false)
const workflowProgress = ref(0)
const workflowStep = ref('')
const hasPath = ref(false)

/* ── WebSocket state ─────────────────────────── */

let wsClient: WebSocketClient | null = null
let currentAssistantMsg: ChatMsg | null = null
let isMounted = false

/* ── 多画像状态 ──────────────────────────────── */

const profiles = ref<any[]>([])
const activeProfileId = ref<number | null>(null)
const showProfileList = ref(false)
const showNewProfileDialog = ref(false)
const newProfileName = ref('')
const editingProfileId = ref<number | null>(null)
const editingProfileName = ref('')

/* ── Profile state ───────────────────────────── */

const profile = reactive<StudentProfile & { profile_name?: string }>({
  id: 0, user_id: 0, major: '', grade: '', goal: '',
  knowledge_level: '', learning_style: '', coding_ability: '',
  interests: [], weakness: [], profile_name: '',
})

/* ── Helpers ─────────────────────────────────── */

function levelTagType(level?: string): 'success' | 'warning' | 'danger' | 'info' {
  const map: Record<string, 'success' | 'warning' | 'danger' | 'info'> = {
    高级: 'danger', 中级: 'warning', 初级: 'info', 入门: 'success',
  }
  return map[level || ''] ?? 'info'
}

function scrollBottom() {
  nextTick(() => {
    if (chatRef.value) chatRef.value.scrollTop = chatRef.value.scrollHeight
  })
}

function addMsg(role: 'user' | 'assistant', content: string, streaming = false) {
  messages.value.push({ role, content, time: now(), streaming })
  scrollBottom()
}

/* ── Chat history ────────────────────────────── */

async function loadHistory() {
  try {
    let res: any
    if (activeProfileId.value) {
      res = await studentAPI.getProfileChatHistory(activeProfileId.value)
    } else {
      res = await request.get('/v1/student/chat/history')
    }
    if (res?.messages?.length) {
      messages.value = res.messages.map((m: any) => ({
        role: m.role as 'user' | 'assistant',
        content: m.content,
        time: m.time || '',
      }))
    } else {
      messages.value = []
    }
    scrollBottom()
  } catch { /* keep default */ }
}

async function persistMessage(role: 'user' | 'assistant', content: string) {
  try { await request.post('/v1/student/chat/message', { role, content, profile_id: activeProfileId.value }) } catch { /* best-effort */ }
}

/* ── WebSocket setup ─────────────────────────── */

function initWebSocket() {
  const token = localStorage.getItem('token')
  if (!token) return

  wsClient = createProfileChatWebSocket(token)

  wsClient.on('message', (data: any) => {
    if (!isMounted) return
    switch (data.type) {
      case 'chunk': {
        if (!currentAssistantMsg) {
          currentAssistantMsg = { role: 'assistant', content: '', time: now(), streaming: true }
          messages.value.push(currentAssistantMsg)
        }
        // 替换整个消息对象，强制 Vue 重渲染
        const idx = messages.value.indexOf(currentAssistantMsg)
        if (idx !== -1) {
          const updated = { ...currentAssistantMsg, content: currentAssistantMsg.content + data.content }
          messages.value[idx] = updated
          currentAssistantMsg = updated
        }
        scrollBottom()
        break
      }

      case 'end':
        if (currentAssistantMsg) {
          const endIdx = messages.value.indexOf(currentAssistantMsg)
          if (endIdx !== -1) {
            messages.value[endIdx] = { ...currentAssistantMsg, streaming: false }
          }
          persistMessage('assistant', currentAssistantMsg.content)
          currentAssistantMsg = null
        }
        sending.value = false
        break

      case 'profile_update':
        fetchProfile()
        break

      case 'check_workflow':
        // 画像已完善，自动启动工作流（不往聊天里塞硬编码消息）
        needsWorkflow.value = true
        startAutoWorkflow()
        break

      case 'error':
        addMsg('assistant', data.message || '生成回答失败，请稍后重试')
        currentAssistantMsg = null
        sending.value = false
        break
    }
  })

  wsClient.connect(token).catch(() => {})
}

/* ── Send message ────────────────────────────── */

async function sendMessage() {
  const text = inputText.value.trim()
  if (!text || sending.value || !wsClient) return

  inputText.value = ''
  addMsg('user', text)
  persistMessage('user', text)

  sending.value = true
  currentAssistantMsg = null

  // 超时保护：30秒后自动恢复输入（防止 WebSocket 断连导致卡死）
  const sendTimeout = setTimeout(() => {
    if (sending.value) {
      sending.value = false
      addMsg('assistant', '响应超时，请重试。')
    }
  }, 30000)

  const chatHistory = messages.value.slice(-10).map(m => ({ role: m.role, content: m.content }))

  wsClient.send({
    type: 'query',
    question: text,
    session_id: `profile_${userStore.user?.id}`,
    chat_history: chatHistory,
    profile: { ...profile },
    profile_id: activeProfileId.value,
  })

  // 收到 end 时清除超时
  const origOnEnd = wsClient.onmessage
  const clearSendTimeout = () => { clearTimeout(sendTimeout) }
  // end 事件已在上面的 switch 中处理，这里用一个简单的方式：
  // 在 sending.value = false 时也清除超时
  const unwatchSending = watch(sending, (val) => {
    if (!val) { clearTimeout(sendTimeout); unwatchSending() }
  })
}

/* ── Workflow ────────────────────────────────── */

const STEP_NAMES: Record<string, string> = {
  build_profile: '画像构建 Agent · 构建学习画像',
  generate_path: '路径规划 Agent · 生成学习路径',
  generate_knowledge_graph: '知识图谱 Agent · 生成全局知识图谱',
  generate_document: '文档生成 Agent · 生成学习文档',
  generate_ppt_video: 'PPT 视频 Agent · 生成教学视频',
  generate_mindmap: '思维导图 Agent · 生成思维导图',
  generate_questions: '题库生成 Agent · 生成练习题目',
  generate_code: '代码实操 Agent · 生成代码示例',
  generate_reading: '拓展阅读 Agent · 生成阅读材料',
  generate_glossary: '术语词汇 Agent · 生成词汇卡片',
  generate_knowledge_link: '知识图谱 Agent · 生成知识点关联图',
  generate_summary: '学习总结 Agent · 生成总结报告',
  quality_evaluate: '质量评估 Agent · 资源质量评估',
}

// 子步骤关键词 → 显示名称映射
const SUB_STEP_NAMES: Record<string, string> = {
  '知识图谱': '知识图谱 Agent · 生成全局知识图谱',
  '思维导图': '思维导图 Agent · 生成思维导图',
  '拓展阅读': '拓展阅读 Agent · 生成阅读材料',
  '术语词汇': '术语词汇 Agent · 生成词汇卡片',
  '知识关联': '知识图谱 Agent · 生成知识点关联图',
  '学习总结': '学习总结 Agent · 生成总结报告',
  '总结报告': '学习总结 Agent · 生成总结报告',
  'PPT': '教学视频 Agent · 生成教学视频',
  'ppt': '教学视频 Agent · 生成教学视频',
  'synthesizing_tts': '教学视频 Agent · 合成语音',
  'tts': '教学视频 Agent · 合成语音',
  'rendering': '教学视频 Agent · 渲染页面',
  'rendering_html': '教学视频 Agent · 渲染页面',
  'uploading': '教学视频 Agent · 上传视频',
  'generating_ppt': '教学视频 Agent · 生成PPT内容',
  'generating_pages': '教学视频 Agent · 生成PPT页面',
  'generating_subtitles': '教学视频 Agent · 生成字幕',
  'composing_video': '教学视频 Agent · 合成视频',
  'combining': '教学视频 Agent · 合成视频',
}

const currentAgentName = computed(() => {
  const step = workflowStep.value || ''
  // 先匹配子步骤关键词
  for (const [keyword, name] of Object.entries(SUB_STEP_NAMES)) {
    if (step.includes(keyword)) return name.split('·')[0].trim()
  }
  const parts = step.split('·')
  return (parts[0] || '准备中').trim()
})

async function checkAndStartWorkflow() {
  try {
    const status: any = await request.get('/v1/student/init-status')
    if (status?.needs_workflow) {
      needsWorkflow.value = true
    }
  } catch { /* ignore */ }
}

async function handleStartWorkflow() {
  appStore.addTask({ id: 'workflow', type: 'workflow', label: '生成学习路径', progress: 0, status: 'running' })
  await startAutoWorkflow()
}

async function startAutoWorkflow() {
  workflowRunning.value = true
  appStore.addTask({ id: 'workflow', type: 'workflow', label: '生成学习路径', progress: 0, status: 'running' })
  try {
    const startRes: any = await request.post('/v1/student/learn/start')
    const sessionId = startRes.session_id
    const token = localStorage.getItem('token') || ''

    const { createWorkflowWebSocket } = await import('@/utils/websocket')
    const ws = createWorkflowWebSocket(token)
    let finished = false

    ws.on('message', (data: any) => {
      switch (data.type) {
        case 'step':
          // sub_step 已包含 Agent 名称（如"思维导图 Agent · 生成思维导图"）
          workflowStep.value = data.data.sub_step || (STEP_NAMES[data.data.current_step] || data.data.current_step)
          workflowProgress.value = Math.round((data.data.progress || 0) * 100)
          appStore.updateTask('workflow', { progress: workflowProgress.value, detail: workflowStep.value })
          break
        case 'complete':
          if (finished) break
          finished = true
          ws.close()
          workflowRunning.value = false
          hasPath.value = true
          appStore.completeTask('workflow')
          addMsg('assistant', '✅ 学习路径和学习资源已准备就绪！\n\n请前往「学习路径」页面查看并开始学习。')
          break
        case 'error':
          if (finished) break
          finished = true
          ws.close()
          workflowRunning.value = false
          appStore.failTask('workflow', data.message)
          addMsg('assistant', '资源生成遇到问题，您可以稍后在「学习路径」页面手动触发生成。')
          break
      }
    })

    ws.on('error', () => {
      if (!finished) {
        finished = true
        workflowRunning.value = false
        addMsg('assistant', '资源生成遇到问题，您可以稍后在「学习路径」页面手动触发生成。')
      }
    })

    await ws.connect(token)
    ws.send({ type: 'start', session_id: sessionId })
  } catch {
    workflowRunning.value = false
    addMsg('assistant', '资源生成遇到问题，您可以稍后在「学习路径」页面手动触发生成。')
  }
}

/* ── Fetch profile ───────────────────────────── */

async function fetchProfile() {
  try {
    const res: any = await studentAPI.getProfile()
    if (res) Object.assign(profile, res)
  } catch { /* ignore */ }
}

/* ── Profile management ─────────────────────── */

const fetchProfiles = async () => {
  try {
    const res: any = await studentAPI.getProfiles()
    profiles.value = res || []
    const active = profiles.value.find((p: any) => p.is_active)
    if (active) activeProfileId.value = active.id
  } catch (e) {
    console.error('获取画像列表失败', e)
  }
}

const handleCreateProfile = async () => {
  if (!newProfileName.value.trim()) return
  try {
    await studentAPI.createProfile({ profile_name: newProfileName.value.trim() })
    newProfileName.value = ''
    showNewProfileDialog.value = false
    await fetchProfiles()
    await fetchProfile()
    await loadHistory() // 加载新画像的欢迎消息
    ElMessage.success('新画像创建成功')
  } catch (e) {
    ElMessage.error('创建失败')
  }
}

const handleActivateProfile = async (id: number) => {
  try {
    await studentAPI.activateProfile(id)
    activeProfileId.value = id
    await fetchProfiles()
    await fetchProfile()
    await loadHistory()
    showProfileList.value = false
    // 刷新学习路径 store，确保切换画像后路径数据同步
    const pathStore = useLearningPathStore()
    await pathStore.fetchPath()
    // 刷新该画像的学习路径状态
    try {
      const res: any = await request.get('/v1/student/init-status')
      hasPath.value = !!res?.has_path
      needsWorkflow.value = false  // 切换画像不自动触发工作流
      workflowRunning.value = false
    } catch { /* ignore */ }
    ElMessage.success('已切换画像')
  } catch (e) {
    ElMessage.error('切换失败')
  }
}

const handleArchiveProfile = async (id: number) => {
  try {
    await ElMessageBox.confirm('确定要归档该画像吗？', '归档确认', { type: 'warning' })
    await studentAPI.archiveProfile(id)
    await fetchProfiles()
    ElMessage.success('已归档')
  } catch (e) {
    if (e !== 'cancel') ElMessage.error('归档失败')
  }
}

const handleRestoreProfile = async (id: number) => {
  try {
    await studentAPI.restoreProfile(id)
    await fetchProfiles()
    ElMessage.success('已恢复')
  } catch (e) {
    ElMessage.error('恢复失败')
  }
}

const startEditProfileName = (profileItem: any) => {
  editingProfileId.value = profileItem.id
  editingProfileName.value = profileItem.profile_name
}

const saveProfileName = async () => {
  if (!editingProfileId.value || !editingProfileName.value.trim()) {
    editingProfileId.value = null
    return
  }
  try {
    await studentAPI.updateProfileName(editingProfileId.value, { profile_name: editingProfileName.value.trim() })
    editingProfileId.value = null
    await fetchProfiles()
    await fetchProfile()
  } catch (e) {
    ElMessage.error('修改失败')
  }
}

const handleProfileCommand = async (command: any) => {
  if (command.action === 'switch') {
    await handleActivateProfile(command.id)
  } else if (command.action === 'new') {
    showNewProfileDialog.value = true
  } else if (command.action === 'manage') {
    showProfileList.value = true
  }
}

const currentProfileName = computed(() => {
  const active = profiles.value.find((p: any) => p.is_active)
  return active?.profile_name || '我的画像'
})

const nonArchivedProfiles = computed(() => {
  return profiles.value.filter((p: any) => !p.is_archived)
})

const profileComplete = computed(() => {
  return profile.major && profile.grade && profile.goal && profile.knowledge_level
    && (profile.interests?.length > 0) && (profile.weakness?.length > 0)
})

/* ── Lifecycle ───────────────────────────────── */

onMounted(async () => {
  isMounted = true
  await fetchProfiles()
  await Promise.all([loadHistory(), fetchProfile()])
  initWebSocket()
  try {
    const res: any = await request.get('/v1/student/init-status')
    if (res?.has_path) {
      hasPath.value = true
      workflowRunning.value = false  // 已有路径，强制重置工作流状态
    } else if (res?.needs_workflow) {
      needsWorkflow.value = true
      startAutoWorkflow()
    }
  } catch { /* ignore */ }
})

onUnmounted(() => {
  isMounted = false
  if (wsClient) { wsClient.close(); wsClient = null }
})
</script>

<style scoped>
.profile-page { max-width: 1400px; }

.page-header { margin-bottom: var(--space-section-gap); }
.page-title { font-size: var(--text-xl); font-weight: 700; color: var(--color-text-primary); }

/* ── Card ──────────────────────────────────── */

.chat-card, .profile-card {
  background: var(--color-bg-card);
  border-radius: var(--radius-lg);
  border: 1px solid var(--color-border-light);
}

.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 10px;
}

.ai-avatar {
  width: 34px;
  height: 34px;
  border-radius: 10px;
  background: linear-gradient(135deg, var(--color-primary), var(--color-primary-light));
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.card-title {
  font-weight: 600;
  font-size: var(--text-base);
  color: var(--color-text-primary);
  display: block;
  line-height: 1.3;
}

.card-subtitle {
  font-size: var(--text-xs);
  color: var(--color-text-muted);
  display: block;
  line-height: 1.3;
}

.status-dot {
  width: 8px; height: 8px; border-radius: 50%;
  background: var(--color-border);
  transition: background var(--transition-fast);
}
.status-dot.active {
  background: #22c55e;
  animation: pulse-dot 1.5s ease infinite;
}
@keyframes pulse-dot {
  0%, 100% { box-shadow: 0 0 0 0 rgba(34,197,94,0.4); }
  50% { box-shadow: 0 0 0 6px rgba(34,197,94,0); }
}

/* ── Chat messages ─────────────────────────── */

.chat-messages {
  height: 480px;
  overflow-y: auto;
  padding: 20px 16px;
  background: var(--color-bg-page);
  border-radius: var(--radius-md);
  margin-bottom: 16px;
}

.chat-message {
  display: flex;
  gap: 10px;
  margin-bottom: 20px;
  align-items: flex-start;
}
.chat-message.user { flex-direction: row-reverse; }

.msg-avatar {
  width: 30px; height: 30px; border-radius: 8px;
  display: flex; align-items: center; justify-content: center;
  flex-shrink: 0; font-size: var(--text-xs); font-weight: 600;
}
.msg-avatar.ai { background: linear-gradient(135deg, var(--color-primary), var(--color-primary-light)); color: #fff; }
.msg-avatar.user { background: var(--color-primary); color: #fff; }

.bubble-wrap {
  max-width: 75%;
  display: flex;
  flex-direction: column;
}

.bubble {
  padding: 11px 15px;
  border-radius: 14px;
  background: var(--color-bg-card);
  box-shadow: var(--shadow-sm);
  color: var(--color-text-primary);
  font-size: 14px;
  line-height: 1.7;
  word-break: break-word;
}
.chat-message.assistant .bubble { border-top-left-radius: 4px; }
.chat-message.user .bubble {
  background: var(--color-primary);
  color: #fff;
  border-top-right-radius: 4px;
}

/* ── Typing indicator ──────────────────────── */

.typing-indicator {
  display: inline-flex;
  gap: 4px;
  padding: 8px 4px 2px;
}
.typing-indicator .dot {
  width: 6px; height: 6px; border-radius: 50%;
  background: var(--color-primary);
  opacity: 0.4;
  animation: typing-bounce 1.2s ease-in-out infinite;
}
.typing-indicator .dot:nth-child(2) { animation-delay: 0.15s; }
.typing-indicator .dot:nth-child(3) { animation-delay: 0.3s; }
@keyframes typing-bounce {
  0%, 60%, 100% { transform: translateY(0); opacity: 0.4; }
  30% { transform: translateY(-4px); opacity: 1; }
}

/* ── Meta ──────────────────────────────────── */

.msg-meta { margin-top: 4px; }
.msg-time { font-size: var(--text-xs); color: var(--color-text-muted); }
.chat-message.user .msg-time { text-align: right; }

/* ── Chat input ────────────────────────────── */

.chat-input-area { padding: 0 4px; }

.input-wrap {
  display: flex;
  align-items: flex-end;
  gap: 8px;
  background: var(--color-bg-page);
  border: 1px solid var(--color-border);
  border-radius: 14px;
  padding: 8px 12px;
  transition: border-color var(--transition-fast);
}
.input-wrap:focus-within { border-color: var(--color-primary); }

.chat-textarea :deep(.el-textarea__inner) {
  background: transparent !important;
  border: none !important;
  box-shadow: none !important;
  padding: 4px 0;
  font-size: 14px;
  line-height: 1.5;
}

.send-btn {
  width: 36px; height: 36px; border-radius: 10px;
  border: none; background: var(--color-border-light); color: var(--color-text-muted);
  display: flex; align-items: center; justify-content: center;
  cursor: not-allowed; transition: all var(--transition-fast); flex-shrink: 0;
}
.send-btn.active {
  background: var(--color-primary); color: #fff; cursor: pointer;
}
.send-btn.active:hover { transform: scale(1.05); }

/* ── Profile fields ────────────────────────── */

.profile-fields {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.field-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 0;
  border-bottom: 1px solid var(--color-border-light);
}
.field-row:last-child { border-bottom: none; }

.field-label {
  font-size: 13px;
  color: var(--color-text-secondary);
  font-weight: 500;
}

.field-value {
  font-size: 13px;
  color: var(--color-text-primary);
}

.profile-section {
  margin-top: 16px;
}

.section-title {
  font-size: 13px;
  font-weight: 600;
  color: var(--color-text-secondary);
  margin-bottom: 8px;
}

.tag-list {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.empty-hint {
  color: var(--color-text-muted);
  font-size: var(--text-xs);
}

.workflow-progress {
  margin-top: 16px;
  padding: 14px;
  background: var(--color-primary-lightest);
  border-radius: var(--radius-md);
  border: 1px solid var(--color-primary-lightest);
}

.workflow-progress-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
}

.workflow-progress-label {
  font-size: 13px;
  font-weight: 600;
  color: var(--color-primary);
  flex: 1;
}

.workflow-progress-pct {
  font-size: var(--text-xs);
  color: var(--color-primary-light);
  font-weight: 500;
}

.workflow-btn {
  width: 100%;
  margin-top: 16px;
}

.profile-header-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;
  padding-bottom: 12px;
  border-bottom: 1px solid var(--color-border-light);
}

.profile-name-text {
  font-size: var(--text-lg);
  font-weight: 600;
  color: var(--color-text-primary);
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 4px;
}

.profile-name-text:hover {
  color: var(--color-primary);
}

.profile-complete-tip {
  background: #f0fdf4;
  color: var(--color-success);
  padding: 10px 14px;
  border-radius: var(--radius-md);
  font-size: 13px;
  margin-bottom: 12px;
  border: 1px solid #bbf7d0;
}

.link-text {
  color: var(--color-primary);
  cursor: pointer;
  font-weight: 500;
}

.link-text:hover {
  text-decoration: underline;
}
</style>
