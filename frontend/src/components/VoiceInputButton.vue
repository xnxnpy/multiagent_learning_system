<template>
  <div class="voice-wrap">
    <!-- 空闲状态：麦克风按钮 -->
    <button
      v-if="!isRecording && !isLoading"
      class="voice-btn"
      @click="startRecording"
      title="点击开始语音输入"
    >
      <el-icon :size="size"><Microphone /></el-icon>
    </button>

    <!-- 录音中：停止 + 取消 -->
    <template v-else-if="isRecording">
      <button class="voice-btn recording" @click="stopAndSend" title="停止并识别">
        <el-icon :size="size"><Microphone /></el-icon>
        <span class="recording-time">{{ recordingTime }}s</span>
      </button>
      <button class="voice-btn cancel" @click="cancelRecording" title="取消录音">
        <el-icon :size="size"><Close /></el-icon>
      </button>
    </template>

    <!-- 识别中 -->
    <button v-else class="voice-btn loading" disabled>
      <el-icon :size="size" class="spin"><Loading /></el-icon>
    </button>
  </div>
</template>

<script setup lang="ts">
import { ref, onUnmounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Microphone, Loading, Close } from '@element-plus/icons-vue'

const props = withDefaults(defineProps<{
  size?: number
  maxDuration?: number
}>(), {
  size: 18,
  maxDuration: 60,
})

const emit = defineEmits<{
  (e: 'result', text: string): void
  (e: 'error', msg: string): void
}>()

const isRecording = ref(false)
const isLoading = ref(false)
const recordingTime = ref(0)

let mediaRecorder: MediaRecorder | null = null
let audioChunks: Blob[] = []
let timer: ReturnType<typeof setInterval> | null = null

async function startRecording() {
  if (isLoading.value) return
  try {
    const stream = await navigator.mediaDevices.getUserMedia({
      audio: { sampleRate: 16000, channelCount: 1, echoCancellation: true, noiseSuppression: true }
    })

    audioChunks = []
    recordingTime.value = 0

    const mimeType = MediaRecorder.isTypeSupported('audio/webm;codecs=opus')
      ? 'audio/webm;codecs=opus'
      : MediaRecorder.isTypeSupported('audio/webm') ? 'audio/webm' : ''

    mediaRecorder = new MediaRecorder(stream, mimeType ? { mimeType } : undefined)
    mediaRecorder.ondataavailable = (e) => { if (e.data.size > 0) audioChunks.push(e.data) }
    mediaRecorder.onstop = () => {
      stream.getTracks().forEach(t => t.stop())
      if (timer) { clearInterval(timer); timer = null }
    }
    mediaRecorder.start(200)
    isRecording.value = true

    timer = setInterval(() => {
      recordingTime.value++
      if (recordingTime.value >= props.maxDuration) stopAndSend()
    }, 1000)
  } catch (err: any) {
    const msg = err.name === 'NotAllowedError' ? '请允许麦克风权限'
      : err.name === 'NotFoundError' ? '未检测到麦克风设备'
      : '录音启动失败: ' + err.message
    emit('error', msg)
    ElMessage.error(msg)
  }
}

function stopAndSend() {
  if (mediaRecorder && mediaRecorder.state === 'recording') {
    mediaRecorder.stop()
  }
  isRecording.value = false
  if (audioChunks.length > 0) processAudio()
}

function cancelRecording() {
  if (mediaRecorder && mediaRecorder.state === 'recording') {
    mediaRecorder.stop()
  }
  audioChunks = []
  isRecording.value = false
  if (timer) { clearInterval(timer); timer = null }
  ElMessage.info('已取消录音')
}

async function processAudio() {
  isLoading.value = true
  try {
    const audioBlob = new Blob(audioChunks, { type: audioChunks[0]?.type || 'audio/webm' })
    const pcmData = await convertToPCM16k(audioBlob)
    const { studentAPI } = await import('@/api')
    const formData = new FormData()
    formData.append('file', new Blob([pcmData], { type: 'audio/wav' }), 'audio.wav')
    const res: any = await studentAPI.recognizeSpeech(formData)
    if (res.text) emit('result', res.text)
    else ElMessage.warning('未识别出文字')
  } catch (err: any) {
    const msg = err?.response?.data?.detail || '语音识别失败'
    emit('error', msg)
    ElMessage.error(msg)
  } finally {
    isLoading.value = false
  }
}

async function convertToPCM16k(blob: Blob): Promise<ArrayBuffer> {
  try {
    const audioCtx = new (window.AudioContext || (window as any).webkitAudioContext)()
    const arrayBuffer = await blob.arrayBuffer()
    const audioBuffer = await audioCtx.decodeAudioData(arrayBuffer)
    const targetRate = 16000
    const offlineCtx = new OfflineAudioContext(1, Math.ceil(audioBuffer.duration * targetRate), targetRate)
    const source = offlineCtx.createBufferSource()
    source.buffer = audioBuffer
    source.connect(offlineCtx.destination)
    source.start(0)
    const rendered = await offlineCtx.startRendering()
    const float32 = rendered.getChannelData(0)
    const int16 = new Int16Array(float32.length)
    for (let i = 0; i < float32.length; i++) {
      const s = Math.max(-1, Math.min(1, float32[i]))
      int16[i] = s < 0 ? s * 0x8000 : s * 0x7FFF
    }
    const wavBuffer = new ArrayBuffer(44 + int16.byteLength)
    const view = new DataView(wavBuffer)
    writeWavHeader(view, int16.length, targetRate)
    new Int16Array(wavBuffer, 44).set(int16)
    audioCtx.close()
    return wavBuffer
  } catch {
    return blob.arrayBuffer()
  }
}

function writeWavHeader(view: DataView, dataLength: number, sampleRate: number) {
  const writeStr = (offset: number, str: string) => {
    for (let i = 0; i < str.length; i++) view.setUint8(offset + i, str.charCodeAt(i))
  }
  writeStr(0, 'RIFF')
  view.setUint32(4, 36 + dataLength * 2, true)
  writeStr(8, 'WAVE')
  writeStr(12, 'fmt ')
  view.setUint32(16, 16, true)
  view.setUint16(20, 1, true)
  view.setUint16(22, 1, true)
  view.setUint32(24, sampleRate, true)
  view.setUint32(28, sampleRate * 2, true)
  view.setUint16(32, 2, true)
  view.setUint16(34, 16, true)
  writeStr(36, 'data')
  view.setUint32(40, dataLength * 2, true)
}

onUnmounted(() => {
  if (timer) clearInterval(timer)
  if (mediaRecorder && mediaRecorder.state === 'recording') mediaRecorder.stop()
})
</script>

<style scoped>
.voice-wrap { display: flex; align-items: center; gap: 4px; flex-shrink: 0; }

.voice-btn {
  width: 36px; height: 36px; border-radius: var(--radius-md); border: none;
  background: var(--color-border-light); color: var(--color-text-muted);
  display: flex; align-items: center; justify-content: center;
  cursor: pointer; transition: all var(--transition-fast); position: relative;
}
.voice-btn:hover { background: var(--color-border); color: var(--color-text-secondary); }
.voice-btn.recording {
  background: #fef2f2; color: var(--color-error);
  animation: pulse 1.2s ease-in-out infinite;
}
.voice-btn.cancel {
  background: var(--color-border-light); color: var(--color-text-muted); width: 28px; height: 28px; border-radius: 50%;
}
.voice-btn.cancel:hover { background: #fee2e2; color: var(--color-error); }
.voice-btn.loading { background: var(--color-border-light); color: var(--color-text-muted); cursor: not-allowed; }

.recording-time {
  position: absolute; top: -6px; right: -6px;
  background: var(--color-error); color: #fff; font-size: 10px;
  padding: 1px 4px; border-radius: 8px; line-height: 1.2;
}

@keyframes pulse {
  0%, 100% { box-shadow: 0 0 0 0 rgba(220,38,38,0.35); }
  50% { box-shadow: 0 0 0 8px rgba(220,38,38,0); }
}
.spin { animation: spin 1s linear infinite; }
@keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
</style>
