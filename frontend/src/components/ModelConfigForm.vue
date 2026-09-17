<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import client from '../api/client'

const form = ref({ base_url: '', api_key: '', model: '' })
const status = ref<any>(null)
const saving = ref(false)
const testing = ref(false)
const testResult = ref<any>(null)

async function load() {
  const { data } = await client.get('/settings/model')
  status.value = data
  form.value.base_url = data.base_url || ''
  form.value.model = data.model || ''
}

async function save() {
  if (!form.value.base_url.trim() || !form.value.model.trim()) {
    ElMessage.warning('Base URL 与模型名不能为空哦～')
    return
  }
  saving.value = true
  try {
    const { data } = await client.post('/settings/model', {
      base_url: form.value.base_url,
      api_key: form.value.api_key,
      model: form.value.model,
    })
    status.value = data
    form.value.api_key = ''
    testResult.value = null
    ElMessage.success('已保存并生效 ✨')
  } finally {
    saving.value = false
  }
}

async function testConn() {
  testing.value = true
  testResult.value = null
  try {
    const { data } = await client.post('/settings/model/test')
    testResult.value = data
  } finally {
    testing.value = false
  }
}

onMounted(load)
</script>

<template>
  <div class="model-config">
    <div class="status-bar">
      <span class="status-tag" :class="{ ready: status?.provider_ready }">
        {{ status?.provider_ready ? '✅ 已配置' : '🌙 未配置' }}
      </span>
      <span v-if="status?.api_key_set" class="key-masked">
        Key：{{ status.api_key_masked }}
      </span>
    </div>

    <el-form label-position="top">
      <el-form-item label="Base URL">
        <el-input v-model="form.base_url" placeholder="https://ark.cn-beijing.volces.com/api/v3" />
      </el-form-item>
      <el-form-item label="API Key">
        <el-input v-model="form.api_key" type="password" show-password placeholder="留空则保留已保存的 Key" />
      </el-form-item>
      <el-form-item label="模型名">
        <el-input v-model="form.model" placeholder="doubao-pro-32k / gpt-4o / deepseek-chat / qwen…" />
      </el-form-item>
      <div class="actions">
        <button class="btn-primary" :disabled="saving" @click="save">
          {{ saving ? '保存中…' : '保存并生效 ✨' }}
        </button>
        <button class="btn-ghost" :disabled="testing" @click="testConn">
          {{ testing ? '测试中…' : '测试连接 🔌' }}
        </button>
      </div>
    </el-form>

    <div v-if="testResult" class="test-result" :class="testResult.ok ? 'ok' : 'fail'">
      <template v-if="testResult.ok">
        🎉 连接成功（{{ testResult.latency_ms }} ms）
        <div class="test-reply">{{ testResult.reply }}</div>
      </template>
      <template v-else>
        😢 连接失败：{{ testResult.error }}
      </template>
    </div>

    <div class="tip-box">
      💡 支持任意 OpenAI 兼容端点（豆包 / DeepSeek / Ollama 等）。保存后立即生效，无需重启～
    </div>
  </div>
</template>

<style scoped>
.status-bar {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 16px;
  flex-wrap: wrap;
}
.status-tag {
  padding: 5px 14px;
  border-radius: 14px;
  background: #fff5eb;
  color: #c88a3d;
  font-size: 12px;
  font-weight: 600;
}
.status-tag.ready {
  background: #f0f9f4;
  color: #3d8b6a;
}
.key-masked {
  font-size: 12px;
  color: var(--text-secondary);
}
.actions {
  display: flex;
  gap: 10px;
  margin-bottom: 4px;
}
.btn-primary {
  padding: 9px 20px;
  border-radius: 14px;
  border: none;
  background: linear-gradient(135deg, #b8e6d0, #9dd8ba);
  color: #2d6b4f;
  font-size: 13px;
  font-weight: 700;
  cursor: pointer;
  transition: all 0.15s;
}
.btn-primary:hover:not(:disabled) {
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(123, 200, 164, 0.35);
}
.btn-primary:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}
.btn-ghost {
  padding: 9px 18px;
  border-radius: 14px;
  border: 1.5px solid var(--border-soft);
  background: #fff;
  color: var(--text-primary);
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.15s;
}
.btn-ghost:hover:not(:disabled) {
  border-color: #d4c5f0;
  background: #faf8ff;
}
.btn-ghost:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}
.test-result {
  margin-top: 14px;
  padding: 12px 16px;
  border-radius: 14px;
  font-size: 13px;
  line-height: 1.6;
}
.test-result.ok {
  background: #f0f9f4;
  border: 1px solid #c8e6d5;
  color: #2d6b4f;
}
.test-result.fail {
  background: #fff0f3;
  border: 1px solid #ffc9d4;
  color: #b35a6a;
}
.test-reply {
  font-size: 12px;
  color: var(--text-secondary);
  margin-top: 4px;
  word-break: break-all;
}
.tip-box {
  margin-top: 14px;
  padding: 10px 14px;
  border-radius: 12px;
  background: #faf8f3;
  font-size: 12px;
  color: var(--text-secondary);
  line-height: 1.6;
}
</style>
