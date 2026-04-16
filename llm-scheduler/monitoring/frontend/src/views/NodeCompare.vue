<template>
  <div style="max-width:1100px;margin:24px auto;padding:0 16px;">
    <el-card>
      <template #header><b style="color:#f3f4f6;">节点性能对比</b></template>
      <el-row :gutter="16">
        <el-col :span="12"><div ref="reqChart" style="height:300px;" /></el-col>
        <el-col :span="12"><div ref="latChart" style="height:300px;" /></el-col>
      </el-row>
      <el-table :data="nodes" stripe style="margin-top:16px;">
        <el-table-column label="节点" prop="node_id" />
        <el-table-column label="平均QPS" prop="avg_qps" />
        <el-table-column label="平均延迟(ms)" prop="avg_latency_ms" />
        <el-table-column label="成功率" >
          <template #default="{row}">{{ (row.avg_success_rate * 100).toFixed(1) }}%</template>
        </el-table-column>
        <el-table-column label="错误数" prop="error_count" />
        <el-table-column label="平均活跃连接" prop="avg_active_conns" />
      </el-table>
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import * as echarts from 'echarts'
import client from '../api/client'

const LIGHT_CHART = {
  backgroundColor: 'transparent',
  textStyle: { color: '#9ca3af' },
  tooltip: { backgroundColor: '#1f2937', borderColor: '#374151', textStyle: { color: '#f3f4f6' } },
  xAxis: { type: 'category', axisLine: { lineStyle: { color: '#374151' } }, axisLabel: { color: '#9ca3af' }, splitLine: { show: false } },
  yAxis: { type: 'value', axisLine: { lineStyle: { color: '#374151' } }, axisLabel: { color: '#9ca3af' }, splitLine: { lineStyle: { color: '#1f2937', type: 'dashed' } } },
  grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
}

const nodes = ref([])
const reqChart = ref(null)
const latChart = ref(null)
let reqInst, latInst

async function load() {
  try {
    const { data } = await client.get('/api/metrics/nodes', { params: { range: '1h' } })
    nodes.value = data
    const ids = data.map(n => n.node_id)
    reqInst?.setOption({
      ...LIGHT_CHART,
      title: { text: '平均QPS', textStyle: { color: '#9ca3af' } },
      xAxis: { ...LIGHT_CHART.xAxis, data: ids },
      series: [{ type: 'bar', data: data.map(n => n.avg_qps), itemStyle: { color: '#818cf8' } }],
    })
    latInst?.setOption({
      ...LIGHT_CHART,
      title: { text: '平均延迟 (ms)', textStyle: { color: '#9ca3af' } },
      xAxis: { ...LIGHT_CHART.xAxis, data: ids },
      series: [{ type: 'bar', data: data.map(n => n.avg_latency_ms), itemStyle: { color: '#f87171' } }],
    })
  } catch {}
}

onMounted(() => {
  reqInst = echarts.init(reqChart.value)
  latInst = echarts.init(latChart.value)
  load()
})
onUnmounted(() => { reqInst?.dispose(); latInst?.dispose() })
</script>
