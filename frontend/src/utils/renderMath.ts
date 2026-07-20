import katex from 'katex'
import 'katex/dist/katex.min.css'

/**
 * 渲染 HTML 中的 LaTeX 数学公式
 * - `$$...$$` → 块级公式（displayMode）
 * - `$...$` → 行内公式
 *
 * 需要在 marked 渲染后的 HTML 上调用（因为 marked 会转义 < > 等），
 * 所以先把 HTML 实体还原，渲染 KaTeX，再返回。
 */
export function renderMath(html: string): string {
  if (!html) return html

  // 1. 块级公式 $$...$$
  html = html.replace(/\$\$([\s\S]+?)\$\$/g, (_match, tex: string) => {
    return renderBlock(tex)
  })

  // 2. 行内公式 $...$（排除已处理的 $$ 和单独的 $）
  html = html.replace(/(?<!\$)\$(?!\$)(.+?)(?<!\$)\$(?!\$)/g, (_match, tex: string) => {
    return renderInline(tex)
  })

  return html
}

function renderBlock(tex: string): string {
  try {
    return katex.renderToString(decodeHTMLEntities(tex.trim()), {
      displayMode: true,
      throwOnError: false,
      trust: true,
    })
  } catch {
    return `<div class="math-error" style="color:#ef4444;font-style:italic">${tex}</div>`
  }
}

function renderInline(tex: string): string {
  try {
    return katex.renderToString(decodeHTMLEntities(tex.trim()), {
      displayMode: false,
      throwOnError: false,
      trust: true,
    })
  } catch {
    return `<span class="math-error" style="color:#ef4444;font-style:italic">${tex}</span>`
  }
}

function decodeHTMLEntities(text: string): string {
  return text
    .replace(/&lt;/g, '<')
    .replace(/&gt;/g, '>')
    .replace(/&amp;/g, '&')
    .replace(/&quot;/g, '"')
    .replace(/&#39;/g, "'")
    .replace(/&nbsp;/g, ' ')
}
