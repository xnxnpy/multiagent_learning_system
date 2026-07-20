/* ============================================================
 *  AI Learning System — Global Type Definitions
 * ============================================================ */

// ── Auth ──────────────────────────────────────────────────────

export interface User {
  id: number
  username: string
  real_name?: string
  email?: string
  role: 'student' | 'teacher' | 'admin'
  created_at: string
}

export interface LoginRequest {
  username: string
  password: string
}

export interface LoginResponse {
  access_token: string
  token_type: string
  user: User
}

// ── Student Profile ───────────────────────────────────────────

export interface StudentProfile {
  id: number
  user_id: number
  major?: string
  grade?: string
  goal?: string
  knowledge_level?: string
  learning_style?: string
  coding_ability?: string
  interests?: string[]
  weakness?: string[]
  updated_at?: string
}

// ── Learning Path ─────────────────────────────────────────────

export interface LearningPath {
  id: number
  user_id: number
  title: string
  stages: LearningStage[]
  created_at?: string
}

export interface LearningStage {
  stage_id?: number
  title: string
  description?: string
  knowledge_points: string[]
  recommended_resource_types?: string[]
  estimated_hours?: number
}

// ── Resources ─────────────────────────────────────────────────

export interface PptVideoResource {
  video_url: string
  duration_seconds: number
  pages_count: number
  oss_key: string
  generated_at?: string
}

export interface FilteredResource {
  type: string
  display_name: string
  reason: string
  score: number
  threshold: number
}

export interface ResourceBundle {
  document: { topic: string; content: string; images?: DocumentImage[] } | null
  video_script: VideoScript | null
  mindmap: any | null
  mindmap_html: string | null
  mindmap_markdown: string | null
  knowledge_graph: KnowledgeGraphData | null
  questions: QuestionsData | null
  code: CodeData | null
  images: any[] | null
  reading_material: { topic: string; content: string } | null
  glossary: { title: string; terms: GlossaryTerm[] } | null
  knowledge_link: { title: string; nodes: KnowledgeGraphNode[]; edges: KnowledgeGraphEdge[] } | null
  summary: { topic: string; content: string } | null
  ppt_video: PptVideoResource | null
  filteredResources: FilteredResource[]
}

export interface GlossaryTerm {
  term: string
  definition: string
  example?: string
  related_terms?: string[]
  difficulty?: string
}

export interface DocumentImage {
  index: number
  description: string
  url?: string
  base64?: string
}

export interface QuestionsData {
  questions: Question[]
}

export interface Question {
  question_id: number
  type: 'choice' | 'judge' | 'blank' | 'fill' | 'code' | 'case_analysis'
  difficulty?: 'easy' | 'medium' | 'hard'
  question: string
  options?: string[] | null
  answer?: string
  score?: number
  explanation?: string
  test_cases?: TestCase[]
  rubric?: {
    criteria: string[]
    max_score?: number
  }
}

export interface TestCase {
  input: string
  expected: string
}

export interface CodeData {
  title?: string
  description?: string
  code: string
  input_example?: string
  expected_output?: string
  test_cases?: TestCase[]
  difficulty?: string
  tags?: string[]
}

export interface CodeResult {
  success: boolean
  stdout?: string
  stderr?: string
  error?: string
}

// ── Knowledge Graph ───────────────────────────────────────────

export interface KnowledgeGraphData {
  title: string
  knowledge_point_count: number
  nodes: KnowledgeGraphNode[]
  edges: KnowledgeGraphEdge[]
}

export interface KnowledgeGraphNode {
  id: string
  label: string
  level: number
  description?: string
}

export interface KnowledgeGraphEdge {
  source: string
  target: string
  relationship?: string
}

// ── Workflow ──────────────────────────────────────────────────

export interface WorkflowState {
  session_id: string
  current_step: string
  progress: number
  steps_history: WorkflowStep[]
  error?: string
  completed: boolean
}

export interface WorkflowStep {
  step: string
  status: 'started' | 'completed' | 'failed'
  timestamp?: string
}

// ── Evaluation ────────────────────────────────────────────────

export interface EvaluationReport {
  overall_grade: string
  total_score: number
  total_attempts: number
  accuracy_rate: number
  mastery_level: number
  analysis?: {
    strengths: string[]
    weaknesses: string[]
    suggestions: string[]
  }
  knowledge_points?: KnowledgePointStatus[]
  report?: string
  should_update_path?: boolean
}

export interface KnowledgePointStatus {
  topic: string
  score: number
  total: number
  mastery: number
  status: string
}

// ── Notifications ─────────────────────────────────────────────

export interface Notification {
  id: number
  title: string
  content: string
  type: string
  read: boolean
  created_at: string
}

// ── Teacher ───────────────────────────────────────────────────

export interface Course {
  id: number
  teacher_id: number
  title: string
  description?: string
  knowledge_tree?: any
  created_at: string
}

export interface ResourceReview {
  id: number
  resource_type: string
  resource_content: string
  status: 'pending' | 'approved' | 'rejected'
  creator_id: number
  reviewer_id?: number
  review_comment?: string
  reviewed_at?: string
  created_at: string
}

export interface ClassStats {
  total_students: number
  active_students: number
  average_accuracy: number
  total_learning_records: number
  student_progress: StudentProgress[]
}

export interface StudentProgress {
  student_id: number
  student_name: string
  total_learning_records: number
  accuracy: number
  average_score: number
  current_path_stage?: number
  last_activity?: string
}

// ── Admin ─────────────────────────────────────────────────────

export interface ContentReviewItem {
  id: number
  content_type: string
  content: string
  status: string
  reviewer_id?: number
  review_comment?: string
  created_at: string
}

export interface SystemConfig {
  app_name: string
  debug: boolean
  jwt_expire_minutes: number
  backend_host: string
  backend_port: number
}

export interface MonitoringStats {
  cpu_percent: number
  memory_percent: number
  memory_used_mb: number
  memory_total_mb: number
  disk_percent: number
  uptime_seconds: number
  request_count: number
  error_count: number
}

export interface LogEntry {
  timestamp: string
  level: string
  message: string
  module?: string
}

// ── Tutor ─────────────────────────────────────────────────────

export interface TutorMessage {
  id?: number
  role: 'user' | 'assistant'
  content: string
  time?: string
}

export interface ChatMsg extends TutorMessage {
  streaming?: boolean
  time: string
  renderedContent?: string
}

export interface SessionItem {
  id: string
  title: string
  updated_at?: string
}

// ── Common UI ─────────────────────────────────────────────────

export interface MenuItem {
  key: string
  label: string
  icon?: string
}

export interface PaginationParams {
  page: number
  page_size: number
  total: number
}

export interface PageResponse<T> {
  total: number
  page: number
  page_size: number
  items: T[]
}

export interface ApiResponse<T = any> {
  success: boolean
  data?: T
  message?: string
}
