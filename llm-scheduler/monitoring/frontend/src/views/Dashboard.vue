<template>
  <div style="max-width:1100px;margin:24px auto;padding:0 16px;">
    <!-- KPI cards -->
    <el-row :gutter="16" style="margin-bottom:20px;">
      <el-col :span="6" v-for="kpi in kpis" :key="kpi.label">
        <el-card shadow="hover" style="text-align:center;">
          <div style="font-size:13px;color:#9ca3af;">{{ kpi.label }}</div>
          <div style="font-size:28px;font-weight:bold;color:#818cf8;">{{ kpi.value }}</div>
        </el-card>
      </el-col>
    </el-row>

    <!-- QPS + Latency charts -->
    <el-row :gutter="16">
      <el-col :span="12">
        <el-card>
          <template #header><b style="color:#f3f4f6;">QPS 趋势</b></template>
          <div ref="qpsChart" style="height:300px;" />
        </el-card>
      </el-col>
      <el-col :span="12">
        <el-card>
          <template #header><b style="color:#f3f4f6;">P95 延迟趋势 (ms)</b></template>
          <div ref="latChart" style="height:300px;" />
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import * as echarts from 'echarts'
import client from '../api/client'

const LIGHT_CHART = {
  backgroundColor: 'transparent',
  textStyle: { color: '#9ca3af' },
  tooltip: { trigger: 'axis', backgroundColor: '#1f2937', borderColor: '#374151', textStyle: { color: '#f3f4f6' } },
  xAxis: { type: 'category', axisLine: { lineStyle: { color: '#374151' } }, axisLabel: { color: '#9ca3af' }, splitLine: { show: false } },
  yAxis: { type: 'value', axisLine: { lineStyle: { color: '#374151' } }, axisLabel: { color: '#9ca3af' }, splitLine: { lineStyle: { color: '#1f2937', type: 'dashed' } } },
  grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
}

const summary = ref({})
const qpsChart = ref(null)
const latChart = ref(null)
let qpsInstance, latInstance, timer

const kpis = computed(() => [
  { label: 'QPS', value: summary.value.qps?.toFixed(3) ?? '-' },
  { label: '平均延迟 (ms)', value: summary.value.avg_latency_ms?.toFixed(1) ?? '-' },
  { label: '成功率', value: summary.value.success_rate ? (summary.value.success_rate * 100).toFixed(1) + '%' : '-' },
  { label: '错误总数', value: summary.value.error_count ?? '-' },
])

async function load() {
  try {
    const { data } = await client.get('/api/metrics/summary', { params: { range: '1h' } })
    summary.value = data
    updateCharts(data.time_series || [])
  } catch {}
}

function updateCharts(series) {
  const times = series.map(r => r.bucket)
  const qps = series.map(r => r.qps ?? 0)
  const lat = series.map(r => r.latency_p95 ?? 0)

  qpsInstance?.setOption({
    ...LIGHT_CHART,
    xAxis: { ...LIGHT_CHART.xAxis, data: times },
    series: [{ type: 'line', data: qps, smooth: true, name: 'QPS', itemStyle: { color: '#818cf8' }, lineStyle: { color: '#818cf8' }, areaStyle: { color: { type: 'linear', x: 0, y: 0, x2: 0, y2: 1, colorStops: [{ offset: 0, color: 'rgba(129,140,248,0.3)' }, { offset: 1, color: 'rgba(129,140,248,0.02)' }] } } }],
  })
  latInstance?.setOption({
    ...LIGHT_CHART,
    xAxis: { ...LIGHT_CHART.xAxis, data: times },
    series: [{ type: 'line', data: lat, smooth: true, name: 'P95 延迟', itemStyle: { color: '#f87171' }, lineStyle: { color: '#f87171' }, areaStyle: { color: { type: 'linear', x: 0, y: 0, x2: 0, y2: 1, colorStops: [{ offset: 0, color: 'rgba(248,113,113,0.3)' }, { offset: 1, color: 'rgba(248,113,113,0.02)' }] } } }],
  })
}

onMounted(() => {
  qpsInstance = echarts.init(qpsChart.value)
  latInstance = echarts.init(latChart.value)
  load()
  timer = setInterval(load, 5000)
})
onUnmounted(() => { clearInterval(timer); qpsInstance?.dispose(); latInstance?.dispose() })
</script>
