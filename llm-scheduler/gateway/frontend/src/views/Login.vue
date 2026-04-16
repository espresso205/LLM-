<template>
  <div style="min-height:100vh;display:flex;align-items:center;justify-content:center;background:#111827;">
    <el-col :xs="22" :sm="12" :md="7">
      <el-card shadow="always" style="border-radius:12px;">
        <template #header>
          <div style="text-align:center;padding:8px 0;">
            <div style="color:#f3f4f6;font-size:20px;font-weight:600;">LLM 调度系统</div>
            <div style="color:#9ca3af;font-size:13px;margin-top:4px;">请登录以继续</div>
          </div>
        </template>
        <el-form :model="form" @submit.prevent="submit" label-position="top">
          <el-form-item label="用户名">
            <el-input v-model="form.username" placeholder="请输入用户名" prefix-icon="User" size="large" />
          </el-form-item>
          <el-form-item label="密码">
            <el-input v-model="form.password" type="password" placeholder="请输入密码" prefix-icon="Lock" show-password size="large" />
          </el-form-item>
          <el-button type="primary" native-type="submit" :loading="loading" style="width:100%;height:40px;font-size:15px;margin-top:8px;" size="large">登 录</el-button>
          <el-divider style="margin:16px 0;"><span style="color:#9ca3af;font-size:12px;">还没有账号？</span></el-divider>
          <el-button style="width:100%;" plain @click="showRegister=true">注 册</el-button>
        </el-form>
      </el-card>
    </el-col>
  </div>

  <!-- Register dialog -->
  <el-dialog v-model="showRegister" title="注册新账号" width="400px">
    <el-form :model="reg" label-position="top">
      <el-form-item label="用户名">
        <el-input v-model="reg.username" />
      </el-form-item>
      <el-form-item label="密码（至少6位）">
        <el-input v-model="reg.password" type="password" show-password />
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="showRegister=false">取消</el-button>
      <el-button type="primary" :loading="regLoading" @click="doRegister">注册</el-button>
    </template>
  </el-dialog>
</template>

<script setup>
import { reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import { ElMessage } from 'element-plus'
import axios from 'axios'

const auth = useAuthStore()
const router = useRouter()
const form = reactive({ username: '', password: '' })
const loading = ref(false)
const showRegister = ref(false)
const reg = reactive({ username: '', password: '' })
const regLoading = ref(false)

async function submit() {
  loading.value = true
  try {
    await auth.login(form.username, form.password)
    ElMessage.success('登录成功')
    router.push('/chat')
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '登录失败，请检查用户名和密码')
  } finally {
    loading.value = false
  }
}

async function doRegister() {
  regLoading.value = true
  try {
    await axios.post('/auth/register', { username: reg.username, password: reg.password })
    ElMessage.success('注册成功，请登录')
    showRegister.value = false
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '注册失败')
  } finally {
    regLoading.value = false
  }
}
</script>
