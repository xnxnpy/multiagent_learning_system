const API = {
  AUTH: {
    LOGIN: '/auth/login',
    REGISTER: '/auth/register',
    ME: '/auth/me',
    UPDATE_ME: '/auth/me',
    CHANGE_PASSWORD: '/auth/change-password'
  },
  STUDENT: {
    PROFILE: '/student/profile',
    PROFILES: '/student/profiles',
    PROFILE_CHAT_HISTORY: '/student/chat/history',
    PROFILE_CHAT_MESSAGE: '/student/chat/message',
    CLEAR_CHAT: '/student/chat/history',
    INIT_STATUS: '/student/init-status',
    LEARNING_PATH: '/student/learning-path',
    GENERATE_PATH: '/student/learning-path/generate',
    RESOURCES: '/student/resources',
    STAGE_RESOURCES: '/student/learn/stage/resources/{stage_id}',
    KNOWLEDGE_GRAPH: '/student/knowledge-graph',
    GENERATE_KNOWLEDGE_GRAPH: '/student/knowledge-graph/generate',
    COMPLETE_STAGE: '/student/learn/stage/complete',
    REGENERATE_RESOURCE: '/student/resources/{resource_type}/regenerate',
    GENERATE_STAGE_RESOURCES: '/student/learn/stage/generate',
    QUESTION_SUBMIT: '/student/question/submit',
    QUESTION_ANSWERS: '/student/question/answers',
    CODE_RUN: '/student/code/run',
    EVALUATION_RUN: '/student/evaluation/run',
    EVALUATION_REPORT: '/student/evaluation/report',
    LEARN_START: '/student/learn/start',
    LEARN_STATE: '/student/learn/state/{session_id}',
    WORKFLOW_WS: '/student/ws/workflow',
    PROGRESS_SUMMARY: '/student/progress/summary',
    TUTOR_CHATS: '/student/tutor-chats',
    ASSIGNMENTS: '/student/assignments',
    ASSIGNMENT_SUBMIT: '/student/assignments/{assignment_id}/submit',
    ASSIGNMENT_SUBMISSION: '/student/assignments/{assignment_id}/submission',
    TRACK_EVENT: '/student/track/event'
  },
  NOTIFICATION: {
    LIST: '/notifications',
    UNREAD_COUNT: '/notifications/unread-count',
    MARK_READ: '/notifications/mark-read/{notification_id}',
    MARK_ALL_READ: '/notifications/mark-all-read',
    DELETE: '/notifications/{notification_id}',
    CLEAR: '/notifications/clear'
  },
  TUTOR: {
    WS_CHAT: '/tutor/ws/chat',
    SESSIONS: '/tutor/sessions',
    CREATE_SESSION: '/tutor/sessions',
    CHAT_HISTORY: '/tutor/history/{session_id}',
    CLEAR_SESSION: '/tutor/session/{session_id}',
    WS_STATUS: '/tutor/ws/status',
    DELETE_SESSION: '/tutor/session/{session_id}'
  },
  TEACHER: {
    COURSES: '/teacher/courses',
    COURSE: '/teacher/courses/{course_id}',
    COURSE_EXPORT: '/teacher/courses/{course_id}/export',
    KNOWLEDGE_UPLOAD: '/teacher/knowledge/upload',
    KNOWLEDGE_DOCUMENTS: '/teacher/knowledge/documents',
    KNOWLEDGE_CLEAR: '/teacher/knowledge/clear',
    KNOWLEDGE_STATS: '/teacher/knowledge/stats',
    KNOWLEDGE_GRAPH_GENERATE: '/teacher/knowledge/graph/generate',
    KNOWLEDGE_GRAPH: '/teacher/knowledge/graph',
    RESOURCES_PENDING: '/teacher/resources/pending',
    RESOURCE: '/teacher/resources/{review_id}',
    RESOURCE_REVIEW: '/teacher/resources/{review_id}/review',
    STUDENT_RESOURCES: '/teacher/students/resources',
    STUDENT_REGENERATE: '/teacher/students/{student_id}/resources/{resource_type}/regenerate',
    STUDENT_REEVALUATE: '/teacher/students/{student_id}/resources/{resource_type}/reevaluate',
    CLASS_STATS: '/teacher/class/stats',
    CLASS_EXPORT: '/teacher/class/export',
    STUDENT_PROGRESS: '/teacher/student/{student_id}/progress',
    STUDENTS_PROGRESS: '/teacher/students/progress',
    ADJUST_PATH: '/teacher/student/{student_id}/path',
    ASSIGNMENTS: '/teacher/assignments',
    ASSIGNMENT: '/teacher/assignments/{assignment_id}',
    ASSIGNMENT_SUBMISSIONS: '/teacher/assignments/{assignment_id}/submissions',
    ASSIGN_ASSIGNMENT: '/teacher/assignments/{assignment_id}/assign',
    UPDATE_ASSIGNMENT: '/teacher/assignments/{assignment_id}',
    DELETE_ASSIGNMENT: '/teacher/assignments/{assignment_id}'
  },
  ADMIN: {
    USERS: '/admin/users',
    USER: '/admin/users/{user_id}',
    USER_DETAIL: '/admin/users/{user_id}',
    COURSES: '/admin/courses',
    COURSE_DETAIL: '/admin/courses/{course_id}',
    CONFIG: '/admin/config',
    MODEL_PROVIDERS: '/admin/model-providers',
    MODEL_PROVIDER: '/admin/model-providers/{provider_id}',
    MONITORING: '/admin/monitoring',
    STATS: '/admin/stats',
    LOGS: '/admin/logs',
    LOGS_CLEAN: '/admin/logs/clean',
    BACKUP: '/admin/backup',
    BACKUPS: '/admin/backups',
    RESTORE: '/admin/restore',
    DELETE_BACKUP: '/admin/backups/{backup_name}',
    SYSTEM_STATS: '/admin/system/stats',
    CACHE_CLEAR: '/admin/cache/clear',
    CONTENT_REVIEW: '/admin/content-review',
    CONTENT_REVIEW_ACTION: '/admin/content-review/{content_id}/action',
    CONTENT_SECURITY: '/admin/content-security',
    SECURITY_WORDS: '/admin/content-security/words',
    SECURITY_LOGS: '/admin/content-security/logs',
    MODELS: '/admin/models',
    AGENT_MODEL: '/admin/models/agent/{agent_name}',
    IMAGE_MODEL: '/admin/models/image/{task_name}',
    VIDEO_MODEL: '/admin/models/video/{task_name}',
    TTS_VOICE: '/admin/tts/voice',
    TTS_VOICES: '/admin/tts/voices'
  }
}

function replaceParams(url, params) {
  let result = url
  for (const key in params) {
    result = result.replace(`{${key}}`, params[key])
  }
  return result
}

module.exports = {
  API,
  replaceParams
}