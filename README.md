# AI ResGen Learning Multi-Agent System

基于大模型的个性化资源生成与学习多智能体系统 -- 由 4 个核心 Agent（Supervisor 调度、画像、辅导、评估）驱动资源生成 Tool，为学生自动生成学习路径、文档、题目、代码、思维导图、PPT 视频等学习资源，并提供智能辅导和学习评估。

---

## 功能特性

### 学生端（Web + 微信小程序）
- **多画像管理** -- 支持创建、切换、归档、恢复多个学习画像（专业/年级/目标/风格等）
- **画像对话构建** -- 通过 WebSocket 流式对话，ProfileAgent 自动提取并更新学生画像
- **学习路径生成** -- LearningPathAgent 根据画像生成分阶段学习计划，支持增量优化；支持一句话需求重新规划
- **Supervisor 学习环** -- 真 LangGraph 状态图（plan → act → observe → quality_gate），失败回环重规划、质量不达标自动重做
- **资源生成向导** -- 生成前配置薄弱知识点优先、视频风格（讲解动画/科技风/治愈系等）、资源类型
- **9 类资源自动生成** -- 学习文档、PPT 教学视频、思维导图、练习题目、代码示例、拓展阅读、术语词汇、知识关联图、学习总结
- **资源按需生成 / force 补生成** -- 画像跳过的类型（如视频）可随时点名补生成；单资源重生统一走 Supervisor
- **资源质量门控** -- ResourceQualityAgent 自动评分，低于阈值回环重做
- **题库 + 错题本** -- 题库分页筛选、页内作答判分；错题自动入本，重练定位到具体题目
- **智能辅导 (Tutor)** -- RAG 检索增强 + ReAct 五层防幻觉 + 流式对话，支持多轮上下文
- **学习评估 + AI 周报** -- EvaluationAgent 评估报告；近 7 天 AI 学习周报生成，支持追问
- **学习发现** -- 联网检索外部视频/文章/论文/仓库，一键收藏进个人库
- **学习广场** -- 发帖分享笔记速查表，点赞互动
- **个人知识库** -- 上传 PDF/DOCX/TXT/MD 材料，按用户隔离索引，辅导与生成可检索引用
- **知识图谱可视化** -- 节点可点击查看详情（掌握度着色、前置/后续跳转、去练习）
- **学习进度汇总** -- 阶段完成率、答题正确率、连续学习天数、近 7 天统计
- **行为追踪 / 作业 / ASR / 案例展示 / 思维导图 / Mermaid / 视频播放** -- 同前

### 教师端（Web + 微信小程序）
- **课程管理** -- 创建/编辑/删除课程，维护知识树结构，导出 CSV 报表
- **学生看板四指标** -- 平均掌握度 / 最长连续学习 / 累计学时 / 任务完成率
- **班级学情** -- 学生进度表、正确率、路径调整
- **干预中心** -- 风险学生识别（正确率/错题/沉默）+ 干预原因与建议
- **共享知识库** -- 上传教材自动切片向量化（全员可检索）；清理只动共享层，不碰学生数据
- **资源审核与代重生** -- 审核 AI 资源；为学生重新生成/评估资源（Supervisor force）
- **作业管理** -- 创建/分配/批改作业

### 管理员端（Web + 微信小程序）
- **用户管理** -- 增删改查用户，支持分页搜索和角色筛选
- **系统配置 / 模型管理 / 日志 / 备份恢复** -- 同前
- **知识库运维** -- 分区统计（资源/笔记/上传/无主）、按用户清理索引、安全清空上传材料
- **学习分析大屏** -- 日活趋势、24h 时段分布、需求类型占比、风险学生 KPI
- **内容安全 / 敏感词过滤** -- 同前

---

## 技术栈

### 后端
| 类别 | 技术 |
|------|------|
| 框架 | FastAPI 0.109.0 + Uvicorn 0.27.0 |
| ORM | SQLAlchemy 2.0.25 (异步, aiomysql) |
| 数据库 | MySQL 8.0 |
| 缓存 | Redis 5.0.1 |
| 向量数据库 | ChromaDB 1.5.9 |
| 知识图谱 | Neo4j (bolt 协议) |
| 工作流 | LangGraph >= 0.1.0 |
| RAG | LangChain 1.3.10 + LangChain-Chroma 1.1.0 |
| 嵌入模型 | sentence-transformers 5.6.0 (BGE) |
| 任务队列 | Celery 5.3.6 |
| 安全 | python-jose + passlib + bcrypt |
| 配置 | pydantic-settings 2.14.2 |
| 日志 | loguru 0.7.2 |
| TTS/ASR | 讯飞 WebSocket API |
| PPT 视频 | Playwright + FFmpeg + 阿里云 OSS |

### Web 前端
| 类别 | 技术 |
|------|------|
| 框架 | Vue 3.4 + TypeScript 5.3 |
| 构建 | Vite 5.0 |
| UI | Element Plus 2.5 |
| 状态管理 | Pinia 2.1 |
| 路由 | Vue Router 4.2 |
| 图表 | ECharts 5.5 |
| Markdown | marked 11.1 + KaTeX 0.17 |
| 思维导图 | markmap-lib 0.18 + markmap-view 0.18 |
| 流程图 | Mermaid 11.16 |
| HTTP | Axios 1.6 |
| 视频播放 | Artplayer 5.4 |

### 微信小程序
| 类别 | 技术 |
|------|------|
| 框架 | 微信小程序原生开发 (WXML/WXSS/JS) |
| 基础库 | 3.14.3 |
| 通信 | wx.request (REST API) + wx.connectSocket (WebSocket) |
| 渲染 | Canvas 2D API (知识图谱、思维导图) |
| 语音 | 录音管理器 (wx.getRecorderManager) |
| Markdown | 自定义 markdown.js 渲染器 |
| 流程图 | mermaid.ink 在线渲染 |

---

## 快速启动（两种部署方式）

| 方式 | 适用 | 说明 |
|------|------|------|
| **A. 本地开发** | 开发调试 | `run.bat` / 手动起前后端，依赖本机 MySQL、Redis、FFmpeg |
| **B. Docker Compose** | 部署上线 | 一条命令起 MySQL + Redis + 后端 + 前端（Nginx） |

---

### 方式 A：本地开发

#### 环境要求
- Python 3.11+
- Node.js 18+
- MySQL 8.0
- Redis 5+
- 微信开发者工具 (小程序开发)
- (可选) Neo4j 5+、Playwright、FFmpeg（PPT 视频需要）

#### A1. 克隆项目
```bash
git clone https://github.com/xnxnpy/ai-resgen-learning-multiagent-system.git
cd ai-resgen-learning-multiagent-system
```

#### A2. 后端启动
```bash
conda create -n multi_agent python=3.11
conda activate multi_agent
pip install -r requirements.txt
cp .env.example .env   # 按需修改密钥与数据库
playwright install chromium
python scripts/create_admin.py --username admin --password admin123
python main.py
```

#### A3. Web 前端
```bash
cd frontend && npm install && npm run dev
# http://localhost:3000
```

#### A4. 微信小程序
1. 微信开发者工具导入 `miniprogram/`
2. 修改 `miniprogram/utils/request.js` 中 `BASE_URL` 指向本机后端
3. 开发阶段勾选「不校验合法域名」

#### A5. Windows 一键
双击 `run.bat` 自动安装依赖并启动前后端。

#### A6. 访问
- Web: http://localhost:3000
- API / Swagger: http://localhost:8000/docs

---

### 方式 B：Docker 部署（推荐上线）

```bash
# 1. 配置环境变量（至少改 SECRET / JWT / 讯飞密钥）
cp .env.example .env

# 2. 构建并启动（MySQL + Redis + 后端 + 前端 Nginx）
docker compose up -d --build

# 3. 创建管理员（容器内执行一次）
docker compose exec backend python scripts/create_admin.py --username admin --password admin123
```

| 服务 | 地址 |
|------|------|
| **Web 前端** | http://localhost:8080 |
| **API / Swagger** | http://localhost:8000/docs |
| MySQL | localhost:3306 |
| Redis | localhost:6379 |

- 可选 Neo4j：`docker compose --profile neo4j up -d`
- 数据卷：MySQL / Redis / Chroma 持久化；代码热更新可挂载 `./data` `./logs`
- WebSocket 与 API 均走前端 Nginx 同源反代（`/api/`），无需额外配置

---

## 项目目录结构

```
ai-resgen-learning-multiagent-system/
├── main.py                          # FastAPI 入口，lifespan 管理
├── requirements.txt                 # Python 依赖
├── Dockerfile                       # 后端镜像（FFmpeg + Playwright）
├── docker-compose.yml               # MySQL + Redis + 后端 + 前端 一键部署
├── .dockerignore
├── app/
│   ├── __init__.py
│   ├── agents/                      # 智能体与生成工具（目录名 agents/ 为历史沿用）
│   │   ├── base.py                  # 公共基类
│   │   ├── supervisor_agent.py      # Supervisor 调度 Agent（学习环决策中枢）
│   │   ├── profile_agent.py         # 画像构建 Agent
│   │   ├── tutor_agent.py           # 智能辅导 Agent
│   │   ├── evaluation_agent.py      # 学习评估 Agent
│   │   ├── learning_path_agent.py   # 路径规划 Tool
│   │   ├── document_agent.py        # 文档生成 Tool
│   │   ├── question_agent.py        # 题库生成 Tool
│   │   ├── code_agent.py            # 代码示例 Tool
│   │   ├── mindmap_agent.py         # 思维导图 Tool
│   │   ├── ppt_video_agent.py       # PPT 教学视频 Tool
│   │   ├── reading_material_agent.py# 拓展阅读 Tool
│   │   ├── glossary_agent.py        # 术语词汇 Tool
│   │   ├── knowledge_graph_agent.py # 知识图谱 Tool
│   │   ├── summary_agent.py         # 学习总结 Tool
│   │   ├── resource_quality_agent.py# 质量评估 Tool（守门）
│   │   └── utils.py                 # 解析与提示词工具
│   ├── api/v1/                      # API 路由层
│   │   ├── __init__.py              # 路由注册
│   │   ├── auth.py                  # 认证接口
│   │   ├── student.py               # 学生端接口（含周报/生成向导）
│   │   ├── teacher.py               # 教师端接口（看板/干预/共享知识库）
│   │   ├── admin.py                 # 管理员端（含知识库运维/学习分析）
│   │   ├── knowledge.py             # 学生个人知识库
│   │   ├── discovery.py             # 学习发现（外部检索+收藏）
│   │   ├── plaza.py                 # 学习广场
│   │   ├── intervention.py          # 教师干预中心
│   │   ├── tutor.py                 # 智能辅导 WebSocket
│   │   ├── tutor_stream.py          # 辅导流式端点
│   │   ├── notification.py          # 通知系统
│   │   ├── profile_chat.py          # 画像对话 WebSocket
│   │   ├── showcase.py              # 案例展示
│   │   ├── ws_base.py               # WebSocket 基类
│   │   └── deps.py                  # 依赖注入（认证、角色）
│   ├── core/                        # 核心模块
│   │   ├── config.py                # 应用配置 (pydantic-settings)
│   │   ├── security.py              # JWT + 密码哈希
│   │   ├── model_manager.py         # 统一模型管理器
│   │   ├── llm_client.py            # 大模型客户端封装
│   │   ├── celery_app.py            # Celery 任务队列配置
│   │   ├── websocket_manager.py     # WebSocket 连接管理
│   │   ├── websocket_heartbeat.py   # WebSocket 心跳
│   │   ├── websocket_dispatcher.py  # WebSocket 消息分发
│   │   ├── redis_client.py          # Redis 客户端
│   │   ├── neo4j_client.py          # Neo4j 客户端
│   │   ├── logger.py                # 日志配置
│   │   ├── exceptions.py            # 自定义异常
│   │   ├── content_security.py      # 敏感词过滤
│   │   ├── quality_thresholds.py    # 质量阈值配置
│   │   ├── tutor_streaming.py       # 辅导上下文管理
│   │   └── ppt_video_config.py      # PPT 视频配置
│   ├── embeddings/                  # 嵌入模型
│   │   └── bge_embeddings.py        # BGE 嵌入
│   ├── models/                      # SQLAlchemy 数据模型 (15 张表)
│   │   ├── base.py                  # 引擎/会话/DDL 迁移
│   │   ├── user.py                  # users
│   │   ├── student_profile.py       # student_profiles
│   │   ├── learning_path.py         # learning_paths
│   │   ├── learning_record.py       # learning_records
│   │   ├── learning_resource.py     # learning_resources
│   │   ├── course.py                # courses
│   │   ├── assignment.py            # assignments + assignment_submissions
│   │   ├── evaluation_report.py     # evaluation_reports
│   │   ├── chat_history.py          # profile_chat_messages + tutor_chat_messages
│   │   ├── knowledge_document.py    # knowledge_documents
│   │   ├── resource_review.py       # resource_reviews
│   │   ├── system_config.py         # system_config
│   │   ├── workflow_state.py        # workflow_states
│   │   └── upsert.py                # MySQL upsert 工具
│   ├── rag/                         # RAG 管线
│   │   ├── document_loader.py       # 文档解析
│   │   ├── text_splitter.py         # 中文文本分块
│   │   ├── retriever.py             # 检索器
│   │   └── bge_reranker.py          # BGE 重排序
│   ├── repositories/                # 数据访问层
│   │   ├── base_repository.py
│   │   ├── user_repository.py
│   │   ├── course_repository.py
│   │   ├── learning_path_repository.py
│   │   ├── learning_record_repository.py
│   │   └── profile_repository.py
│   ├── sandbox/                     # 代码沙箱
│   │   ├── docker_runner.py         # Docker 沙箱
│   │   └── local_runner.py          # 本地沙箱
│   ├── schemas/                     # Pydantic 请求/响应模型
│   │   ├── common.py                # 通用响应 + 分页
│   │   ├── user.py                  # 用户相关模型
│   │   ├── profile.py               # 画像相关模型
│   │   ├── learning_path.py         # 学习路径模型
│   │   ├── question.py              # 题目模型
│   │   └── showcase.py              # 案例展示模型
│   ├── services/                    # 业务服务层
│   │   ├── auth_service.py
│   │   ├── user_service.py
│   │   ├── course_service.py
│   │   ├── resource_review_service.py
│   │   ├── stats_service.py
│   │   └── config_service.py
│   ├── vectorstore/                 # 向量存储
│   │   ├── base.py
│   │   └── chroma_store.py
│   ├── workflows/                   # LangGraph 学习环
│   │   ├── stage_workflow.py        # Supervisor 阶段学习状态图（plan→act→gate）
│   │   └── graph_builder.py         # 路径/图谱构建
│   └── multimodal/                  # 多模态处理
│       ├── ocr_client.py            # OCR 图片识别 (讯飞)
│       ├── oss_uploader.py          # 阿里云 OSS 上传
│       ├── generators.py            # 图片生成器
│       ├── asr_client.py            # 语音识别 (讯飞 ASR)
│       ├── tts_client.py            # 语音合成 (讯飞 TTS)
│       ├── ppt_video_generator.py   # PPT 视频生成
│       ├── ppt_templates.py         # PPT 模板
│       └── subtitle_generator.py    # 字幕生成
├── frontend/                        # Vue 3 Web 前端
│   ├── package.json
│   ├── Dockerfile                   # 多阶段构建 → Nginx
│   ├── nginx.conf                   # 静态站 + /api 与 WS 反代
│   └── src/
│       ├── pages/
│       │   ├── auth/                # 登录/注册/落地页/个人信息
│       │   ├── student/             # 学生端（画像/路径/资源/题库/错题/笔记/知识库/发现/广场…）
│       │   ├── teacher/             # 教师端 5 个页面
│       │   └── admin/               # 管理员端（用户/配置/模型/知识库运维/分析/备份…）
│       ├── api/                     # API 封装
│       ├── components/              # 公共组件
│       ├── composables/             # 组合式函数
│       ├── layouts/                 # 布局
│       ├── router/                  # 路由
│       ├── stores/                  # Pinia 状态
│       └── types/                   # TypeScript 类型
├── miniprogram/                     # 微信小程序
│   ├── app.js                       # 小程序入口
│   ├── app.json                     # 小程序配置
│   ├── app.wxss                     # 全局样式
│   ├── project.config.json          # 项目配置 (AppID: wx08363c06216a3c12)
│   ├── components/                  # 公共组件
│   │   └── navigation-bar/          # 自定义导航栏
│   ├── images/                      # 图标资源
│   ├── pages/
│   │   ├── index/                   # 登录页
│   │   ├── register/                # 注册页
│   │   ├── profile/                 # 学习画像 (TabBar)
│   │   ├── path/                    # 学习路径 (TabBar)
│   │   ├── resource/                # 学习资源 (TabBar)
│   │   ├── tutor/                   # 智能辅导 (TabBar)
│   │   ├── report/                  # 学习报告 (TabBar)
│   │   ├── user-profile/            # 个人信息管理
│   │   ├── notifications/           # 通知中心
│   │   ├── my-learning/             # 综合学习概览
│   │   ├── wrong-book/              # 错题本
│   │   ├── video-player/            # 视频播放器
│   │   ├── kg/                      # 知识图谱可视化
│   │   ├── mindmap/                 # 思维导图渲染
│   │   ├── mermaid/                 # Mermaid 流程图
│   │   ├── teacher/                 # 教师端页面
│   │   │   ├── teacher.wxml/js/wxss # 教师端主页
│   │   │   └── knowledge.wxml/js/wxss # 知识库管理
│   │   └── admin/                   # 管理员端页面
│   │       ├── admin.wxml/js/wxss   # 管理员端主页
│   │       ├── config.wxml/js/wxss  # 系统配置
│   │       ├── models.wxml/js/wxss  # 模型管理
│   │       ├── content-security.wxml/js/wxss # 敏感词管理
│   │       └── backup.wxml/js/wxss  # 数据备份
│   └── utils/                       # 工具函数
│       ├── api.js                   # API 路径常量
│       ├── request.js               # HTTP 请求封装
│       ├── markdown.js              # Markdown 渲染
│       └── voice.js                 # 语音录制 (ASR)
├── scripts/                         # 脚本
│   ├── create_admin.py              # 创建管理员
│   └── data.sql                     # SQL 初始化
├── prompts/                         # Agent Prompt 模板
│   ├── profile_extract_multi.txt    # 画像多维提取
│   ├── learning_path_prompt.txt     # 学习路径
│   ├── document_prompt.txt          # 文档生成
│   ├── question_prompt.txt          # 题目生成
│   ├── code_prompt.txt              # 代码生成
│   ├── mindmap_prompt.txt           # 思维导图
│   ├── ppt_video_prompt.txt         # PPT 视频
│   ├── reading_material_prompt.txt  # 拓展阅读
│   ├── glossary_prompt.txt          # 术语词汇
│   ├── knowledge_graph_prompt.txt   # 知识图谱
│   ├── summary_prompt.txt           # 学习总结
│   ├── evaluation_prompt.txt        # 学习评估
│   ├── resource_quality_prompt.txt  # 资源质量评估
│   └── tutor_prompt.txt             # 智能辅导
├── tests/                           # 测试
├── run.bat                          # Windows 本地一键启动
├── Dockerfile                       # 后端镜像
└── docker-compose.yml               # Docker 一键部署
```

---

## 微信小程序 TabBar 结构

| Tab | 页面路径 | 说明 |
|-----|----------|------|
| 学习画像 | pages/profile/profile | 画像对话构建、画像管理 |
| 学习路径 | pages/path/path | 学习路径展示、阶段管理 |
| 学习资源 | pages/resource/resource | 资源浏览、答题、代码运行 |
| 智能辅导 | pages/tutor/tutor | RAG 智能辅导对话 |
| 学习报告 | pages/report/report | 评估报告、AI 周报、进度统计 |

其他入口：错题本、我的知识库、教师端（课程/知识库）、管理端。

---

## WebSocket 端点

| 端点路径 | 用途 | 认证方式 | 客户端 |
|----------|------|----------|--------|
| `/api/v1/tutor/ws/chat` | 智能辅导对话 (RAG + 流式) | query 消息内带 token | Web + 小程序 |
| `/api/v1/profile-chat/ws/chat` | 画像对话构建 (流式) | query 消息内带 token | Web + 小程序 |
| `/api/v1/notifications/ws` | 实时通知推送 | query 消息内带 token | Web + 小程序 |
| `/api/v1/student/ws/workflow` | 学习工作流进度推送 | URL query param `token` | Web + 小程序 |

**WebSocket 消息类型：**
- 客户端发送: `query` (提问), `stop` (停止生成), `ping` (心跳)
- 服务端推送: `status` (状态), `chunk` (流式片段), `end` (完成), `error` (错误), `pong` (心跳响应)

---

## 默认测试账号

系统通过 `scripts/create_admin.py` 创建管理员。用户可通过注册接口创建 student/teacher/admin 角色账号。

```bash
# 本地创建管理员
python scripts/create_admin.py --username admin --password admin123

# Docker 环境
docker compose exec backend python scripts/create_admin.py --username admin --password admin123
```

---

## 许可证

本项目为内部教学研究用途。
