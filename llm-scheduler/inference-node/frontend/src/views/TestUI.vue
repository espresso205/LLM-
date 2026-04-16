<template>
  <div style="max-width:1100px;margin:24px auto;padding:0 16px;">
    <el-row :gutter="16">
      <el-col :span="16">
        <el-card>
          <template #header><b style="color:#f3f4f6;">本地推理测试</b></template>
          <el-input v-model="prompt" type="textarea" :rows="4" placeholder="直接输入Prompt进行本地测试（不经过调度器）" />
          <div style="display:flex;gap:8px;margin-top:8px;">
            <el-input-number v-model="maxTokens" :min="64" :max="2048" :step="64" />
            <el-slider v-model="temperature" :min="0" :max="2" :step="0.1" style="flex:1;" />
            <el-button type="primary" :loading="loading" @click="run">运行推理</el-button>
          </div>
          <el-divider />
          <div v-if="result" class="result-area">{{ result }}</div>
          <div v-if="info" style="font-size:12px;color:#9ca3af;margin-top:8px;">耗时: {{ info.ms }}ms | Tokens: {{ info.tokens }}</div>
        </el-card>
      </el-col>
      <el-col :span="8">
        <el-card>
          <template #header><b style="color:#f3f4f6;">参数</b></template>
          <el-descriptions :column="1" border>
            <el-descriptions-item label="Max Tokens">{{ maxTokens }}</el-descriptions-item>
            <el-descriptions-item label="Temperature">{{ temperature }}</el-descriptions-item>
          </el-descriptions>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { ElMessage } from 'element-plus'
import axios from 'axios'

const prompt = ref('')
const maxTokens = ref(512)
const temperature = ref(0.7)
const loading = ref(false)
const result = ref('')
const info = ref(null)

async function run() {
  if (!prompt.value.trim()) return
  loading.value = true
  result.value = ''
  try {
    const start = Date.now()
    const { data } = await axios.post('/v1/chat/completions', {
      model: 'auto',
      messages: [{ role: 'user', content: prompt.value }],
      max_tokens: maxTokens.value,
      temperature: temperature.value,
    })
    result.value = data.choices?.[0]?.message?.content || ''
    info.value = { ms: Date.now() - start, tokens: data.usage?.total_tokens }
  } catch (e) {
    ElMessage.error('推理失败: ' + (e.response?.data?.detail || e.message))
  } finally { loading.value = false }
}
</script>
