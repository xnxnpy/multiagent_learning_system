import { marked } from 'marked'
import { renderMath } from '@/utils/renderMath'

function extractCodeBlocks(text: string): [string, { lang: string; code: string }[]] {
  const blocks: { lang: string; code: string }[] = []
  const cleaned = text.replace(/```(\w*)\n([\s\S]*?)```/g, (_m, lang: string, code: string) => {
    blocks.push({ lang: (lang || '').toLowerCase(), code: code.trimEnd() })
    return `\x00CB${blocks.length - 1}\x00`
  })
  return [cleaned, blocks]
}

function restoreCodeBlocks(html: string, blocks: { lang: string; code: string }[]): string {
  const diagramLangs = ['mermaid', 'plantuml', 'uml', 'dot', 'graphviz']
  blocks.forEach((block, i) => {
    const placeholder = `\x00CB${i}\x00`
    if (diagramLangs.includes(block.lang)) {
      const escaped = block.code.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
      html = html.replace(placeholder, `<pre style="margin:12px 0;padding:16px;background:#f8f9fb;border-radius:8px;border:1px solid #d0d5dd;white-space:pre-wrap;word-break:break-word"><code>${escaped}</code></pre>`)
    } else {
      const fenced = '```' + block.lang + '\n' + block.code + '\n```'
      html = html.replace(placeholder, marked.parse(fenced) as string)
    }
  })
  return html
}

/** 统一 markdown 渲染：去包裹 → 提取代码块 → marked 渲染 → 还原代码块 */
export function renderMd(text: string): string {
  if (!text) return ''
  // 去掉 ```markdown / ```md 包裹层
  let content = text.trim()
  const firstLine = content.split('\n')[0]?.trim()
  if (firstLine === '```markdown' || firstLine === '```md') {
    content = content.split('\n').slice(1).join('\n')
    const lastLine = content.split('\n').pop()?.trim()
    if (lastLine === '```') {
      content = content.split('\n').slice(0, -1).join('\n')
    }
    content = content.trim()
  }
  const [cleaned, blocks] = extractCodeBlocks(content)
  let html = marked.parse(cleaned) as string
  html = restoreCodeBlocks(html, blocks)
  return renderMath(html)
}
