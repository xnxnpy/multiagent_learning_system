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
            <div class="bubble markdown-body" v-html="msg.renderedContent || renderMarkdown(msg.content)"></div>
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
        <div class="input-wrap">
          <el-input
            v-model="store.inputText"
            type="textarea"
            :rows="2"
            :autosize="{ minRows: 1, maxRows: 4 }"
            placeholder="输入你的问题... (Enter 发送, Shift+Enter 换行)"
            resize="none"
            class="chat-textarea"
            @keydown="handleKeydown"
          />
          <VoiceInputButton @result="(t) => store.inputText = t" />
          <button
            class="send-btn"
            :class="{ active: store.inputText.trim() && !store.loading }"
            :disabled="!store.inputText.trim() || store.loading"
            @click="sendAndTrack()"
          >
            <el-icon :size="18"><Promotion /></el-icon>
          </button>
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
            <div class="bubble markdown-body" v-html="msg.renderedContent || renderMarkdown(msg.content)"></div>
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
        <div class="input-wrap">
          <el-input
            v-model="store.inputText"
            type="textarea"
            :rows="1"
            :autosize="{ minRows: 1, maxRows: 3 }"
            placeholder="输入问题..."
            resize="none"
            class="chat-textarea"
            @keydown="handleKeydown"
          />
          <VoiceInputButton :size="16" @result="(t) => store.inputText = t" />
          <button
            class="send-btn"
            :class="{ active: store.inputText.trim() && !store.loading }"
            :disabled="!store.inputText.trim() || store.loading"
            @click="sendAndTrack()"
          >
            <el-icon :size="16"><Promotion /></el-icon>
          </button>
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
  </div>
</template>

<script setup lang="ts">
import { ref, watch, nextTick, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Service, Promotion, MagicStick } from '@element-plus/icons-vue'
import { useTutorStore } from '@/stores/tutorStore'
import { useMarkdown } from '@/composables/useMarkdown'
import { studentAPI } from '@/api'
import VoiceInputButton from '@/components/VoiceInputButton.vue'

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
.msg-avatar.ai { background: linear-gradient(135deg, var(--color-primary), var(--color-primary-light)); color: #fff; }
.msg-avatar.user { background: var(--color-primary); color: #fff; }
.bubble-wrap { max-width: 75%; display: flex; flex-direction: column; }
.bubble { padding: 12px 16px; border-radius: 14px; background: var(--color-bg-card); box-shadow: var(--shadow-sm); color: var(--color-text-primary); font-size: var(--text-sm); line-height: 1.7; word-break: break-word; }
.compact .bubble { padding: 8px 12px; font-size: 13px; line-height: 1.6; }
.chat-message.assistant .bubble { border-top-left-radius: 4px; }
.chat-message.user .bubble { background: var(--color-primary); color: var(--color-text-inverse); border-top-right-radius: 4px; }
.bubble :deep(p) { margin: 0 0 8px; }
.bubble :deep(p:last-child) { margin-bottom: 0; }
.bubble :deep(ul), .bubble :deep(ol) { padding-left: 20px; margin: 8px 0; }
.bubble :deep(h1), .bubble :deep(h2), .bubble :deep(h3) { margin: 12px 0 6px; font-weight: 700; }
.bubble :deep(h1) { font-size: 18px; }
.bubble :deep(h2) { font-size: 16px; }
.bubble :deep(h3) { font-size: var(--text-sm); }
.bubble :deep(p > code) { background: rgba(37,99,235,0.06); padding: 2px 6px; border-radius: 4px; font-size: 13px; color: var(--color-primary); }
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
.typing-indicator .dot { width: 6px; height: 6px; border-radius: 50%; background: var(--color-primary); opacity: 0.4; animation: typing-bounce 1.2s ease-in-out infinite; }
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
.copy-msg-btn:hover { color: var(--color-primary); border-color: var(--color-primary); background: rgba(37,99,235,0.04); }

/* ── Chat input ────────────────────────────── */
.chat-input-area { padding: 0 4px; }
.input-wrap { display: flex; align-items: flex-end; gap: 8px; background: var(--color-bg-page); border: 1px solid var(--color-border-light); border-radius: 14px; padding: 8px 12px; transition: border-color var(--transition-fast); }
.input-wrap:focus-within { border-color: var(--color-primary); box-shadow: 0 0 0 2px rgba(37,99,235,0.08); }
.chat-textarea :deep(.el-textarea__inner) { background: transparent !important; border: none !important; box-shadow: none !important; padding: 4px 0; font-size: var(--text-sm); line-height: 1.5; }
.compact .chat-textarea :deep(.el-textarea__inner) { font-size: 13px; }
.send-btn { width: 36px; height: 36px; border-radius: var(--radius-md); border: none; background: var(--color-border-light); color: var(--color-text-muted); display: flex; align-items: center; justify-content: center; cursor: not-allowed; transition: all var(--transition-fast); flex-shrink: 0; }
.compact .send-btn { width: 32px; height: 32px; border-radius: 8px; }
.send-btn.active { background: var(--color-primary); color: #fff; cursor: pointer; }
.send-btn.active:hover { transform: scale(1.05); }

/* ── Quick questions ───────────────────────── */
.quick-tags { display: flex; flex-wrap: wrap; gap: 8px; }
.quick-tag { background: var(--color-bg-page); border: 1px solid var(--color-border-light); color: var(--color-text-secondary); padding: 7px 16px; border-radius: 20px; font-size: 13px; cursor: pointer; transition: all var(--transition-fast); font-family: inherit; }
.quick-tag:hover { border-color: var(--color-primary); color: var(--color-primary); background: rgba(37,99,235,0.04); }
</style>
