<template>
  <div style="max-width:1100px;margin:24px auto;padding:0 16px;">
    <el-card>
      <template #header>
        <div style="display:flex;justify-content:space-between;align-items:center;">
          <b style="color:#f3f4f6;">调度决策日志</b>
          <div style="display:flex;gap:8px;">
            <el-input v-model="nodeFilter" placeholder="按节点ID筛选" clearable style="width:160px;" @change="load" />
            <el-button plain @click="load" :loading="loading">刷新</el-button>
            <el-button type="danger" plain :disabled="!selectedIds.length" @click="deleteSelected">删除选中 ({{ selectedIds.length }})</el-button>
            <el-button type="danger" @click="deleteAll">清空日志</el-button>
          </div>
        </div>
      </template>

      <el-table :data="items" v-loading="loading" stripe @selection-change="onSelectionChange">
        <el-table-column type="selection" width="45" />
        <el-table-column label="时间" width="180">
          <template #default="{row}">{{ formatTime(row.created_at) }}</template>
        </el-table-column>
        <el-table-column label="请求ID" prop="request_id" show-overflow-tooltip />
        <el-table-column label="选中节点" prop="selected_node" width="120" />
        <el-table-column label="算法" prop="algorithm" width="150" />
        <el-table-column label="决策耗时(ms)" prop="decision_ms" width="130">
          <template #default="{row}">{{ row.decision_ms?.toFixed(3) }}</template>
        </el-table-column>
        <el-table-column label="活跃连接数" prop="active_conns_at_decision" width="110" />
        <el-table-column label="候选节点" prop="candidates" show-overflow-tooltip />
      </el-table>

      <el-pagination style="margin-top:16px;" v-model:current-page="page" :page-size="50"
        :total="total" layout="total, prev, pager, next" @current-change="load" />
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import client from '../api/client'

const items = ref([])
const total = ref(0)
const page = ref(1)
const loading = ref(false)
const nodeFilter = ref('')
const selectedIds = ref([])

function formatTime(ts) {
  if (!ts) return '-'
  const d = new Date(ts.replace(' ', 'T') + 'Z')
  if (isNaN(d.getTime())) return ts
  const pad = n => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth()+1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`
}

function onSelectionChange(rows) {
  selectedIds.value = rows.map(r => r.id)
}

async function load() {
  loading.value = true
  try {
    const { data } = await client.get('/api/logs', { params: { page: page.value, size: 50, node_id: nodeFilter.value } })
    items.value = data.items
    total.value = data.total
  } catch { ElMessage.error('加载失败') } finally { loading.value = false }
}

async function deleteSelected() {
  try {
    await ElMessageBox.confirm(`确定删除选中的 ${selectedIds.value.length} 条日志？`, '确认删除', { type: 'warning' })
    const { data } = await client.delete('/api/logs', { params: { mode: 'selected', ids: selectedIds.value.join(',') } })
    ElMessage.success(`已删除 ${data.deleted} 条`)
    load()
  } catch { /* cancelled */ }
}

async function deleteAll() {
  try {
    await ElMessageBox.confirm('确定清空全部调度日志？此操作不可撤销！', '确认清空', { type: 'error' })
    const { data } = await client.delete('/api/logs', { params: { mode: 'all' } })
    ElMessage.success(`已删除 ${data.deleted} 条`)
    page.value = 1
    load()
  } catch { /* cancelled */ }
}

onMounted(load)
</script>
