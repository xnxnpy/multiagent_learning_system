const { request } = require('../../utils/request')
const { API, replaceParams } = require('../../utils/api')

Page({
  data: {
    providers: [],
    agentModels: [],
    imageModels: [],
    ttsVoices: [],
    activeTab: 0,
    tabs: ['模型提供者', 'Agent模型', '图片模型', 'TTS音色'],
    isLoading: false
  },

  onLoad() {
    this.loadAll()
  },

  async loadAll() {
    this.setData({ isLoading: true })
    await Promise.all([
      this.loadProviders(),
      this.loadAgentModels(),
      this.loadImageModels(),
      this.loadTtsVoices()
    ])
    this.setData({ isLoading: false })
  },

  async loadProviders() {
    try {
      const result = await request({ url: API.ADMIN.MODEL_PROVIDERS, method: 'GET' })
      const providers = (result.items || []).map(p => ({
        id: p.id, name: p.name || '', provider_type: p.provider_type || '',
        api_url: p.api_url || '', is_active: p.is_active !== false,
        config: p.config || {},
        created_at: p.created_at ? new Date(p.created_at).toLocaleString() : ''
      }))
      this.setData({ providers })
    } catch (err) {
      console.error('加载提供者失败:', err)
    }
  },

  async loadAgentModels() {
    try {
      const agents = ['profile', 'tutor', 'learning_path', 'document', 'question', 'code', 'mindmap', 'evaluation', 'tutor_stream']
      const models = []
      for (const agent of agents) {
        try {
          const res = await request({ url: replaceParams(API.ADMIN.AGENT_MODEL, { agent_name: agent }), method: 'GET' })
          models.push({ agent, model: res.model || res.model_name || '-', provider: res.provider || '-' })
        } catch (e) {
          models.push({ agent, model: '-', provider: '-' })
        }
      }
      this.setData({ agentModels: models })
    } catch (err) {
      console.error('加载Agent模型失败:', err)
    }
  },

  async loadImageModels() {
    try {
      const tasks = ['mindmap', 'ppt_cover', 'illustration']
      const models = []
      for (const task of tasks) {
        try {
          const res = await request({ url: replaceParams(API.ADMIN.IMAGE_MODEL, { task_name: task }), method: 'GET' })
          models.push({ task, model: res.model || res.model_name || '-', provider: res.provider || '-' })
        } catch (e) {
          models.push({ task, model: '-', provider: '-' })
        }
      }
      this.setData({ imageModels: models })
    } catch (err) {
      console.error('加载图片模型失败:', err)
    }
  },

  async loadTtsVoices() {
    try {
      const res = await request({ url: API.ADMIN.TTS_VOICES, method: 'GET' })
      this.setData({ ttsVoices: res.items || res.voices || [] })
    } catch (err) {
      console.error('加载TTS音色失败:', err)
    }
  },

  switchTab(e) {
    this.setData({ activeTab: parseInt(e.currentTarget.dataset.index) })
  },

  async addProvider() {
    wx.showModal({
      title: '添加提供者', editable: true, placeholderText: '请输入提供者名称',
      success: async (res) => {
        if (res.confirm && res.content) {
          try {
            await request({ url: API.ADMIN.MODEL_PROVIDERS, method: 'POST', data: { name: res.content, provider_type: 'openai', api_url: '' } })
            wx.showToast({ title: '添加成功', icon: 'success' })
            await this.loadProviders()
          } catch (err) {
            wx.showToast({ title: '添加失败', icon: 'none' })
          }
        }
      }
    })
  },

  async deleteProvider(e) {
    const id = e.currentTarget.dataset.id
    wx.showModal({
      title: '确认删除', content: '确定要删除该提供者吗？',
      success: async (res) => {
        if (res.confirm) {
          try {
            await request({ url: `${API.ADMIN.MODEL_PROVIDERS}/${id}`, method: 'DELETE' })
            wx.showToast({ title: '删除成功', icon: 'success' })
            await this.loadProviders()
          } catch (err) {
            wx.showToast({ title: '删除失败', icon: 'none' })
          }
        }
      }
    })
  },

  async toggleProvider(e) {
    const id = e.currentTarget.dataset.id
    const active = e.currentTarget.dataset.active
    try {
      await request({ url: `${API.ADMIN.MODEL_PROVIDERS}/${id}`, method: 'PUT', data: { is_active: !active } })
      wx.showToast({ title: active ? '已禁用' : '已启用', icon: 'success' })
      await this.loadProviders()
    } catch (err) {
      wx.showToast({ title: '操作失败', icon: 'none' })
    }
  },

  goBack() {
    wx.navigateBack()
  }
})
