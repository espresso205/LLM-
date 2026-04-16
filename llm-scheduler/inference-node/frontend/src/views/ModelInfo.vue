<template>
  <div style="max-width:1100px;margin:24px auto;padding:0 16px;">
    <el-card>
      <template #header><b style="color:#f3f4f6;">模型信息</b></template>
      <el-descriptions :column="1" border v-if="model">
        <el-descriptions-item v-for="(v, k) in model" :key="k" :label="k">{{ v }}</el-descriptions-item>
      </el-descriptions>
      <el-empty v-else description="暂无模型信息" />
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import axios from 'axios'

const model = ref(null)
onMounted(async () => {
  try {
    const { data } = await axios.get('/api/model')
    const first = data.data?.[0]
    if (first) model.value = first
  } catch {}
})
</script>
