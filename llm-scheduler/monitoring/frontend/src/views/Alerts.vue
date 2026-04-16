<template>
  <div style="max-width:1100px;margin:24px auto;padding:0 16px;">
    <!-- Active alerts banner -->
    <el-alert v-for="a in activeAlerts" :key="a.id" :title="a.message" type="error" show-icon closable style="margin-bottom:8px;">
      <template #default>
        <span>{{ a.fired_at }}</span>
        <el-button size="small" style="margin-left:12px;" @click="resolve(a.id)">标记已解决</el-button>
      </template>
    </el-alert>

    <el-row :gutter="16">
      <!-- Rules management -->
      <el-col :span="14">
        <el-card>
          <template #header>
            <div style="display:flex;justify-content:space-between;align-items:center;">
              <b style="color:#f3f4f6;">告警规则</b>
              <el-button type="primary" size="small" @click="showAdd=true">添加规则</el-button>
            </div>
          </template>
          <el-table :data="rules" stripe>
            <el-table-column label="名称" prop="name" />
            <el-table-column label="指标" prop="metric" width="120" />
            <el-table-column label="条件" width="130">
              <template #default="{row}">{{ row.metric }} {{ opLabel(row.operator) }} {{ row.threshold }}</template>
            </el-table-column>
            <el-table-column label="窗口(s)" prop="window_s" width="80" />
            <el-table-column label="状态" width="80">
              <template #default="{row}">
                <el-switch v-model="row.is_active" :active-value="1" :inactive-value="0" @change="toggleRule(row)" />
              </template>
            </el-table-column>
            <el-table-column label="删除" width="70">
              <template #default="{row}">
                <el-button size="small" type="danger" @click="deleteRule(row.id)">删除</el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-col>

      <!-- Alert history -->
      <el-col :span="10">
        <el-card>
          <template #header><b style="color:#f3f4f6;">告警历史</b></template>
          <el-table :data="history" stripe>
            <el-table-column label="规则" prop="rule_name" width="100" />
            <el-table-column label="时间" prop="fired_at" />
            <el-table-column label="值" prop="triggered_value" width="80">
              <template #default="{row}">{{ row.triggered_value?.toFixed(3) }}</template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-col>
    </el-row>

    <!-- Add rule dialog -->
    <el-dialog v-model="showAdd" title="新增告警规则" width="450px">
      <el-form :model="newRule" label-width="100px">
        <el-form-item label="规则名称"><el-input v-model="newRule.name" /></el-form-item>
        <el-form-item label="监控指标">
          <el-select v-model="newRule.metric">
            <el-option label="QPS" value="qps" />
            <el-option label="P95延迟" value="latency_p95" />
            <el-option label="成功率" value="success_rate" />
            <el-option label="错误数" value="error_count" />
          </el-select>
        </el-form-item>
        <el-form-item label="触发条件">
          <el-select v-model="newRule.operator" style="width:100px;margin-right:8px;">
            <el-option label="大于(>)" value="gt" />
            <el-option label="小于(<)" value="lt" />
            <el-option label="等于(=)" value="eq" />
          </el-select>
          <el-input-number v-model="newRule.threshold" :precision="3" style="width:140px;" />
        </el-form-item>
        <el-form-item label="窗口时间(s)"><el-input-number v-model="newRule.window_s" :min="30" :max="3600" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showAdd=false">取消</el-button>
        <el-button type="primary" @click="addRule">添加</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import client from '../api/client'

const rules = ref([])
const history = ref([])
const activeAlerts = ref([])
const showAdd = ref(false)
const newRule = reactive({ name: '', metric: 'latency_p95', operator: 'gt', threshold: 2000, window_s: 300 })

const OP = { gt: '>', lt: '<', eq: '=' }
function opLabel(op) { return OP[op] || op }

async function load() {
  try {
    const [r, h, a] = await Promise.all([
      client.get('/api/alerts/rules'),
      client.get('/api/alerts/history', { params: { resolved: false } }),
      client.get('/api/alerts/history', { params: { resolved: false } }),
    ])
    rules.value = r.data
    history.value = h.data.items
    activeAlerts.value = a.data.items
  } catch {}
}

async function addRule() {
  try {
    await client.post('/api/alerts/rules', newRule)
    ElMessage.success('规则已添加')
    showAdd.value = false
    load()
  } catch { ElMessage.error('添加失败') }
}

async function toggleRule(row) {
  try { await client.patch(`/api/alerts/rules/${row.id}`, { is_active: row.is_active }) } catch {}
}

async function deleteRule(id) {
  try { await client.delete(`/api/alerts/rules/${id}`); ElMessage.success('已删除'); load() } catch {}
}

async function resolve(id) {
  try { await client.post(`/api/alerts/history/${id}/resolve`); load() } catch {}
}

onMounted(load)
</script>
