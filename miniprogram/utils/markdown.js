// 统一的 markdown → HTML 渲染函数
function markdownToHtml(text) {
  if (!text || typeof text !== 'string') return ''
  
  let md = text.trim()
  
  // 剥离外层 ```markdown 包装（后端返回的文档内容常带此包装）
  md = md.replace(/^```markdown\s*\n?/i, '').replace(/\n?```\s*$/i, '').trim()
  
  // 1. 先提取代码块，防止被其他规则干扰
  const codeBlocks = []
  const diagramLangs = ['mermaid', 'plantuml', 'uml', 'dot', 'graphviz']
  md = md.replace(/```(\w*)\n([\s\S]*?)```/g, (_, lang, code) => {
    const i = codeBlocks.length
    const l = (lang || '').toLowerCase()
    codeBlocks.push({ lang: l, code: code.trimEnd(), isDiagram: diagramLangs.includes(l) })
    return `\x00CB${i}\x00`
  })
  
  // 2. 提取行内代码
  const inlineCodes = []
  md = md.replace(/`([^`\n]+)`/g, (_, code) => {
    const i = inlineCodes.length
    inlineCodes.push(code)
    return `\x00IC${i}\x00`
  })
  
  // 3. 处理标题（必须在列表之前）
  md = md.replace(/^####\s+(.+)$/gm, '<h4>$1</h4>')
  md = md.replace(/^###\s+(.+)$/gm, '<h3>$1</h3>')
  md = md.replace(/^##\s+(.+)$/gm, '<h2>$1</h2>')
  md = md.replace(/^#\s+(.+)$/gm, '<h1>$1</h1>')
  
  // 4. 加粗和斜体
  md = md.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
  md = md.replace(/\*(.+?)\*/g, '<em>$1</em>')
  
  // 5. 无序列表
  md = md.replace(/^[\s]*[-*+]\s+(.+)$/gm, '<li>$1</li>')
  
  // 6. 有序列表
  md = md.replace(/^[\s]*(\d+)\.\s+(.+)$/gm, '<li><b>$1.</b> $2</li>')
  
  // 7. 连续 li 包裹为 ul
  md = md.replace(/((?:<li>.*?<\/li>\n?)+)/g, '<ul>$1</ul>')
  
  // 8. 引用
  md = md.replace(/^>\s*(.+)$/gm, '<blockquote>$1</blockquote>')
  
  // 9. 分割线
  md = md.replace(/^---+$/gm, '<hr/>')
  
  // 10. 图片
  md = md.replace(/!\[([^\]]*)\]\(([^)]+)\)/g, '<img src="$2" alt="$1" style="max-width:100%;border-radius:8rpx;margin:12rpx 0"/>')
  
  // 11. 链接
  md = md.replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" style="color:#2563eb">$1</a>')
  
  // 12. 段落处理：双换行分段，单换行换行
  md = md.replace(/\n{2,}/g, '\x00P\x00')
  md = md.replace(/\n/g, '<br/>')
  md = md.replace(/\x00P\x00/g, '</p><p>')
  
  // 13. 还原行内代码
  inlineCodes.forEach((code, i) => {
    md = md.replace(`\x00IC${i}\x00`, `<code>${escapeHtml(code)}</code>`)
  })
  
  // 14. 还原代码块（mermaid 用图片内联渲染）
  codeBlocks.forEach((block, i) => {
    let cb
    if (block.isDiagram) {
      const base64 = wx.arrayBufferToBase64(
        new Uint8Array(unescape(encodeURIComponent(block.code)).split('').map(c => c.charCodeAt(0)))
      )
      const imgUrl = `https://mermaid.ink/img/${base64}?bgColor=white&width=2400&scale=4`
      cb = `<div style="margin:16rpx 0;padding:16rpx;background:#f8fafc;border-radius:12rpx;border:1rpx solid #e2e8f0">`
        + `<div style="font-size:20rpx;color:#64748b;font-family:monospace;text-transform:uppercase;margin-bottom:8rpx">${block.lang}</div>`
        + `<img src="${imgUrl}" style="width:100%;display:block" />`
        + `</div>`
    } else {
      cb = renderCodeBlock(block.code, block.lang)
    }
    md = md.replace(`\x00CB${i}\x00`, cb)
  })
  
  // 15. 包裹段落
  if (md && !md.match(/^<(h[1-6]|ul|ol|li|div|table|pre|blockquote|hr|img)/)) {
    md = '<p>' + md + '</p>'
  }
  
  // 16. 清理空标签
  md = md.replace(/<p>\s*<\/p>/g, '')
  md = md.replace(/<p>\s*<br\/>/g, '<p>')
  md = md.replace(/<\/p>\s*<\/p>/g, '</p>')
  
  return md
}

// 代码块渲染
function renderCodeBlock(code, lang) {
  if (!code) return ''
  lang = (lang || '').toLowerCase()
  
  const isMermaid = ['mermaid', 'plantuml', 'uml', 'dot', 'graphviz'].includes(lang)
  
  if (isMermaid) {
    return `<div style="margin:16rpx 0;border-radius:12rpx;overflow:hidden;border:1rpx solid #e5e7eb;background:#f8fafc">`
      + `<div style="padding:8rpx 16rpx;background:#f1f5f9;border-bottom:1rpx solid #e5e7eb">`
      + `<span style="color:#64748b;font-family:monospace;font-size:20rpx">${lang}</span></div>`
      + `<pre style="margin:0;padding:16rpx;font-size:22rpx;line-height:1.5;white-space:pre-wrap;font-family:monospace;color:#475569">${escapeHtml(code)}</pre></div>`
  }
  
  const highlighted = highlightCode(code, lang)
  return `<div style="margin:16rpx 0;border-radius:12rpx;overflow:hidden;border:1rpx solid #e5e7eb">`
    + `<div style="display:flex;align-items:center;justify-content:space-between;padding:6rpx 16rpx;background:#f8fafc;border-bottom:1rpx solid #e5e7eb">`
    + `<span style="color:#64748b;font-family:monospace;font-size:20rpx">${lang || 'code'}</span></div>`
    + `<pre style="margin:0;padding:16rpx;background:#fff;overflow-x:auto;font-size:24rpx;line-height:1.6;font-family:'Courier New',Consolas,monospace;color:#1e293b">${highlighted}</pre></div>`
}

// 语法高亮
function highlightCode(code, lang) {
  if (!code) return ''
  
  const tokens = []
  let tIdx = 0
  function tok(match, color) {
    const ph = `\x01T${tIdx++}\x01`
    tokens.push({ ph, html: `<span style="color:${color}">${escapeHtml(match)}</span>` })
    return ph
  }
  
  let r = code
  
  // 字符串（必须在注释和关键字之前）
  r = r.replace(/'(?:[^'\\]|\\.)*'/g, m => tok(m, '#ce9178'))
  r = r.replace(/"(?:[^"\\]|\\.)*"/g, m => tok(m, '#ce9178'))
  
  // 注释
  r = r.replace(/#.*$/gm, m => tok(m, '#6a9955'))
  r = r.replace(/\/\/.*$/gm, m => tok(m, '#6a9955'))
  r = r.replace(/\/\*[\s\S]*?\*\//g, m => tok(m, '#6a9955'))
  
  // 关键字
  const kw = 'True|False|None|def|class|import|from|return|if|elif|else|for|while|in|and|or|not|as|with|try|except|finally|raise|yield|lambda|pass|break|continue|self|print|async|await|const|let|var|function|new|this|typeof|instanceof|switch|case|default|do|void|delete|export|super'
  r = r.replace(new RegExp(`\\b(${kw})\\b`, 'g'), m => tok(m, '#c678dd'))
  
  // 内置函数/类型
  const builtins = 'print|len|range|int|float|str|list|dict|set|tuple|bool|type|input|open|map|filter|zip|enumerate|sorted|reversed|sum|min|max|abs|round|isinstance|hasattr|getattr|setattr|super|property|staticmethod|classmethod'
  r = r.replace(new RegExp(`\\b(${builtins})\\b`, 'g'), m => tok(m, '#e5c07b'))
  
  // 数字
  r = r.replace(/\b(\d+\.?\d*(?:e[+-]?\d+)?)\b/gi, m => tok(m, '#d19a66'))
  
  // 函数调用
  r = r.replace(/\b([a-zA-Z_]\w*)\s*(?=\()/g, m => tok(m, '#61afef'))
  
  // 转义 HTML
  r = escapeHtml(r)
  
  // 还原 token
  tokens.forEach(t => {
    r = r.replace(t.ph, t.html)
  })
  
  return r
}

function escapeHtml(text) {
  if (!text) return ''
  return String(text)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
}

module.exports = { markdownToHtml, escapeHtml, highlightCode, renderCodeBlock }
