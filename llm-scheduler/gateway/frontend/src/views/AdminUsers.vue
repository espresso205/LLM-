<template>
  <div style="max-width:900px;margin:24px auto;padding:0 16px;">
    <el-card>
      <template #header>
        <div style="display:flex;align-items:center;justify-content:space-between;">
          <b style="color:#f3f4f6;">用户管理</b>
          <el-button type="primary" @click="showCreate=true">新建用户</el-button>
        </div>
      </template>

      <el-table :data="users" v-loading="loading" stripe>
        <el-table-column label="用户名" prop="username" />
        <el-table-column label="角色" width="100">
          <template #default="{row}">
            <el-tag :type="row.role==='admin'?'danger':'success'">{{ row.role }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="90">
          <template #default="{row}">
            <el-tag :type="row.is_active?'success':'info'">{{ row.is_active ? '启用' : '禁用' }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="创建时间" prop="created_at" width="180" />
        <el-table-column label="最后登录" prop="last_login" width="180" />
        <el-table-column label="操作" width="220">
          <template #default="{row}">
            <el-button size="small" @click="toggleRole(row)">
              切换为{{ row.role==='admin'?'用户':'管理员' }}
            </el-button>
            <el-button size="small" :type="row.is_active?'warning':'success'" @click="toggleActive(row)">
              {{ row.is_active?'禁用':'启用' }}
            </el-button>
            <el-popconfirm title="确认删除该用户？" @confirm="deleteUser(row.id)">
              <template #reference>
                <el-button size="small" type="danger">删除</el-button>
              </template>
            </el-popconfirm>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- Create user dialog -->
    <el-dialog v-model="showCreate" title="新建用户" width="400px">
      <el-form :model="newUser" label-width="80px">
        <el-form-item label="用户名"><el-input v-model="newUser.username" /></el-form-item>
        <el-form-item label="密码"><el-input v-model="newUser.password" type="password" show-password /></el-form-item>
        <el-form-item label="角色">
          <el-select v-model="newUser.role">
            <el-option label="用户" value="user" />
            <el-option label="管理员" value="admin" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showCreate=false">取消</el-button>
        <el-button type="primary" :loading="creating" @click="createUser">创建</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted, reactive } from 'vue'
import { ElMessage } from 'element-plus'
import axios from 'axios'
import client from '../api/client'

const users = ref([])
const loading = ref(false)
const showCreate = ref(false)
const creating = ref(false)
const newUser = reactive({ username: '', password: '', role: 'user' })

async function load() {
  loading.value = true
  try {
    const { data } = await client.get('/api/admin/users')
    users.value = data
  } catch { ElMessage.error('加载失败') } finally { loading.value = false }
}

async function toggleRole(row) {
  try {
    const newRole = row.role === 'admin' ? 'user' : 'admin'
    await client.patch(`/api/admin/users/${row.id}`, { role: newRole })
    ElMessage.success('角色已更新')
    load()
  } catch (e) { ElMessage.error(e.response?.data?.detail || '操作失败') }
}

async function toggleActive(row) {
  try {
    await client.patch(`/api/admin/users/${row.id}`, { is_active: !row.is_active })
    ElMessage.success('状态已更新')
    load()
  } catch { ElMessage.error('操作失败') }
}

async function deleteUser(id) {
  try {
    await client.delete(`/api/admin/users/${id}`)
    ElMessage.success('用户已删除')
    load()
  } catch (e) { ElMessage.error(e.response?.data?.detail || '删除失败') }
}

async function createUser() {
  creating.value = true
  try {
    await axios.post('/auth/register', { username: newUser.username, password: newUser.password })
    if (newUser.role === 'admin') {
      const { data: list } = await client.get('/api/admin/users')
      const found = list.find(u => u.username === newUser.username)
      if (found) await client.patch(`/api/admin/users/${found.id}`, { role: 'admin' })
    }
    ElMessage.success('用户创建成功')
    showCreate.value = false
    load()
  } catch (e) { ElMessage.error(e.response?.data?.detail || '创建失败') } finally { creating.value = false }
}

onMounted(load)
</script>
