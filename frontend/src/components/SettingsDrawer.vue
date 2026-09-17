<script setup lang="ts">
import { computed, ref } from 'vue'
import ModelConfigForm from './ModelConfigForm.vue'

const props = defineProps<{ modelValue: boolean }>()
const emit = defineEmits<{ (e: 'update:modelValue', v: boolean): void }>()

const drawerVisible = computed({
  get: () => props.modelValue,
  set: (v) => emit('update:modelValue', v),
})

const sections = [
  { key: 'model', label: '模型配置', emoji: '🤖' },
]

const activeSection = ref('model')
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
</style>
