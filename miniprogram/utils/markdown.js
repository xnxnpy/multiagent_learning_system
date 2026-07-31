// Markdown → 纯文本渲染（不使用 rich-text，避免默认 margin 问题）
// 输出带格式的纯文本，用 <text> 组件渲染

// Markdown → HTML 字符串（用于 rich-text 组件渲染）
function markdownToHtml(text) {
  if (!text || typeof text !== 'string') return ''
  
  let md = text.trim()
  md = md.replace(/^```markdown\s*\n?/i, '').replace(/\n?```\s*$/i, '').trim()
  
  // 压缩多余空行
  md = md.replace(/\n{3,}/g, '\n\n')
  
  let lines = md.split('\n')
  let html = ''
  let inCodeBlock = false
  let codeLines = []
  let codeLang = ''
  let inList = false
  let listItems = []
  let listType = ''
  let listIndent = 0
  
  const flushList = () => {
    if (listItems.length > 0) {
      const tag = listType === 'ordered' ? 'ol' : 'ul'
      html += '<' + tag + ' style="margin:8rpx 0;padding-left:32rpx;">'
      for (const item of listItems) {
        html += '<li style="margin:4rpx 0;">' + item + '</li>'
      }
      html += '</' + tag + '>'
      listItems = []
      inList = false
    }
  }
  
  for (let i = 0; i < lines.length; i++) {
    let line = lines[i]
    
    // 代码块处理
    const codeMatch = line.match(/^```(\w*)/)
    if (codeMatch) {
      flushList()
      if (inCodeBlock) {
        if (codeLines.length > 0) {
          html += '<pre style="background:#fff;padding:16rpx;border-radius:12rpx;border:1rpx solid #e2e8f0;font-size:24rpx;overflow-x:auto;"><code class="language-' + (codeLang || 'text') + '">' + escapeHtml(codeLines.join('\n')) + '</code></pre>'
        }
        inCodeBlock = false
        codeLines = []
        codeLang = ''
      } else {
        inCodeBlock = true
        codeLang = codeMatch[1] || ''
      }
      continue
    }
    
    if (inCodeBlock) {
      codeLines.push(line)
      continue
    }
    
    // 空行
    if (/^\s*$/.test(line)) {
      flushList()
      continue
    }
    
    // 标题
    const hMatch = line.match(/^(#{1,4})\s+(.+)/)
    if (hMatch) {
      flushList()
      const level = hMatch[1].length
      const hSizes = ['36rpx', '32rpx', '28rpx', '26rpx']
      html += '<h' + level + ' style="font-size:' + hSizes[level-1] + ';font-weight:700;margin:12rpx 0;color:#2B2D42;">' + cleanInline(hMatch[2]) + '</h' + level + '>'
      continue
    }
    
    // 分割线
    if (/^---+\s*$/.test(line)) {
      flushList()
      html += '<hr style="border:none;border-top:1rpx solid #e2e8f0;margin:16rpx 0;">'
      continue
    }
    
    // 引用
    const quoteMatch = line.match(/^>\s*(.+)/)
    if (quoteMatch) {
      flushList()
      html += '<blockquote style="border-left:4rpx solid #B0512C;background:rgba(176,81,44,0.08);padding:8rpx 16rpx;margin:8rpx 0;border-radius:0 12rpx 12rpx 0;font-size:26rpx;">' + cleanInline(quoteMatch[1]) + '</blockquote>'
      continue
    }
    
    // 无序列表
    const ulMatch = line.match(/^(\s*)[-*+]\s+(.+)/)
    if (ulMatch) {
      const indent = Math.floor(ulMatch[1].length / 2)
      if (!inList || listType !== 'unordered' || listIndent !== indent) {
        flushList()
        inList = true
        listType = 'unordered'
        listIndent = indent
      }
      listItems.push(cleanInline(ulMatch[2]))
      continue
    }
    
    // 有序列表
    const olMatch = line.match(/^(\s*)(\d+)\.\s+(.+)/)
    if (olMatch) {
      const indent = Math.floor(olMatch[1].length / 2)
      if (!inList || listType !== 'ordered' || listIndent !== indent) {
        flushList()
        inList = true
        listType = 'ordered'
        listIndent = indent
      }
      listItems.push(cleanInline(olMatch[3]))
      continue
    }
    
    // 普通段落
    flushList()
    html += '<p style="margin:8rpx 0;line-height:1.6;font-size:28rpx;color:#4a4e69;">' + cleanInline(line) + '</p>'
  }
  
  // 处理剩余列表
  flushList()
  
  // 处理最后一个代码块
  if (inCodeBlock && codeLines.length > 0) {
    html += '<pre style="background:#fff;padding:16rpx;border-radius:12rpx;border:1rpx solid #e2e8f0;font-size:24rpx;overflow-x:auto;"><code class="language-' + (codeLang || 'text') + '">' + escapeHtml(codeLines.join('\n')) + '</code></pre>'
  }
  
  return html
}

function markdownToPlainText(text) {
  if (!text || typeof text !== 'string') return []
  
  let md = text.trim()
  
  // 剥离外层 ```markdown 包装
  md = md.replace(/^```markdown\s*\n?/i, '').replace(/\n?```\s*$/i, '').trim()
  
  // 先把连续多个空行压缩为单个换行符，然后去掉开头和结尾的空行
  md = md.replace(/\n{3,}/g, '\n\n')  // 3+空行 → 2空行
         .replace(/^\n+/, '')          // 开头空行
         .replace(/\n+$/, '')          // 结尾空行
  
  let lines = md.split('\n')
  const output = []
  let inCodeBlock = false
  let codeLines = []
  let codeLang = ''
  
  for (let i = 0; i < lines.length; i++) {
    let line = lines[i]
    
    // 代码块处理
    const codeMatch = line.match(/^```(\w*)/)
    if (codeMatch) {
      if (inCodeBlock) {
        if (codeLines.length > 0) {
          output.push({ type: 'code', lang: codeLang, content: codeLines.join('\n') })
        }
        inCodeBlock = false
        codeLines = []
        codeLang = ''
      } else {
        inCodeBlock = true
        codeLang = codeMatch[1] || ''
      }
      continue
    }
    
    if (inCodeBlock) {
      codeLines.push(line)
      continue
    }
    
    // 跳过空行（压缩空行后，只会有最多1个连续空行）
    // 不再生成 blank token，直接跳过
    if (/^\s*$/.test(line)) {
      continue
    }
    
    // 标题
    const hMatch = line.match(/^(#{1,4})\s+(.+)/)
    if (hMatch) {
      const level = hMatch[1].length
      const text = cleanInline(hMatch[2])
      output.push({ type: 'heading', level, text })
      continue
    }
    
    // 分割线
    if (/^---+\s*$/.test(line)) {
      output.push({ type: 'hr' })
      continue
    }
    
    // 引用
    const quoteMatch = line.match(/^>\s*(.+)/)
    if (quoteMatch) {
      output.push({ type: 'quote', text: cleanInline(quoteMatch[1]) })
      continue
    }
    
    // 无序列表
    const ulMatch = line.match(/^(\s*)[-*+]\s+(.+)/)
    if (ulMatch) {
      output.push({ type: 'list_item', ordered: false, indent: Math.floor(ulMatch[1].length / 2), text: cleanInline(ulMatch[2]) })
      continue
    }
    
    // 有序列表
    const olMatch = line.match(/^(\s*)(\d+)\.\s+(.+)/)
    if (olMatch) {
      output.push({ type: 'list_item', ordered: true, number: parseInt(olMatch[2]), indent: Math.floor(olMatch[1].length / 2), text: cleanInline(olMatch[3]) })
      continue
    }
    
    // 普通段落
    const cleanedText = cleanInline(line)
    if (cleanedText && cleanedText.trim()) {
      output.push({ type: 'paragraph', text: cleanedText })
    }
  }
  
  // 处理最后一个代码块
  if (inCodeBlock && codeLines.length > 0) {
    output.push({ type: 'code', lang: codeLang, content: codeLines.join('\n') })
  }
  
  return output
}

// 清理行内格式（去掉 **加粗**、*斜体*、`code` 等标记）
function cleanInline(text) {
  return text
    .replace(/`([^`]+)`/g, '$1')
    .replace(/\*\*([^*]+)\*\*/g, '$1')
    .replace(/\*([^*]+)\*/g, '$1')
    .replace(/\[([^\]]+)\]\([^)]+\)/g, '$1')
    .replace(/!\[([^\]]*)\]\([^)]+\)/g, '$1')
    .trim()
}

// 将 markdown 转为纯文本字符串（用于仅显示文本的场景）
function markdownToSimpleText(text) {
  if (!text || typeof text !== 'string') return ''
  
  let md = text.trim()
  md = md.replace(/^```markdown\s*\n?/i, '').replace(/\n?```\s*$/i, '').trim()
  
  let lines = md.split('\n')
  const result = []
  let inCode = false
  let codeBuf = []
  
  for (let line of lines) {
    if (line.match(/^```/)) {
      if (inCode) {
        result.push('```\n' + codeBuf.join('\n') + '\n```')
        codeBuf = []
        inCode = false
      } else {
        inCode = true
      }
      continue
    }
    if (inCode) {
      codeBuf.push(line)
      continue
    }
    
    // 标题转为纯文本
    line = line.replace(/^#{1,4}\s+/, '')
    // 列表转为纯文本
    line = line.replace(/^[-*+]\s+/, '• ')
    line = line.replace(/^\s*\d+\.\s+/, '')
    // 清理行内格式
    line = cleanInline(line)
    
    result.push(line)
  }
  
  if (inCode && codeBuf.length > 0) {
    result.push('```\n' + codeBuf.join('\n') + '\n```')
  }
  
  return result.join('\n')
}

function escapeHtml(text) {
  if (!text) return ''
  return String(text)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
}

// 单独渲染代码块为 HTML（用于资源页中的单独代码内容）
function renderCodeBlock(code, language) {
  if (!code) return ''
  const lang = (language || 'text').toLowerCase()
  const escaped = escapeHtml(code)
  return (
    '<pre style="background:#fff;padding:16rpx;border-radius:12rpx;border:1rpx solid #e2e8f0;font-size:24rpx;overflow-x:auto;margin:8rpx 0;">' +
    '<div style="padding:4rpx 12rpx;background:#f8fafc;border-bottom:1rpx solid #e2e8f0;font-size:20rpx;color:#64748b;font-family:monospace;text-transform:uppercase;letter-spacing:0.05em;">' + lang + '</div>' +
    '<code class="language-' + lang + '" style="display:block;padding:12rpx 14rpx;font-size:24rpx;line-height:1.5;color:#24292e;font-family:monospace;white-space:pre-wrap;word-break:break-all;">' + escaped + '</code>' +
    '</pre>'
  )
}

module.exports = { markdownToHtml, markdownToPlainText, markdownToSimpleText, escapeHtml, renderCodeBlock }
