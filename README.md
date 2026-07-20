# AI ResGen Learning Multi-Agent System

基于大模型的个性化资源生成与学习多智能体系统 -- 通过多 Agent 协作，为学生自动生成学习路径、文档、题目、代码、思维导图、PPT 视频、知识图谱等全套学习资源，并提供智能辅导和学习评估。

---

## 功能特性

### 学生端（Web + 微信小程序）
- **多画像管理** -- 支持创建、切换、归档、恢复多个学习画像（专业/年级/目标/风格等）
- **画像对话构建** -- 通过 WebSocket 流式对话，ProfileAgent 自动提取并更新学生画像
- **学习路径生成** -- LearningPathAgent 根据画像生成分阶段学习计划，支持增量优化
- **9 类资源自动生成** -- 学习文档、PPT 教学视频、思维导图、练习题目、代码示例、拓展阅读、术语词汇、知识关联图、学习总结
- **资源按需生成** -- 按学习阶段按需触发，支持单资源重新生成
- **资源质量门控** -- ResourceQualityAgent 自动评分，低于阈值的资源不展示
- **智能辅导 (Tutor)** -- RAG 检索增强 + 流式对话，支持多轮上下文
- **学习评估** -- EvaluationAgent 自动触发（累积行为/正确率下降/学习时长），生成评估报告并增量更新路径
- **学习进度汇总** -- 阶段完成率、答题正确率、连续学习天数、近 7 天统计
- **行为追踪** -- 记录资源浏览、答题、代码执行、阶段完成等事件
- **作业系统** -- 查看分配的作业、提交作业、查看批改结果
- **语音识别 (ASR)** -- 讯飞语音转文本
- **案例展示** -- 从数据库查询真实系统数据进行展示
- **错题本** -- 自动收集答错的题目，方便复习巩固
- **知识图谱可视化** -- Canvas 绘制可交互的知识图谱
- **思维导图渲染** -- 原生 Canvas 渲染思维导图，支持缩放和拖拽
- **Mermaid 流程图** -- 通过 mermaid.ink 在线渲染流程图
- **视频播放** -- PPT 教学视频在线播放

### 教师端（Web + 微信小程序）
- **课程管理** -- 创建/编辑/删除课程，维护知识树结构，导出 CSV 报表
- **知识库管理** -- 上传 PDF/DOCX/TXT/MD 文档，自动分块向量化存储到 ChromaDB
- **知识图谱** -- 从上传文档自动生成知识图谱，支持查看
- **资源审核** -- 审核 AI 生成的资源（通过/拒绝）
- **学生资源查看** -- 查看所有学生的学习资源及质量分数
- **资源重新生成/评估** -- 教师可为指定学生重新生成或重新评估某类资源
- **班级学情统计** -- 总学生数、活跃数、正确率、平均分、个体进度
- **学习路径调整** -- 手动调整学生学习路径
- **作业管理** -- 创建/编辑/删除/分配作业，查看提交和批改
- **导出报表** -- 班级统计报表 CSV 导出

### 管理员端（Web + 微信小程序）
- **用户管理** -- 增删改查用户，支持分页搜索和角色筛选
- **系统配置** -- 应用名、调试模式、JWT 过期时间、质量阈值、PPT 视频页数、TTS 音色等
- **模型管理** -- 查看/切换 Agent 文本模型、图片模型、视频模型、TTS 音色
- **模型提供商管理** -- 讯飞星火、Qwen-Image、Stable Diffusion
- **系统监控** -- CPU/内存/磁盘使用率
- **日志管理** -- 分页查看系统日志，清理过期日志
- **数据备份与恢复** -- 一键备份数据库 + ChromaDB，列出/删除/恢复备份
- **缓存清理** -- Redis / ChromaDB 缓存清理
- **内容安全审核** -- 查看/审核资源内容
- **敏感词过滤** -- 开关控制、词库管理（按类别增删）、过滤日志

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

## 快速启动

### 环境要求
- Python 3.11+
- Node.js 18+
- MySQL 8.0
- Redis 5+
- 微信开发者工具 (小程序开发)
- (可选) Neo4j 5+
- (可选) Playwright (PPT 视频生成需要)
- (可选) FFmpeg (PPT 视频合成需要)

### 1. 克隆项目
```bash
git clone https://github.com/xnxnpy/ai-resgen-learning-multiagent-system.git
cd ai-resgen-learning-multiagent-system
```

### 2. 后端启动
```bash
# 创建 conda 环境
conda create -n multi_agent python=3.11
conda activate multi_agent

# 安装依赖
pip install -r requirements.txt

# 配置环境变量（可选，有默认值）
cp .env.example .env
# 编辑 .env 文件

# 创建管理员账号
python scripts/create_admin.py --username admin --password admin123

# 启动后端
python main.py
# 或
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

### 3. Web 前端启动
```bash
cd frontend
npm install
npm run dev
```

### 4. 微信小程序启动
1. 打开微信开发者工具
2. 导入 `miniprogram/` 目录
3. AppID: `wx08363c06216a3c12`（或使用测试号）
4. 在微信开发者工具中勾选「不校验合法域名」（开发阶段）
5. 修改 `miniprogram/utils/request.js` 中的 `BASE_URL` 为后端地址

### 5. 访问
- Web 前端: http://localhost:5173
- 后端 API: http://localhost:8000
- API 文档 (Swagger): http://localhost:8000/docs
- 健康检查: http://localhost:8000/health
- 微信小程序: 通过微信开发者工具预览

### 6. 一键启动（Windows）
双击项目根目录下的 `run.bat`，自动安装依赖并启动前后端服务。

---

## 项目目录结构

```
ai-resgen-learning-multiagent-system/
├── main.py                          # FastAPI 入口，lifespan 管理
├── requirements.txt                 # Python 依赖
├── app/
│   ├── __init__.py
│   ├── agents/                      # 15 个 AI Agent
│   │   ├── base.py                  # Agent 基类
│   │   ├── profile_agent.py         # 画像对话 Agent
│   │   ├── learning_path_agent.py   # 学习路径 Agent
│   │   ├── document_agent.py        # 文档生成 Agent
│   │   ├── question_agent.py        # 题目生成 Agent
│   │   ├── code_agent.py            # 代码生成/执行 Agent
│   │   ├── mindmap_agent.py         # 思维导图 Agent
│   │   ├── ppt_video_agent.py       # PPT 教学视频 Agent
│   │   ├── reading_material_agent.py# 拓展阅读 Agent
│   │   ├── glossary_agent.py        # 术语词汇 Agent
│   │   ├── knowledge_graph_agent.py # 知识图谱 Agent
│   │   ├── summary_agent.py         # 学习总结 Agent
│   │   ├── evaluation_agent.py      # 学习评估 Agent
│   │   ├── resource_quality_agent.py# 资源质量评估 Agent
│   │   ├── tutor_agent.py           # 智能辅导 Agent
│   │   └── utils.py                 # Agent 工具函数
│   ├── api/v1/                      # API 路由层
│   │   ├── __init__.py              # 路由注册
│   │   ├── auth.py                  # 认证接口
│   │   ├── student.py               # 学生端接口
│   │   ├── teacher.py               # 教师端接口
│   │   ├── admin.py                 # 管理员端接口
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
│   ├── workflows/                   # LangGraph 工作流
│   │   └── graph_builder.py         # 工作流定义 + 管理器
│   └── multimodal/                  # 多模态处理
├── frontend/                        # Vue 3 Web 前端
│   ├── package.json
│   └── src/
│       ├── pages/
│       │   ├── auth/                # 登录/注册/个人信息
│       │   ├── student/             # 学生端 8 个页面
│       │   ├── teacher/             # 教师端 5 个页面
│       │   └── admin/               # 管理员端 9 个页面
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
├── tests/                           # 测试
└── run.bat                         # Windows 一键启动脚本
```

---

## 微信小程序 TabBar 结构

| Tab | 页面路径 | 说明 |
|-----|----------|------|
| 学习画像 | pages/profile/profile | 画像对话构建、画像管理 |
| 学习路径 | pages/path/path | 学习路径展示、阶段管理 |
| 学习资源 | pages/resource/resource | 资源浏览、答题、代码运行 |
| 智能辅导 | pages/tutor/tutor | RAG 智能辅导对话 |
| 学习报告 | pages/report/report | 评估报告、进度统计 |

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
# 创建管理员
python scripts/create_admin.py --username admin --password admin123
```

---

## 许可证

本项目为内部教学研究用途。
