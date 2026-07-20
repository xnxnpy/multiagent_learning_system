<template>
  <div class="knowledge-graph-container">
    <div class="graph-header" v-if="graphData && graphData.nodes?.length">
      <div class="graph-info">
        <span class="graph-title">{{ graphData.title }}</span>
        <el-tag type="success" size="small">{{ graphData.knowledge_point_count }}个知识点</el-tag>
      </div>
      <div class="graph-controls">
        <el-switch v-model="showNodeLabels" active-text="显示标签" size="small" @change="updateLabels" />
        <el-button-group size="small">
          <el-button @click="zoomIn">
            <el-icon><ZoomIn /></el-icon>
          </el-button>
          <el-button @click="zoomOut">
            <el-icon><ZoomOut /></el-icon>
          </el-button>
          <el-button @click="resetZoom">
            <el-icon><FullScreen /></el-icon>
          </el-button>
        </el-button-group>
      </div>
    </div>
    <div ref="chartRef" class="graph-chart" :style="{ height: height }"></div>
    <div class="graph-legend">
      <span class="legend-item">
        <span class="legend-dot" style="background: #F5A623"></span>一级·章节
      </span>
      <span class="legend-item">
        <span class="legend-dot" style="background: #4A90D9"></span>二级·小节
      </span>
      <span class="legend-item">
        <span class="legend-dot" style="background: #52C41A"></span>三级·子节
      </span>
      <span class="legend-item">
        <span class="legend-dot" style="background: #9B59B6"></span>四级·细节
      </span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch, onMounted, onUnmounted, nextTick } from 'vue'
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
}>(), {
  height: '600px'
})

const chartRef = ref<HTMLElement>()
const showNodeLabels = ref(true)
let chart: echarts.ECharts | null = null
let currentZoom = 1

const LEVEL_COLORS = ['#F5A623', '#4A90D9', '#52C41A', '#9B59B6']
const LEVEL_NAMES = ['一级·章节', '二级·小节', '三级·子节', '四级·细节']
const LEVEL_SIZES = [50, 35, 25, 18]

function buildOption(data: GraphData) {
  // 去重：ECharts 要求节点 name 唯一，给重复 label 加后缀
  const labelCount: Record<string, number> = {}
  const nodes = data.nodes.map((node) => {
    const base = node.label || node.id
    labelCount[base] = (labelCount[base] || 0) + 1
    const uniqueName = labelCount[base] > 1 ? `${base} (${labelCount[base]})` : base
    return {
      name: uniqueName,
      nodeId: node.id,
      category: node.level - 1,
      symbolSize: LEVEL_SIZES[node.level - 1] || 18,
      description: node.description || '',
      itemStyle: {
        color: LEVEL_COLORS[node.level - 1],
        borderColor: '#fff',
        borderWidth: 2,
      },
      label: {
        show: showNodeLabels.value,
        position: 'right' as const,
        fontSize: 12,
        color: '#333',
      },
    }
  })

  // 构建 id → uniqueName 映射，用于边的 source/target 替换
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
      color: '#aaa',
      curveness: 0.1,
    },
  }))

  return {
    tooltip: {
      trigger: 'item' as const,
      formatter: (params: any) => {
        if (params.dataType === 'node') {
          const levelName = LEVEL_NAMES[params.data.category] || '未知'
          let html = `<strong>${params.data.name}</strong><br/>级别: ${levelName}`
          if (params.data.description) {
            html += `<br/>${params.data.description}`
          }
          return html
        }
        if (params.dataType === 'edge') {
          return `${params.data.source} → ${params.data.target}${params.data.label?.formatter ? '<br/>关系: ' + params.data.label.formatter : ''}`
        }
        return ''
      },
    },
    animationDuration: 1500,
    animationEasingUpdate: 'quinticInOut' as const,
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
          color: '#aaa',
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

function renderChart() {
  if (!chartRef.value || !props.graphData) return

  // Wait for DOM to have dimensions (handles hidden tabs)
  const { clientWidth, clientHeight } = chartRef.value
  if (clientWidth === 0 || clientHeight === 0) {
    // Retry after a short delay when element becomes visible
    setTimeout(() => renderChart(), 200)
    return
  }

  if (!chart) {
    chart = echarts.init(chartRef.value)
  }

  const option = buildOption(props.graphData)
  chart.setOption(option, true)
  chart.resize()
}

function updateLabels() {
  if (!chart || !props.graphData) return
  chart.setOption({
    series: [
      {
        label: { show: showNodeLabels.value },
      },
    ],
  })
}

function zoomIn() {
  if (!chart) return
  currentZoom *= 1.3
  chart.setOption({
    series: [{ zoom: currentZoom }],
  })
}

function zoomOut() {
  if (!chart) return
  currentZoom /= 1.3
  chart.setOption({
    series: [{ zoom: currentZoom }],
  })
}

function resetZoom() {
  if (!chart) return
  currentZoom = 1
  chart.setOption({
    series: [{ zoom: 1 }],
  })
  chart.dispatchAction({ type: 'restore' })
}

function handleResize() {
  chart?.resize()
}

watch(() => props.graphData, () => {
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
  gap: 24px;
  padding: 10px 16px;
  border-top: 1px solid var(--color-border);
  background: var(--color-border-light);
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
</style>
