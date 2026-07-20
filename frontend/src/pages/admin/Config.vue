<template>
  <div class="page-container">
    <el-row :gutter="24">
      <!-- 左列：系统配置 -->
      <el-col :xs="24" :lg="14">
        <!-- 基础配置 -->
        <el-card class="page-card" shadow="never">
          <template #header>
            <div class="card-header">
              <el-icon class="card-header__icon"><Setting /></el-icon>
              <h2 class="card-header__title">基础配置</h2>
            </div>
          </template>
          <el-form :label-width="110" label-position="left" class="config-form">
            <el-form-item label="应用名称">
              <el-input v-model="config.app_name" placeholder="应用名称" />
            </el-form-item>
            <el-form-item label="调试模式">
              <el-switch v-model="config.debug" active-text="开" inactive-text="关" />
            </el-form-item>
            <el-form-item label="后端主机">
              <el-input v-model="config.backend_host" placeholder="0.0.0.0" />
            </el-form-item>
            <el-form-item label="后端端口">
              <el-input-number v-model="config.backend_port" :min="1" :max="65535" />
            </el-form-item>
          </el-form>
        </el-card>

        <!-- 安全配置 -->
        <el-card class="page-card" shadow="never">
          <template #header>
            <div class="card-header">
              <el-icon class="card-header__icon"><Lock /></el-icon>
              <h2 class="card-header__title">安全配置</h2>
            </div>
          </template>
          <el-form :label-width="110" label-position="left" class="config-form">
            <el-form-item label="JWT 过期时间">
              <div class="inline-input">
                <el-input-number v-model="config.jwt_expire_minutes" :min="1" :max="1440" />
                <span class="inline-label">分钟</span>
              </div>
            </el-form-item>
            <el-form-item label="Secret Key">
              <el-input :model-value="config.secret_key" disabled />
            </el-form-item>
          </el-form>
        </el-card>

        <!-- 质量阈值 -->
        <el-card class="page-card" shadow="never">
          <template #header>
            <div class="card-header">
              <el-icon class="card-header__icon"><DataLine /></el-icon>
              <h2 class="card-header__title">质量阈值</h2>
              <el-tag size="small" type="info">低于阈值的资源不展示给学生</el-tag>
            </div>
          </template>
          <el-form :label-width="110" label-position="left" class="config-form">
            <el-form-item v-for="(label, key) in THRESHOLD_LABELS" :key="key" :label="label">
              <div class="threshold-row">
                <el-slider v-model="config.quality_thresholds[key]" :min="0" :max="100" :step="5" style="flex:1" />
                <span class="threshold-val">{{ config.quality_thresholds[key] || 60 }}</span>
              </div>
            </el-form-item>
          </el-form>
        </el-card>

        <!-- 资源生成 -->
        <el-card class="page-card" shadow="never">
          <template #header>
            <div class="card-header">
              <el-icon class="card-header__icon"><VideoPlay /></el-icon>
              <h2 class="card-header__title">资源生成</h2>
            </div>
          </template>
          <el-form :label-width="110" label-position="left" class="config-form">
            <el-form-item label="PPT 最大页数">
              <el-input-number v-model="config.ppt_video_max_pages" :min="1" :max="15" />
            </el-form-item>
            <el-form-item label="TTS 默认音色">
              <el-select v-model="config.tts_voice" style="width: 200px">
                <el-option v-for="v in TTS_VOICE_LIST" :key="v.id" :label="v.name" :value="v.id" />
              </el-select>
            </el-form-item>
          </el-form>
        </el-card>

        <!-- 保存按钮 -->
        <div style="text-align:center;margin-top:16px">
          <el-button type="primary" size="large" :loading="saving" @click="handleSave">
            <el-icon><Check /></el-icon> 保存全部配置
          </el-button>
          <el-button size="large" @click="fetchConfig">
            <el-icon><RefreshRight /></el-icon> 重置
          </el-button>
        </div>
      </el-col>

      <!-- 右列：监控 + 统计 -->
      <el-col :xs="24" :lg="10">
        <el-card class="page-card" shadow="never">
          <template #header>
            <div class="card-header">
              <div class="card-header__left">
                <el-icon class="card-header__icon"><Monitor /></el-icon>
                <h2 class="card-header__title">系统监控</h2>
              </div>
              <el-button size="small" @click="fetchMonitor" :loading="monitorLoading">
                <el-icon><RefreshRight /></el-icon> 刷新
              </el-button>
            </div>
          </template>
          <el-row :gutter="16">
            <el-col :span="12">
              <div class="monitor-item">
                <el-progress type="dashboard" :percentage="monitor.cpu_percent" :color="'#4F46E5'" :width="90" :stroke-width="10" />
                <div class="monitor-item__label">CPU 使用率</div>
              </div>
            </el-col>
            <el-col :span="12">
              <div class="monitor-item">
                <el-progress type="dashboard" :percentage="monitor.memory_percent" :color="'#10b981'" :width="90" :stroke-width="10" />
                <div class="monitor-item__label">内存使用率</div>
              </div>
            </el-col>
          </el-row>
          <el-divider />
          <el-row :gutter="16">
            <el-col :span="12">
              <div class="monitor-detail">
                <span class="monitor-detail__label">已用内存</span>
                <span class="monitor-detail__value">{{ monitor.memory_used_mb }} MB</span>
              </div>
            </el-col>
            <el-col :span="12">
              <div class="monitor-detail">
                <span class="monitor-detail__label">总内存</span>
                <span class="monitor-detail__value">{{ monitor.memory_total_mb }} MB</span>
              </div>
            </el-col>
          </el-row>
        </el-card>

        <el-card class="page-card" shadow="never">
          <template #header>
            <h2 class="card-header__title">系统统计</h2>
          </template>
          <el-row :gutter="16">
            <el-col :span="8">
              <div class="stat-mini">
                <div class="stat-mini__value">{{ stats.total_users }}</div>
                <div class="stat-mini__label">用户总数</div>
              </div>
            </el-col>
            <el-col :span="8">
              <div class="stat-mini">
                <div class="stat-mini__value">{{ stats.total_students }}</div>
                <div class="stat-mini__label">学生数</div>
              </div>
            </el-col>
            <el-col :span="8">
              <div class="stat-mini">
                <div class="stat-mini__value">{{ stats.total_teachers }}</div>
                <div class="stat-mini__label">教师数</div>
              </div>
            </el-col>
          </el-row>
          <el-divider />
          <el-row :gutter="16">
            <el-col :span="12">
              <div class="stat-mini">
                <div class="stat-mini__value">{{ stats.total_profiles }}</div>
                <div class="stat-mini__label">画像数</div>
              </div>
            </el-col>
            <el-col :span="12">
              <div class="stat-mini">
                <div class="stat-mini__value">{{ stats.total_learning_paths }}</div>
                <div class="stat-mini__label">学习路径数</div>
              </div>
            </el-col>
          </el-row>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { adminAPI } from '@/api'
import { Setting, Monitor, RefreshRight, Check, Lock, DataLine, VideoPlay } from '@element-plus/icons-vue'

const THRESHOLD_LABELS: Record<string, string> = {
  document: '学习文档', mindmap: '思维导图', code: '代码示例',
  question: '练习题目', reading_material: '拓展阅读', glossary: '术语词汇',
  knowledge_link: '知识关联', summary: '学习总结', ppt_video: 'PPT视频',
}

const TTS_VOICE_LIST = [
  { id: 'x4_xiaoyan', name: '讯飞小燕（女）' },
  { id: 'x4_yezi', name: '讯飞小露（女）' },
  { id: 'aisjiuxu', name: '讯飞许久（男）' },
  { id: 'aisjinger', name: '讯飞小婧（女）' },
  { id: 'aisbabyxu', name: '讯飞许小宝（男）' },
]

const saving = ref(false)
const monitorLoading = ref(false)

const config = reactive({
  app_name: '',
  debug: false,
  secret_key: '',
  jwt_expire_minutes: 1440,
  backend_host: '0.0.0.0',
  backend_port: 8000,
  quality_thresholds: {} as Record<string, number>,
  ppt_video_max_pages: 10,
  tts_voice: 'x4_yezi',
})

const monitor = reactive({
  cpu_percent: 0, memory_percent: 0,
  memory_used_mb: 0, memory_total_mb: 0, disk_percent: 0,
})

const stats = reactive({
  total_users: 0, total_students: 0, total_teachers: 0,
  total_profiles: 0, total_learning_paths: 0,
})

const fetchConfig = async () => {
  try {
    const res: any = await adminAPI.getConfig()
    Object.assign(config, res)
    // 确保 quality_thresholds 有默认值
    for (const key of Object.keys(THRESHOLD_LABELS)) {
      if (!(key in config.quality_thresholds)) config.quality_thresholds[key] = 60
    }
  } catch { ElMessage.error('获取配置失败') }
}

const handleSave = async () => {
  saving.value = true
  try {
    await adminAPI.updateConfig({
      app_name: config.app_name,
      debug: config.debug,
      jwt_expire_minutes: config.jwt_expire_minutes,
      backend_host: config.backend_host,
      backend_port: config.backend_port,
      quality_thresholds: config.quality_thresholds,
      ppt_video_max_pages: config.ppt_video_max_pages,
      tts_voice: config.tts_voice,
    })
    ElMessage.success('配置已保存')
  } catch { ElMessage.error('保存失败') }
  finally { saving.value = false }
}

const fetchMonitor = async () => {
  monitorLoading.value = true
  try { Object.assign(monitor, await adminAPI.getMonitoring()) }
  finally { monitorLoading.value = false }
}

const fetchStats = async () => {
  try { Object.assign(stats, await adminAPI.getStats()) } catch {}
}

onMounted(() => { fetchConfig(); fetchMonitor(); fetchStats() })
</script>

<style scoped>
.page-container { padding: 24px; background: var(--color-bg-page, #F4F5F7); min-height: 100%; }
.page-card { border-radius: 12px; box-shadow: 0 2px 12px rgba(0, 0, 0, 0.06); margin-bottom: 20px; }
.card-header { display: flex; justify-content: space-between; align-items: center; }
.card-header__left { display: flex; align-items: center; gap: 8px; }
.card-header__icon { font-size: 20px; color: #4F46E5; }
.card-header__title { font-size: 16px; font-weight: 600; margin: 0; color: #1a1a2e; }
.config-form { max-width: 100%; }
.inline-input { display: flex; align-items: center; gap: 8px; }
.inline-label { color: #374151; font-size: 13px; }
.threshold-row { display: flex; align-items: center; gap: 12px; width: 100%; }
.threshold-val { min-width: 32px; text-align: right; font-weight: 600; color: #4F46E5; font-size: 14px; }
.monitor-item { display: flex; flex-direction: column; align-items: center; padding: 12px 0; }
.monitor-item__label { margin-top: 8px; font-size: 13px; color: #374151; font-weight: 500; }
.monitor-detail { display: flex; justify-content: space-between; align-items: center; padding: 8px 16px; background: #e5e7eb; border-radius: 8px; }
.monitor-detail__label { font-size: 13px; color: #374151; }
.monitor-detail__value { font-size: 14px; font-weight: 600; color: #374151; }
.stat-mini { text-align: center; padding: 12px 0; }
.stat-mini__value { font-size: 22px; font-weight: 700; color: #1a1a2e; }
.stat-mini__label { font-size: 12px; color: #6b7280; margin-top: 4px; }
</style>
