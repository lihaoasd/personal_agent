<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import ModelConfigForm from './ModelConfigForm.vue'
import client from '../api/client'

const props = defineProps<{ modelValue: boolean }>()
const emit = defineEmits<{ (e: 'update:modelValue', v: boolean): void }>()

const drawerVisible = computed({
  get: () => props.modelValue,
  set: (v) => emit('update:modelValue', v),
})

const sections = [
  { key: 'model', label: '模型配置', emoji: '🤖' },
  { key: 'chat', label: '对话模式', emoji: '💬' },
]

const activeSection = ref('model')

// 对话模式
const chatMode = ref<'simple' | 'agent'>('simple')

async function loadMode() {
  try {
    const { data } = await client.get('/settings/chat-mode')
    chatMode.value = data.mode
  } catch {}
}

async function switchMode(mode: 'simple' | 'agent') {
  chatMode.value = mode
  await client.post('/settings/chat-mode', { mode })
}

onMounted(loadMode)
</script>

<template>
  <el-drawer v-model="drawerVisible" title="⚙️ 设置" size="500px" direction="rtl" class="cute-drawer">
    <div class="settings-body">
      <div class="sections">
        <div
          v-for="s in sections"
          :key="s.key"
          class="section-item"
          :class="{ active: activeSection === s.key }"
          @click="activeSection = s.key"
        >
          <span class="section-emoji">{{ s.emoji }}</span>
          {{ s.label }}
        </div>
      </div>
      <div class="section-content">
        <ModelConfigForm v-if="activeSection === 'model'" />
        <div v-else-if="activeSection === 'chat'" class="chat-mode-panel">
          <h3 class="panel-title">选择对话模式</h3>
          <p class="panel-desc">对话打卡的工作方式</p>

          <div class="mode-options">
            <div
              class="mode-card"
              :class="{ active: chatMode === 'simple' }"
              @click="switchMode('simple')"
            >
              <div class="mode-emoji">🎯</div>
              <div class="mode-name">简单模式</div>
              <div class="mode-desc">
                固定规则识别意图，快速响应，稳定可靠，适合日常打卡
              </div>
            </div>

            <div
              class="mode-card"
              :class="{ active: chatMode === 'agent' }"
              @click="switchMode('agent')"
            >
              <div class="mode-emoji">🤖</div>
              <div class="mode-name">Agent Loop 模式</div>
              <div class="mode-desc">
                模型自主决定调用工具，更灵活智能，能主动查询数据和执行操作
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </el-drawer>
</template>

<style scoped>
.settings-body {
  display: flex;
  gap: 16px;
  height: 100%;
}
.sections {
  flex: 0 0 120px;
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.section-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 11px 14px;
  border-radius: 14px;
  font-size: 13px;
  color: var(--text-secondary);
  cursor: pointer;
  transition: all 0.15s;
  font-weight: 500;
}
.section-item:hover {
  background: #f5f0e8;
  color: var(--text-primary);
}
.section-item.active {
  background: linear-gradient(135deg, #b8e6d0, #d4f0e2);
  color: #3d8b6a;
  font-weight: 700;
}
.section-emoji {
  font-size: 15px;
}
.section-content {
  flex: 1;
  min-width: 0;
  overflow-y: auto;
}

/* 对话模式选择 */
.chat-mode-panel {
  padding: 8px 4px;
}
.panel-title {
  font-size: 16px;
  font-weight: 700;
  color: var(--text-primary);
  margin: 0 0 4px;
}
.panel-desc {
  font-size: 13px;
  color: var(--text-secondary);
  margin: 0 0 20px;
}
.mode-options {
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.mode-card {
  padding: 18px 20px;
  background: #fff;
  border: 2px solid var(--border-soft);
  border-radius: 18px;
  cursor: pointer;
  transition: all 0.15s;
}
.mode-card:hover {
  border-color: #b8e6d0;
  transform: translateY(-1px);
}
.mode-card.active {
  border-color: #7bc8a4;
  background: #f0faf5;
}
.mode-emoji {
  font-size: 28px;
  margin-bottom: 8px;
}
.mode-name {
  font-size: 15px;
  font-weight: 700;
  color: var(--text-primary);
  margin-bottom: 6px;
}
.mode-desc {
  font-size: 13px;
  color: var(--text-secondary);
  line-height: 1.6;
}
</style>
