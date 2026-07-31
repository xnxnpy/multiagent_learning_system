<template>
  <div class="chat-container" :class="{ compact }">
    <!-- Header (full mode only) -->
    <el-card v-if="showHeader" class="chat-card" shadow="never">
      <template #header>
        <div class="card-header">
          <div class="header-left">
            <div class="ai-avatar">
              <el-icon :size="20" color="#fff"><Service /></el-icon>
            </div>
            <div>
              <span class="card-title">AI 辅导助手</span>
              <span class="card-subtitle">{{ store.streaming ? '正在思考...' : '在线' }}</span>
            </div>
          </div>
          <div class="status-dot" :class="{ active: store.streaming }"></div>
        </div>
      </template>

      <!-- Messages -->
      <div class="chat-messages" ref="messagesRef">
        <div
          v-for="(msg, idx) in store.messages"
          :key="idx"
          class="chat-message"
          :class="msg.role"
        >
          <div v-if="msg.role === 'assistant'" class="msg-avatar ai">
            <el-icon :size="16" color="#fff"><Service /></el-icon>
          </div>
          <div class="bubble-wrap">
            <img
              v-if="msg.image_base64"
              class="msg-thumb"
              :src="`data:image/jpeg;base64,${msg.image_base64}`"
              @click="previewImage(msg.image_base64)"
            />
            <div
              v-if="msg.content && msg.content !== '[图片]'"
              class="bubble markdown-body"
              v-html="msg.renderedContent || renderMarkdown(msg.content)"
            ></div>
            <div v-if="msg.streaming" class="typing-indicator">
              <span class="dot"></span>
              <span class="dot"></span>
              <span class="dot"></span>
            </div>
            <div class="msg-meta">
              <span class="msg-time">{{ msg.time }}</span>
              <button v-if="msg.role === 'assistant' && !msg.streaming" class="copy-msg-btn" @click="copyMessage(msg.content, $event)">
                <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg>
                <span>复制</span>
              </button>
            </div>
          </div>
          <div v-if="msg.role === 'user'" class="msg-avatar user">
            <span>我</span>
          </div>
        </div>
      </div>

      <!-- Input area -->
      <div class="chat-input-area">
        <div
          class="input-wrap"
          :class="{ 'drag-over': isDragOver }"
          @dragover.prevent="isDragOver = true"
          @dragleave="isDragOver = false"
          @drop.prevent="handleDrop"
        >
          <!-- 待发送图片附件卡片 -->
          <div v-if="store.pendingImage" class="pending-chip" @click="previewPending">
            <img class="pending-thumb" :src="`data:image/jpeg;base64,${store.pendingImage}`" />
            <div class="pending-info">
              <span class="pending-name">{{ store.pendingImageName || '粘贴图片.png' }}</span>
              <span class="pending-size">{{ formatSize(store.pendingImageSize) }}</span>
            </div>
            <button class="pending-remove" @click.stop="clearPending">×</button>
          </div>
          <el-input
            v-model="store.inputText"
            type="textarea"
            :rows="2"
            :autosize="{ minRows: 1, maxRows: 4 }"
            placeholder="输入你的问题... (Enter 发送, Shift+Enter 换行, Ctrl+V 粘贴图片)"
            resize="none"
            class="chat-textarea"
            @keydown="handleKeydown"
            @paste="handlePaste"
          />
          <div class="input-toolbar">
            <div class="toolbar-left">
              <VoiceInputButton @result="(t) => store.inputText = t" />
              <ImageUploadButton @result="(t, img, name, size) => { store.pendingOcrText = t; store.pendingImage = img; store.pendingImageName = name; store.pendingImageSize = size }" />
            </div>
            <button
              class="send-btn"
              :class="{ active: (store.inputText.trim() || store.pendingImage) && !store.loading }"
              :disabled="(!store.inputText.trim() && !store.pendingImage) || store.loading"
              @click="sendAndTrack()"
            >
              <el-icon :size="18"><Promotion /></el-icon>
            </button>
          </div>
        </div>
      </div>
    </el-card>

    <!-- Compact mode: no card wrapper -->
    <template v-else>
      <div class="chat-messages" ref="messagesRef">
        <div
          v-for="(msg, idx) in store.messages"
          :key="idx"
          class="chat-message"
          :class="msg.role"
        >
          <div v-if="msg.role === 'assistant'" class="msg-avatar ai">
            <el-icon :size="14" color="#fff"><Service /></el-icon>
          </div>
          <div class="bubble-wrap">
            <img
              v-if="msg.image_base64"
              class="msg-thumb"
              :src="`data:image/jpeg;base64,${msg.image_base64}`"
              @click="previewImage(msg.image_base64)"
            />
            <div
              v-if="msg.content && msg.content !== '[图片]'"
              class="bubble markdown-body"
              v-html="msg.renderedContent || renderMarkdown(msg.content)"
            ></div>
            <div v-if="msg.streaming" class="typing-indicator">
              <span class="dot"></span>
              <span class="dot"></span>
              <span class="dot"></span>
            </div>
          </div>
          <div v-if="msg.role === 'user'" class="msg-avatar user">
            <span>我</span>
          </div>
        </div>
      </div>

      <div class="chat-input-area">
        <div
          class="input-wrap"
          :class="{ 'drag-over': isDragOver }"
          @dragover.prevent="isDragOver = true"
          @dragleave="isDragOver = false"
          @drop.prevent="handleDrop"
        >
          <div v-if="store.pendingImage" class="pending-chip compact" @click="previewPending">
            <el-icon class="pending-icon"><Picture /></el-icon>
            <div class="pending-info">
              <span class="pending-name">{{ store.pendingImageName || '粘贴图片.png' }}</span>
              <span class="pending-size">{{ formatSize(store.pendingImageSize) }}</span>
            </div>
            <button class="pending-remove" @click.stop="clearPending">×</button>
          </div>
          <el-input
            v-model="store.inputText"
            type="textarea"
            :rows="1"
            :autosize="{ minRows: 1, maxRows: 3 }"
            placeholder="输入问题... (Ctrl+V 粘贴图片)"
            resize="none"
            class="chat-textarea"
            @keydown="handleKeydown"
            @paste="handlePaste"
          />
          <div class="input-toolbar">
            <div class="toolbar-left">
              <VoiceInputButton :size="16" @result="(t) => store.inputText = t" />
              <ImageUploadButton :size="16" @result="(t, img, name, size) => { store.pendingOcrText = t; store.pendingImage = img; store.pendingImageName = name; store.pendingImageSize = size }" />
            </div>
            <button
              class="send-btn"
              :class="{ active: (store.inputText.trim() || store.pendingImage) && !store.loading }"
              :disabled="(!store.inputText.trim() && !store.pendingImage) || store.loading"
              @click="sendAndTrack()"
            >
              <el-icon :size="16"><Promotion /></el-icon>
            </button>
          </div>
        </div>
      </div>
    </template>

    <!-- Quick questions (full mode only) -->
    <el-card v-if="showQuickQuestions" class="quick-card" shadow="never">
      <template #header>
        <div class="card-header">
          <div class="header-left">
            <el-icon :size="16" color="var(--color-warning)"><MagicStick /></el-icon>
            <span class="card-title">快捷问题</span>
          </div>
        </div>
      </template>
      <div class="quick-tags">
        <button v-for="q in quickQuestions" :key="q" class="quick-tag" @click="sendAndTrack(q)">{{ q }}</button>
      </div>
    </el-card>

    <!-- 图片预览 -->
    <el-image-viewer
      v-if="previewVisible"
      :url-list="previewUrlList"
      @close="previewVisible = false"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, watch, nextTick, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { ElImageViewer } from 'element-plus'
import { Service, Promotion, MagicStick, Picture } from '@element-plus/icons-vue'
import { useTutorStore } from '@/stores/tutorStore'
import { useMarkdown } from '@/composables/useMarkdown'
import { studentAPI } from '@/api'
import VoiceInputButton from '@/components/VoiceInputButton.vue'
import ImageUploadButton from '@/components/ImageUploadButton.vue'

const props = withDefaults(defineProps<{
  compact?: boolean
  showHeader?: boolean
  showQuickQuestions?: boolean
}>(), {
  compact: false,
  showHeader: true,
  showQuickQuestions: false,
})

const store = useTutorStore()
const { renderMarkdown, scheduleRender, throttledScroll } = useMarkdown()

// 图片预览
const previewVisible = ref(false)
const previewUrlList = ref<string[]>([])

// 拖拽状态
const isDragOver = ref(false)

// ── 工具函数 ──────────────────────────────────
function formatSize(bytes?: number): string {
  if (!bytes) return '0 B'
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`
}

function getExt(name?: string): string {
  if (!name) return 'PNG'
  const parts = name.split('.')
  return parts.length > 1 ? parts[parts.length - 1].toUpperCase() : 'PNG'
}

function previewPending() {
  if (!store.pendingImage) return
  previewUrlList.value = [`data:image/jpeg;base64,${store.pendingImage}`]
  previewVisible.value = true
}

function clearPending() {
  store.pendingImage = null
  store.pendingImageName = ''
  store.pendingImageSize = 0
  store.pendingOcrText = ''
}

function previewImage(base64: string) {
  previewUrlList.value = [`data:image/jpeg;base64,${base64}`]
  previewVisible.value = true
}

/** File → base64（不含 data:image/xxx;base64, 前缀） */
function fileToBase64(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader()
    reader.onload = () => {
      const result = reader.result as string
      resolve(result.includes(',') ? result.split(',')[1] : result)
    }
    reader.onerror = reject
    reader.readAsDataURL(file)
  })
}

/** 调用 OCR 接口识别图片，返回识别文本（失败返回空字符串） */
async function recognizeImage(file: File): Promise<string> {
  try {
    const formData = new FormData()
    formData.append('file', file)
    const res: any = await studentAPI.recognizeImage(formData)
    if (res?.text) return res.text
    return ''
  } catch {
    return ''
  }
}

/** 粘贴图片处理：添加图片 + OCR 识别 + 拼接文本 */
async function handlePaste(e: ClipboardEvent) {
  const items = e.clipboardData?.items
  if (!items) return
  for (const item of items) {
    if (item.type.startsWith('image/')) {
      const file = item.getAsFile()
      if (file) {
        e.preventDefault()
        const b64 = await fileToBase64(file)
        store.pendingImage = b64
        store.pendingImageName = file.name || '粘贴图片.png'
        store.pendingImageSize = file.size

        const ocrText = await recognizeImage(file)
        if (ocrText) {
          store.pendingOcrText = ocrText
          ElMessage.success('图片添加成功')
        } else {
          ElMessage.success('图片添加成功')
        }
      }
      break
    }
  }
}

/** 拖拽图片处理：添加图片 + OCR 识别 + 拼接文本 */
async function handleDrop(e: DragEvent) {
  isDragOver.value = false
  const files = e.dataTransfer?.files
  if (!files || files.length === 0) return
  for (const file of files) {
    if (file.type.startsWith('image/')) {
      const b64 = await fileToBase64(file)
      store.pendingImage = b64
      store.pendingImageName = file.name
      store.pendingImageSize = file.size

      const ocrText = await recognizeImage(file)
      if (ocrText) {
        store.pendingOcrText = ocrText
        ElMessage.success('图片添加成功')
      } else {
        ElMessage.success('图片添加成功')
      }
      break
    }
  }
}

// 挂载时恢复最近的对话
onMounted(() => { store.resumeLastSession() })

const messagesRef = ref<HTMLElement | null>(null)

const quickQuestions = [
  '请解释这个概念', '给我一个代码示例', '这个知识点有什么难点？',
  '如何更好地掌握这部分内容？', '推荐一些练习题',
]

function sendAndTrack(text?: string) {
  store.sendMessage(text)
  studentAPI.trackEvent({ event_type: 'chat_message' }).catch(() => {})
}

function copyMessage(content: string, event: MouseEvent) {
  const btn = (event.currentTarget as HTMLElement)
  navigator.clipboard.writeText(content).then(() => {
    btn.innerHTML = `<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"/></svg><span>已复制</span>`
    btn.style.color = '#22c55e'
    setTimeout(() => {
      btn.innerHTML = `<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg><span>复制</span>`
      btn.style.color = ''
    }, 2000)
  }).catch(() => {
    ElMessage.error('复制失败')
  })
}

function handleKeydown(e: KeyboardEvent) {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault()
    sendAndTrack()
  }
}

function scrollBottom() {
  nextTick(() => {
    if (messagesRef.value) messagesRef.value.scrollTop = messagesRef.value.scrollHeight
  })
}

// Watch for streaming chunks → scheduleRender + throttledScroll
watch(
  () => store.messages[store.messages.length - 1]?.content,
  () => {
    scheduleRender(store.messages)
    throttledScroll(messagesRef.value)
  },
)

// Watch for new messages → scroll to bottom
watch(
  () => store.messages.length,
  () => scrollBottom(),
)
</script>

<style scoped>
.chat-container { display: flex; flex-direction: column; gap: 12px; }
.chat-container.compact { gap: 0; flex: 1; height: 100%; min-height: 0; }

/* ── Card ──────────────────────────────────── */
.chat-card, .quick-card {
  background: var(--color-bg-card); border-radius: var(--radius-lg);
  border: 1px solid var(--color-border-light);
  box-shadow: var(--shadow-card);
}
.card-header { display: flex; align-items: center; justify-content: space-between; }
.header-left { display: flex; align-items: center; gap: 10px; }
.ai-avatar {
  width: 36px; height: 36px; border-radius: var(--radius-md);
  background: linear-gradient(135deg, var(--color-primary), var(--color-primary-light));
  display: flex; align-items: center; justify-content: center; flex-shrink: 0;
}
.card-title { font-weight: 600; font-size: var(--text-base); color: var(--color-text-primary); display: block; line-height: 1.3; }
.card-subtitle { font-size: 12px; color: var(--color-text-muted); display: block; line-height: 1.3; }
.status-dot { width: 8px; height: 8px; border-radius: 50%; background: var(--color-border); transition: background 0.3s; }
.status-dot.active { background: var(--color-success); animation: pulse-dot 1.5s ease infinite; }
@keyframes pulse-dot { 0%, 100% { box-shadow: 0 0 0 0 rgba(5,150,105,0.4); } 50% { box-shadow: 0 0 0 6px rgba(5,150,105,0); } }

/* ── Chat messages ─────────────────────────── */
.chat-messages { height: 480px; overflow-y: auto; padding: 20px 16px; background: var(--color-bg-page); border-radius: var(--radius-md); }
.compact .chat-messages { height: 100%; padding: 12px 8px; min-height: 300px; flex: 1; }
.chat-message { display: flex; gap: 10px; margin-bottom: 20px; align-items: flex-start; }
.chat-message.user { flex-direction: row-reverse; }
.msg-avatar { width: 32px; height: 32px; border-radius: 8px; display: flex; align-items: center; justify-content: center; flex-shrink: 0; font-size: 12px; font-weight: 600; }
.compact .msg-avatar { width: 24px; height: 24px; border-radius: 6px; }
.msg-avatar.ai { background: linear-gradient(135deg, var(--color-student), var(--color-student-soft)); color: #fff; }
.msg-avatar.user { background: var(--color-student); color: #fff; }
.bubble-wrap { max-width: 75%; display: flex; flex-direction: column; }
.bubble { padding: 12px 16px; border-radius: 14px; background: var(--color-bg-card); box-shadow: var(--shadow-sm); color: var(--color-text-primary); font-size: var(--text-sm); line-height: 1.7; word-break: break-word; }
.compact .bubble { padding: 8px 12px; font-size: 13px; line-height: 1.6; }
.chat-message.assistant .bubble { border-top-left-radius: 4px; }
.chat-message.user .bubble { background: var(--color-student); color: var(--color-text-inverse); border-top-right-radius: 4px; box-shadow: 0 2px 8px rgba(176, 81, 44, 0.18); }
.bubble :deep(p) { margin: 0 0 8px; }
.bubble :deep(p:last-child) { margin-bottom: 0; }
.bubble :deep(ul), .bubble :deep(ol) { padding-left: 20px; margin: 8px 0; }
.bubble :deep(h1), .bubble :deep(h2), .bubble :deep(h3) { margin: 12px 0 6px; font-weight: 700; }
.bubble :deep(h1) { font-size: 18px; }
.bubble :deep(h2) { font-size: 16px; }
.bubble :deep(h3) { font-size: var(--text-sm); }
.bubble :deep(p > code) { background: var(--color-primary-pale); padding: 2px 6px; border-radius: 4px; font-size: 13px; color: var(--color-primary); }
.bubble :deep(.code-block-wrap) { margin: 12px 0; border-radius: 8px; overflow: hidden; border: 1px solid var(--color-border); background: var(--color-bg-card); }
.bubble :deep(.code-header) { display: flex; align-items: center; justify-content: space-between; padding: 6px 14px; background: var(--color-border-light); border-bottom: 1px solid var(--color-border); }
.bubble :deep(.code-lang) { color: var(--color-text-muted); font-family: var(--font-mono); font-size: 11px; text-transform: uppercase; letter-spacing: 0.5px; }
.bubble :deep(.copy-btn) { background: transparent; border: 1px solid var(--color-border); color: var(--color-text-muted); padding: 2px 10px; border-radius: var(--radius-sm); font-size: 11px; cursor: pointer; transition: all var(--transition-fast); font-family: inherit; }
.bubble :deep(.copy-btn:hover) { background: var(--color-border-light); color: var(--color-text-secondary); border-color: var(--color-text-muted); }
.bubble :deep(pre) { margin: 0; padding: 16px; background: var(--color-bg-card) !important; overflow-x: auto; font-size: 13px; line-height: 1.6; }
.bubble :deep(pre code) { font-family: var(--font-mono); font-size: 13px; background: transparent !important; padding: 0; color: var(--color-text-primary); }
.bubble :deep(.diagram-block) { border-color: var(--color-border); background: var(--color-bg-page); }
.bubble :deep(.diagram-pre) { background: var(--color-bg-page) !important; color: var(--color-text-secondary); white-space: pre-wrap; word-break: break-word; }
.bubble :deep(table) { border-collapse: collapse; margin: 8px 0; width: 100%; font-size: 13px; }
.bubble :deep(th), .bubble :deep(td) { border: 1px solid var(--color-border); padding: 6px 10px; text-align: left; }
.bubble :deep(th) { background: var(--color-border-light); font-weight: 600; }

/* ── Typing indicator ────────────────────── */
.typing-indicator { display: inline-flex; gap: 4px; padding: 8px 4px 2px; }
.typing-indicator .dot { width: 6px; height: 6px; border-radius: 50%; background: var(--color-student); opacity: 0.4; animation: typing-bounce 1.2s ease-in-out infinite; }
.typing-indicator .dot:nth-child(2) { animation-delay: 0.15s; }
.typing-indicator .dot:nth-child(3) { animation-delay: 0.3s; }
@keyframes typing-bounce { 0%, 60%, 100% { transform: translateY(0); opacity: 0.4; } 30% { transform: translateY(-4px); opacity: 1; } }

.msg-meta { margin-top: 4px; display: flex; align-items: center; gap: 8px; }
.msg-time { font-size: 11px; color: var(--color-text-muted); }
.chat-message.user .msg-time { text-align: right; }
.copy-msg-btn {
  font-size: 11px; color: var(--color-text-muted); background: transparent;
  border: 1px solid var(--color-border); border-radius: var(--radius-sm); padding: 3px 8px;
  cursor: pointer; transition: all var(--transition-fast); line-height: 1; display: inline-flex; align-items: center; gap: 4px;
}
.copy-msg-btn:hover { color: var(--color-student); border-color: var(--color-student); background: var(--color-student-pale); }

/* ── Chat input ────────────────────────────── */
.chat-input-area { padding: 0 4px; }
.input-wrap { display: flex; flex-direction: column; gap: 8px; background: var(--color-bg-page); border: 1px solid var(--color-border-light); border-radius: 12px; padding: 8px 10px; transition: border-color var(--transition-fast); }
.input-wrap:focus-within { border-color: var(--color-student); box-shadow: 0 0 0 2px rgba(176, 81, 44, 0.12); }
.input-wrap.drag-over { border-color: var(--color-student); background: var(--color-student-pale); box-shadow: 0 0 0 2px rgba(176, 81, 44, 0.18); }

/* 待发送图片附件卡片 — 紧凑 */
.pending-chip {
  display: inline-flex; align-items: center; gap: 6px;
  background: var(--color-bg-card); border: 1px solid var(--color-border);
  border-radius: 8px; padding: 4px 8px; margin-right: 4px;
  font-size: 12px; color: var(--color-text-secondary);
  cursor: pointer; transition: all var(--transition-fast);
  align-self: flex-start; width: fit-content; max-width: 320px;
}
.pending-chip:hover { border-color: var(--color-student); }
.pending-chip.compact { padding: 3px 6px; }
.pending-icon { color: var(--color-student); flex-shrink: 0; font-size: 14px; }
.pending-thumb {
  width: 32px; height: 32px; border-radius: 6px;
  object-fit: cover; flex-shrink: 0;
  background: var(--color-bg-page);
}
.pending-info { display: flex; flex-direction: column; gap: 0; min-width: 0; }
.pending-name { font-weight: 500; color: var(--color-text-primary); font-size: 12px; max-width: 140px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.pending-size { font-size: 10px; color: var(--color-text-muted); }
.pending-remove {
  width: 16px; height: 16px; border-radius: 50%; border: none;
  background: var(--color-border); color: var(--color-text-secondary);
  cursor: pointer; display: flex; align-items: center; justify-content: center;
  font-size: 10px; line-height: 1; transition: all var(--transition-fast); flex-shrink: 0;
}
.pending-remove:hover { background: #ef4444; color: #fff; }

/* 聊天消息中的图片缩略图 */
.msg-thumb {
  width: 100%;
  max-width: 160px;
  border-radius: 10px;
  object-fit: cover;
  cursor: zoom-in;
  box-shadow: var(--shadow-sm);
  margin-bottom: 6px;
  border: 1px solid var(--color-border-light);
  transition: all var(--transition-fast);
}
.msg-thumb:hover {
  border-color: var(--color-student);
  transform: scale(1.02);
}
.file-attach-info { display: flex; flex-direction: column; gap: 1px; min-width: 0; }
.file-attach-name { font-weight: 500; color: var(--color-text-primary); font-size: 12px; max-width: 160px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.file-attach-meta { font-size: 10px; color: var(--color-text-muted); }
.chat-message.user .file-attach { background: rgba(255,255,255,0.15); border-color: rgba(255,255,255,0.2); }
.chat-textarea :deep(.el-textarea__inner) { background: transparent !important; border: none !important; box-shadow: none !important; padding: 2px 0; font-size: var(--text-sm); line-height: 1.5; }
.compact .chat-textarea :deep(.el-textarea__inner) { font-size: 13px; }

/* 输入区工具栏 */
.input-toolbar { display: flex; align-items: center; justify-content: space-between; width: 100%; }
.toolbar-left { display: flex; align-items: center; gap: 4px; }
.input-wrap .el-input { width: 100%; }
.input-wrap .image-upload-wrap, .input-wrap .voice-input-wrap { flex-shrink: 0; }
.input-wrap .upload-btn, .input-wrap .voice-btn { width: 30px; height: 30px; border-radius: 8px; }
.send-btn { width: 32px; height: 32px; border-radius: 8px; border: none; background: var(--color-border-light); color: var(--color-text-muted); display: flex; align-items: center; justify-content: center; cursor: not-allowed; transition: all var(--transition-fast); flex-shrink: 0; }
.compact .send-btn { width: 28px; height: 28px; }
.send-btn.active { background: var(--color-student); color: #fff; cursor: pointer; box-shadow: 0 2px 8px rgba(176, 81, 44, 0.22); }
.send-btn.active:hover { transform: scale(1.05); }

/* ── Quick questions ───────────────────────── */
.quick-tags { display: flex; flex-wrap: wrap; gap: 8px; }
.quick-tag { background: var(--color-bg-page); border: 1px solid var(--color-border-light); color: var(--color-text-secondary); padding: 7px 16px; border-radius: 20px; font-size: 13px; cursor: pointer; transition: all var(--transition-fast); font-family: inherit; }
.quick-tag:hover { border-color: var(--color-student); color: var(--color-student); background: var(--color-student-pale); }
</style>
