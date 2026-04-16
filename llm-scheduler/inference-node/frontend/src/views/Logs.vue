<template>
  <div style="max-width:1100px;margin:24px auto;padding:0 16px;">
    <el-card>
      <template #header>
        <div style="display:flex;justify-content:space-between;align-items:center;">
          <b style="color:#f3f4f6;">本节点请求日志</b>
          <el-button plain @click="load" :loading="loading">刷新</el-button>
        </div>
      </template>
      <el-table :data="items" v-loading="loading" stripe>
        <el-table-column label="时间" prop="created_at" width="180" />
        <el-table-column label="状态" width="90">
          <template #default="{row}">
            <el-tag :type="row.status==='success'?'success':'danger'" size="small">{{ row.status }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="延迟(ms)" prop="latency_ms" width="100">
          <template #default="{row}">{{ row.latency_ms?.toFixed(0) }}</template>
        </el-table-column>
        <el-table-column label="Prompt Tokens" prop="prompt_tokens" width="120" />
        <el-table-column label="Completion" prop="completion_tokens" width="110" />
        <el-table-column label="模型" prop="model" />
        <el-table-column label="错误" prop="error_message" show-overflow-tooltip />
      </el-table>
      <el-pagination style="margin-top:12px;" v-model:current-page="page" :page-size="20"
        :total="total" layout="total, prev, pager, next" @current-change="load" />
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import axios from 'axios'

const items = ref([])
const total = ref(0)
const page = ref(1)
const loading = ref(false)

async function load() {
  loading.value = true
  try {
    const { data } = await axios.get('/api/logs', { params: { page: page.value, size: 20 } })
    items.value = data.items
    total.value = data.total
  } catch { ElMessage.error('加载失败') } finally { loading.value = false }
}
onMounted(load)
</script>
