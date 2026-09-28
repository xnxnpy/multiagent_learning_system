<template>
  <div class="knowledge-graph-container">
    <div class="graph-header" v-if="graphData && graphData.nodes?.length">
      <div class="graph-info">
        <span class="graph-title">{{ graphData.title }}</span>
        <el-tag type="success" size="small">{{ graphData.knowledge_point_count }}个知识点</el-tag>
        <span v-if="hasMastery" class="mastery-hint">颜色 = 掌握度 · 点击节点看详情</span>
      </div>
      <div class="graph-controls">
        <el-switch v-model="showNodeLabels" active-text="显示标签" size="small" @change="updateLabels" />
        <el-button-group size="small">
          <el-button @click="zoomIn"><el-icon><ZoomIn /></el-icon></el-button>
          <el-button @click="zoomOut"><el-icon><ZoomOut /></el-icon></el-button>
          <el-button @click="resetZoom"><el-icon><FullScreen /></el-icon></el-button>
        </el-button-group>
      </div>
    </div>
    <div ref="chartRef" class="graph-chart" :style="{ height: height }"></div>
    <div class="graph-legend">
      <span class="legend-item"><span class="legend-dot" style="background: #22C55E"></span>掌握 ≥80%</span>
      <span class="legend-item"><span class="legend-dot" style="background: #F59E0B"></span>掌握 50–79%</span>
      <span class="legend-item"><span class="legend-dot" style="background: #EF4444"></span>薄弱 &lt;50%</span>
      <span class="legend-item"><span class="legend-dot" style="background: #94A3B8"></span>暂无数据</span>
      <span class="legend-item" v-if="!hasMastery">
        <span class="legend-dot" style="background: #F5A623"></span>一级
        <span class="legend-dot" style="background: #4A90D9"></span>二级
        <span class="legend-dot" style="background: #52C41A"></span>三级
      </span>
    </div>

    <!-- 节点详情抽屉 -->
    <el-drawer v-model="drawerVisible" :title="selected?.label || '知识点详情'" size="360px">
      <div v-if="selected" class="detail">
        <div class="detail-row">
          <span class="lbl">层级</span>
          <el-tag size="small" effect="plain">Lv.{{ selected.level }}</el-tag>
        </div>
        <div class="detail-row">
          <span class="lbl">掌握度</span>
          <template v-if="selectedMastery != null">
            <el-progress
              :percentage="Math.round(selectedMastery * 100)"
              :status="selectedMastery >= 0.8 ? 'success' : selectedMastery >= 0.5 ? undefined : 'exception'"
              :stroke-width="10"
              style="flex: 1"
            />
            <b class="mastery-num">{{ Math.round(selectedMastery * 100) }}%</b>
          </template>
          <span v-else class="muted">暂无评估数据</span>
        </div>
        <div class="detail-block" v-if="selected.description">
          <div class="lbl">说明</div>
          <p class="desc">{{ selected.description }}</p>
        </div>
        <div class="detail-block" v-if="prereqs.length">
          <div class="lbl">前置知识点（学它之前要懂）</div>
          <div class="chip-list">
            <el-tag v-for="p in prereqs" :key="p" size="small" type="warning" effect="plain" class="link-tag" @click="jumpToName(p)">
              {{ p }}
            </el-tag>
          </div>
        </div>
        <div class="detail-block" v-if="nexts.length">
          <div class="lbl">后续知识点</div>
          <div class="chip-list">
            <el-tag v-for="n in nexts" :key="n" size="small" type="primary" effect="plain" class="link-tag" @click="jumpToName(n)">
              {{ n }}
            </el-tag>
          </div>
        </div>
        <div class="detail-actions">
          <el-button type="primary" size="small" @click="emit('practice', selected)">去练习这个点</el-button>
          <el-button size="small" @click="emit('resources', selected)">看相关资源</el-button>
        </div>
      </div>
    </el-drawer>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted, onUnmounted, nextTick } from 'vue'
import * as echarts from 'echarts'
import { ZoomIn, ZoomOut, FullScreen } from '@element-plus/icons-vue'

interface GraphNode {
  id: string
  label: string
  level: number
  description?: string
}

interface GraphEdge {
  source: string
  target: string
  relationship?: string
}

interface GraphData {
  title: string
  knowledge_point_count: number
  nodes: GraphNode[]
  edges: GraphEdge[]
}

const props = withDefaults(defineProps<{
  graphData: GraphData | null
  height?: string
  /** label 或 id → 掌握度 0~1 */
  masteryMap?: Record<string, number>
}>(), {
  height: '600px',
  masteryMap: () => ({}),
})

const emit = defineEmits<{
  (e: 'practice', node: GraphNode): void
  (e: 'resources', node: GraphNode): void
}>()

const chartRef = ref<HTMLElement>()
const showNodeLabels = ref(true)
const drawerVisible = ref(false)
const selected = ref<GraphNode | null>(null)
let chart: echarts.ECharts | null = null
let currentZoom = 1

const hasMastery = computed(() => Object.keys(props.masteryMap || {}).length > 0)

const selectedMastery = computed(() => {
  if (!selected.value) return null
  const m = lookupMastery(selected.value)
  return m
})

function lookupMastery(node: GraphNode): number | null {
  const map = props.masteryMap || {}
  const keys = [node.label, node.id, node.label.replace(/\s*\(\d+\)$/, '')]
  for (const k of keys) {
    if (map[k] != null) return map[k]
    // 模糊：包含关系
    for (const [mk, mv] of Object.entries(map)) {
      if (mk && (mk.includes(node.label) || node.label.includes(mk))) return mv
    }
  }
  return null
}

const LEVEL_COLORS = ['#F5A623', '#4A90D9', '#52C41A', '#9B59B6']
const LEVEL_NAMES = ['一级·章节', '二级·小节', '三级·子节', '四级·细节']
const LEVEL_SIZES = [50, 35, 25, 18]

function masteryColor(m: number | null): string {
  if (m == null) return '#94A3B8'
  if (m >= 0.8) return '#22C55E'
  if (m >= 0.5) return '#F59E0B'
  return '#EF4444'
}

function buildOption(data: GraphData) {
  const labelCount: Record<string, number> = {}
  const nodes = data.nodes.map((node) => {
    const base = node.label || node.id
    labelCount[base] = (labelCount[base] || 0) + 1
    const name = labelCount[base] > 1 ? `${base} (${labelCount[base]})` : base
    const m = lookupMastery(node)
    const color = hasMastery.value ? masteryColor(m) : (LEVEL_COLORS[node.level - 1] || '#94A3B8')
    return {
      name,
      nodeId: node.id,
      labelRaw: node.label,
      description: node.description || '',
      mastery: m,
      category: node.level - 1,
      symbolSize: LEVEL_SIZES[node.level - 1] || 18,
      itemStyle: {
        color,
        borderColor: '#fff',
        borderWidth: 2,
        shadowBlur: 6,
        shadowColor: 'rgba(0,0,0,0.12)',
      },
      label: {
        show: showNodeLabels.value,
        position: 'right' as const,
        fontSize: 12,
        color: '#333',
      },
    }
  })

  const idToName: Record<string, string> = {}
  data.nodes.forEach((node, i) => {
    idToName[node.id] = nodes[i].name
  })

  const links = data.edges
    .filter(e => idToName[e.source] && idToName[e.target])
    .map((edge) => ({
      source: idToName[edge.source],
      target: idToName[edge.target],
      label: {
        show: false,
        formatter: edge.relationship || '',
        fontSize: 10,
      },
      lineStyle: {
        color: '#bbb',
        curveness: 0.1,
      },
    }))

  return {
    tooltip: {
      trigger: 'item' as const,
      formatter: (params: any) => {
        if (params.dataType === 'node') {
          const levelName = LEVEL_NAMES[params.data.category] || '知识点'
          let html = `<strong>${params.data.name}</strong><br/>级别: ${levelName}`
          if (params.data.mastery != null) {
            html += `<br/>掌握度: ${Math.round(params.data.mastery * 100)}%`
          }
          if (params.data.description) {
            html += `<br/>${params.data.description}`
          }
          html += `<br/><span style="color:#888">点击查看详情</span>`
          return html
        }
        if (params.dataType === 'edge') {
          return `${params.data.source} → ${params.data.target}`
        }
        return ''
      },
    },
    animationDuration: 800,
    series: [
      {
        type: 'graph' as const,
        layout: 'force' as const,
        data: nodes,
        links: links,
        categories: LEVEL_NAMES.map((name, i) => ({
          name,
          itemStyle: { color: LEVEL_COLORS[i] },
        })),
        roam: true,
        draggable: true,
        force: {
          repulsion: 300,
          gravity: 0.1,
          edgeLength: [100, 300],
          layoutAnimation: true,
        },
        label: {
          show: showNodeLabels.value,
          position: 'right' as const,
          fontSize: 12,
        },
        lineStyle: {
          color: '#bbb',
          curveness: 0.1,
        },
        emphasis: {
          focus: 'adjacency' as const,
          lineStyle: { width: 3 },
        },
      },
    ],
  }
}

function onNodeClick(params: any) {
  if (params.dataType !== 'node' || !props.graphData) return
  const id = params.data.nodeId
  const node = props.graphData.nodes.find(n => n.id === id)
    || props.graphData.nodes.find(n => (n.label || n.id) === (params.data.labelRaw || params.data.name))
  if (!node) return
  selected.value = node
  drawerVisible.value = true
}

const prereqs = computed(() => {
  if (!selected.value || !props.graphData) return []
  const label = selected.value.label
  const id = selected.value.id
  return props.graphData.edges
    .filter(e => e.target === id || e.target === label)
    .map(e => {
      const n = props.graphData!.nodes.find(x => x.id === e.source)
      return n?.label || e.source
    })
    .filter(Boolean)
})

const nexts = computed(() => {
  if (!selected.value || !props.graphData) return []
  const id = selected.value.id
  const label = selected.value.label
  return props.graphData.edges
    .filter(e => e.source === id || e.source === label)
    .map(e => {
      const n = props.graphData!.nodes.find(x => x.id === e.target)
      return n?.label || e.target
    })
    .filter(Boolean)
})

function jumpToName(name: string) {
  const node = props.graphData?.nodes.find(n => n.label === name || n.id === name)
  if (node) {
    selected.value = node
  }
}

function renderChart() {
  if (!chartRef.value || !props.graphData) return

  const { clientWidth, clientHeight } = chartRef.value
  if (clientWidth === 0 || clientHeight === 0) {
    setTimeout(() => renderChart(), 200)
    return
  }

  if (!chart) {
    chart = echarts.init(chartRef.value)
    chart.on('click', onNodeClick)
  }

  const option = buildOption(props.graphData)
  chart.setOption(option, true)
  chart.resize()
}

function updateLabels() {
  if (!chart || !props.graphData) return
  chart.setOption({ series: [{ label: { show: showNodeLabels.value } }] })
}

function zoomIn() {
  if (!chart) return
  currentZoom *= 1.3
  chart.setOption({ series: [{ zoom: currentZoom }] })
}

function zoomOut() {
  if (!chart) return
  currentZoom /= 1.3
  chart.setOption({ series: [{ zoom: currentZoom }] })
}

function resetZoom() {
  if (!chart) return
  currentZoom = 1
  chart.setOption({ series: [{ zoom: 1 }] })
  chart.dispatchAction({ type: 'restore' })
}

function handleResize() {
  chart?.resize()
}

watch(() => [props.graphData, props.masteryMap], () => {
  nextTick(() => renderChart())
}, { deep: true })

onMounted(() => {
  nextTick(() => renderChart())
  window.addEventListener('resize', handleResize)
})

onUnmounted(() => {
  window.removeEventListener('resize', handleResize)
  chart?.dispose()
  chart = null
})
</script>

<style scoped>
.knowledge-graph-container {
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  overflow: hidden;
  background: var(--color-bg-card);
}

.graph-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 16px;
  border-bottom: 1px solid var(--color-border);
  background: var(--color-border-light);
  flex-wrap: wrap;
  gap: 8px;
}

.graph-info {
  display: flex;
  align-items: center;
  gap: 12px;
}

.graph-title {
  font-size: var(--text-lg);
  font-weight: 600;
  color: var(--color-text-primary);
}

.mastery-hint {
  font-size: 12px;
  color: var(--color-text-secondary);
}

.graph-controls {
  display: flex;
  align-items: center;
  gap: 12px;
}

.graph-chart {
  width: 100%;
  min-height: 400px;
}

.graph-legend {
  display: flex;
  justify-content: center;
  gap: 16px;
  padding: 10px 16px;
  border-top: 1px solid var(--color-border);
  background: var(--color-border-light);
  flex-wrap: wrap;
}

.legend-item {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: var(--text-sm);
  color: var(--color-text-secondary);
}

.legend-dot {
  width: 12px;
  height: 12px;
  border-radius: 50%;
  display: inline-block;
}

.detail { display: flex; flex-direction: column; gap: 14px; }
.detail-row { display: flex; align-items: center; gap: 10px; }
.lbl {
  font-size: 12px;
  color: var(--el-text-color-secondary);
  min-width: 64px;
}
.mastery-num { font-size: 14px; min-width: 40px; text-align: right; }
.muted { color: var(--el-text-color-placeholder); font-size: 13px; }
.detail-block .lbl { display: block; margin-bottom: 6px; min-width: auto; }
.desc { margin: 0; font-size: 13px; line-height: 1.6; color: var(--el-text-color-regular); }
.chip-list { display: flex; flex-wrap: wrap; gap: 6px; }
.link-tag { cursor: pointer; }
.detail-actions { display: flex; gap: 8px; margin-top: 8px; }
</style>
