<template>
  <div style="max-width:1100px;margin:24px auto;padding:0 16px;">
    <el-card>
      <template #header>
        <div style="display:flex;gap:12px;align-items:center;">
          <b style="color:#f3f4f6;">性能趋势</b>
          <el-select v-model="range" @change="load" style="width:120px;">
            <el-option label="15分钟" value="15m" />
            <el-option label="1小时" value="1h" />
            <el-option label="6小时" value="6h" />
            <el-option label="24小时" value="24h" />
          </el-select>
          <el-button plain @click="load" :loading="loading">刷新</el-button>
        </div>
      </template>
      <div ref="chart" style="height:400px;" />
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import * as echarts from 'echarts'
import client from '../api/client'

const range = ref('1h')
const loading = ref(false)
const chart = ref(null)
let instance

const LIGHT_CHART = {
  backgroundColor: 'transparent',
  textStyle: { color: '#9ca3af' },
  tooltip: { trigger: 'axis', backgroundColor: '#1f2937', borderColor: '#374151', textStyle: { color: '#f3f4f6' } },
  legend: { textStyle: { color: '#9ca3af' } },
  xAxis: { type: 'category', axisLine: { lineStyle: { color: '#374151' } }, axisLabel: { color: '#9ca3af' }, splitLine: { show: false } },
  yAxis: [
    { type: 'value', name: 'QPS / 延迟(ms)', nameTextStyle: { color: '#9ca3af' }, axisLine: { lineStyle: { color: '#374151' } }, axisLabel: { color: '#9ca3af' }, splitLine: { lineStyle: { color: '#1f2937', type: 'dashed' } } },
    { type: 'value', name: '成功率(%)', max: 100, nameTextStyle: { color: '#9ca3af' }, axisLine: { lineStyle: { color: '#374151' } }, axisLabel: { color: '#9ca3af' }, splitLine: { show: false } },
  ],
  grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
}

async function load() {
  loading.value = true
  try {
    const { data } = await client.get('/api/metrics/summary', { params: { range: range.value } })
    const series = data.time_series || []
    const times = series.map(r => r.bucket)
    instance?.setOption({
      ...LIGHT_CHART,
      xAxis: { ...LIGHT_CHART.xAxis, data: times },
      legend: { ...LIGHT_CHART.legend, data: ['QPS', 'P95延迟(ms)', '成功率(%)'] },
      series: [
        { name: 'QPS', type: 'line', smooth: true, data: series.map(r => r.qps ?? 0), itemStyle: { color: '#818cf8' }, lineStyle: { color: '#818cf8' } },
        { name: 'P95延迟(ms)', type: 'line', smooth: true, data: series.map(r => r.latency_p95 ?? 0), itemStyle: { color: '#f87171' }, lineStyle: { color: '#f87171' } },
        { name: '成功率(%)', type: 'line', smooth: true, yAxisIndex: 1, data: series.map(r => ((r.success_rate ?? 1) * 100).toFixed(2)), itemStyle: { color: '#34d399' }, lineStyle: { color: '#34d399' } },
      ],
    })
  } catch {} finally { loading.value = false }
}

onMounted(() => { instance = echarts.init(chart.value); load() })
onUnmounted(() => instance?.dispose())
</script>
