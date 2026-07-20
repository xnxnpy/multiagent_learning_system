<template>
  <div class="page-container">
    <!-- 统计卡片 -->
    <el-row :gutter="20" class="stats-row">
      <el-col :xs="12" :sm="6">
        <el-card class="stat-card stat-card--primary" shadow="hover">
          <div class="stat-card__icon"><el-icon :size="28"><User /></el-icon></div>
          <div class="stat-card__info">
            <div class="stat-card__value">{{ stats.total_students }}</div>
            <div class="stat-card__label">学生总数</div>
          </div>
        </el-card>
      </el-col>
      <el-col :xs="12" :sm="6">
        <el-card class="stat-card stat-card--success" shadow="hover">
          <div class="stat-card__icon"><el-icon :size="28"><UserFilled /></el-icon></div>
          <div class="stat-card__info">
            <div class="stat-card__value">{{ stats.active_students }}</div>
            <div class="stat-card__label">活跃学生</div>
          </div>
        </el-card>
      </el-col>
      <el-col :xs="12" :sm="6">
        <el-card class="stat-card stat-card--warning" shadow="hover">
          <div class="stat-card__icon"><el-icon :size="28"><TrendCharts /></el-icon></div>
          <div class="stat-card__info">
            <div class="stat-card__value">{{ (stats.average_accuracy * 100).toFixed(1) }}%</div>
            <div class="stat-card__label">平均正确率</div>
          </div>
        </el-card>
      </el-col>
      <el-col :xs="12" :sm="6">
        <el-card class="stat-card stat-card--danger" shadow="hover">
          <div class="stat-card__icon"><el-icon :size="28"><Document /></el-icon></div>
          <div class="stat-card__info">
            <div class="stat-card__value">{{ stats.total_learning_records }}</div>
            <div class="stat-card__label">学习记录数</div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <el-row :gutter="24">
      <!-- 学生进度表格 -->
      <el-col :xs="24" :lg="16">
        <el-card class="page-card" shadow="never">
          <template #header>
            <div class="card-header">
              <h2 class="card-header__title">学生学习进度</h2>
              <el-button @click="refreshStats" :loading="loading">
                <el-icon><RefreshRight /></el-icon> 刷新
              </el-button>
            </div>
          </template>
          <el-table :data="stats.student_progress" v-loading="loading" stripe class="data-table">
            <el-table-column label="学生姓名" prop="student_name" width="130">
              <template #default="{ row }">
                <span class="link-text" @click="showStudentDetail(row)">{{ row.student_name }}</span>
              </template>
            </el-table-column>
            <el-table-column label="学习记录" prop="total_learning_records" width="90" align="center" />
            <el-table-column label="正确率" width="200">
              <template #default="{ row }">
                <el-progress
                  :percentage="Number((row.accuracy * 100).toFixed(1))"
                  :status="getAccuracyStatus(row.accuracy)"
                  :stroke-width="10"
                  striped
                />
              </template>
            </el-table-column>
            <el-table-column label="平均分" width="100" align="center">
              <template #default="{ row }">
                <span class="score-text">{{ row.average_score.toFixed(1) }}</span>
              </template>
            </el-table-column>
            <el-table-column label="最后活动" width="170">
              <template #default="{ row }">
                <span class="time-text">{{ formatDate(row.last_activity) }}</span>
              </template>
            </el-table-column>
            <el-table-column label="操作" width="100" fixed="right">
              <template #default="{ row }">
                <el-button type="primary" link size="small" @click="adjustPath(row)">
                  调整路径
                </el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-col>

      <!-- 侧边操作 -->
      <el-col :xs="24" :lg="8">
        <el-card class="page-card" shadow="never">
          <template #header>
            <h2 class="card-header__title">快捷操作</h2>
          </template>
          <div class="action-buttons">
            <el-button class="action-btn" type="primary" plain @click="exportAllReport">
              <el-icon><Download /></el-icon> 导出班级报表 (CSV)
            </el-button>
            <el-button class="action-btn" plain @click="refreshStats">
              <el-icon><RefreshRight /></el-icon> 刷新统计数据
            </el-button>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 调整路径对话框 -->
    <el-dialog
      v-model="pathModalVisible"
      title="调整学习路径"
      width="700px"
      class="custom-dialog"
    >
      <el-form :label-width="100">
        <el-form-item label="学生">
          <span class="student-name">{{ currentStudent?.student_name }}</span>
        </el-form-item>

        <el-divider content-position="left">学习阶段</el-divider>

        <div v-for="(stage, idx) in newStages" :key="idx" class="stage-card">
          <div class="stage-card__header">
            <span class="stage-card__num">阶段 {{ stage.stage_id }}</span>
            <el-button type="danger" link size="small" @click="removeStage(idx)" :disabled="newStages.length <= 1">
              <el-icon><Delete /></el-icon> 删除
            </el-button>
          </div>
          <el-form-item label="阶段ID">
            <el-input-number v-model="stage.stage_id" :min="1" :max="20" />
          </el-form-item>
          <el-form-item label="阶段标题">
            <el-input v-model="stage.title" placeholder="例如：Python基础入门" />
          </el-form-item>
          <el-form-item label="阶段描述">
            <el-input v-model="stage.description" type="textarea" :rows="2" placeholder="描述本阶段的学习内容和目标" />
          </el-form-item>
          <el-form-item label="知识点">
            <el-input v-model="stage.knowledge_points_str" placeholder="多个知识点用逗号分隔，例如：变量, 数据类型, 控制流" />
          </el-form-item>
          <el-form-item label="预计时长">
            <el-input-number v-model="stage.estimated_hours" :min="1" :max="200" />
            <span style="margin-left: 8px; color: #909399;">小时</span>
          </el-form-item>
        </div>

        <el-button type="primary" link @click="addStage" style="margin-top: 8px;">
          <el-icon><Plus /></el-icon> 添加阶段
        </el-button>

        <el-form-item label="调整原因" style="margin-top: 20px;">
          <el-input v-model="adjustReason" placeholder="请输入调整原因" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="pathModalVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitLoading" @click="handlePathSubmit">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, h } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { teacherAPI } from '@/api'
import { User, UserFilled, Document, Download, RefreshRight, TrendCharts, Delete, Plus } from '@element-plus/icons-vue'

interface StudentProgress {
  student_id: string
  student_name: string
  total_learning_records: number
  accuracy: number
  average_score: number
  last_activity: string
  current_path_stage?: string
}

interface Stats {
  total_students: number
  active_students: number
  average_accuracy: number
  total_learning_records: number
  student_progress: StudentProgress[]
}

const loading = ref(false)
const submitLoading = ref(false)
const pathModalVisible = ref(false)
const currentStudent = ref<StudentProgress | null>(null)
const newStages = ref<Array<{title: string; description: string; knowledge_points_str: string; estimated_hours: number}>>([])
const adjustReason = ref('')

const stats = reactive<Stats>({
  total_students: 0,
  active_students: 0,
  average_accuracy: 0,
  total_learning_records: 0,
  student_progress: []
})

const getAccuracyStatus = (accuracy: number): '' | 'success' | 'warning' | 'exception' => {
  if (accuracy >= 0.8) return 'success'
  if (accuracy >= 0.6) return 'warning'
  return 'exception'
}

const formatDate = (dateStr: string): string => {
  if (!dateStr) return '-'
  return new Date(dateStr).toLocaleString('zh-CN')
}

const fetchStats = async () => {
  loading.value = true
  try {
    const response = await teacherAPI.getClassStats()
    Object.assign(stats, response)
  } catch (error) {
    ElMessage.error('获取统计数据失败')
  } finally {
    loading.value = false
  }
}

const refreshStats = () => {
  fetchStats()
  ElMessage.success('统计数据已刷新')
}

const showStudentDetail = (student: StudentProgress) => {
  ElMessageBox({
    title: student.student_name + ' 的学习详情',
    message: h('div', { style: 'line-height: 2' }, [
      h('p', {}, `学习记录数: ${student.total_learning_records}`),
      h('p', {}, `正确率: ${(student.accuracy * 100).toFixed(1)}%`),
      h('p', {}, `平均分: ${student.average_score.toFixed(1)}`),
      h('p', {}, `当前阶段: ${student.current_path_stage || '未开始'}`)
    ]),
    confirmButtonText: '确定'
  })
}

const adjustPath = (student: StudentProgress) => {
  currentStudent.value = student
  newStages.value = [
    { stage_id: 1, title: '', description: '', knowledge_points_str: '', estimated_hours: 20 }
  ]
  adjustReason.value = ''
  pathModalVisible.value = true
}

const addStage = () => {
  const maxId = Math.max(0, ...newStages.value.map(s => s.stage_id))
  newStages.value.push({ stage_id: maxId + 1, title: '', description: '', knowledge_points_str: '', estimated_hours: 20 })
}

const removeStage = (idx: number) => {
  newStages.value.splice(idx, 1)
}

const handlePathSubmit = async () => {
  try {
    submitLoading.value = true

    // 校验
    for (const stage of newStages.value) {
      if (!stage.title.trim()) {
        ElMessage.error('请填写阶段标题')
        submitLoading.value = false
        return
      }
    }

    const newStagesData = newStages.value.map(s => ({
      stage_id: s.stage_id,
      title: s.title,
      description: s.description,
      knowledge_points: s.knowledge_points_str ? s.knowledge_points_str.split(/[,，]/).map((k: string) => k.trim()).filter(Boolean) : [],
      estimated_hours: s.estimated_hours,
      recommended_resource_types: ['document', 'question', 'code'],
    }))

    if (currentStudent.value) {
      await teacherAPI.adjustStudentPath(currentStudent.value.student_id, {
        new_stages: newStagesData,
        reason: adjustReason.value
      })
    }

    ElMessage.success('学习路径已调整')
    pathModalVisible.value = false
    fetchStats()
  } catch (error) {
    ElMessage.error('调整失败')
  } finally {
    submitLoading.value = false
  }
}

const exportAllReport = async () => {
  try {
    const response: any = await teacherAPI.exportClassReport()
    const blob = new Blob([response], { type: 'text/csv' })
    const url = window.URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = `class_report_${new Date().toISOString().split('T')[0]}.csv`
    link.click()
    window.URL.revokeObjectURL(url)
    ElMessage.success('报表导出成功')
  } catch (error) {
    ElMessage.error('导出失败')
  }
}

onMounted(() => {
  fetchStats()
})
</script>

<style scoped>
.page-container {
  padding: 24px;
  background: var(--color-bg-page, #F4F5F7);
  min-height: 100%;
}

.stats-row {
  margin-bottom: 24px;
}

.stat-card {
  border-radius: 12px;
  border: none;
  transition: transform 0.2s ease;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.06);
}

.stat-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.1);
}

.stat-card :deep(.el-card__body) {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 20px;
}

.stat-card__icon {
  width: 56px;
  height: 56px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.stat-card--primary .stat-card__icon {
  background: rgba(79, 70, 229, 0.1);
  color: #4F46E5;
}

.stat-card--success .stat-card__icon {
  background: rgba(16, 185, 129, 0.1);
  color: #10b981;
}

.stat-card--warning .stat-card__icon {
  background: rgba(245, 158, 11, 0.1);
  color: #f59e0b;
}

.stat-card--danger .stat-card__icon {
  background: rgba(239, 68, 68, 0.1);
  color: #ef4444;
}

.stat-card__value {
  font-size: 28px;
  font-weight: 700;
  color: #1a1a2e;
  line-height: 1.2;
}

.stat-card__label {
  font-size: 12px;
  color: #6b7280;
  margin-top: 2px;
}

.page-card {
  border-radius: 12px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.06);
  margin-bottom: 24px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.card-header__title {
  font-size: 18px;
  font-weight: 600;
  margin: 0;
  color: #1a1a2e;
}

.link-text {
  color: #4F46E5;
  cursor: pointer;
  font-weight: 500;
}

.link-text:hover {
  text-decoration: underline;
}

.score-text {
  font-weight: 600;
  color: #374151;
}

.time-text {
  color: #6b7280;
  font-size: 12px;
}

.student-name {
  font-weight: 600;
  color: #1a1a2e;
}

.action-buttons {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.action-btn {
  width: 100%;
  height: 44px;
  font-size: 14px;
  border-radius: 8px;
}

:deep(.el-table) {
  border-radius: 8px;
  overflow: hidden;
}

:deep(.el-table th.el-table__cell) {
  background: var(--color-bg-page, #F4F5F7);
  color: #374151;
  font-weight: 600;
  font-size: 12px;
}

:deep(.el-dialog) {
  border-radius: 12px;
}

.stage-card {
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  padding: 16px;
  margin-bottom: 12px;
  background: #fafbfc;
}

.stage-card__header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.stage-card__num {
  font-weight: 600;
  font-size: 14px;
  color: #374151;
}
</style>
