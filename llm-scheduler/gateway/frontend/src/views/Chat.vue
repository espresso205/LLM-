<template>
  <div style="max-width:900px;margin:24px auto;padding:0 16px;position:relative;">
    <!-- Settings button (left side) -->
    <div style="position:fixed;left:24px;top:50%;transform:translateY(-50%);z-index:100;display:flex;flex-direction:column;gap:12px;">
      <el-tooltip placement="right" :show-after="100">
        <template #content>
          <div style="max-width:240px;line-height:1.6;">
            <b>Max Tokens (最大生成长度)</b><br/>
            控制模型单次回复最多生成的 token 数量。值越大回复越长，但消耗更多算力。
            <br/><span style="color:#909399;">范围: 64 - 4096</span>
          </div>
        </template>
        <div class="setting-btn" @click="showTokens = !showTokens" :class="{active: showTokens}">
          <el-icon :size="18"><Memo /></el-icon>
        </div>
      </el-tooltip>

      <el-tooltip placement="right" :show-after="100">
        <template #content>
          <div style="max-width:240px;line-height:1.6;">
            <b>Temperature (温度)</b><br/>
            控制输出的随机性。值越低（如 0.2）回答越集中、确定；值越高（如 1.5）回答越有创造性和多样性。
            <br/><span style="color:#909399;">范围: 0 - 2.0</span>
          </div>
        </template>
        <div class="setting-btn" @click="showTemp = !showTemp" :class="{active: showTemp}">
          <el-icon :size="18"><Opportunity /></el-icon>
        </div>
      </el-tooltip>

      <el-tooltip placement="right" :show-after="100">
        <template #content>
          <div style="max-width:240px;line-height:1.6;">
            <b>Top-P (核采样)</b><br/>
            通过限制候选 token 的累积概率来控制多样性。值越低（如 0.5）输出越集中；值越高（如 0.95）输出越丰富多变。
            <br/><span style="color:#909399;">范围: 0.1 - 1.0</span>
          </div>
        </template>
        <div class="setting-btn" @click="showTopP = !showTopP" :class="{active: showTopP}">
          <el-icon :size="18"><TrendCharts /></el-icon>
        </div>
      </el-tooltip>

      <el-tooltip placement="right" :show-after="100">
        <template #content>
          <div style="max-width:240px;line-height:1.6;">
            <b>流式输出 (Streaming)</b><br/>
            开启后回复将逐字显示，无需等待完整生成。关闭则等待完整回复后一次性显示。
          </div>
        </template>
        <div class="setting-btn" @click="useStream = !useStream" :class="{active: useStream}">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M5 12h14"/>
            <path d="M12 5l7 7-7 7"/>
          </svg>
        </div>
      </el-tooltip>
    </div>

    <!-- Left floating panels (appear on click) -->
    <transition name="slide">
      <div v-if="showTokens" class="param-panel" style="top:calc(50% - 100px);">
        <div class="param-title">Max Tokens</div>
        <el-input-number v-model="params.max_tokens" :min="64" :max="4096" :step="64" size="small" style="width:100%;" />
        <div class="param-val">{{ params.max_tokens }}</div>
      </div>
    </transition>
    <transition name="slide">
      <div v-if="showTemp" class="param-panel" style="top:calc(50% - 20px);">
        <div class="param-title">Temperature</div>
        <el-slider v-model="params.temperature" :min="0" :max="2" :step="0.05" />
        <div class="param-val">{{ params.temperature.toFixed(2) }}</div>
      </div>
    </transition>
    <transition name="slide">
      <div v-if="showTopP" class="param-panel" style="top:calc(50% + 60px);">
        <div class="param-title">Top-P</div>
        <el-slider v-model="params.top_p" :min="0.1" :max="1" :step="0.05" />
        <div class="param-val">{{ params.top_p.toFixed(2) }}</div>
      </div>
    </transition>

    <!-- Main chat card -->
    <el-card>
      <template #header>
        <div style="display:flex;align-items:center;justify-content:space-between;">
          <b style="color:#f3f4f6;font-size:15px;">推理对话</b>
          <div v-if="lastInfo" style="display:flex;gap:16px;align-items:center;font-size:12px;color:#9ca3af;">
            <span><b style="color:#f3f4f6;">{{ lastInfo.latency_ms?.toFixed(0) }}ms</b></span>
            <span><span style="color:#9ca3af;">{{ lastInfo.total_tokens }} tokens</span></span>
            <span><el-tag size="small" type="info">{{ lastInfo.node_id || '-' }}</el-tag></span>
          </div>
        </div>
      </template>

      <!-- Chat history -->
      <div ref="chatBox" style="height:480px;overflow-y:auto;padding:12px;background:#111827;border-radius:8px;margin-bottom:12px;border:1px solid #374151;">
        <div v-if="messages.length === 0" style="display:flex;align-items:center;justify-content:center;height:100%;color:#6b7280;font-size:14px;">
          开始一段新的对话...
        </div>
        <div v-for="(msg, i) in messages" :key="i" :style="{textAlign: msg.role==='user'?'right':'left', marginBottom:'14px'}">
          <div :style="{
            display:'inline-block',
            maxWidth:'82%',
            textAlign:'left',
            padding:'10px 14px',
            borderRadius: msg.role==='user' ? '12px 12px 4px 12px' : '12px 12px 12px 4px',
            background: msg.role==='user' ? '#6366f1' : '#1f2937',
            color: msg.role==='user' ? '#ffffff' : '#f3f4f6',
            fontSize:'14px',
            lineHeight:'1.6',
            whiteSpace:'pre-wrap',
            border: msg.role==='user' ? 'none' : '1px solid #374151',
          }">
            <template v-if="msg.images && msg.images.length">
              <div style="display:flex;gap:6px;flex-wrap:wrap;margin-bottom:6px;">
                <img v-for="(src,j) in msg.images" :key="j" :src="src" style="max-width:200px;max-height:160px;border-radius:6px;cursor:pointer;" @click="previewImage(src)" />
              </div>
            </template>
            {{ msg.content }}
          </div>
        </div>
        <div v-if="loading" style="text-align:center;color:#818cf8;padding:8px;"><el-icon class="is-loading"><Loading /></el-icon> 推理中...</div>
      </div>

      <!-- Input area -->
      <!-- Pending images preview -->
      <div v-if="pendingImages.length" style="display:flex;gap:8px;flex-wrap:wrap;margin-bottom:8px;">
        <div v-for="(img, i) in pendingImages" :key="i" style="position:relative;display:inline-block;">
          <img :src="img" style="height:64px;border-radius:6px;border:1px solid #374151;object-fit:cover;" />
          <div class="remove-img" @click="pendingImages.splice(i, 1)">✕</div>
        </div>
      </div>
      <div style="display:flex;gap:8px;align-items:flex-end;">
        <el-button :icon="UploadFilled" @click="triggerUpload" style="flex-shrink:0;height:40px;" />
        <el-input v-model="prompt" type="textarea" :rows="3" placeholder="输入你的问题... (Ctrl+Enter 发送)" @keydown.ctrl.enter="send" style="flex:1;" />
        <el-tooltip content="丰富提示词" placement="top" :show-after="300">
          <div class="sparkle-btn" :class="{active: enhancing}" @click="enhancePrompt">
            <svg v-if="!enhancing" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <path d="M12 2l2.09 6.26L20.18 10l-6.09 1.74L12 18l-2.09-6.26L3.82 10l6.09-1.74L12 2z"/>
              <path d="M19 15l.81 2.43L22.24 18l-2.43.57L19 21l-.81-2.43L15.76 18l2.43-.57L19 15z"/>
            </svg>
            <el-icon v-else :size="18" class="is-loading"><Loading /></el-icon>
          </div>
        </el-tooltip>
      </div>
      <div style="margin-top:10px;display:flex;gap:8px;align-items:center;">
        <el-button type="primary" :loading="loading" @click="send" style="flex:1;">发送</el-button>
        <el-button @click="clearChat" plain>清空</el-button>
      </div>
      <input ref="fileInput" type="file" accept="image/*" multiple style="display:none;" @change="onFileSelect" />
    </el-card>

    <!-- Image preview dialog -->
    <el-dialog v-model="showPreview" :show-close="true" width="auto" style="background:transparent;">
      <img :src="previewSrc" style="max-width:80vw;max-height:80vh;border-radius:8px;" />
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, nextTick } from 'vue'
import { ElMessage } from 'element-plus'
import { UploadFilled } from '@element-plus/icons-vue'
import client from '../api/client'

const prompt = ref('')
const messages = ref([])
const loading = ref(false)
const chatBox = ref(null)
const lastInfo = ref(null)
const params = reactive({ max_tokens: 512, temperature: 0.7, top_p: 0.95 })
const pendingImages = ref([])
const fileInput = ref(null)
const showPreview = ref(false)
const previewSrc = ref('')
const enhancing = ref(false)

const showTokens = ref(false)
const showTemp = ref(false)
const showTopP = ref(false)
const useStream = ref(false)

function triggerUpload() { fileInput.value?.click() }

function onFileSelect(e) {
  const files = Array.from(e.target.files || [])
  files.forEach(file => {
    const reader = new FileReader()
    reader.onload = () => { pendingImages.value.push(reader.result) }
    reader.readAsDataURL(file)
  })
  e.target.value = ''
}

function previewImage(src) { previewSrc.value = src; showPreview.value = true }

function buildContent(text, images) {
  if (!images || images.length === 0) return text
  const parts = images.map(src => ({ type: 'image_url', image_url: { url: src } }))
  if (text) parts.push({ type: 'text', text })
  return parts
}

const ENHANCE_SYSTEM = `你的唯一任务是将用户的简短输入改写为一条更完善的"提示词/指令"。
你绝不是在回答问题，而是在帮用户写出一个更好的提问。绝对禁止直接给出答案、代码、方案或任何解题内容。

改写规则：
1. 保持用户的原始意图不变
2. 补充必要的背景上下文和约束条件
3. 明确期望的输出格式、篇幅、风格等要求
4. 提示词应以祈使句结尾，像是在给AI下指令
5. 如果附带了图片，补充"请结合图片中的XXX进行分析"之类的引导
6. 直接输出改写后的提示词文本，不加任何解释、标注、前缀或引号包裹`

async function enhancePrompt() {
  if (!prompt.value.trim() || enhancing.value) return
  enhancing.value = true
  try {
    const userContent = buildContent(prompt.value.trim(), pendingImages.value.length ? pendingImages.value : null)
    const { data } = await client.post('/v1/chat/completions', {
      model: 'auto',
      messages: [
        { role: 'system', content: ENHANCE_SYSTEM },
        { role: 'user', content: userContent },
      ],
      max_tokens: 512,
      temperature: 0.7,
    })
    const enhanced = data.choices?.[0]?.message?.content?.trim()
    if (enhanced) {
      prompt.value = enhanced
      ElMessage.success('提示词已丰富')
    }
  } catch {
    ElMessage.error('丰富失败，请重试')
  } finally {
    enhancing.value = false
  }
}

async function send() {
  const hasContent = prompt.value.trim() || pendingImages.value.length
  if (!hasContent || loading.value) return
  const userMsg = prompt.value.trim()
  const images = [...pendingImages.value]
  messages.value.push({ role: 'user', content: userMsg, images: images.length ? images : undefined })
  prompt.value = ''
  pendingImages.value = []
  loading.value = true
  await scrollToBottom()

  const chatMessages = messages.value.map(m => ({
    role: m.role,
    content: buildContent(m.content, m.images),
  }))

  if (useStream.value) {
    await sendStream(chatMessages)
  } else {
    await sendNonStream(chatMessages)
  }
}

async function sendNonStream(chatMessages) {
  try {
    const start = Date.now()
    const { data } = await client.post('/v1/chat/completions', {
      model: 'auto',
      messages: chatMessages,
      ...params,
    })
    const reply = data.choices?.[0]?.message?.content || ''
    messages.value.push({ role: 'assistant', content: reply })
    lastInfo.value = {
      latency_ms: Date.now() - start,
      total_tokens: data.usage?.total_tokens,
      node_id: data._node_id,
    }
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '推理失败，请重试')
    messages.value.push({ role: 'assistant', content: '推理失败: ' + (e.response?.data?.detail || e.message) })
  } finally {
    loading.value = false
    await scrollToBottom()
  }
}

async function sendStream(chatMessages) {
  // Add a placeholder assistant message that we'll update in-place
  const assistantIdx = messages.value.length
  messages.value.push({ role: 'assistant', content: '' })
  const start = Date.now()

  try {
    const auth = JSON.parse(localStorage.getItem('auth') || '{}')
    const token = auth.token || ''
    const resp = await fetch('/v1/chat/completions', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`,
      },
      body: JSON.stringify({
        model: 'auto',
        messages: chatMessages,
        stream: true,
        ...params,
      }),
    })

    if (!resp.ok) {
      const err = await resp.json().catch(() => ({ detail: resp.statusText }))
      throw new Error(err.detail || 'Stream request failed')
    }

    const reader = resp.body.getReader()
    const decoder = new TextDecoder()
    let buffer = ''
    let totalTokens = null
    let nodeId = null

    while (true) {
      const { done, value } = await reader.read()
      if (done) break

      buffer += decoder.decode(value, { stream: true })
      const lines = buffer.split('\n')
      buffer = lines.pop() || ''

      for (const line of lines) {
        // Parse SSE events
        if (line.startsWith('event: meta')) {
          // Next data line has node metadata
          continue
        }
        if (!line.startsWith('data: ')) continue
        const raw = line.slice(6).trim()
        if (raw === '[DONE]') continue

        try {
          const parsed = JSON.parse(raw)

          // Meta event with node info
          if (parsed._node_id) {
            nodeId = parsed._node_id
            continue
          }
          // Error event
          if (parsed.error) {
            throw new Error(parsed.error)
          }

          // Extract content delta
          const delta = parsed.choices?.[0]?.delta?.content
          if (delta) {
            messages.value[assistantIdx].content += delta
            await scrollToBottom()
          }

          // Capture usage from the last chunk
          if (parsed.usage) {
            totalTokens = parsed.usage.total_tokens
          }
        } catch (e) {
          if (e.message && !e.message.includes('JSON')) throw e
        }
      }
    }

    lastInfo.value = {
      latency_ms: Date.now() - start,
      total_tokens: totalTokens,
      node_id: nodeId,
    }
  } catch (e) {
    const content = messages.value[assistantIdx].content
    messages.value[assistantIdx].content = content + (content ? '\n' : '') + '[流式错误: ' + e.message + ']'
    ElMessage.error('流式推理失败')
  } finally {
    loading.value = false
    await scrollToBottom()
  }
}

function clearChat() { messages.value = []; lastInfo.value = null }

async function scrollToBottom() {
  await nextTick()
  if (chatBox.value) chatBox.value.scrollTop = chatBox.value.scrollHeight
}
</script>

<style scoped>
.setting-btn {
  width: 42px;
  height: 42px;
  border-radius: 12px;
  background: #1f2937;
  border: 1px solid #374151;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #9ca3af;
  cursor: pointer;
  transition: all 0.2s ease;
  box-shadow: 0 1px 3px rgba(0,0,0,0.3);
}
.setting-btn:hover {
  background: #6366f1;
  border-color: #6366f1;
  color: #fff;
  transform: scale(1.1);
}
.setting-btn.active {
  background: #6366f1;
  border-color: #6366f1;
  color: #fff;
}

.param-panel {
  position: fixed;
  left: 80px;
  width: 200px;
  z-index: 99;
  background: #1f2937;
  border: 1px solid #374151;
  border-radius: 12px;
  padding: 16px;
  box-shadow: 0 1px 3px rgba(0,0,0,0.3);
}
.param-title {
  font-size: 12px;
  font-weight: 600;
  color: #818cf8;
  margin-bottom: 10px;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}
.param-val {
  text-align: center;
  font-size: 13px;
  color: #9ca3af;
  margin-top: 6px;
}

.slide-enter-active, .slide-leave-active {
  transition: all 0.25s ease;
}
.slide-enter-from, .slide-leave-to {
  opacity: 0;
  transform: translateX(-12px);
}
.remove-img {
  position: absolute;
  top: -6px;
  right: -6px;
  width: 18px;
  height: 18px;
  border-radius: 50%;
  background: #f56c6c;
  color: #fff;
  font-size: 11px;
  line-height: 18px;
  text-align: center;
  cursor: pointer;
}
.remove-img:hover { background: #e04040; }

.sparkle-btn {
  flex-shrink: 0;
  width: 40px;
  height: 40px;
  border-radius: 10px;
  background: #1f2937;
  border: 1px solid #374151;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fbbf24;
  cursor: pointer;
  transition: all 0.25s ease;
  box-shadow: 0 1px 3px rgba(0,0,0,0.3);
}
.sparkle-btn:hover {
  background: #fbbf24;
  border-color: #fbbf24;
  color: #111827;
}
.sparkle-btn.active {
  color: #818cf8;
  border-color: #818cf8;
}
</style>
