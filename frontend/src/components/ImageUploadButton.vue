<template>
  <div class="image-upload-wrap">
    <!-- 空闲状态：上传按钮 -->
    <button
      v-if="!isLoading"
      class="upload-btn"
      @click="triggerUpload"
      title="上传题目图片，自动识别文字"
    >
      <el-icon :size="size"><Picture /></el-icon>
    </button>

    <!-- 识别中 -->
    <button v-else class="upload-btn loading" disabled>
      <el-icon :size="size" class="spin"><Loading /></el-icon>
    </button>

    <input
      ref="fileInputRef"
      type="file"
      accept="image/jpeg,image/png,image/jpg,image/webp"
      style="display: none"
      @change="handleFileChange"
    />
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { ElMessage } from 'element-plus'
import { Picture, Loading } from '@element-plus/icons-vue'

const props = withDefaults(defineProps<{
  size?: number
  maxSizeMB?: number
}>(), {
  size: 18,
  maxSizeMB: 5,
})

const emit = defineEmits<{
  (e: 'result', text: string, imageBase64: string, fileName: string, fileSize: number): void
  (e: 'error', msg: string): void
}>()

const isLoading = ref(false)
const fileInputRef = ref<HTMLInputElement | null>(null)

/** 将 File 转为 base64 字符串（不含 data:image/xxx;base64, 前缀） */
function fileToBase64(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader()
    reader.onload = () => {
      const result = reader.result as string
      // 去掉 "data:image/jpeg;base64," 前缀，只保留纯 base64
      const base64 = result.includes(',') ? result.split(',')[1] : result
      resolve(base64)
    }
    reader.onerror = reject
    reader.readAsDataURL(file)
  })
}

function triggerUpload() {
  fileInputRef.value?.click()
}

async function handleFileChange(e: Event) {
  const input = e.target as HTMLInputElement
  const file = input.files?.[0]
  if (!file) return

  // 重置 input，允许重复上传同一文件
  input.value = ''

  // 校验文件类型
  if (!file.type.startsWith('image/')) {
    ElMessage.error('请上传图片文件')
    return
  }

  // 校验文件大小
  if (file.size > props.maxSizeMB * 1024 * 1024) {
    ElMessage.error(`图片不能超过 ${props.maxSizeMB}MB`)
    return
  }

  isLoading.value = true
  try {
    // 本地转 base64（用于保存到聊天记录，与 OCR 并行）
    const localBase64 = await fileToBase64(file)

    const { studentAPI } = await import('@/api')
    const formData = new FormData()
    formData.append('file', file)
    const res: any = await studentAPI.recognizeImage(formData)
    if (res.text) {
      emit('result', res.text, localBase64, file.name, file.size)
      ElMessage.success('图片上传成功')
    } else {
      ElMessage.success('图片上传成功')
    }
  } catch (err: any) {
    const msg = err?.response?.data?.detail || '图片识别失败'
    emit('error', msg)
    ElMessage.error(msg)
  } finally {
    isLoading.value = false
  }
}
</script>

<style scoped>
.image-upload-wrap { display: flex; align-items: center; flex-shrink: 0; }

.upload-btn {
  width: 36px; height: 36px; border-radius: var(--radius-md); border: none;
  background: var(--color-border-light); color: var(--color-text-muted);
  display: flex; align-items: center; justify-content: center;
  cursor: pointer; transition: all var(--transition-fast);
}
.upload-btn:hover { background: var(--color-border); color: var(--color-text-secondary); }
.upload-btn.loading { background: var(--color-border-light); color: var(--color-text-muted); cursor: not-allowed; }

.spin { animation: spin 1s linear infinite; }
@keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
</style>
