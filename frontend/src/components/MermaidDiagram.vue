<template>
  <div class="mermaid-diagram">
    <div class="mermaid-toolbar">
      <span class="mermaid-lang">mermaid</span>
      <div class="mermaid-actions">
        <button class="action-btn" @click="toggleSource" :title="showSource ? '查看图' : '查看代码'">
          {{ showSource ? '查看图' : '查看代码' }}
        </button>
        <button class="action-btn" @click="downloadSvg" title="下载图片">下载图片</button>
        <button class="action-btn copy-block-btn" :data-copy-text="code" title="复制代码">复制</button>
      </div>
    </div>
    <div v-if="showSource" class="mermaid-source">
      <pre><code>{{ code }}</code></pre>
    </div>
    <div v-else ref="containerRef" class="mermaid-render" v-html="svgContent"></div>
    <div v-if="error" class="mermaid-error">
      <p>渲染失败，显示源码：</p>
      <pre><code>{{ code }}</code></pre>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, watch, nextTick } from 'vue'

const props = defineProps<{ code: string }>()

const containerRef = ref<HTMLElement | null>(null)
const svgContent = ref('')
const error = ref(false)
const showSource = ref(false)

let mermaidId = 0

async function renderDiagram() {
  if (!props.code) return
  error.value = false
  svgContent.value = ''

  try {
    const mermaid = (await import('mermaid')).default
    mermaid.initialize({
      startOnLoad: false,
      theme: 'default',
      securityLevel: 'loose',
      fontFamily: 'inherit',
    })

    const id = `mermaid-${++mermaidId}`
    const { svg } = await mermaid.render(id, props.code)
    svgContent.value = svg
  } catch (e) {
    console.error('Mermaid render error:', e)
    error.value = true
  }
}

function toggleSource() {
  showSource.value = !showSource.value
}

function downloadSvg() {
  if (!containerRef.value) return
  const svgEl = containerRef.value.querySelector('svg')
  if (!svgEl) return

  // Serialize SVG
  const serializer = new XMLSerializer()
  let svgStr = serializer.serializeToString(svgEl)
  // Add XML declaration and UTF-8 encoding for Chinese support
  svgStr = '<?xml version="1.0" encoding="UTF-8"?>\n' + svgStr

  const blob = new Blob([svgStr], { type: 'image/svg+xml;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = 'diagram.svg'
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  URL.revokeObjectURL(url)
}

onMounted(() => { renderDiagram() })
watch(() => props.code, () => { renderDiagram() })
</script>

<style scoped>
.mermaid-diagram {
  margin: 12px 0;
  border-radius: var(--radius-lg);
  overflow: hidden;
  border: 1px solid var(--color-border);
  background: var(--color-bg-card);
}

.mermaid-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 6px 14px;
  background: var(--color-border-light);
  border-bottom: 1px solid var(--color-border);
}

.mermaid-lang {
  color: var(--color-text-muted);
  font-family: var(--font-mono);
  font-size: var(--text-xs);
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.mermaid-actions {
  display: flex;
  gap: 6px;
}

.action-btn {
  background: transparent;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  padding: 2px 10px;
  cursor: pointer;
  color: var(--color-text-muted);
  font-size: var(--text-xs);
  transition: all var(--transition-fast);
  font-family: inherit;
}

.action-btn:hover {
  border-color: var(--color-primary);
  color: var(--color-primary);
}

.mermaid-render {
  padding: 16px;
  display: flex;
  justify-content: center;
  overflow-x: auto;
}

.mermaid-render :deep(svg) {
  max-width: 100%;
  height: auto;
}

.mermaid-source {
  padding: 16px;
  background: var(--color-bg-page);
}

.mermaid-source pre {
  margin: 0;
  font-size: var(--text-sm);
  line-height: 1.6;
  color: var(--color-text-secondary);
  white-space: pre-wrap;
  word-break: break-word;
}

.mermaid-error {
  padding: 16px;
  color: var(--color-error);
}

.mermaid-error pre {
  margin: 8px 0 0;
  font-size: var(--text-sm);
  color: var(--color-text-secondary);
  white-space: pre-wrap;
}
</style>
