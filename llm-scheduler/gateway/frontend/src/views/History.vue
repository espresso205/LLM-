<template>
  <div style="max-width:1000px;margin:24px auto;padding:0 16px;">
    <el-card>
      <template #header>
        <div style="display:flex;align-items:center;justify-content:space-between;">
          <b style="color:#f3f4f6;">我的请求历史</b>
          <div style="display:flex;gap:8px;">
            <el-select v-model="statusFilter" placeholder="状态筛选" clearable style="width:130px;" @change="load">
              <el-option label="成功" value="success" />
              <el-option label="失败" value="error" />
              <el-option label="待处理" value="pending" />
            </el-select>
            <el-button @click="load" :loading="loading">刷新</el-button>
            <el-button type="danger" @click="deleteAll">清空历史</el-button>
          </div>
        </div>
      </template>

      <el-table :data="items" v-loading="loading" stripe>
        <el-table-column label="时间" width="180">
          <template #default="{row}">{{ formatTime(row.created_at) }}</template>
        </el-table-column>
        <el-table-column label="模型" prop="model" width="160" />
        <el-table-column label="状态" width="90">
          <template #default="{row}">
            <el-tag :type="row.status==='success'?'success':row.status==='error'?'danger':'info'" size="small">{{ row.status }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="延迟(ms)" prop="latency_ms" width="100">
          <template #default="{row}">{{ row.latency_ms?.toFixed(0) ?? '-' }}</template>
        </el-table-column>
        <el-table-column label="Tokens" prop="total_tokens" width="80" />
        <el-table-column label="节点" prop="node_id" width="100" />
        <el-table-column label="操作" width="140">
          <template #default="{row}">
            <el-button size="small" @click="viewDetail(row.id)">详情</el-button>
            <el-button size="small" type="danger" @click="deleteOne(row.id)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>

      <el-pagination style="margin-top:16px;" v-model:current-page="page" :page-size="20"
        :total="total" layout="total, prev, pager, next" @current-change="load" />
    </el-card>

    <!-- Detail dialog -->
    <el-dialog v-model="showDetail" title="请求详情" width="700px">
      <el-descriptions :column="1" border v-if="detail">
        <el-descriptions-item label="ID">{{ detail.id }}</el-descriptions-item>
        <el-descriptions-item label="创建时间">{{ formatTime(detail.created_at) }}</el-descriptions-item>
        <el-descriptions-item label="完成时间">{{ formatTime(detail.completed_at) }}</el-descriptions-item>
        <el-descriptions-item label="状态"><el-tag :type="detail.status==='success'?'success':'danger'">{{ detail.status }}</el-tag></el-descriptions-item>
        <el-descriptions-item label="延迟">{{ detail.latency_ms?.toFixed(2) }} ms</el-descriptions-item>
        <el-descriptions-item label="Tokens">{{ detail.total_tokens }}</el-descriptions-item>
        <el-descriptions-item label="节点">{{ detail.node_id }}</el-descriptions-item>
        <el-descriptions-item label="请求内容">
          <pre style="white-space:pre-wrap;max-height:200px;overflow:auto;font-size:12px;">{{ formatJson(detail.messages_json) }}</pre>
        </el-descriptions-item>
        <el-descriptions-item label="响应内容">
          <pre style="white-space:pre-wrap;max-height:200px;overflow:auto;font-size:12px;">{{ extractReply(detail.response_json) }}</pre>
        </el-descriptions-item>
        <el-descriptions-item v-if="detail.error_message" label="错误">{{ detail.error_message }}</el-descriptions-item>
      </el-descriptions>
    </el-dialog>
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
const showDetail = ref(false)
const detail = ref(null)

function formatTime(ts) {
  if (!ts) return '-'
  const d = new Date(ts.replace(' ', 'T') + 'Z')
  if (isNaN(d.getTime())) return ts
  const pad = n => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth()+1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`
}

async function load() {
  loading.value = true
  try {
    const { data } = await client.get('/api/history', {
      params: { page: page.value, size: 20, status: statusFilter.value }
    })
    items.value = data.items
    total.value = data.total
  } catch (e) { ElMessage.error('加载失败') } finally { loading.value = false }
}

async function viewDetail(id) {
  try {
    const { data } = await client.get(`/api/history/${id}`)
    detail.value = data
    showDetail.value = true
  } catch { ElMessage.error('获取详情失败') }
}

async function deleteOne(id) {
  try {
    await ElMessageBox.confirm('确定删除该条记录？', '确认删除', { type: 'warning' })
    const { data } = await client.delete(`/api/history/${id}`)
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

function formatJson(str) {
  try { return JSON.stringify(JSON.parse(str), null, 2) } catch { return str || '' }
}

function extractReply(str) {
  try {
    const obj = JSON.parse(str)
    return obj?.choices?.[0]?.message?.content || JSON.stringify(obj, null, 2)
  } catch { return str || '' }
}

onMounted(load)
</script>
