<template>
  <el-container style="min-height:100vh;background:#111827;">
    <el-header style="display:flex;align-items:center;justify-content:space-between;background:#111827;border-bottom:1px solid #374151;height:56px;">
      <span style="font-size:16px;font-weight:600;color:#f3f4f6;">推理节点管理</span>
      <div style="display:flex;gap:16px;align-items:center;">
        <el-menu mode="horizontal" background-color="#111827" text-color="#9ca3af" active-text-color="#818cf8" router :default-active="$route.path" style="border:none;">
          <el-menu-item index="/test">本地测试</el-menu-item>
          <el-menu-item index="/model">模型信息</el-menu-item>
          <el-menu-item index="/logs">请求日志</el-menu-item>
        </el-menu>
        <div style="display:flex;gap:8px;align-items:center;">
          <el-tag :type="health.status==='ok'?'success':'danger'">{{ health.status || 'unknown' }}</el-tag>
          <el-tag type="info">连接数: {{ health.active_connections ?? '-' }}</el-tag>
          <el-button size="small" plain @click="goHome">返回主界面</el-button>
        </div>
      </div>
    </el-header>
    <el-main style="background:#111827;padding:0;">
      <router-view />
    </el-main>
  </el-container>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import axios from 'axios'
const health = ref({})
let timer
async function loadHealth() {
  try { const { data } = await axios.get('/health'); health.value = data } catch {}
}
onMounted(() => { loadHealth(); timer = setInterval(loadHealth, 5000) })
onUnmounted(() => clearInterval(timer))

function goHome() {
  window.open('http://localhost:8080', '_self')
}
</script>
