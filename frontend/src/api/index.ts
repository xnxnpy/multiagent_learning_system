import request from '@/utils/axios'
import type { LoginRequest, LoginResponse } from '@/types'

export const authAPI = {
  login: (data: LoginRequest) => {
    return request.post<any, LoginResponse>('/v1/auth/login', data)
  },

  register: (data: {
    username: string
    password: string
    email?: string
    real_name?: string
    role: string
  }) => {
    return request.post('/v1/auth/register', data)
  },

  getCurrentUser: () => {
    return request.get('/v1/auth/me')
  },

  updateProfile: (data: any) => {
    return request.put('/v1/auth/me', data)
  },

  changePassword: (data: { old_password: string; new_password: string }) => {
    return request.post('/v1/auth/change-password', data)
  }
}

export const adminAPI = {
  getUsers: (params?: { page?: number; page_size?: number; search?: string }) => {
    return request.get('/v1/admin/users', { params })
  },

  getUser: (id: number) => {
    return request.get(`/v1/admin/users/${id}`)
  },

  createUser: (data: any) => {
    return request.post('/v1/admin/users', data)
  },

  updateUser: (id: number, data: any) => {
    return request.put(`/v1/admin/users/${id}`, data)
  },

  deleteUser: (id: number) => {
    return request.delete(`/v1/admin/users/${id}`)
  },

  getConfig: () => {
    return request.get('/v1/admin/config')
  },

  updateConfig: (data: any) => {
    return request.put('/v1/admin/config', data)
  },

  getMonitoring: () => {
    return request.get('/v1/admin/monitoring')
  },

  getStats: () => {
    return request.get('/v1/admin/stats')
  },

  getLogs: (params?: { level?: string; limit?: number }) => {
    return request.get('/v1/admin/logs', { params })
  },

  getContentReview: (params?: any) => {
    return request.get('/v1/admin/content-review', { params })
  },

  reviewContent: (id: number, data: { action: string; comment?: string }) => {
    return request.put(`/v1/admin/content-review/${id}/action`, data)
  },

  getContentSecurity: () => {
    return request.get('/v1/admin/content-security')
  },

  updateContentSecurity: (data: { enabled: boolean }) => {
    return request.put('/v1/admin/content-security', data)
  },

  addSecurityWords: (data: { category: string; words: string[] }) => {
    return request.post('/v1/admin/content-security/words', data)
  },

  deleteSecurityWords: (data: { category: string; word: string }) => {
    return request.delete('/v1/admin/content-security/words', { data })
  },

  getSecurityLogs: (params?: { page?: number; page_size?: number }) => {
    return request.get('/v1/admin/content-security/logs', { params })
  },

  // 数据备份维护
  getSystemStats: () => {
    return request.get('/v1/admin/system/stats')
  },

  createBackup: () => {
    return request.post('/v1/admin/backup')
  },

  getBackups: () => {
    return request.get('/v1/admin/backups')
  },

  restoreBackup: (backupName: string) => {
    return request.post('/v1/admin/restore', { backup_name: backupName })
  },

  clearCache: (target: string) => {
    return request.post('/v1/admin/cache/clear', { target })
  },

  cleanLogs: (days: number) => {
    return request.delete('/v1/admin/logs/clean', { params: { days } })
  },

  deleteBackup: (backupName: string) => {
    return request.delete(`/v1/admin/backups/${encodeURIComponent(backupName)}`)
  },
}

export const studentAPI = {
  getProfile: () => {
    return request.get('/v1/student/profile')
  },

  getLearningPath: () => {
    return request.get('/v1/student/learning-path')
  },

  generateLearningPath: () => {
    return request.post('/v1/student/learning-path/generate')
  },

  startLearn: () => {
    return request.post('/v1/student/learn/start')
  },

  generateStageResources: (data: { stage_id: number; profile_id?: number }) => {
    // Supervisor 学习环：同步等待生成完成（可能数分钟）
    return request.post('/v1/student/learn/stage/generate', data, { timeout: 600000 })
  },

  getStageResources: (stageId: number) => {
    return request.get(`/v1/student/learn/stage/resources/${stageId}`)
  },

  // ── 题库与错题本 ──
  getQuestionBank: (params?: { stage_id?: number; knowledge_point?: string; status?: string; page?: number; page_size?: number }) => {
    return request.get('/v1/question-bank', { params })
  },

  getWrongBook: (params?: { page?: number; page_size?: number }) => {
    return request.get('/v1/question-bank/wrong-book', { params })
  },

  getWrongBookStats: () => {
    return request.get('/v1/question-bank/wrong-book/stats')
  },

  removeFromWrongBook: (questionUid: string) => {
    return request.post(`/v1/question-bank/wrong-book/${questionUid}/remove`)
  },

  submitAnswer: (data: { question_id: string; answer: string }) => {
    return request.post('/v1/student/question/submit', data)
  },

  runCode: (data: { code: string; timeout?: number }) => {
    return request.post('/v1/student/code/run', data)
  },

  getReport: () => {
    return request.get('/v1/student/evaluation/report')
  },

  regenerateResource: (resourceType: string, stageId: number) => {
    return request.post(`/v1/student/resources/${resourceType}/regenerate`, { stage_id: stageId }, { timeout: 300000 })
  },

  trackEvent: (data: {
    event_type: string
    resource_type?: string
    stage_id?: number
    metadata?: Record<string, any>
    duration_seconds?: number
  }) => {
    return request.post('/v1/student/track/event', data)
  },

  getNotifications: () => {
    return request.get('/v1/notifications')
  },

  generateKnowledgeGraph: (data: { topic: string; force?: boolean }) => {
    return request.post('/v1/student/knowledge-graph/generate', data)
  },

  recognizeSpeech: (formData: FormData) => {
    return request.post('/v1/student/asr/recognize', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
      timeout: 30000,
    })
  },

  recognizeImage: (formData: FormData) => {
    return request.post('/v1/student/ocr/recognize', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
      timeout: 30000,
    })
  },

  // 多画像管理
  getProfiles: () => {
    return request.get('/v1/student/profiles')
  },

  createProfile: (data: { profile_name: string }) => {
    return request.post('/v1/student/profiles', data)
  },

  updateProfile: (id: number, data: {
    profile_name?: string
    major?: string
    grade?: string
    goal?: string
    learning_style?: string
    interests?: string[]
    coding_ability?: string
  }) => {
    return request.put(`/v1/student/profiles/${id}`, data)
  },

  activateProfile: (id: number) => {
    return request.post(`/v1/student/profiles/${id}/activate`)
  },

  archiveProfile: (id: number) => {
    return request.post(`/v1/student/profiles/${id}/archive`)
  },

  restoreProfile: (id: number) => {
    return request.post(`/v1/student/profiles/${id}/restore`)
  },

  getProfileChatHistory: (profileId: number) => {
    return request.get(`/v1/student/profiles/${profileId}/chat-history`)
  },
}

export const teacherAPI = {
  getCourses: (params?: { page?: number; page_size?: number; search?: string }) => {
    return request.get('/v1/teacher/courses', { params })
  },

  getCourse: (id: number) => {
    return request.get(`/v1/teacher/courses/${id}`)
  },

  createCourse: (data: any) => {
    return request.post('/v1/teacher/courses', data)
  },

  updateCourse: (id: number, data: any) => {
    return request.put(`/v1/teacher/courses/${id}`, data)
  },

  deleteCourse: (id: number) => {
    return request.delete(`/v1/teacher/courses/${id}`)
  },

  exportCourseReport: (id: number) => {
    return request.get(`/v1/teacher/courses/${id}/export`, { responseType: 'blob' })
  },

  getResources: () => {
    return request.get('/v1/teacher/resources')
  },

  getPendingResources: (params?: any) => {
    return request.get('/v1/teacher/resources', { params })
  },

  reviewResource: (id: number, data: { action?: string; approved?: boolean; comment?: string; feedback?: string }) => {
    return request.put(`/v1/teacher/resources/${id}/review`, data)
  },

  uploadKnowledge: (formData: FormData) => {
    return request.post('/v1/teacher/knowledge/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
      timeout: 300000
    })
  },

  getKnowledgeDocuments: (params?: { page?: number; page_size?: number }) => {
    return request.get('/v1/teacher/knowledge/documents', { params })
  },

  getKnowledgeStats: () => {
    return request.get('/v1/teacher/knowledge/stats')
  },

  clearKnowledge: () => {
    return request.delete('/v1/teacher/knowledge')
  },

  generateKnowledgeGraph: () => {
    return request.post('/v1/teacher/knowledge/graph/generate')
  },

  getKnowledgeGraph: () => {
    return request.get('/v1/teacher/knowledge/graph')
  },

  getAnalytics: () => {
    return request.get('/v1/teacher/analytics')
  },

  getClassStats: () => {
    return request.get('/v1/teacher/analytics/class-stats')
  },

  exportClassReport: () => {
    return request.get('/v1/teacher/analytics/export', { responseType: 'blob' })
  },

  getStudentProgress: (studentId?: number) => {
    return request.get('/v1/teacher/students/progress', { params: { student_id: studentId } })
  },

  adjustStudentPath: (studentId: number | string, data: any) => {
    return request.post(`/v1/teacher/students/${studentId}/adjust-path`, data)
  },

  getAllStudentResources: () => {
    return request.get('/v1/teacher/students/resources')
  },

  regenerateStudentResource: (studentId: number, resourceType: string, data: { stage_id: number }) => {
    return request.post(`/v1/teacher/students/${studentId}/resources/${resourceType}/regenerate`, data)
  },

  reevaluateStudentResource: (studentId: number, resourceType: string, data: { stage_id: number }) => {
    return request.post(`/v1/teacher/students/${studentId}/resources/${resourceType}/reevaluate`, data)
  },

  // 作业管理
  getAssignments: (params?: { page?: number; page_size?: number; status?: string }) => {
    return request.get('/v1/teacher/assignments', { params })
  },

  getAssignment: (id: number) => {
    return request.get(`/v1/teacher/assignments/${id}`)
  },

  createAssignment: (data: { title: string; description: string; due_date?: string; target_students?: number[] }) => {
    return request.post('/v1/teacher/assignments', data)
  },

  updateAssignment: (id: number, data: any) => {
    return request.put(`/v1/teacher/assignments/${id}`, data)
  },

  deleteAssignment: (id: number) => {
    return request.delete(`/v1/teacher/assignments/${id}`)
  },

  assignStudents: (id: number, student_ids: number[]) => {
    return request.put(`/v1/teacher/assignments/${id}/assign`, { student_ids })
  },

  getAssignmentSubmissions: (id: number) => {
    return request.get(`/v1/teacher/assignments/${id}/submissions`)
  },
}

export const tutorAPI = {
  getSessions: () => {
    return request.get('/v1/tutor/sessions')
  },

  getHistory: (sessionId: string) => {
    return request.get(`/v1/tutor/history/${sessionId}`)
  },

  deleteSession: (sessionId: string) => {
    return request.delete(`/v1/tutor/session/${sessionId}`)
  },

  createSession: () => {
    return request.post('/v1/tutor/sessions')
  },
}
