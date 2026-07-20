Page({
  data: {
    title: '思维导图',
    content: '',
    nodes: [],
    connections: [],
    treeWidth: 800,
    treeHeight: 600,
    scale: 0.6
  },

  linesCtx: null,

  onLoad(options) {
    if (options?.content) {
      this.setData({ content: decodeURIComponent(options.content) })
    }
    if (options?.title) {
      this.setData({ title: decodeURIComponent(options.title) })
    }
  },

  onReady() {
    this.parseAndRender()
  },

  onShow() {
    this.drawLines()
  },

  parseAndRender() {
    const { content } = this.data
    
    if (!content) return

    const lines = content.split('\n').filter(line => line.trim())
    const root = this.parseMarkdown(lines)
    
    if (!root) return

    const { nodes, connections, treeWidth, treeHeight } = this.layoutTree(root)
    
    this.setData({
      nodes,
      connections,
      treeWidth,
      treeHeight
    })
    
    setTimeout(() => {
      this.drawLines()
    }, 300)
  },

  parseMarkdown(lines) {
    const root = { text: '', children: [], level: 0 }
    const stack = [root]
    const levelRegex = /^(#{1,6})\s*(.+)$/

    lines.forEach(line => {
      const match = line.match(levelRegex)
      if (match) {
        const level = match[1].length
        const text = match[2].trim()

        while (stack.length > level) {
          stack.pop()
        }

        const parent = stack[stack.length - 1]
        const node = { text, children: [], level }
        parent.children.push(node)
        stack.push(node)
      } else {
        const trimmed = line.trim()
        if (trimmed && stack.length > 0) {
          const lastNode = stack[stack.length - 1]
          if (!lastNode.text) {
            lastNode.text = trimmed
          } else {
            const node = { text: trimmed, children: [], level: stack.length }
            stack[stack.length - 1].children.push(node)
          }
        }
      }
    })

    return root.children.length > 0 ? root.children[0] : null
  },

  layoutTree(root) {
    const nodes = []
    const connections = []
    const colors = ['#4F46E5', '#10B981', '#F59E0B', '#EF4444', '#8B5CF6', '#EC4899']
    
    let nodeId = 0

    const nodeWidth = 140
    const nodeHeight = 36
    const hGap = 60
    const vGap = 40
    const padding = 80

    const getSubtreeHeight = (node) => {
      if (node.children.length === 0) return nodeHeight
      const totalHeight = node.children.reduce((sum, child) => sum + getSubtreeHeight(child), 0)
      return Math.max(nodeHeight, totalHeight + (node.children.length - 1) * vGap)
    }

    const layout = (node, centerX, centerY) => {
      const id = nodeId++
      const colorIndex = node.level % colors.length
      const subtreeHeight = getSubtreeHeight(node)
      
      const leftX = centerX - nodeWidth / 2
      const topY = centerY - nodeHeight / 2
      
      nodes.push({
        id,
        text: node.text,
        x: leftX,
        y: topY,
        color: colors[colorIndex],
        level: node.level,
        width: nodeWidth,
        height: nodeHeight,
        centerX: centerX,
        centerY: centerY
      })

      if (node.children.length === 0) return

      const childCount = node.children.length
      let currentY = centerY - (subtreeHeight - nodeHeight) / 2

      node.children.forEach(child => {
        const childHeight = getSubtreeHeight(child)
        const childX = centerX + nodeWidth + hGap
        const childY = currentY + childHeight / 2
        
        const dx = childX - (centerX + nodeWidth / 2)
        const dy = childY - centerY
        const length = Math.sqrt(dx * dx + dy * dy)
        const angle = (Math.atan2(dy, dx) * 180) / Math.PI
        
        connections.push({
          x1: centerX + nodeWidth / 2,
          y1: centerY,
          length: length,
          angle: angle,
          color: colors[colorIndex]
        })

        layout(child, childX, childY)
        currentY += childHeight + vGap
      })
    }

    const totalHeight = getSubtreeHeight(root)
    layout(root, padding + nodeWidth / 2, padding + totalHeight / 2)

    let minX = Infinity
    let maxX = 0
    let minY = Infinity
    let maxY = 0

    nodes.forEach(node => {
      minX = Math.min(minX, node.x)
      maxX = Math.max(maxX, node.x + nodeWidth)
      minY = Math.min(minY, node.y - nodeHeight / 2)
      maxY = Math.max(maxY, node.y + nodeHeight / 2)
    })

    const offsetX = minX < 0 ? -minX : 0
    const offsetY = minY < 0 ? -minY : 0

    nodes.forEach(node => {
      node.x += offsetX
      node.y += offsetY
    })

    connections.forEach(conn => {
      conn.x1 += offsetX
      conn.y1 += offsetY
      conn.x2 += offsetX
      conn.y2 += offsetY
    })

    const treeWidth = maxX + offsetX + padding
    const treeHeight = maxY + offsetY + padding

    return { nodes, connections, treeWidth, treeHeight }
  },

  drawLines() {
    if (!this.data.connections.length) return

    const query = wx.createSelectorQuery()
    query.select('#linesCanvas').fields({ node: true, size: true }).exec((res) => {
      if (!res[0]) return

      const { node, width, height } = res[0]
      const ctx = node.getContext('2d')
      this.linesCtx = ctx

      const systemInfo = wx.getWindowInfo ? wx.getWindowInfo() : wx.getSystemInfoSync()
      const dpr = systemInfo.pixelRatio || 2

      node.width = width * dpr
      node.height = height * dpr
      ctx.scale(dpr, dpr)

      ctx.clearRect(0, 0, width, height)

      this.data.connections.forEach(conn => {
        ctx.beginPath()
        ctx.moveTo(conn.x1, conn.y1)
        ctx.lineTo(conn.x2, conn.y2)
        ctx.strokeStyle = conn.color || '#CBD5E1'
        ctx.lineWidth = 2
        ctx.stroke()

        ctx.beginPath()
        ctx.arc(conn.x2, conn.y2, 5, 0, Math.PI * 2)
        ctx.fillStyle = conn.color || '#CBD5E1'
        ctx.fill()
      })
    })
  },

  onNodeClick(e) {
    const text = e.currentTarget.dataset.text
    wx.showToast({
      title: text,
      icon: 'none',
      duration: 1500
    })
  },

  zoomIn() {
    this.setData({ scale: Math.min(this.data.scale * 1.2, 2) })
  },

  zoomOut() {
    this.setData({ scale: Math.max(this.data.scale * 0.8, 0.3) })
  },

  fitView() {
    this.setData({ scale: 0.6 })
  },

  goBack() {
    wx.navigateBack()
  }
})