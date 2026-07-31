<template>
  <div class="resources-page">
    <!-- Action Bar -->
    <div class="action-bar">
      <div class="action-left">
        <el-button type="primary" :loading="store.generating" @click="handleGenerateAll">
          <el-icon><MagicStick /></el-icon>
          {{ store.workflowSessionId ? '继续生成' : '一键生成全部资源' }}
        </el-button>
        <el-popconfirm
          title="重新生成会清除当前所有学习资源和答题记录，确定继续吗？"
          confirm-button-text="确定重新生成"
          cancel-button-text="取消"
          @confirm="handleRegenerate"
        >
          <template #reference>
            <el-button :loading="store.loading">重新生成全部资源</el-button>
          </template>
        </el-popconfirm>
      </div>
      <div class="action-right">
        <el-tag v-if="store.currentTopic" type="info" size="large" effect="plain">
          主题：{{ store.currentTopic }}
        </el-tag>
        <el-tag v-else type="warning" size="large" effect="plain">
          请先完成学习画像，再生成资源
        </el-tag>
      </div>
    </div>

    <!-- Loading state -->
    <div v-if="store.loading && !hasAnyData" class="loading-state">
      <el-icon class="is-loading" :size="32"><Loading /></el-icon>
      <p>正在加载学习资源...</p>
    </div>

    <!-- 推荐理由（画像可解释性） -->
    <el-card v-if="store.currentTopic" class="recommend-card" shadow="never">
      <div class="recommend-content">
        <el-icon :size="18" color="var(--color-primary)"><DataAnalysis /></el-icon>
        <div class="recommend-text">
          <span class="recommend-title">个性化推荐依据：</span>
          <span class="recommend-reason">
            基于您的专业<strong>{{ profileInfo.major || '未知' }}</strong>、
            知识水平<strong>{{ profileInfo.level || '未知' }}</strong>、
            学习目标<strong>{{ profileInfo.goal || '未知' }}</strong>
            <template v-if="profileInfo.weakness?.length">
              ，重点强化薄弱点：<el-tag v-for="w in profileInfo.weakness" :key="w" size="small" type="danger" effect="plain" style="margin: 0 4px;">{{ w }}</el-tag>
            </template>
          </span>
        </div>
      </div>
    </el-card>

    <!-- Resource Tabs -->
    <el-tabs v-model="activeTab" class="resource-tabs">
      <!-- Document Tab -->
      <el-tab-pane name="document">
        <template #label>
          <span class="tab-label"><el-icon><Document /></el-icon> 学习文档</span>
        </template>
        <div class="tab-content">
          <div class="tab-action-bar">
            <el-button type="warning" plain size="small"
                       :loading="regeneratingType === 'document'"
                       @click="handleRegenerateSingle('document')">
              重新生成
            </el-button>
          </div>
          <!-- 质量门控 -->
          <div v-if="isFiltered('document')" class="quality-gate-card">
            <div class="gate-icon">⚠️</div>
            <div class="gate-info">
              <div class="gate-title">质量未达标</div>
              <div class="gate-detail">
                当前评分 {{ getFilteredInfo('document')?.score }} 分，质量未达标
              </div>
            </div>
            <el-button type="warning" plain size="small"
                       :loading="regeneratingType === 'document'"
                       @click="handleRegenerateSingle('document')">
              重新生成
            </el-button>
          </div>
          <div v-if="store.resources.document">
            <!-- AI 配图 -->
            <div v-if="store.resources.document.images?.length" class="doc-images">
              <div v-for="img in store.resources.document.images" :key="img.index" class="doc-image-item">
                <img v-if="img.url" :src="img.url" :alt="img.description" />
                <img v-else-if="img.base64" :src="`data:image/png;base64,${img.base64}`" :alt="img.description" />
                <p class="image-caption">{{ img.description }}</p>
              </div>
            </div>
            <!-- Markdown 文档内容 -->
            <template v-for="(seg, i) in docSegments" :key="i">
              <div v-if="seg.type === 'markdown'" class="markdown-body" v-html="renderMd(seg.content)"></div>
              <MermaidDiagram v-else :code="seg.content" :forceKey="mermaidRenderKey" />
            </template>
          </div>
          <el-empty v-else description="暂无文档，请先生成" />
        </div>
      </el-tab-pane>

      <!-- PPT Video Tab -->
      <el-tab-pane name="video">
        <template #label>
          <span class="tab-label"><el-icon><VideoCamera /></el-icon> 教学视频</span>
        </template>
        <div class="tab-content">
          <div class="tab-action-bar">
            <el-button type="warning" plain size="small" :loading="regeneratingType === 'video'" @click="handleRegenerateSingle('video')">重新生成</el-button>
          </div>
          <div v-if="isFiltered('video')" class="quality-gate-card">
            <div class="gate-icon">⚠️</div>
            <div class="gate-info">
              <div class="gate-title">质量未达标</div>
              <div class="gate-detail">当前评分 {{ getFilteredInfo('video')?.score }} 分，质量未达标</div>
            </div>
            <el-button type="warning" plain size="small" :loading="regeneratingType === 'video'" @click="handleRegenerateSingle('video')">重新生成</el-button>
          </div>
          <div v-if="store.resources.ppt_video?.video_url" class="video-player-wrap">
            <div ref="videoPlayerRef" class="artplayer-container"></div>
            <div class="video-meta">
              <el-tag type="info" size="small">时长: {{ formatDuration(store.resources.ppt_video.duration_seconds) }}</el-tag>
              <el-tag type="info" size="small">{{ store.resources.ppt_video.pages_count }} 页</el-tag>
            </div>
          </div>
          <el-empty v-else description="暂无教学视频，请先生成" />
        </div>
      </el-tab-pane>

      <!-- Mindmap Tab -->
      <el-tab-pane name="mindmap">
        <template #label>
          <span class="tab-label"><el-icon><Share /></el-icon> 思维导图</span>
        </template>
        <div class="tab-content">
          <div class="tab-action-bar">
            <el-button type="warning" plain size="small" :loading="regeneratingType === 'mindmap'" @click="handleRegenerateSingle('mindmap')">重新生成</el-button>
          </div>
          <div v-if="isFiltered('mindmap')" class="quality-gate-card">
            <div class="gate-icon">⚠️</div>
            <div class="gate-info">
              <div class="gate-title">质量未达标</div>
              <div class="gate-detail">当前评分 {{ getFilteredInfo('mindmap')?.score }} 分，质量未达标</div>
            </div>
            <el-button type="warning" plain size="small" :loading="regeneratingType === 'mindmap'" @click="handleRegenerateSingle('mindmap')">重新生成</el-button>
          </div>
          <template v-if="store.resources.mindmap_markdown">
            <div class="mindmap-toolbar">
              <el-button size="small" :type="mindmapShowSource ? 'primary' : ''" plain @click="mindmapShowSource = !mindmapShowSource">
                {{ mindmapShowSource ? '查看图' : '查看代码' }}
              </el-button>
              <el-button size="small" @click="downloadMindmap">下载图片</el-button>
              <el-button size="small" @click="zoomMindmap(1.2)">放大</el-button>
              <el-button size="small" @click="zoomMindmap(0.8)">缩小</el-button>
              <el-button size="small" @click="fitMindmap">适应</el-button>
            </div>
            <div v-if="mindmapShowSource" class="mindmap-source">
              <pre><code>{{ mindmapSourceText }}</code></pre>
            </div>
            <div v-else-if="store.resources.mindmap_markdown" ref="mindmapContainerRef" class="mindmap-container"></div>
          </template>
          <el-empty v-else description="暂无思维导图，请先生成" />
        </div>
      </el-tab-pane>

      <!-- Questions Tab -->
      <el-tab-pane name="questions">
        <template #label>
          <span class="tab-label"><el-icon><EditPen /></el-icon> 练习题目</span>
        </template>
        <div class="tab-content">
          <div class="tab-action-bar">
            <el-button type="warning" plain size="small" :loading="regeneratingType === 'questions'" @click="handleRegenerateSingle('questions')">重新生成</el-button>
          </div>
          <div v-if="isFiltered('questions')" class="quality-gate-card">
            <div class="gate-icon">⚠️</div>
            <div class="gate-info">
              <div class="gate-title">质量未达标</div>
              <div class="gate-detail">当前评分 {{ getFilteredInfo('questions')?.score }} 分，质量未达标</div>
            </div>
            <el-button type="warning" plain size="small" :loading="regeneratingType === 'questions'" @click="handleRegenerateSingle('questions')">重新生成</el-button>
          </div>

          <div v-if="questions.length > 0" class="quiz-layout">
            <!-- 左侧答题卡 -->
            <div class="answer-card">
              <div class="card-title">答题卡</div>
              <div class="card-grid">
                <div v-for="(q, i) in questions" :key="q.question_id"
                     class="card-cell"
                     :class="{
                       'cell-active': viewMode === 'single' && selectedQuestionIdx === i,
                       'cell-correct': submittedAnswers[q.question_id]?.correct,
                       'cell-wrong': submittedAnswers[q.question_id] && !submittedAnswers[q.question_id]?.correct,
                       'cell-answered': answers[q.question_id] && !submittedAnswers[q.question_id],
                     }"
                     @click="selectQuestion(i)">
                  {{ i + 1 }}
                </div>
              </div>
              <div class="card-stats">
                <span class="stat-total">共 {{ questions.length }} 题</span>
                <span class="stat-done" v-if="submittedCount > 0">已答 {{ submittedCount }} 题</span>
              </div>
              <div class="card-actions">
                <el-radio-group v-model="viewMode" size="small" class="view-toggle">
                  <el-radio-button value="single">单题</el-radio-button>
                  <el-radio-button value="all">全部</el-radio-button>
                </el-radio-group>
              </div>
            </div>

            <!-- 右侧题目区域 -->
            <div class="question-panel">
              <!-- 单题模式 -->
              <template v-if="viewMode === 'single'">
                <div class="question-nav">
                  <el-button size="small" :disabled="selectedQuestionIdx <= 0" @click="selectedQuestionIdx--">
                    ← 上一题
                  </el-button>
                  <span class="nav-indicator">{{ selectedQuestionIdx + 1 }} / {{ questions.length }}</span>
                  <el-button size="small" :disabled="selectedQuestionIdx >= questions.length - 1" @click="selectedQuestionIdx++">
                    下一题 →
                  </el-button>
                </div>
                <div class="question-card" v-if="questions[selectedQuestionIdx]">
                  <div class="question-card-header">
                    <span class="question-num">第 {{ selectedQuestionIdx + 1 }} 题</span>
                    <el-tag :type="difficultyType(questions[selectedQuestionIdx].difficulty)" size="small">
                      {{ questions[selectedQuestionIdx].difficulty || '中等' }}
                    </el-tag>
                    <el-tag size="small" type="info">{{ questions[selectedQuestionIdx].score || 10 }}分</el-tag>
                    <el-tag v-if="submittedAnswers[questions[selectedQuestionIdx]?.question_id]" size="small"
                      :type="submittedAnswers[questions[selectedQuestionIdx].question_id]?.correct ? 'success' : 'danger'">
                      {{ submittedAnswers[questions[selectedQuestionIdx].question_id]?.correct ? '✓ 正确' : '✗ 错误' }}
                    </el-tag>
                  </div>
                  <div class="question-text">{{ questions[selectedQuestionIdx].question }}</div>
                  <div class="question-body">
                    <!-- Choice -->
                    <div v-if="questions[selectedQuestionIdx].type === 'choice' && questions[selectedQuestionIdx].options" class="question-options">
                      <el-radio-group v-model="answers[questions[selectedQuestionIdx].question_id]">
                        <el-radio v-for="(opt, optIdx) in questions[selectedQuestionIdx].options" :key="opt" :value="opt" class="option-radio">
                          <span class="option-label">{{ String.fromCharCode(65 + optIdx) }}.</span> {{ opt }}
                        </el-radio>
                      </el-radio-group>
                    </div>
                    <!-- Judge -->
                    <div v-else-if="questions[selectedQuestionIdx].type === 'judge'" class="question-options">
                      <el-radio-group v-model="answers[questions[selectedQuestionIdx].question_id]">
                        <el-radio value="正确" class="option-radio">正确</el-radio>
                        <el-radio value="错误" class="option-radio">错误</el-radio>
                      </el-radio-group>
                    </div>
                    <!-- Blank -->
                    <div v-else-if="questions[selectedQuestionIdx].type === 'blank' || questions[selectedQuestionIdx].type === 'fill'">
                      <el-input v-model="answers[questions[selectedQuestionIdx].question_id]" placeholder="请输入答案..." />
                    </div>
                    <!-- Code -->
                    <div v-else-if="questions[selectedQuestionIdx].type === 'code'">
                      <el-input v-model="answers[questions[selectedQuestionIdx].question_id]" type="textarea" :rows="8" placeholder="请输入 Python 代码..." />
                      <div v-if="questions[selectedQuestionIdx].test_cases?.length" class="test-cases-hint">
                        <p style="font-size:13px;color:#909399;margin:8px 0 4px">测试用例：</p>
                        <div v-for="(tc, ti) in questions[selectedQuestionIdx].test_cases" :key="ti" style="font-size:12px;color:#606266;margin:2px 0">
                          输入: <code>{{ tc.input }}</code> → 期望: <code>{{ tc.expected }}</code>
                        </div>
                      </div>
                      <el-button size="small" style="margin-top:8px" @click="handleRunTestCode(questions[selectedQuestionIdx])"
                        :loading="codeRunning[questions[selectedQuestionIdx].question_id]">运行测试</el-button>
                      <div v-if="codeResults[questions[selectedQuestionIdx].question_id]" class="answer-feedback"
                        :class="codeResults[questions[selectedQuestionIdx].question_id].correct ? 'feedback-correct' : 'feedback-wrong'">
                        <div>{{ codeResults[questions[selectedQuestionIdx].question_id].feedback }}</div>
                        <div v-if="codeResults[questions[selectedQuestionIdx].question_id].details" style="font-size:12px;margin-top:4px;white-space:pre-wrap">{{ codeResults[questions[selectedQuestionIdx].question_id].details }}</div>
                      </div>
                    </div>
                    <!-- Case Analysis -->
                    <div v-else-if="questions[selectedQuestionIdx].type === 'case_analysis'">
                      <el-input v-model="answers[questions[selectedQuestionIdx].question_id]" type="textarea" :rows="8" placeholder="请输入您的分析..." />
                      <div v-if="questions[selectedQuestionIdx].rubric?.criteria" class="rubric-box">
                        <p class="rubric-title">评分标准：</p>
                        <ul><li v-for="(c, ci) in questions[selectedQuestionIdx].rubric.criteria" :key="ci">{{ c }}</li></ul>
                      </div>
                    </div>
                  </div>
                  <!-- 提交反馈 -->
                  <div v-if="questions[selectedQuestionIdx].type !== 'code' && submittedAnswers[questions[selectedQuestionIdx].question_id]" class="answer-feedback"
                    :class="submittedAnswers[questions[selectedQuestionIdx].question_id].correct ? 'feedback-correct' : 'feedback-wrong'">
                    <span v-if="submittedAnswers[questions[selectedQuestionIdx].question_id].correct">✓ 回答正确！得分：{{ submittedAnswers[questions[selectedQuestionIdx].question_id].score }}</span>
                    <span v-else>✗ 回答错误。正确答案：{{ questions[selectedQuestionIdx].answer }}，得分：{{ submittedAnswers[questions[selectedQuestionIdx].question_id].score }}</span>
                  </div>
                </div>
              </template>

              <!-- 全部模式 -->
              <template v-else>
                <div v-for="(q, i) in questions" :key="q.question_id" class="question-card">
                  <div class="question-card-header">
                    <span class="question-num">第 {{ i + 1 }} 题</span>
                    <el-tag :type="difficultyType(q.difficulty)" size="small">{{ q.difficulty || '中等' }}</el-tag>
                    <el-tag size="small" type="info">{{ q.score || 10 }}分</el-tag>
                    <el-tag v-if="submittedAnswers[q.question_id]" size="small"
                      :type="submittedAnswers[q.question_id].correct ? 'success' : 'danger'">
                      {{ submittedAnswers[q.question_id].correct ? '✓ 正确' : '✗ 错误' }}
                    </el-tag>
                  </div>
                  <div class="question-text">{{ q.question }}</div>
                  <div class="question-body">
                    <div v-if="q.type === 'choice' && q.options" class="question-options">
                      <el-radio-group v-model="answers[q.question_id]">
                        <el-radio v-for="(opt, optIdx) in q.options" :key="opt" :value="opt" class="option-radio">
                          <span class="option-label">{{ String.fromCharCode(65 + optIdx) }}.</span> {{ opt }}
                        </el-radio>
                      </el-radio-group>
                    </div>
                    <div v-else-if="q.type === 'judge'" class="question-options">
                      <el-radio-group v-model="answers[q.question_id]">
                        <el-radio value="正确" class="option-radio">正确</el-radio>
                        <el-radio value="错误" class="option-radio">错误</el-radio>
                      </el-radio-group>
                    </div>
                    <div v-else-if="q.type === 'blank' || q.type === 'fill'">
                      <el-input v-model="answers[q.question_id]" placeholder="请输入答案..." />
                    </div>
                    <div v-else-if="q.type === 'code'">
                      <el-input v-model="answers[q.question_id]" type="textarea" :rows="8" placeholder="请输入 Python 代码..." />
                      <div v-if="q.test_cases?.length" class="test-cases-hint">
                        <p style="font-size:13px;color:#909399;margin:8px 0 4px">测试用例：</p>
                        <div v-for="(tc, ti) in q.test_cases" :key="ti" style="font-size:12px;color:#606266;margin:2px 0">
                          输入: <code>{{ tc.input }}</code> → 期望: <code>{{ tc.expected }}</code>
                        </div>
                      </div>
                      <el-button size="small" style="margin-top:8px" @click="handleRunTestCode(q)" :loading="codeRunning[q.question_id]">运行测试</el-button>
                      <div v-if="codeResults[q.question_id]" class="answer-feedback"
                        :class="codeResults[q.question_id].correct ? 'feedback-correct' : 'feedback-wrong'">
                        <div>{{ codeResults[q.question_id].feedback }}</div>
                        <div v-if="codeResults[q.question_id].details" style="font-size:12px;margin-top:4px;white-space:pre-wrap">{{ codeResults[q.question_id].details }}</div>
                      </div>
                    </div>
                    <div v-else-if="q.type === 'case_analysis'">
                      <el-input v-model="answers[q.question_id]" type="textarea" :rows="8" placeholder="请输入您的分析..." />
                      <div v-if="q.rubric?.criteria" class="rubric-box">
                        <p class="rubric-title">评分标准：</p>
                        <ul><li v-for="(c, ci) in q.rubric.criteria" :key="ci">{{ c }}</li></ul>
                      </div>
                    </div>
                  </div>
                  <div v-if="q.type !== 'code' && submittedAnswers[q.question_id]" class="answer-feedback"
                    :class="submittedAnswers[q.question_id].correct ? 'feedback-correct' : 'feedback-wrong'">
                    <span v-if="submittedAnswers[q.question_id].correct">✓ 回答正确！得分：{{ submittedAnswers[q.question_id].score }}</span>
                    <span v-else>✗ 回答错误。正确答案：{{ q.answer }}，得分：{{ submittedAnswers[q.question_id].score }}</span>
                  </div>
                </div>
              </template>

              <!-- 底部提交栏 -->
              <div class="submit-bar">
                <el-button type="primary" :loading="submitting" @click="handleSubmitAnswers">
                  提交答案
                </el-button>
              </div>
            </div>
          </div>
          <el-empty v-else description="暂无练习题目，请先生成" />
        </div>
      </el-tab-pane>

      <!-- Code Tab -->
      <el-tab-pane name="code">
        <template #label>
          <span class="tab-label"><el-icon><Monitor /></el-icon> 代码示例</span>
        </template>
        <div class="tab-content">
          <div class="tab-action-bar">
            <el-button type="warning" plain size="small" :loading="regeneratingType === 'code'" @click="handleRegenerateSingle('code')">重新生成</el-button>
          </div>
          <div v-if="isFiltered('code')" class="quality-gate-card">
            <div class="gate-icon">⚠️</div>
            <div class="gate-info">
              <div class="gate-title">质量未达标</div>
              <div class="gate-detail">当前评分 {{ getFilteredInfo('code')?.score }} 分，质量未达标</div>
            </div>
            <el-button type="warning" plain size="small" :loading="regeneratingType === 'code'" @click="handleRegenerateSingle('code')">重新生成</el-button>
          </div>
          <div v-if="store.resources.code">
            <!-- Info -->
            <el-descriptions :column="2" border class="code-info">
              <el-descriptions-item label="标题">{{ store.resources.code.title || '代码示例' }}</el-descriptions-item>
              <el-descriptions-item label="难度">
                <el-tag :type="difficultyType(store.resources.code.difficulty)">
                  {{ store.resources.code.difficulty || '中等' }}
                </el-tag>
              </el-descriptions-item>
            </el-descriptions>
            <p v-if="store.resources.code.description" class="code-desc">{{ store.resources.code.description }}</p>

            <!-- Input/Output Examples -->
            <div v-if="store.resources.code.input_example" class="example-box">
              <h4>输入示例：</h4>
              <pre>{{ store.resources.code.input_example }}</pre>
            </div>
            <div v-if="store.resources.code.expected_output" class="example-box">
              <h4>期望输出：</h4>
              <pre>{{ store.resources.code.expected_output }}</pre>
            </div>

            <!-- Code Block -->
            <div class="code-block">
              <div class="code-toolbar">
                <el-button size="small" @click="handleCopyCode">复制代码</el-button>
                <el-button size="small" type="primary" :loading="runningCode" @click="handleRunCode">运行代码</el-button>
              </div>
              <pre><code class="hljs" v-html="highlightedCode"></code></pre>
            </div>

            <!-- Run Result -->
            <div v-if="store.codeResult" class="run-result" :class="store.codeResult.success ? 'success' : 'error'">
              <h4>运行结果：</h4>
              <pre>{{ store.codeResult.stdout || store.codeResult.stderr || store.codeResult.error }}</pre>
            </div>

            <!-- Test Cases -->
            <div v-if="store.resources.code.test_cases?.length" class="test-cases">
              <h4>测试用例：</h4>
              <el-table :data="store.resources.code.test_cases" border size="small">
                <el-table-column prop="input" label="输入" />
                <el-table-column prop="expected" label="期望输出" />
              </el-table>
            </div>
          </div>
          <el-empty v-else description="暂无代码示例，请先生成" />
        </div>
      </el-tab-pane>

      <!-- 拓展阅读 Tab -->
      <el-tab-pane name="reading_material">
        <template #label>
          <span class="tab-label"><el-icon><Reading /></el-icon> 拓展阅读</span>
        </template>
        <div class="tab-content">
          <div class="tab-action-bar">
            <el-button type="warning" plain size="small" :loading="regeneratingType === 'reading_material'" @click="handleRegenerateSingle('reading_material')">重新生成</el-button>
          </div>
          <div v-if="isFiltered('reading_material')" class="quality-gate-card">
            <div class="gate-icon">⚠️</div>
            <div class="gate-info">
              <div class="gate-title">质量未达标</div>
              <div class="gate-detail">当前评分 {{ getFilteredInfo('reading_material')?.score }} 分，质量未达标</div>
            </div>
            <el-button type="warning" plain size="small" :loading="regeneratingType === 'reading_material'" @click="handleRegenerateSingle('reading_material')">重新生成</el-button>
          </div>
          <div v-if="store.resources.reading_material">
            <template v-for="(seg, i) in readingSegments" :key="i">
              <div v-if="seg.type === 'markdown'" class="markdown-body" v-html="renderMd(seg.content)"></div>
              <MermaidDiagram v-else :code="seg.content" :forceKey="mermaidRenderKey" />
            </template>
          </div>
          <el-empty v-else description="暂无拓展阅读材料，请先生成" />
        </div>
      </el-tab-pane>

      <!-- 术语词汇 Tab -->
      <el-tab-pane name="glossary">
        <template #label>
          <span class="tab-label"><el-icon><CollectionTag /></el-icon> 术语词汇</span>
        </template>
        <div class="tab-content">
          <div class="tab-action-bar">
            <el-button type="warning" plain size="small" :loading="regeneratingType === 'glossary'" @click="handleRegenerateSingle('glossary')">重新生成</el-button>
          </div>
          <div v-if="isFiltered('glossary')" class="quality-gate-card">
            <div class="gate-icon">⚠️</div>
            <div class="gate-info">
              <div class="gate-title">质量未达标</div>
              <div class="gate-detail">当前评分 {{ getFilteredInfo('glossary')?.score }} 分，质量未达标</div>
            </div>
            <el-button type="warning" plain size="small" :loading="regeneratingType === 'glossary'" @click="handleRegenerateSingle('glossary')">重新生成</el-button>
          </div>
          <div v-if="store.resources.glossary?.terms?.length">
            <h3 class="section-title">{{ store.resources.glossary.title || '术语词汇表' }}</h3>
            <div class="glossary-grid">
              <div v-for="(term, i) in store.resources.glossary.terms" :key="i" class="glossary-card">
                <div class="glossary-term">{{ term.term }}</div>
                <div class="glossary-def">{{ term.definition }}</div>
                <div v-if="term.example" class="glossary-example">
                  <el-icon><InfoFilled /></el-icon> {{ term.example }}
                </div>
                <div v-if="term.related_terms?.length" class="glossary-related">
                  <el-tag v-for="rt in term.related_terms" :key="rt" size="small" type="info" effect="plain" style="margin:2px">{{ rt }}</el-tag>
                </div>
              </div>
            </div>
          </div>
          <el-empty v-else description="暂无术语词汇，请先生成" />
        </div>
      </el-tab-pane>

      <!-- 知识关联图 Tab -->
      <el-tab-pane name="knowledge_link">
        <template #label>
          <span class="tab-label"><el-icon><Connection /></el-icon> 知识关联</span>
        </template>
        <div class="tab-content">
          <div class="tab-action-bar">
            <el-button type="warning" plain size="small" :loading="regeneratingType === 'knowledge_link'" @click="handleRegenerateSingle('knowledge_link')">重新生成</el-button>
          </div>
          <div v-if="isFiltered('knowledge_link')" class="quality-gate-card">
            <div class="gate-icon">⚠️</div>
            <div class="gate-info">
              <div class="gate-title">质量未达标</div>
              <div class="gate-detail">当前评分 {{ getFilteredInfo('knowledge_link')?.score }} 分，质量未达标</div>
            </div>
            <el-button type="warning" plain size="small" :loading="regeneratingType === 'knowledge_link'" @click="handleRegenerateSingle('knowledge_link')">重新生成</el-button>
          </div>
          <KnowledgeGraph v-if="knowledgeLinkData" :graphData="knowledgeLinkData" />
          <el-empty v-else description="暂无知识关联图，请先生成" />
        </div>
      </el-tab-pane>

      <!-- 学习总结 Tab -->
      <el-tab-pane name="summary">
        <template #label>
          <span class="tab-label"><el-icon><DataBoard /></el-icon> 学习总结</span>
        </template>
        <div class="tab-content">
          <div class="tab-action-bar">
            <el-button type="warning" plain size="small" :loading="regeneratingType === 'summary'" @click="handleRegenerateSingle('summary')">重新生成</el-button>
          </div>
          <div v-if="isFiltered('summary')" class="quality-gate-card">
            <div class="gate-icon">⚠️</div>
            <div class="gate-info">
              <div class="gate-title">质量未达标</div>
              <div class="gate-detail">当前评分 {{ getFilteredInfo('summary')?.score }} 分，质量未达标</div>
            </div>
            <el-button type="warning" plain size="small" :loading="regeneratingType === 'summary'" @click="handleRegenerateSingle('summary')">重新生成</el-button>
          </div>
          <div v-if="store.resources.summary">
            <template v-for="(seg, i) in summarySegments" :key="i">
              <div v-if="seg.type === 'markdown'" class="markdown-body" v-html="renderMd(seg.content)"></div>
              <MermaidDiagram v-else :code="seg.content" :forceKey="mermaidRenderKey" />
            </template>
          </div>
          <el-empty v-else description="暂无学习总结，请先生成" />
        </div>
      </el-tab-pane>
    </el-tabs>

    <!-- Agent 协作可视化 -->
    <AgentCollaboration
      v-if="store.generating"
      :agents="agentStatusList"
      :is-running="store.generating"
      style="margin-top: 24px;"
    />

    <!-- Workflow Dialog (legacy) -->
    <el-dialog v-model="showWorkflow" title="资源生成进度" width="500px" :close-on-click-modal="false">
      <el-progress :percentage="Math.round((store.workflowState?.progress || 0) * 100)" :stroke-width="16" />
      <p class="workflow-step">{{ stepName(store.workflowState?.current_step || '') }}</p>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted, onUnmounted, watch, nextTick } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { MagicStick, Loading, DataAnalysis, Document, VideoCamera, Share, EditPen, Monitor, Reading, CollectionTag, InfoFilled, Connection, DataBoard } from '@element-plus/icons-vue'
import { marked } from 'marked'
import hljs from 'highlight.js'
import 'highlight.js/styles/github.css'
import { useResourceStore } from '@/stores/resourceStore'
import { useLearningPathStore } from '@/stores/learningPathStore'
import { renderMath } from '@/utils/renderMath'
import { renderMd } from '@/utils/renderMarkdown'
import AgentCollaboration from '@/components/AgentCollaboration.vue'
import KnowledgeGraph from '@/components/KnowledgeGraph.vue'
import MermaidDiagram from '@/components/MermaidDiagram.vue'
import Artplayer from 'artplayer'

const videoPlayerRef = ref<HTMLElement | null>(null)
let artInstance: Artplayer | null = null

function formatDuration(seconds: number): string {
  if (!seconds) return '0:00'
  const m = Math.floor(seconds / 60)
  const s = Math.floor(seconds % 60)
  return `${m}:${s.toString().padStart(2, '0')}`
}

function initArtplayer(url: string) {
  if (artInstance) {
    artInstance.destroy()
    artInstance = null
  }
  if (!videoPlayerRef.value) return

  artInstance = new Artplayer({
    container: videoPlayerRef.value,
    url: url,
    type: 'mp4',
    autoplay: false,
    pip: true,
    autoSize: true,
    autoMini: true,
    fullscreen: true,
    fullscreenWeb: true,
    subtitleOffset: true,
    miniProgressBar: true,
    mutex: true,
    backdrop: true,
    playsInline: true,
    autoPlayback: true,
    airplay: true,
    theme: '#4F46E5',
    lang: navigator.language.toLowerCase() === 'zh-cn' ? 'zh-cn' : 'en',
    moreVideoAttr: {
      crossOrigin: 'anonymous',
    },
  })
}

// ── 混合内容解析：Markdown + Mermaid ─────────────────────
interface ContentSegment {
  type: 'markdown' | 'mermaid'
  content: string
}

function parseMixedContent(raw: any): ContentSegment[] {
  const text = toMarkdownText(raw)
  if (!text) return []
  // 去掉外层 ```markdown / ```md 包裹（按首尾行剥离，避免正则误匹配内嵌代码块）
  let cleaned = text.trim()
  const firstLine = cleaned.split('\n')[0]?.trim()
  if (firstLine === '```markdown' || firstLine === '```md') {
    cleaned = cleaned.split('\n').slice(1).join('\n')
    // 去掉末尾的 ```
    const lastLine = cleaned.split('\n').pop()?.trim()
    if (lastLine === '```') {
      cleaned = cleaned.split('\n').slice(0, -1).join('\n')
    }
    cleaned = cleaned.trim()
  }
  const segments: ContentSegment[] = []
  const mermaidRe = /```mermaid\s*\n([\s\S]*?)```/g
  let lastIdx = 0, match: RegExpExecArray | null
  while ((match = mermaidRe.exec(cleaned)) !== null) {
    const before = cleaned.slice(lastIdx, match.index).trim()
    if (before) segments.push({ type: 'markdown', content: before })
    segments.push({ type: 'mermaid', content: match[1].trim() })
    lastIdx = match.index + match[0].length
  }
  const after = cleaned.slice(lastIdx).trim()
  if (after) segments.push({ type: 'markdown', content: after })
  if (segments.length === 0) segments.push({ type: 'markdown', content: cleaned.trim() })
  return segments
}

const docSegments = computed(() => parseMixedContent(store.resources.document?.content))
const readingSegments = computed(() => parseMixedContent(store.resources.reading_material?.content))
const summarySegments = computed(() => parseMixedContent(store.resources.summary?.content))

// 配置 marked + highlight.js（文档中代码块高亮）
const renderer = new marked.Renderer()
renderer.code = function (text: string, lang: string | undefined) {
  if (!text) return '<pre><code></code></pre>'
  const language = (lang || '').toLowerCase()
  if (['plantuml', 'uml', 'dot', 'graphviz'].includes(language)) {
    const escaped = text.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
    return `<div class="diagram-block" style="margin:12px 0;border-radius:8px;overflow:hidden;border:1px solid #d0d5dd;background:#f8f9fb"><div style="display:flex;align-items:center;justify-content:space-between;padding:6px 14px;background:#eef1f6;border-bottom:1px solid #d0d5dd"><span style="color:#667085;font-family:monospace;font-size:11px;text-transform:uppercase">${language}</span><button class="copy-block-btn" style="background:transparent;border:1px solid #d0d5dd;border-radius:4px;padding:2px 8px;cursor:pointer;color:#667085;font-size:11px" data-copy-text="${escaped}">复制</button></div><pre style="margin:0;padding:16px;background:#f8f9fb;color:#344054;overflow-x:auto;font-size:13px;line-height:1.6;white-space:pre-wrap;word-break:break-word"><code>${escaped}</code></pre></div>`
  }
  let highlighted: string
  if (language && hljs.getLanguage(language)) {
    highlighted = hljs.highlight(text, { language }).value
  } else {
    highlighted = hljs.highlightAuto(text).value
  }
  const escaped = text.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
  return `<div style="margin:12px 0;border-radius:8px;overflow:hidden;border:1px solid #d0d5dd;background:#fff"><div style="display:flex;align-items:center;justify-content:space-between;padding:6px 14px;background:#f2f4f7;border-bottom:1px solid #d0d5dd"><span style="color:#667085;font-family:monospace;font-size:11px;text-transform:uppercase">${language || 'code'}</span><button class="copy-block-btn" style="background:transparent;border:1px solid #d0d5dd;border-radius:4px;padding:2px 8px;cursor:pointer;color:#667085;font-size:11px" data-copy-text="${escaped}">复制</button></div><pre style="margin:0;padding:16px;background:#fff;overflow-x:auto;font-size:13px;line-height:1.6"><code style="font-family:monospace;font-size:13px;background:transparent;color:#1d2939">${highlighted}</code></pre></div>`
}
marked.use({ renderer, breaks: true })
import type { Question } from '@/types'
import { useLearningTracker } from '@/composables/useLearningTracker'

const route = useRoute()
const store = useResourceStore()
const pathStore = useLearningPathStore()

// ── 质量门控 ──────────────────────────────────────
const regeneratingType = ref('')

function isFiltered(resourceType: string): boolean {
  return store.resources.filteredResources?.some((f: any) => f.type === resourceType) || false
}

function getFilteredInfo(resourceType: string) {
  return store.resources.filteredResources?.find((f: any) => f.type === resourceType) || null
}

const RESOURCE_TYPE_MAP: Record<string, string> = {
  document: 'document', questions: 'question', code: 'code',
  mindmap: 'mindmap', video: 'ppt_video', reading_material: 'reading_material',
  glossary: 'glossary', knowledge_link: 'knowledge_link', summary: 'summary',
}

async function handleRegenerateSingle(resourceType: string) {
  const mappedType = RESOURCE_TYPE_MAP[resourceType] || resourceType
  // 自动获取 stage_id：优先用 currentStageIndex，没有则取第一个阶段
  let stageId = pathStore.learningPath?.stages?.[pathStore.currentStageIndex ?? 0]?.stage_id
  if (!stageId && pathStore.learningPath?.stages?.length) {
    stageId = pathStore.learningPath.stages[0].stage_id
  }
  if (!stageId) {
    ElMessage.error('当前没有可关联的学习阶段')
    return
  }
  await ElMessageBox.confirm(
    `确定要重新生成「${store.getTabLabel?.(resourceType) || resourceType}」吗？旧资源将被删除。`,
    '确认重新生成',
    { confirmButtonText: '确定', cancelButtonText: '取消', type: 'warning' }
  )
  regeneratingType.value = resourceType
  try {
    const { studentAPI } = await import('@/api')
    await studentAPI.regenerateResource(mappedType, stageId)
    ElMessage.success('资源已重新生成')
    // 清空答题记录，重新开始
    submittedAnswers.value = {}
    Object.keys(answers).forEach(k => delete answers[k])
    selectedQuestionIdx.value = 0
    await store.loadForStage(pathStore.currentStageIndex, pathStore.learningPath?.stages)
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || '重新生成失败')
  } finally {
    regeneratingType.value = ''
  }
}

// 监听 ppt_video 数据变化，初始化播放器
watch(
  () => store.resources.ppt_video?.video_url,
  (url) => {
    if (url) {
      nextTick(() => initArtplayer(url))
    }
  },
  { immediate: true }
)

// 学习行为追踪
const stageId = computed(() => {
  const s = route.query.stage
  return s ? Number(s) : undefined
})
const { trackEvent } = useLearningTracker({ resourceType: 'resource_page', stageId: stageId.value })

// ── Local state ────────────────────────────────────

const activeTab = ref('document')
const mermaidRenderKey = ref(0)
const openQuestions = ref<number[]>([])
const answers = reactive<Record<number, string>>({})
const submittedAnswers = ref<Record<number, { answer: string; correct: boolean; score: number }>>({})
const codeResults = ref<Record<number, { correct: boolean; feedback: string; details?: string }>>({})
const codeRunning = ref<Record<number, boolean>>({})
const submitting = ref(false)
const runningCode = ref(false)
const showWorkflow = ref(false)
const viewMode = ref<'single' | 'all'>('single')
const selectedQuestionIdx = ref(0)
const submittedCount = computed(() => Object.keys(submittedAnswers.value).length)

// 画像信息（用于推荐理由展示）
const profileInfo = reactive({
  major: '',
  level: '',
  goal: '',
  weakness: [] as string[],
})

// ── Markmap ────────────────────────────────────────

const mindmapRef = ref<HTMLElement | null>(null)
const mindmapShowSource = ref(false)

const mindmapSourceText = computed(() => {
  return store.resources.mindmap_markdown || ''
})

const mindmapContainerRef = ref<HTMLElement | null>(null)
let markmapInstance: any = null
let mindmapScale = 1

async function renderMindmap() {
  const md = store.resources.mindmap_markdown
  if (!md) return

  await nextTick()
  const el = mindmapContainerRef.value
  if (!el || el.offsetWidth === 0) {
    setTimeout(renderMindmap, 200)
    return
  }

  try {
    const { Transformer } = await import('markmap-lib')
    const { Markmap } = await import('markmap-view')

    const transformer = new Transformer()
    const { root } = transformer.transform(md)

    el.innerHTML = ''
    const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg')
    el.appendChild(svg)

    // 不用 autoFit，手动等浏览器布局完成后调用 fit()
    markmapInstance = Markmap.create(svg, {
      autoFit: false,
      duration: 300,
      maxWidth: 280,
      paddingX: 12,
    }, root)

    // 等浏览器完成布局，SVG 尺寸确定后再 fit
    requestAnimationFrame(() => {
      if (markmapInstance?.fit) markmapInstance.fit()
    })
  } catch (e) {
    console.error('思维导图渲染失败:', e)
    el.innerHTML = `<pre style="padding:16px;font-size:13px;white-space:pre-wrap;color:#667085">${md.replace(/</g, '&lt;')}</pre>`
  }
}

function downloadMindmap() {
  const md = store.resources.mindmap_markdown
  if (!md) return
  const blob = new Blob([md], { type: 'text/markdown;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a'); a.href = url; a.download = 'mindmap.md'
  document.body.appendChild(a); a.click(); document.body.removeChild(a)
  URL.revokeObjectURL(url)
}

function zoomMindmap(factor: number) {
  if (!mindmapContainerRef.value) return
  const svg = mindmapContainerRef.value.querySelector('svg')
  if (!svg) return
  mindmapScale *= factor
  mindmapScale = Math.max(0.3, Math.min(3, mindmapScale))
  svg.style.transform = `scale(${mindmapScale})`
}

function fitMindmap() {
  mindmapScale = 1
  if (!mindmapContainerRef.value) return
  const svg = mindmapContainerRef.value.querySelector('svg')
  if (svg) svg.style.transform = 'scale(1)'
  if (markmapInstance?.fit) markmapInstance.fit()
}

watch(() => store.resources.mindmap_markdown, (val) => {
  if (val && activeTab.value === 'mindmap') {
    nextTick(renderMindmap)
  }
})

watch(activeTab, (tab) => {
  if (tab === 'mindmap') nextTick(renderMindmap)
  mermaidRenderKey.value++
  trackEvent('resource_view', { tab, stage_id: stageId.value })
})

// ── 知识关联图（复用 KnowledgeGraph 组件） ─────────────────────

const knowledgeLinkData = computed(() => {
  const data = store.resources.knowledge_link
  if (!data?.nodes?.length) return null
  return {
    title: data.title || '知识点关联图',
    knowledge_point_count: data.nodes.length,
    nodes: data.nodes,
    edges: data.edges || [],
  }
})

// ── Computed ────────────────────────────────────

const hasAnyData = computed(() =>
  store.resources.document || store.resources.questions || store.resources.code ||
  store.resources.ppt_video || store.resources.mindmap_markdown ||
  store.resources.reading_material || store.resources.glossary ||
  store.resources.knowledge_link || store.resources.summary
)

const agentStatusList = computed(() => {
  const steps = store.workflowState?.steps_history || []
  const currentStep = store.workflowState?.current_step || ''

  const agents = [
    { key: 'build_profile', name: '画像构建 Agent', description: '抽取学生特征（专业、年级、目标等）' },
    { key: 'generate_path', name: '路径规划 Agent', description: '根据画像规划个性化学习路径' },
    { key: 'generate_knowledge_graph', name: '知识图谱 Agent', description: '基于学习路径生成全局知识图谱' },
    { key: 'generate_document', name: '文档生成 Agent', description: '生成 Markdown 学习文档 + AI 配图' },
    { key: 'generate_ppt_video', name: 'PPT 视频 Agent', description: '生成 PPT 教学视频' },
    { key: 'generate_mindmap', name: '思维导图 Agent', description: '生成 Markdown 思维导图' },
    { key: 'generate_questions', name: '题库生成 Agent', description: '生成选择题、填空题、编程题、案例分析题' },
    { key: 'generate_code', name: '代码实操 Agent', description: '生成可运行的代码示例' },
    { key: 'generate_reading', name: '拓展阅读 Agent', description: '生成拓展阅读材料' },
    { key: 'generate_glossary', name: '术语词汇 Agent', description: '生成术语词汇卡片' },
    { key: 'generate_knowledge_link', name: '知识图谱 Agent', description: '生成知识点关联图' },
    { key: 'generate_summary', name: '学习总结 Agent', description: '生成学习总结报告' },
    { key: 'quality_evaluate', name: '质量评估 Agent', description: '评估所有资源质量' },
  ]

  return agents.map(agent => {
    const stepInfo = steps.find((s: any) => s.step === agent.key)
    let status: string = 'waiting'

    if (stepInfo) {
      status = stepInfo.status === 'skipped' ? 'skipped' : stepInfo.status
    } else if (currentStep === agent.key) {
      status = 'running'
    } else if (steps.length > 0) {
      const currentIndex = agents.findIndex(a => a.key === currentStep)
      const agentIndex = agents.findIndex(a => a.key === agent.key)
      if (agentIndex < currentIndex) status = 'completed'
    }

    return { ...agent, status }
  })
})

const questions = computed<Question[]>(() => store.resources.questions?.questions || [])

function toMarkdownText(raw: any): string {
  if (!raw) return ''
  let text = typeof raw === 'string' ? raw : (raw.content || JSON.stringify(raw))
  text = text.replace(/\\n/g, '\n').replace(/\r\n/g, '\n')
  return text
}

const renderedDoc = computed(() => {
  return renderMath(marked(toMarkdownText(store.resources.document?.content)) as string)
})

const renderedReading = computed(() => {
  return renderMath(marked(toMarkdownText(store.resources.reading_material?.content)) as string)
})

const renderedSummary = computed(() => {
  const raw = store.resources.summary?.content
  if (!raw) return ''
  const text = typeof raw === 'string' ? raw : (raw.content || JSON.stringify(raw))
  const cleaned = text.replace(/\\n/g, '\n').replace(/\r\n/g, '\n')
  try {
    const html = marked(cleaned) as string
    return renderMath(html)
  } catch (e) {
    console.error('Summary marked error:', e)
    return `<pre>${cleaned}</pre>`
  }
})

const highlightedCode = computed(() => {
  if (!store.resources.code?.code) return ''
  try {
    return hljs.highlight(store.resources.code.code, { language: 'python' }).value
  } catch {
    return store.resources.code.code
  }
})

// ── Helpers ────────────────────────────────────────

function difficultyType(d?: string) {
  if (d === 'hard') return 'danger'
  if (d === 'medium') return 'warning'
  return 'success'
}

function stepName(step: string): string {
  const map: Record<string, string> = {
    build_profile: '构建画像', generate_path: '生成路径',
    generate_knowledge_graph: '生成知识图谱',
    generate_document: '生成文档', generate_ppt_video: '生成PPT视频',
    generate_mindmap: '生成思维导图', generate_questions: '生成题目',
    generate_code: '生成代码', generate_reading: '生成拓展阅读',
    generate_glossary: '生成术语词汇', generate_knowledge_link: '生成知识关联',
    generate_summary: '生成学习总结', quality_evaluate: '质量评估',
  }
  return map[step] || step
}

// ── Actions ────────────────────────────────────────

async function handleGenerateAll() {
  // Ensure we have a topic
  if (!store.currentTopic) {
    try {
      const axios = (await import('@/utils/axios')).default
      const profile = await axios.get('/v1/student/profile')
      if (profile?.goal) store.currentTopic = profile.goal
      else if (profile?.major) store.currentTopic = profile.major
    } catch { /* ignore */ }
  }
  if (!store.currentTopic) {
    ElMessage.warning('请先在「学习画像」页面构建学习画像，确定学习主题')
    return
  }

  showWorkflow.value = true
  try {
    const sessionId = await store.startWorkflow()
    await store.runWorkflow(sessionId, {
      onComplete: () => {
        ElMessage.success('全部资源生成完成！')
        showWorkflow.value = false
      },
      onError: (err) => {
        ElMessage.error('生成失败：' + err.message)
        showWorkflow.value = false
      },
    })
  } catch (err: any) {
    ElMessage.error('启动失败：' + (err?.message || '未知错误'))
    showWorkflow.value = false
  }
}

async function handleRegenerate() {
  // 清除答题记录
  submittedAnswers.value = {}
  Object.keys(answers).forEach(k => delete answers[k])
  Object.keys(codeResults.value).forEach(k => delete codeResults.value[k])
  selectedQuestionIdx.value = 0

  // 优先使用阶段级重新生成
  if (store.currentStageIndex !== null && pathStore.learningPath?.stages) {
    const stageId = pathStore.learningPath.stages[store.currentStageIndex]?.stage_id
    if (stageId !== undefined) {
      try {
        await pathStore.generateStageResources(stageId, true)
        ElMessage.success('资源已重新生成')
        return
      } catch {
        ElMessage.error('重新生成失败，请重试')
        return
      }
    }
  }
  // fallback：无阶段信息时用旧的逐类型生成
  const topic = store.currentTopic || pathStore.getStageTopic()
  if (!topic) {
    ElMessage.warning('请先确定学习主题')
    return
  }
  await store.fetchResources(topic, true)
  ElMessage.success('资源已重新生成')
}

function selectQuestion(idx: number) {
  selectedQuestionIdx.value = idx
  viewMode.value = 'single'
}

async function handleSubmitAnswers() {
  const count = Object.values(answers).filter(v => v).length
  if (count === 0) {
    ElMessage.warning('请先作答再提交')
    return
  }
  submitting.value = true
  try {
    const results = await store.submitAnswers(answers)
    // 更新本地已提交状态
    const newMap = { ...submittedAnswers.value }
    for (const res of (results || [])) {
      if (!res?.evaluations) continue
      for (const ev of res.evaluations) {
        if (ev?.question_id !== undefined) {
          newMap[ev.question_id] = {
            answer: answers[ev.question_id] || '',
            correct: ev.correct,
            score: ev.score,
          }
        }
      }
    }
    submittedAnswers.value = newMap
    ElMessage.success(`${count} 道题答案已提交`)
  } catch {
    ElMessage.error('提交失败')
  } finally {
    submitting.value = false
  }
}

async function handleRunCode() {
  if (!store.resources.code?.code) return
  runningCode.value = true
  try {
    await store.runCode(store.resources.code.code)
  } catch {
    ElMessage.error('代码运行失败')
  } finally {
    runningCode.value = false
  }
}

function handleCopyCode() {
  if (!store.resources.code?.code) return
  navigator.clipboard.writeText(store.resources.code.code)
  ElMessage.success('代码已复制到剪贴板')
}

async function handleRunTestCode(q: any) {
  const code = answers[q.question_id]
  if (!code?.trim()) {
    ElMessage.warning('请先输入代码')
    return
  }
  codeRunning.value[q.question_id] = true
  try {
    const axios = (await import('@/utils/axios')).default
    const res = await axios.post('/v1/student/question/submit', {
      question_id: q.question_id,
      answer: code,
      topic: store.currentTopic,
    })
    const ev = res?.evaluations?.[0]
    if (ev) {
      const details = ev.code_results?.results
        ? ev.code_results.results.map((r: any) =>
          `用例${r.test_case}: ${r.status === 'passed' ? '✓ 通过' : '✗ 失败'}${r.error ? ' - ' + r.error : ''}`
        ).join('\n')
        : undefined
      codeResults.value[q.question_id] = {
        correct: ev.correct,
        feedback: ev.feedback || (ev.correct ? '✓ 全部通过！' : '✗ 未全部通过'),
        details,
      }
      // 同步到 submittedAnswers
      const newMap = { ...submittedAnswers.value }
      newMap[q.question_id] = { answer: code, correct: ev.correct, score: ev.score }
      submittedAnswers.value = newMap
    }
  } catch {
    ElMessage.error('代码运行失败')
  } finally {
    codeRunning.value[q.question_id] = false
  }
}

async function loadPreviousAnswers() {
  try {
    const axios = (await import('@/utils/axios')).default
    const data = await axios.get('/v1/student/question/answers')
    const map: Record<number, { answer: string; correct: boolean; score: number }> = {}
    for (const a of (data.answers || [])) {
      map[a.question_id] = { answer: a.answer, correct: a.correct, score: a.score }
      // 回填到 answers 让用户能看到之前的选项
      if (!answers[a.question_id]) {
        answers[a.question_id] = a.answer
      }
    }
    submittedAnswers.value = map
    // 回填代码题结果
    const questionsList = store.resources.questions?.questions || []
    for (const q of questionsList) {
      if (q.type === 'code' && map[q.question_id]) {
        const sa = map[q.question_id]
        codeResults.value[q.question_id] = {
          correct: sa.correct,
          feedback: sa.correct ? '✓ 全部通过！' : '✗ 未全部通过，可修改代码后重新运行',
        }
      }
    }
  } catch { /* 静默失败 */ }
}

// ── Lifecycle ──────────────────────────────────────

onMounted(async () => {
  // 代码块复制
  document.addEventListener('click', (e) => {
    const btn = (e.target as HTMLElement).closest('.copy-block-btn') as HTMLButtonElement | null
    if (btn) {
      const raw = btn.getAttribute('data-copy-text') || ''
      const text = raw.replace(/&amp;/g, '&').replace(/&lt;/g, '<').replace(/&gt;/g, '>').replace(/&quot;/g, '"').replace(/&#39;/g, "'")
      navigator.clipboard.writeText(text).then(() => {
        btn.textContent = '已复制'; btn.style.color = '#22c55e'; btn.style.borderColor = '#22c55e'
        setTimeout(() => { btn.textContent = '复制'; btn.style.color = '#667085'; btn.style.borderColor = '#d0d5dd' }, 2000)
      })
      return
    }
  })

  // 无条件加载 profile 数据（推荐依据展示用）
  try {
    const axios = (await import('@/utils/axios')).default
    const profile = await axios.get('/v1/student/profile')
    if (profile?.goal) store.currentTopic = profile.goal
    else if (profile?.major) store.currentTopic = profile.major
    profileInfo.major = profile?.major || ''
    profileInfo.level = profile?.knowledge_level || ''
    profileInfo.goal = profile?.goal || ''
    profileInfo.weakness = profile?.weakness || []
  } catch { /* ignore */ }

  // 从学习路径跳转（带 stage 参数）
  const stageParam = route.query.stage
  if (stageParam !== undefined) {
    const stageIndex = parseInt(String(stageParam), 10)
    if (!pathStore.learningPath) await pathStore.fetchPath()
    // 切换阶段前先清除答题状态
    submittedAnswers.value = {}
    Object.keys(answers).forEach(k => delete answers[k])
    Object.keys(codeResults.value).forEach(k => delete codeResults.value[k])
    selectedQuestionIdx.value = 0
    await store.loadForStage(stageIndex, pathStore.learningPath?.stages)
    await loadPreviousAnswers()
    return
  }

  // 无 stage 参数时，自动加载当前阶段的资源
  if (!pathStore.learningPath) await pathStore.fetchPath()
  const stageIdx = pathStore.currentStage ?? 0
  // 切换阶段前先清除答题状态
  submittedAnswers.value = {}
  Object.keys(answers).forEach(k => delete answers[k])
  Object.keys(codeResults.value).forEach(k => delete codeResults.value[k])
  selectedQuestionIdx.value = 0
  if (pathStore.learningPath?.stages?.length) {
    await store.loadForStage(stageIdx, pathStore.learningPath.stages)
  } else {
    // 学习路径未加载时，至少用当前阶段索引尝试
    await store.loadForStage(stageIdx)
  }
  await loadPreviousAnswers()
})

onUnmounted(() => {
  window.removeEventListener('resource-generated', _onResourceGenerated)
})

// 监听后台资源生成完成通知，自动刷新
function _onResourceGenerated() {
  // 清除旧答题记录
  submittedAnswers.value = {}
  Object.keys(answers).forEach(k => delete answers[k])
  Object.keys(codeResults.value).forEach(k => delete codeResults.value[k])
  selectedQuestionIdx.value = 0

  if (pathStore.learningPath?.stages) {
    store.loadForStage(pathStore.currentStageIndex ?? 0, pathStore.learningPath.stages)
  }
}
onMounted(() => {
  window.addEventListener('resource-generated', _onResourceGenerated)
})
</script>

<style scoped>
.resources-page {
  max-width: 1400px;
}

.action-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 20px;
  flex-wrap: wrap;
  gap: 12px;
}

.action-left {
  display: flex;
  gap: 12px;
}

.loading-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 80px 0;
  color: var(--color-text-muted);
  gap: 16px;
}

.recommend-card {
  margin-bottom: 20px;
  border-radius: var(--radius-lg);
  background: linear-gradient(135deg, var(--color-primary-lightest) 0%, #f0fdf4 100%);
  border: 1px solid var(--color-primary-lightest);
}

.recommend-content {
  display: flex;
  align-items: flex-start;
  gap: 12px;
}

.recommend-text {
  flex: 1;
  font-size: 14px;
  line-height: 1.8;
  color: var(--color-text-secondary);
}

.recommend-title {
  font-weight: 600;
  color: var(--color-primary);
}

.recommend-reason strong {
  color: var(--color-text-primary);
  font-weight: 600;
}

.tab-label {
  display: flex;
  align-items: center;
  gap: 6px;
}

.tab-content {
  background: var(--color-bg-card);
  border-radius: var(--radius-lg);
  padding: var(--space-card-padding);
  min-height: 400px;
}

.tab-action-bar {
  display: flex;
  justify-content: flex-end;
  margin-bottom: 12px;
  padding-bottom: 12px;
  border-bottom: 1px solid var(--color-border-light);
}

/* ── Quality gate ──────────────────────────── */

.quality-gate-card {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 16px 20px;
  margin-bottom: 16px;
  background: #FFF7ED;
  border: 1px solid #FDBA74;
  border-radius: var(--radius-md);
}
.gate-icon { font-size: 22px; }
.gate-info { flex: 1; }
.gate-title { font-weight: 600; font-size: 14px; color: #9A3412; }
.gate-detail { font-size: var(--text-xs); color: #C2410C; margin-top: 2px; }

.section-title {
  font-size: var(--text-xl);
  font-weight: 700;
  margin-bottom: 20px;
  color: var(--color-text-primary);
}

/* ── Document ──────────────────────────────── */

.doc-images {
  display: flex;
  gap: 16px;
  margin-bottom: 24px;
  flex-wrap: wrap;
}

.doc-image-item {
  flex: 1;
  min-width: 200px;
  max-width: 400px;
}

.doc-image-item img {
  width: 100%;
  border-radius: var(--radius-md);
  border: 1px solid var(--color-border);
}

.image-caption {
  text-align: center;
  font-size: var(--text-xs);
  color: var(--color-text-muted);
  margin-top: 6px;
}

.markdown-body {
  line-height: 1.8;
  font-size: var(--text-base);
  color: var(--color-text-primary);
  word-wrap: break-word;
  overflow-wrap: break-word;
}

.markdown-body :deep(h1) { font-size: 24px; margin: 20px 0 12px; color: var(--color-text-primary); font-weight: 700; }
.markdown-body :deep(h2) { font-size: 20px; margin: 18px 0 10px; color: var(--color-text-primary); font-weight: 700; }
.markdown-body :deep(h3) { font-size: var(--text-lg); margin: 14px 0 8px; color: var(--color-text-primary); font-weight: 600; }
.markdown-body :deep(h4) { font-size: 16px; margin: 12px 0 6px; color: var(--color-text-primary); font-weight: 600; }
.markdown-body :deep(h5) { font-size: 14px; margin: 10px 0 4px; color: var(--color-text-primary); font-weight: 600; }
.markdown-body :deep(h6) { font-size: 13px; margin: 8px 0 4px; color: var(--color-text-muted); font-weight: 600; }

.markdown-body :deep(p) { margin: 8px 0; line-height: 1.8; }

.markdown-body :deep(strong) { font-weight: 600; color: var(--color-text-primary); }
.markdown-body :deep(em) { font-style: italic; }

.markdown-body :deep(a) { color: var(--color-primary); text-decoration: none; }
.markdown-body :deep(a:hover) { text-decoration: underline; }

.markdown-body :deep(ul),
.markdown-body :deep(ol) { margin: 8px 0; padding-left: 24px; }
.markdown-body :deep(li) { margin: 4px 0; line-height: 1.8; }
.markdown-body :deep(li > ul),
.markdown-body :deep(li > ol) { margin: 2px 0; }

.markdown-body :deep(blockquote) {
  margin: 12px 0;
  padding: 12px 16px;
  border-left: 4px solid var(--color-primary);
  background: var(--color-bg-page);
  border-radius: 0 var(--radius-md) var(--radius-md) 0;
  color: var(--color-text-secondary);
}

.markdown-body :deep(hr) {
  margin: 16px 0;
  border: none;
  border-top: 1px solid var(--color-border);
}

.markdown-body :deep(table) {
  width: 100%;
  border-collapse: collapse;
  margin: 12px 0;
  font-size: 14px;
}
.markdown-body :deep(th),
.markdown-body :deep(td) {
  border: 1px solid var(--color-border);
  padding: 8px 12px;
  text-align: left;
}
.markdown-body :deep(th) {
  background: var(--color-bg-page);
  font-weight: 600;
}
.markdown-body :deep(tr:nth-child(even)) {
  background: var(--color-bg-page);
}

.markdown-body :deep(img) {
  max-width: 100%;
  border-radius: var(--radius-md);
  margin: 8px 0;
}

.markdown-body :deep(pre) {
  background: #fff;
  padding: 16px;
  border-radius: var(--radius-md);
  overflow-x: auto;
  font-size: 13px;
  line-height: 1.6;
  margin: 12px 0;
}
.markdown-body :deep(code) {
  font-family: var(--font-mono);
  font-size: 13px;
}
.markdown-body :deep(p > code),
.markdown-body :deep(li > code) {
  background: var(--color-bg-page);
  padding: 2px 6px;
  border-radius: 4px;
  color: var(--color-primary);
  font-size: 13px;
}
.markdown-body :deep(pre > code) {
  background: transparent;
  padding: 0;
  color: inherit;
}

.markdown-body :deep(del) {
  text-decoration: line-through;
  color: var(--color-text-muted);
}

/* ── Mindmap ───────────────────────────────── */

.mindmap-toolbar {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 12px;
}

.mindmap-source {
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  padding: 16px;
  background: var(--color-bg-page);
  max-height: 500px;
  overflow: auto;
}

.mindmap-source pre {
  margin: 0;
  font-size: 13px;
  line-height: 1.6;
  color: var(--color-text-primary);
  white-space: pre-wrap;
  word-break: break-word;
}

.mindmap-container {
  width: 100%;
  height: 500px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  overflow: hidden;
  background: var(--color-bg-card);
}

.mindmap-container :deep(svg) {
  width: 100%;
  height: 100%;
}

/* ── Questions / Quiz ──────────────────────── */

.quiz-layout {
  display: flex;
  gap: 20px;
  align-items: flex-start;
}

.answer-card {
  width: 200px;
  flex-shrink: 0;
  background: var(--color-bg-card);
  border: 1px solid var(--color-border);
  border-radius: 14px;
  padding: 20px;
  position: sticky;
  top: 16px;
  box-shadow: var(--shadow-card);
}

.card-title {
  font-size: var(--text-lg);
  font-weight: 700;
  color: var(--color-text-primary);
  margin-bottom: 16px;
  text-align: center;
  letter-spacing: 1px;
}

.card-grid {
  display: grid;
  grid-template-columns: repeat(5, 1fr);
  gap: 8px;
  margin-bottom: 16px;
}

.card-cell {
  aspect-ratio: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: var(--radius-md);
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: all var(--transition-fast);
  border: 2px solid var(--color-border);
  color: var(--color-text-muted);
  background: var(--color-bg-card);
}

.card-cell:hover {
  border-color: var(--color-primary-light);
  color: var(--color-primary);
  background: var(--color-primary-lightest);
  transform: scale(1.08);
}

.cell-active {
  border-color: var(--color-primary) !important;
  background: var(--color-primary) !important;
  color: #fff !important;
  box-shadow: var(--shadow-md);
}

.cell-answered {
  border-color: #f59e0b;
  background: #fffbeb;
  color: #d97706;
}

.cell-correct {
  border-color: #22c55e;
  background: #f0fdf4;
  color: #16a34a;
}

.cell-wrong {
  border-color: #ef4444;
  background: #fef2f2;
  color: #dc2626;
}

.card-stats {
  display: flex;
  justify-content: space-between;
  font-size: var(--text-xs);
  color: var(--color-text-muted);
  margin-bottom: 10px;
}

.card-actions {
  display: flex;
  justify-content: center;
}

.view-toggle {
  width: 100%;
}

.view-toggle .el-radio-button {
  flex: 1;
}

.question-panel {
  flex: 1;
  min-width: 0;
}

.question-nav {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
}

.nav-indicator {
  font-size: 13px;
  color: var(--color-text-muted);
  font-weight: 500;
}

.question-card {
  background: var(--color-bg-card);
  border: 1px solid var(--color-border);
  border-left: 3px solid var(--color-primary);
  border-radius: var(--radius-lg);
  padding: 20px 24px;
  margin-bottom: 12px;
}

.question-card-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 12px;
}

.question-num {
  font-size: 13px;
  font-weight: 600;
  color: var(--color-primary);
}

.question-text {
  font-size: var(--text-base);
  font-weight: 500;
  color: var(--color-text-primary);
  line-height: 1.7;
  margin-bottom: 16px;
}

.question-body {
  padding-left: 2px;
}

.question-options {
  margin: 0;
}

.option-radio {
  display: flex;
  align-items: center;
  gap: 12px;
  margin: 8px 0;
  padding: 12px 16px;
  border-radius: var(--radius-md);
  border: 1.5px solid var(--color-border);
  background: var(--color-bg-card);
  cursor: pointer;
  transition: all var(--transition-fast);
  width: 100%;
}
.option-radio:hover {
  border-color: var(--color-primary);
  background: var(--color-primary-lightest);
}
.option-radio:deep(.el-radio__input) {
  margin-right: 0;
}
.option-radio:deep(.el-radio__label) {
  font-size: var(--text-base);
  color: var(--color-text-primary);
  padding-left: 4px;
}
.option-label {
  font-weight: 600;
  color: var(--color-primary);
  margin-right: 4px;
}
.option-radio:deep(.el-radio__input.is-checked + .el-radio__label) {
  color: var(--color-primary);
  font-weight: 500;
}
.option-radio:deep(.el-radio__input.is-checked) .el-radio__inner {
  background: var(--color-primary);
  border-color: var(--color-primary);
}

.rubric-box {
  margin-top: 12px;
  padding: 12px 16px;
  background: var(--color-bg-page);
  border-radius: var(--radius-md);
}

.rubric-title {
  font-weight: 600;
  margin-bottom: 8px;
  color: var(--color-text-primary);
}

.submit-bar {
  margin-top: 20px;
  text-align: center;
}

.answer-feedback {
  margin-top: 12px;
  padding: 10px 16px;
  border-radius: var(--radius-md);
  font-size: 14px;
  font-weight: 500;
}
.feedback-correct {
  background: #f0f9ff;
  border: 1px solid #22c55e;
  color: #22c55e;
}
.feedback-wrong {
  background: #fef2f2;
  border: 1px solid #ef4444;
  color: #ef4444;
}

/* ── Code ──────────────────────────────────── */

.code-info {
  margin-bottom: 16px;
}

.code-desc {
  color: var(--color-text-secondary);
  margin-bottom: 16px;
  line-height: 1.6;
}

.example-box {
  margin-bottom: 16px;
}

.example-box h4 {
  font-size: 13px;
  color: var(--color-text-secondary);
  margin-bottom: 6px;
}

.example-box pre {
  background: var(--color-bg-page);
  padding: 12px;
  border-radius: var(--radius-md);
  font-family: var(--font-mono);
  font-size: 13px;
  white-space: pre-wrap;
}

.code-block {
  margin: 16px 0;
  border-radius: var(--radius-md);
  overflow: hidden;
  border: 1px solid var(--color-border);
  border-left: 3px solid var(--color-student);
}

/* marked rendered code blocks (inline in document) */
.markdown-body :deep(.code-block-wrap) {
  margin: 12px 0;
  border-radius: var(--radius-md);
  overflow: hidden;
  border: 1px solid var(--color-border);
  background: var(--color-bg-card);
}
.markdown-body :deep(.code-header) {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 6px 14px;
  background: var(--color-bg-page);
  border-bottom: 1px solid var(--color-border);
}
.markdown-body :deep(.code-lang) {
  color: var(--color-text-muted);
  font-family: var(--font-mono);
  font-size: var(--text-xs);
  text-transform: uppercase;
}
.markdown-body :deep(.diagram-block) { border-color: var(--color-border); background: var(--color-bg-page); }
.markdown-body :deep(.diagram-pre) { background: var(--color-bg-page) !important; color: var(--color-text-primary); white-space: pre-wrap; word-break: break-word; }
.markdown-body :deep(pre) {
  margin: 0;
  padding: 16px;
  background: var(--color-bg-card) !important;
  overflow-x: auto;
  font-size: 13px;
  line-height: 1.6;
}
.markdown-body :deep(pre code) {
  font-family: var(--font-mono);
  font-size: 13px;
  background: transparent !important;
  padding: 0;
  color: var(--color-text-primary);
}

.code-toolbar {
  display: flex;
  gap: 8px;
  padding: 8px 12px;
  background: var(--color-bg-page);
  border-bottom: 1px solid var(--color-border);
}

.code-block pre {
  margin: 0;
  padding: 16px;
  background: #fff;
  overflow-x: auto;
  font-size: 13px;
  line-height: 1.6;
}

.code-block code {
  font-family: var(--font-mono);
}

.run-result {
  margin-top: 16px;
  padding: 16px;
  border-radius: var(--radius-md);
}

.run-result.success {
  background: #f0fdf4;
  border: 1px solid #bbf7d0;
}

.run-result.error {
  background: #fef2f2;
  border: 1px solid #fecaca;
}

.run-result pre {
  margin: 8px 0 0;
  font-family: var(--font-mono);
  font-size: 13px;
  white-space: pre-wrap;
}

.test-cases {
  margin-top: 24px;
}

.test-cases h4 {
  font-size: 14px;
  font-weight: 600;
  margin-bottom: 12px;
  color: var(--color-text-primary);
}

/* ── Workflow ──────────────────────────────── */

.workflow-step {
  text-align: center;
  margin-top: 16px;
  color: var(--color-text-secondary);
  font-size: 14px;
}

/* ── Glossary ──────────────────────────────── */

.glossary-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 16px;
  margin-top: 16px;
}

.glossary-card {
  background: var(--color-bg-card);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  padding: 16px;
  transition: box-shadow var(--transition-fast);
}

.glossary-card:hover {
  box-shadow: var(--shadow-card-hover);
}

.glossary-term {
  font-size: var(--text-lg);
  font-weight: 700;
  color: var(--color-primary);
  margin-bottom: 6px;
}

.glossary-def {
  font-size: 14px;
  color: var(--color-text-primary);
  line-height: 1.6;
  margin-bottom: 8px;
}

.glossary-example {
  font-size: 13px;
  color: var(--color-text-muted);
  background: var(--color-bg-page);
  border-radius: var(--radius-sm);
  padding: 8px 10px;
  display: flex;
  align-items: flex-start;
  gap: 6px;
  margin-bottom: 8px;
}

.glossary-related {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
}

/* ── Video Player ───────────────────────────── */

.video-player-wrap {
  max-width: 900px;
  margin: 0 auto;
}

.artplayer-container {
  width: 100%;
  aspect-ratio: 16 / 9;
  border-radius: var(--radius-lg);
  overflow: hidden;
}

.video-meta {
  display: flex;
  gap: 8px;
  margin-top: 12px;
  justify-content: center;
}
</style>
