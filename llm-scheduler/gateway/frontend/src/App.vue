<template>
  <el-container style="min-height:100vh;background:#111827;">
    <el-header v-if="auth.isAuthenticated" style="display:flex;align-items:center;justify-content:space-between;background:#111827;border-bottom:1px solid #374151;height:56px;">
      <span style="font-size:16px;font-weight:600;color:#f3f4f6;">LLM 调度系统</span>
      <div style="display:flex;gap:16px;align-items:center;">
        <el-menu mode="horizontal" background-color="#111827" text-color="#9ca3af" active-text-color="#818cf8" router :default-active="$route.path" style="border:none;">
          <el-menu-item index="/chat">推理对话</el-menu-item>
          <el-menu-item index="/history">我的历史</el-menu-item>
          <template v-if="auth.isAdmin">
            <el-menu-item index="/admin/history">全部历史</el-menu-item>
            <el-menu-item index="/admin/users">用户管理</el-menu-item>
          </template>
        </el-menu>
        <span style="font-size:13px;color:#9ca3af;">{{ auth.username }} <el-tag size="small" :type="auth.isAdmin ? 'danger' : 'success'">{{ auth.role }}</el-tag></span>
        <el-button size="small" plain @click="logout">退出</el-button>
        <template v-if="auth.isAdmin">
          <el-divider direction="vertical" />
          <span style="font-size:12px;color:#6b7280;">管理面板：</span>
          <a :href="`http://localhost:8001?token=${auth.token}`" target="_blank" style="text-decoration:none;"><el-button size="small" plain>调度器</el-button></a>
          <a :href="`http://localhost:8002?token=${auth.token}`" target="_blank" style="text-decoration:none;"><el-button size="small" plain>监控</el-button></a>
          <a :href="`http://localhost:8003?token=${auth.token}`" target="_blank" style="text-decoration:none;"><el-button size="small" plain>节点</el-button></a>
        </template>
      </div>
    </el-header>
    <el-main style="background:#111827;padding:0;">
      <router-view />
    </el-main>
  </el-container>
</template>

<script setup>
import { useAuthStore } from './stores/auth'
import { useRouter } from 'vue-router'
const auth = useAuthStore()
const router = useRouter()
function logout() { auth.logout(); router.push('/login') }
function open(port) { window.open(`http://localhost:${port}`, '_blank') }
</script>
