<template>
  <div style="max-width:1100px;margin:24px auto;padding:0 16px;">
    <el-card>
      <template #header>
        <div style="display:flex;align-items:center;justify-content:space-between;">
          <b style="color:#f3f4f6;">全部请求历史（管理员视图）</b>
          <div style="display:flex;gap:8px;">
            <el-input v-model="usernameFilter" placeholder="按用户名筛选" clearable style="width:160px;" @change="load" />
            <el-select v-model="statusFilter" placeholder="状态" clearable style="width:120px;" @change="load">
              <el-option label="成功" value="success" />
              <el-option label="失败" value="error" />
            </el-select>
            <el-button @click="load" :loading="loading">刷新</el-button>
            <el-button type="danger" plain :disabled="!selectedIds.length" @click="deleteSelected">删除选中 ({{ selectedIds.length }})</el-button>
            <el-button type="danger" @click="deleteAll">清空历史</el-button>
          </div>
        </div>
      </template>

      <el-table :data="items" v-loading="loading" stripe @selection-change="onSelectionChange">
        <el-table-column type="selection" width="45" />
        <el-table-column label="时间" width="180">
          <template #default="{row}">{{ formatTime(row.created_at) }}</template>
        </el-table-column>
        <el-table-column label="用户" prop="username" width="120" />
        <el-table-column label="模型" prop="model" width="150" />
        <el-table-column label="状态" width="90">
          <template #default="{row}">
            <el-tag :type="row.status==='success'?'success':'danger'" size="small">{{ row.status }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="延迟(ms)" prop="latency_ms" width="100">
          <template #default="{row}">{{ row.latency_ms?.toFixed(0) ?? '-' }}</template>
        </el-table-column>
        <el-table-column label="Tokens" prop="total_tokens" width="80" />
        <el-table-column label="节点" prop="node_id" />
        <el-table-column label="错误" prop="error_message" show-overflow-tooltip />
        <el-table-column label="操作" width="80">
          <template #default="{row}">
            <el-button size="small" type="danger" @click="deleteOne(row.id)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>

      <el-pagination style="margin-top:16px;" v-model:current-page="page" :page-size="20"
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
const statusFilter = ref('')
const usernameFilter = ref('')
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
    const { data } = await client.get('/api/history', {
      params: { page: page.value, size: 20, status: statusFilter.value, username: usernameFilter.value }
    })
    items.value = data.items
    total.value = data.total
  } catch { ElMessage.error('加载失败') } finally { loading.value = false }
}

async function deleteOne(id) {
  try {
    await ElMessageBox.confirm('确定删除该条记录？', '确认删除', { type: 'warning' })
    const { data } = await client.delete(`/api/history/${id}`)
    ElMessage.success(`已删除 ${data.deleted} 条`)
    load()
  } catch { /* cancelled */ }
}

async function deleteSelected() {
  try {
    await ElMessageBox.confirm(`确定删除选中的 ${selectedIds.value.length} 条记录？`, '确认删除', { type: 'warning' })
    const { data } = await client.delete('/api/history', {
      params: { mode: 'selected', ids: selectedIds.value.join(',') }
    })
    ElMessage.success(`已删除 ${data.deleted} 条`)
    load()
  } catch { /* cancelled */ }
}

async function deleteAll() {
  try {
    await ElMessageBox.confirm('确定清空全部历史记录？此操作不可撤销！', '确认清空', { type: 'error' })
    const { data } = await client.delete('/api/history')
    ElMessage.success(`已删除 ${data.deleted} 条`)
    page.value = 1
    load()
  } catch { /* cancelled */ }
}

onMounted(load)
</script>
