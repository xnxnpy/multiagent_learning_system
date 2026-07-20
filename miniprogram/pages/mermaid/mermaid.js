Page({
  data: {
    imageUrl: '',
    code: '',
    loading: true,
    error: false
  },
  
  onLoad(options) {
    if (options.code) {
      const code = decodeURIComponent(options.code)
      this.setData({ code })
      // 使用 mermaid.ink 将 mermaid 代码渲染为图片
      const base64 = wx.arrayBufferToBase64(
        new Uint8Array(unescape(encodeURIComponent(code)).split('').map(c => c.charCodeAt(0)))
      )
      const imageUrl = `https://mermaid.ink/img/${base64}?bgColor=white&width=1200&scale=2`
      this.setData({ imageUrl, loading: false })
    }
  },

  onImageError() {
    this.setData({ error: true, loading: false })
  }
})
