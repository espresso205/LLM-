<template>
  <div style="max-width:1100px;margin:24px auto;padding:0 16px;">
    <el-row :gutter="16" style="margin-bottom:16px;">
      <el-col :span="8" v-for="stat in stats" :key="stat.label">
        <el-card shadow="hover" style="text-align:center;">
          <div style="font-size:13px;color:#9ca3af;">{{ stat.label }}</div>
          <div style="font-size:28px;font-weight:bold;color:#818cf8;">{{ stat.value }}</div>
        </el-card>
      </el-col>
    </el-row>

    <el-card>
      <template #header>
        <div style="display:flex;justify-content:space-between;align-items:center;">
          <b style="color:#f3f4f6;">推理节点列表</b>
          <div style="display:flex;gap:8px;">
            <el-input v-model="newNode.host" placeholder="主机地址" style="width:160px;" />
            <el-input-number v-model="newNode.port" :min="1" :max="65535" style="width:120px;" />
            <el-input v-model="newNode.node_id" placeholder="节点ID" style="width:120px;" />
            <el-button type="success" @click="register">注册节点</el-button>
          </div>
        </div>
      </template>

      <el-table :data="nodes" v-loading="loading" stripe>
        <el-table-column label="节点ID" prop="node_id" />
        <el-table-column label="地址" prop="url" />
        <el-table-column label="状态" width="100">
          <template #default="{row}">
            <el-tag :type="row.status==='healthy'?'success':row.status==='unhealthy'?'danger':'warning'">
              {{ row.status }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="活跃连接" prop="active_connections" width="100" />
        <el-table-column label="权重" prop="weight" width="80" />
        <el-table-column label="注册时间" prop="registered_at" width="180" />
        <el-table-column label="操作" width="120">
          <template #default="{row}">
            <el-popconfirm title="确认注销该节点？" @confirm="deregister(row.node_id)">
              <template #reference>
                <el-button size="small" type="danger">注销</el-button>
              </template>
            </el-popconfirm>
          </template>
        </el-table-column>
      </el-table>
    </el-card>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { ElMessage } from 'element-plus'
import client from '../api/client'

const nodes = ref([])
const loading = ref(false)
const newNode = ref({ host: 'localhost', port: 8003, node_id: 'node-new' })

const online = computed(() => nodes.value.filter(n => n.status === 'healthy').length)
const total = computed(() => nodes.value.length)
const totalConns = computed(() => nodes.value.reduce((s, n) => s + (n.active_connections || 0), 0))

const stats = computed(() => [
  { label: '在线节点', value: online.value },
  { label: '离线节点', value: total.value - online.value },
  { label: '总连接数', value: totalConns.value },
])

async function load() {
  loading.value = true
  try {
    const { data } = await client.get('/api/nodes')
    nodes.value = data
  } catch { ElMessage.error('加载节点失败') } finally { loading.value = false }
}

async function register() {
  try {
    await client.post('/api/nodes/register', newNode.value)
    ElMessage.success('节点注册成功')
    load()
  } catch (e) { ElMessage.error(e.response?.data?.detail || '注册失败') }
}

async function deregister(id) {
  try {
    await client.delete(`/api/nodes/${id}/deregister`)
    ElMessage.success('节点已注销')
    load()
  } catch { ElMessage.error('注销失败') }
}

let timer
onMounted(() => { load(); timer = setInterval(load, 10000) })
onUnmounted(() => clearInterval(timer))
</script>
