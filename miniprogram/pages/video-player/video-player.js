Page({
  data: {
    videoUrl: '',
    videoTitle: '教学视频',
    playStatus: '未播放'
  },

  videoContext: null,

  onLoad(options) {
    if (options?.url) {
      const url = decodeURIComponent(options.url)
      this.setData({ videoUrl: url })
    }
    if (options?.title) {
      this.setData({ videoTitle: decodeURIComponent(options.title) })
    }
  },

  onReady() {
    this.videoContext = wx.createVideoContext('videoPlayer')
  },

  goBack() {
    wx.navigateBack()
  },

  onVideoError(e) {
    console.warn('视频加载警告:', e.detail)
  },

  onVideoLoadedMetadata(e) {
    this.setData({ playStatus: '准备就绪' })
  },

  onVideoPlay() {
    this.setData({ playStatus: '播放中' })
  },

  onVideoPause() {
    this.setData({ playStatus: '已暂停' })
  },

  onVideoEnded() {
    this.setData({ playStatus: '已完成' })
  }
})