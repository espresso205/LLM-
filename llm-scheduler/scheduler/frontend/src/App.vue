<template>
  <el-container style="min-height:100vh;background:#111827;">
    <el-header style="display:flex;align-items:center;justify-content:space-between;background:#111827;border-bottom:1px solid #374151;height:56px;">
      <span style="font-size:16px;font-weight:600;color:#f3f4f6;">LLM 调度器管理</span>
      <el-menu mode="horizontal" background-color="#111827" text-color="#9ca3af" active-text-color="#818cf8" router :default-active="$route.path" style="border:none;">
        <el-menu-item index="/nodes">节点状态</el-menu-item>
        <el-menu-item index="/strategy">调度策略</el-menu-item>
        <el-menu-item index="/logs">调度日志</el-menu-item>
      </el-menu>
      <el-button size="small" plain @click="goGateway">返回主界面</el-button>
    </el-header>
    <el-main style="background:#111827;padding:0;">
      <router-view />
    </el-main>
  </el-container>
</template>
<script setup>
function goGateway() { window.location.href = 'http://localhost:8080' }
</script>
