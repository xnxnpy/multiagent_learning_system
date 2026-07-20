import { nextTick, type Ref } from 'vue'
import { Marked } from 'marked'
import hljs from 'highlight.js'
import 'highlight.js/styles/github.css'
import { renderMath } from '@/utils/renderMath'
import { renderMd } from '@/utils/renderMarkdown'
import type { ChatMsg } from '@/types'

/* ── Markdown 渲染配置（独立实例，不污染全局 marked） ─────────── */

const renderer = {
  code(text: string, lang: string | undefined) {
    if (!text) return '<pre><code></code></pre>'
    const language = (lang || '').toLowerCase()
    // 图解代码块
    if (['mermaid', 'plantuml', 'uml', 'dot', 'graphviz'].includes(language)) {
      const escaped = text.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
      return `<div class="diagram-block" style="margin:12px 0;border-radius:8px;overflow:hidden;border:1px solid #d0d5dd;background:#f8f9fb"><div style="display:flex;align-items:center;justify-content:space-between;padding:6px 14px;background:#eef1f6;border-bottom:1px solid #d0d5dd"><span style="color:#667085;font-family:monospace;font-size:11px;text-transform:uppercase">${language}</span><button class="copy-block-btn" style="background:transparent;border:1px solid #d0d5dd;border-radius:4px;padding:2px 8px;cursor:pointer;color:#667085;font-size:11px" data-copy-text="${escaped}">复制</button></div><pre style="margin:0;padding:16px;background:#f8f9fb;color:#344054;overflow-x:auto;font-size:13px;line-height:1.6;white-space:pre-wrap;word-break:break-word"><code>${escaped}</code></pre></div>`
    }
    // 普通代码块
    let highlighted: string
    if (language && hljs.getLanguage(language)) {
      highlighted = hljs.highlight(text, { language }).value
    } else {
      highlighted = hljs.highlightAuto(text).value
    }
    const escaped = text.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
    return `<div style="margin:12px 0;border-radius:8px;overflow:hidden;border:1px solid #d0d5dd;background:#fff"><div style="display:flex;align-items:center;justify-content:space-between;padding:6px 14px;background:#f2f4f7;border-bottom:1px solid #d0d5dd"><span style="color:#667085;font-family:monospace;font-size:11px;text-transform:uppercase">${language || 'code'}</span><button class="copy-block-btn" style="background:transparent;border:1px solid #d0d5dd;border-radius:4px;padding:2px 8px;cursor:pointer;color:#667085;font-size:11px" data-copy-text="${escaped}">复制</button></div><pre style="margin:0;padding:16px;background:#fff;overflow-x:auto;font-size:13px;line-height:1.6"><code style="font-family:monospace;font-size:13px;background:transparent;color:#1d2939">${highlighted}</code></pre></div>`
  }
}

const markedInstance = new Marked({ renderer, breaks: true })

/* ── 事件委托：点击 .copy-block-btn 时复制文本 ─────────── */

let _copyHandlerAttached = false

function ensureCopyHandler() {
  if (_copyHandlerAttached) return
  _copyHandlerAttached = true
  document.addEventListener('click', (e) => {
    const btn = (e.target as HTMLElement).closest('.copy-block-btn') as HTMLButtonElement | null
    if (!btn) return
    const raw = btn.getAttribute('data-copy-text') || ''
    // 还原 HTML 实体
    const text = raw.replace(/&amp;/g, '&').replace(/&lt;/g, '<').replace(/&gt;/g, '>').replace(/&quot;/g, '"').replace(/&#39;/g, "'")
    navigator.clipboard.writeText(text).then(() => {
      btn.textContent = '已复制'
      btn.style.color = '#22c55e'
      btn.style.borderColor = '#22c55e'
      setTimeout(() => {
        btn.textContent = '复制'
        btn.style.color = '#667085'
        btn.style.borderColor = '#d0d5dd'
      }, 2000)
    })
  })
}

/* ── Composable ─────────────────────────────────────────── */

export function useMarkdown() {
  let needsRender = false
  let renderAnimationId: number | null = null
  let scrollTimeout: ReturnType<typeof setTimeout> | null = null

  // 确保复制事件委托已挂载
  ensureCopyHandler()

  function renderMarkdown(content: string): string {
    if (!content) return ''
    return renderMd(content)
  }

  function scheduleRender(messages: Ref<ChatMsg[]>) {
    if (!needsRender) {
      needsRender = true
      renderAnimationId = requestAnimationFrame(() => {
        if (!messages?.value?.length) { needsRender = false; return }
        const lastIdx = messages.value.length - 1
        const lastMsg = messages.value[lastIdx]
        if (lastMsg?.streaming) {
          messages.value[lastIdx] = { ...lastMsg, renderedContent: renderMarkdown(lastMsg.content) }
        }
        needsRender = false
      })
    }
  }

  function scrollBottom(el: HTMLElement | null) {
    nextTick(() => {
      if (el) el.scrollTop = el.scrollHeight
    })
  }

  function throttledScroll(el: HTMLElement | null) {
    if (!scrollTimeout) {
      scrollBottom(el)
      scrollTimeout = setTimeout(() => { scrollTimeout = null }, 50)
    }
  }

  return { renderMarkdown, scheduleRender, scrollBottom, throttledScroll }
}
