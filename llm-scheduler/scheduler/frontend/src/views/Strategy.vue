<template>
  <div style="max-width:1100px;margin:24px auto;padding:0 16px;">
    <el-card>
      <template #header><b style="color:#f3f4f6;">调度策略管理</b></template>

      <el-form label-width="120px">
        <el-form-item label="当前策略">
          <el-select v-model="current" @change="update" :loading="loading" style="width:240px;">
            <el-option v-for="s in available" :key="s" :label="strategyLabel(s)" :value="s" />
          </el-select>
        </el-form-item>
      </el-form>

      <el-descriptions title="策略说明" :column="1" border style="margin-top:16px;">
        <el-descriptions-item label="轮询 (round_robin)">
          依次将请求分配给每个节点，适合节点性能相近的场景。
        </el-descriptions-item>
        <el-descriptions-item label="最少连接 (least_connections)">
          将请求分配给当前活跃连接数最少的节点，适合请求耗时不均衡的场景。
        </el-descriptions-item>
        <el-descriptions-item label="加权轮询 (weighted)">
          按节点权重随机选择，权重越高被选中概率越大，适合异构节点场景。
        </el-descriptions-item>
      </el-descriptions>
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import client from '../api/client'

const current = ref('')
const available = ref([])
const loading = ref(false)

const LABELS = {
  round_robin: '轮询 (round_robin)',
  least_connections: '最少连接 (least_connections)',
  weighted: '加权轮询 (weighted)',
}

function strategyLabel(s) { return LABELS[s] || s }

async function load() {
  loading.value = true
  try {
    const { data } = await client.get('/api/strategy')
    current.value = data.current
    available.value = data.available
  } catch { ElMessage.error('加载策略失败') } finally { loading.value = false }
}

async function update(val) {
  try {
    await client.put('/api/strategy', { strategy: val })
    ElMessage.success(`策略已切换为：${strategyLabel(val)}`)
  } catch { ElMessage.error('策略切换失败') }
}

onMounted(load)
</script>
