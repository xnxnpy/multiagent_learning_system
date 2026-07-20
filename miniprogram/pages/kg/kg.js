Page({
  data: {
    title: '知识图谱',
    nodeCount: 0,
    edgeCount: 0,
    nodes: [],
    edges: []
  },

  canvasWidth: 0,
  canvasHeight: 0,
  ctx: null,
  scale: 1,
  offsetX: 0,
  offsetY: 0,
  lastTouchX: 0,
  lastTouchY: 0,
  selectedNode: null,

  onLoad(options) {
    if (options?.data) {
      try {
        const kgData = JSON.parse(decodeURIComponent(options.data))
        this.setData({
          title: kgData.title || '知识图谱',
          nodes: kgData.nodes || [],
          edges: kgData.edges || [],
          nodeCount: (kgData.nodes || []).length,
          edgeCount: (kgData.edges || []).length
        })
      } catch (e) {
        console.error('解析知识图谱数据失败:', e)
      }
    }
  },

  onReady() {
    this.ctx = wx.createCanvasContext('kgCanvas')
    this.initCanvas()
  },

  onShow() {
    this.drawGraph()
  },

  initCanvas() {
    const query = wx.createSelectorQuery()
    query.select('.kg-canvas').boundingClientRect((rect) => {
      if (rect) {
        this.canvasWidth = rect.width
        this.canvasHeight = rect.height
        this.offsetX = this.canvasWidth / 2
        this.offsetY = this.canvasHeight / 2
        this.layoutNodes()
        this.drawGraph()
      }
    }).exec()
  },

  layoutNodes() {
    const { nodes } = this.data
    if (!nodes || nodes.length === 0) return

    const centerX = 0
    const centerY = 0
    const radius = Math.min(this.canvasWidth, this.canvasHeight) * 0.35

    nodes.forEach((node, index) => {
      const angle = (2 * Math.PI * index) / nodes.length
      node.x = centerX + radius * Math.cos(angle)
      node.y = centerY + radius * Math.sin(angle)
      node.color = node.color || this.getRandomColor()
    })
  },

  getRandomColor() {
    const colors = ['#4F46E5', '#10B981', '#F59E0B', '#EF4444', '#8B5CF6', '#EC4899', '#06B6D4', '#84CC16']
    return colors[Math.floor(Math.random() * colors.length)]
  },

  drawGraph() {
    if (!this.ctx) return

    const ctx = this.ctx
    ctx.clearRect(0, 0, this.canvasWidth, this.canvasHeight)

    ctx.save()
    ctx.translate(this.offsetX, this.offsetY)
    ctx.scale(this.scale, this.scale)

    this.drawEdges(ctx)
    this.drawNodes(ctx)

    ctx.restore()
    ctx.draw()
  },

  drawEdges(ctx) {
    const { nodes, edges } = this.data

    edges.forEach(edge => {
      const source = nodes.find(n => n.id === edge.source || n.id === edge.source_id)
      const target = nodes.find(n => n.id === edge.target || n.id === edge.target_id)

      if (source && target) {
        ctx.beginPath()
        ctx.moveTo(source.x, source.y)
        ctx.lineTo(target.x, target.y)
        ctx.setStrokeStyle('#CBD5E1')
        ctx.setLineWidth(2)
        ctx.stroke()
      }
    })
  },

  drawNodes(ctx) {
    const { nodes, selectedNode } = this.data

    nodes.forEach(node => {
      const isSelected = selectedNode === node.id
      const radius = isSelected ? 35 : 28

      ctx.beginPath()
      ctx.arc(node.x, node.y, radius, 0, 2 * Math.PI)
      ctx.setFillStyle(node.color)
      ctx.fill()

      ctx.beginPath()
      ctx.arc(node.x, node.y, radius, 0, 2 * Math.PI)
      ctx.setStrokeStyle(isSelected ? '#fff' : 'rgba(255,255,255,0.5)')
      ctx.setLineWidth(isSelected ? 3 : 2)
      ctx.stroke()

      ctx.setFillStyle('#fff')
      ctx.setFontSize(12)
      ctx.setTextAlign('center')
      ctx.setTextBaseline('middle')

      const label = node.label || node.name || ''
      const maxLength = 6
      const displayLabel = label.length > maxLength ? label.substring(0, maxLength) + '...' : label
      ctx.fillText(displayLabel, node.x, node.y)
    })
  },

  onTouchStart(e) {
    const touch = e.touches[0]
    this.lastTouchX = touch.x
    this.lastTouchY = touch.y
  },

  onTouchMove(e) {
    const touch = e.touches[0]
    const deltaX = touch.x - this.lastTouchX
    const deltaY = touch.y - this.lastTouchY

    this.offsetX += deltaX
    this.offsetY += deltaY

    this.lastTouchX = touch.x
    this.lastTouchY = touch.y

    this.drawGraph()
  },

  onTouchEnd(e) {
    const touch = e.changedTouches[0]
    const clickX = touch.x
    const clickY = touch.y

    const localX = (clickX - this.offsetX) / this.scale
    const localY = (clickY - this.offsetY) / this.scale

    const { nodes } = this.data
    let foundNode = null

    for (let i = nodes.length - 1; i >= 0; i--) {
      const node = nodes[i]
      const distance = Math.sqrt(Math.pow(localX - node.x, 2) + Math.pow(localY - node.y, 2))
      if (distance <= 35) {
        foundNode = node.id
        break
      }
    }

    this.setData({ selectedNode: foundNode })
    this.drawGraph()

    if (foundNode) {
      const node = nodes.find(n => n.id === foundNode)
      if (node) {
        wx.showToast({
          title: node.label || node.name || '知识点',
          icon: 'none',
          duration: 1500
        })
      }
    }
  },

  goBack() {
    wx.navigateBack()
  }
})