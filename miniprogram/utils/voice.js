const { BASE_URL } = require('./request')

class VoiceInput {
  constructor(options = {}) {
    this.onStart = options.onStart || (() => {})
    this.onRecording = options.onRecording || (() => {})
    this.onResult = options.onResult || (() => {})
    this.onError = options.onError || (() => {})
    this.onCancel = options.onCancel || (() => {})
    this.onLoading = options.onLoading || (() => {})
    this.maxDuration = options.maxDuration || 60
    this.recorderManager = null
    this.timer = null
    this.recordingTime = 0
    this.isRecording = false
    this.isLoading = false
  }

  init() {
    this.recorderManager = wx.getRecorderManager()

    this.recorderManager.onStart(() => {
      this.isRecording = true
      this.recordingTime = 0
      this.onStart()
      this._startTimer()
    })

    this.recorderManager.onStop((res) => {
      this.isRecording = false
      this._clearTimer()
      if (res.duration < 300) {
        wx.showToast({ title: '录音时间过短', icon: 'none' })
        this.onCancel()
        return
      }
      this.processAudio(res.tempFilePath)
    })

    this.recorderManager.onError((err) => {
      this.isRecording = false
      this._clearTimer()
      this.onError(err.errMsg || '录音失败')
    })
  }

  _startTimer() {
    this._clearTimer()
    this.timer = setInterval(() => {
      this.recordingTime++
      this.onRecording(this.recordingTime)
      if (this.recordingTime >= this.maxDuration) this.stop()
    }, 1000)
  }

  _clearTimer() {
    if (this.timer) { clearInterval(this.timer); this.timer = null }
  }

  start() {
    if (this.isLoading) return
    this.init()
    this.startRecording()
  }

  startRecording() {
    this.recordingTime = 0
    try {
      this.recorderManager.start({
        duration: this.maxDuration * 1000,
        sampleRate: 16000,
        numberOfChannels: 1,
        encodeBitRate: 48000,
        format: 'wav'
      })
    } catch (err) {
      this.onError('录音启动失败')
    }
  }

  stop() {
    if (this.isRecording && this.recorderManager) this.recorderManager.stop()
  }

  cancel() {
    this.isRecording = false
    this._clearTimer()
    if (this.recorderManager) { try { this.recorderManager.stop() } catch (e) {} }
    setTimeout(() => { this.onCancel() }, 100)
  }

  // ── 核心：音频处理 ──

  async processAudio(filePath) {
    this.isLoading = true
    this.onLoading(true)

    try {
      const token = wx.getStorageSync('access_token') || ''
      const fsm = wx.getFileSystemManager()

      const arrayBuffer = await new Promise((resolve, reject) => {
        fsm.readFile({ filePath, success: r => resolve(r.data), fail: reject })
      })

      const header = new Uint8Array(arrayBuffer.slice(0, 12))
      const isWAV = String.fromCharCode(...header.slice(0, 4)) === 'RIFF'
                 && String.fromCharCode(...header.slice(8, 12)) === 'WAVE'

      let wavBuffer

      if (isWAV) {
        // 真机：直接从录制的 WAV 中提取 PCM，重建标准 WAV（16kHz 16bit mono）
        wavBuffer = this._rebuildWAVFromWAV(arrayBuffer)
      } else {
        // WebM（开发者工具）：用 Web Audio API 解码，手动重采样到 16kHz，构建 WAV
        wavBuffer = await this._convertWebMtoWAV(arrayBuffer)
      }

      if (!wavBuffer || wavBuffer.byteLength < 100) {
        wx.showToast({ title: '音频处理失败', icon: 'none' })
        this.onError('音频处理失败')
        return
      }

      const tmpPath = `${wx.env.USER_DATA_PATH}/voice.wav`
      await new Promise((resolve, reject) => {
        fsm.writeFile({ filePath: tmpPath, data: wavBuffer, success: resolve, fail: reject })
      })

      const res = await new Promise((resolve, reject) => {
        wx.uploadFile({
          url: `${BASE_URL}/student/asr/recognize`,
          filePath: tmpPath,
          name: 'file',
          header: { 'Authorization': `Bearer ${token}` },
          success: r => { try { resolve(JSON.parse(r.data)) } catch (e) { resolve({}) } },
          fail: reject
        })
      })

      try { fsm.unlink({ filePath: tmpPath }) } catch (e) {}

      if (res.text !== undefined && res.text !== null && String(res.text).trim()) {
        this.onResult(res.text)
      } else {
        wx.showToast({ title: '未识别出文字，请重试', icon: 'none' })
        this.onError('未识别出文字')
      }
    } catch (err) {
      console.error('语音识别失败:', err)
      this.onError(err.errMsg || '语音识别失败')
      wx.showToast({ title: err.errMsg || '语音识别失败', icon: 'none' })
    } finally {
      this.isLoading = false
      this.onLoading(false)
    }
  }

  // ── WAV → 标准 WAV（真机：解析原始 WAV 采样率，提取 PCM，重建 16kHz WAV）──

  _rebuildWAVFromWAV(arrayBuffer) {
    const view = new DataView(arrayBuffer)

    // 解析原始 WAV 参数
    const origRate = view.getUint32(24, true)
    const origBits = view.getUint16(34, true)
    const origChannels = view.getUint16(22, true)

    // 找到 data chunk，提取原始 PCM
    let pos = 12
    let pcmData = null
    while (pos < arrayBuffer.byteLength - 8) {
      const id = String.fromCharCode(view.getUint8(pos), view.getUint8(pos+1), view.getUint8(pos+2), view.getUint8(pos+3))
      const size = view.getUint32(pos + 4, true)
      if (id === 'data') {
        pcmData = arrayBuffer.slice(pos + 8, pos + 8 + size)
        break
      }
      pos += 8 + size
    }

    if (!pcmData) return null

    // 如果已经是 16kHz 16bit mono，直接重建 WAV
    if (origRate === 16000 && origBits === 16 && origChannels === 1) {
      return this._buildWAV(new Int16Array(pcmData), 16000)
    }

    // 否则需要重采样（简单线性插值）
    const origData = origBits === 16 ? new Int16Array(pcmData) : new Int8Array(pcmData)
    const ratio = origRate / 16000
    const outLength = Math.ceil(origData.length / ratio / origChannels)
    const outData = new Int16Array(outLength)
    for (let i = 0; i < outLength; i++) {
      const srcIdx = Math.floor(i * ratio) * origChannels
      outData[i] = origData[srcIdx] || 0
    }
    return this._buildWAV(outData, 16000)
  }

  // ── WebM → WAV（对应前端 convertToPCM16k）──

  async _convertWebMtoWAV(arrayBuffer) {
    return new Promise((resolve, reject) => {
      try {
        const audioCtx = wx.createWebAudioContext()
        audioCtx.decodeAudioData(arrayBuffer).then(audioBuffer => {
          const targetRate = 16000
          const ratio = audioBuffer.sampleRate / targetRate
          const sourceData = audioBuffer.getChannelData(0)
          const outLength = Math.ceil(audioBuffer.duration * targetRate)
          const int16 = new Int16Array(outLength)
          for (let i = 0; i < outLength; i++) {
            const sample = sourceData[Math.floor(i * ratio)] || 0
            const s = Math.max(-1, Math.min(1, sample))
            int16[i] = s < 0 ? s * 0x8000 : s * 0x7FFF
          }
          audioCtx.close()
          resolve(this._buildWAV(int16, targetRate))
        }).catch(reject)
      } catch (err) { reject(err) }
    })
  }

  // ── 构建 WAV 文件（和前端 writeWavHeader 完全一致）──

  _buildWAV(int16Data, sampleRate) {
    const dataLength = int16Data.length
    const buf = new ArrayBuffer(44 + dataLength * 2)
    const v = new DataView(buf)
    const ws = (o, s) => { for (let i = 0; i < s.length; i++) v.setUint8(o + i, s.charCodeAt(i)) }

    ws(0, 'RIFF')
    v.setUint32(4, 36 + dataLength * 2, true)
    ws(8, 'WAVE')
    ws(12, 'fmt ')
    v.setUint32(16, 16, true)
    v.setUint16(20, 1, true)       // PCM
    v.setUint16(22, 1, true)       // mono
    v.setUint32(24, sampleRate, true)
    v.setUint32(28, sampleRate * 2, true)
    v.setUint16(32, 2, true)
    v.setUint16(34, 16, true)
    ws(36, 'data')
    v.setUint32(40, dataLength * 2, true)
    new Int16Array(buf, 44).set(int16Data)
    return buf
  }

  destroy() {
    this.cancel()
    this.recorderManager = null
  }
}

module.exports = { VoiceInput }
