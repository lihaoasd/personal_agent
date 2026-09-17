<script setup lang="ts">
import { computed, ref } from 'vue'

const props = defineProps<{ count: number }>()
const shaking = ref(false)

const stages = [
  { min: 0, emoji: '🌰', label: '小种子', tip: '刚刚种下，慢慢来～' },
  { min: 3, emoji: '🌱', label: '发芽啦', tip: '冒出小芽芽了！' },
  { min: 10, emoji: '🌿', label: '小苗苗', tip: '正在努力生长～' },
  { min: 30, emoji: '🪴', label: '小盆栽', tip: '已经很茂盛啦！' },
  { min: 60, emoji: '🌳', label: '小树苗', tip: '越长越高了！' },
  { min: 100, emoji: '🌲', label: '参天大树', tip: '你太厉害了！🎉' },
]

const stage = computed(() => {
  let current = stages[0]
  for (const s of stages) {
    if (props.count >= s.min) current = s
  }
  return current
})

const nextStage = computed(() => stages.find((s) => s.min > props.count))
const progress = computed(() => {
  if (!nextStage.value) return 100
  const prev = stage.value.min
  const next = nextStage.value.min
  return Math.min(100, Math.round(((props.count - prev) / (next - prev)) * 100))
})

function shake() {
  shaking.value = true
  setTimeout(() => { shaking.value = false }, 600)
}
</script>

<template>
  <div class="growth-tree" @click="shake">
    <div class="tree-emoji" :class="{ shake: shaking }">{{ stage.emoji }}</div>
    <div class="tree-label">{{ stage.label }}</div>
    <div class="tree-tip">{{ stage.tip }}</div>
    <div v-if="nextStage" class="tree-progress">
      <div class="bar">
        <div class="fill" :style="{ width: progress + '%' }"></div>
      </div>
      <span class="next">距「{{ nextStage.label }}」还差 {{ nextStage.min - count }} 条</span>
    </div>
    <div v-else class="tree-max">已达最高形态 🌟</div>
  </div>
</template>

<style scoped>
.growth-tree {
  text-align: center;
  padding: 20px;
  background: linear-gradient(180deg, #f0f9f4 0%, #fff 100%);
  border-radius: 20px;
  border: 1px solid #e0f0e8;
  cursor: pointer;
  user-select: none;
  transition: transform 0.15s;
}
.growth-tree:hover {
  transform: translateY(-2px);
}
.tree-emoji {
  font-size: 56px;
  line-height: 1;
  margin-bottom: 8px;
  display: inline-block;
  transition: transform 0.1s;
}
.tree-emoji.shake {
  animation: tree-shake 0.6s ease;
}
@keyframes tree-shake {
  0%, 100% { transform: rotate(0deg); }
  20% { transform: rotate(-15deg) scale(1.1); }
  40% { transform: rotate(12deg) scale(1.15); }
  60% { transform: rotate(-8deg) scale(1.1); }
  80% { transform: rotate(5deg); }
}
.tree-label {
  font-size: 15px;
  font-weight: 700;
  color: #3d8b6a;
  margin-bottom: 4px;
}
.tree-tip {
  font-size: 12px;
  color: #9a9a9a;
  margin-bottom: 12px;
}
.tree-progress {
  text-align: left;
}
.bar {
  height: 8px;
  background: #e8f0eb;
  border-radius: 5px;
  overflow: hidden;
  margin-bottom: 5px;
}
.fill {
  height: 100%;
  background: linear-gradient(90deg, #7bc8a4, #b8e6d0);
  border-radius: 5px;
  transition: width 0.6s ease;
}
.next {
  font-size: 11px;
  color: #9a9a9a;
}
.tree-max {
  font-size: 12px;
  color: #e8a33d;
  font-weight: 600;
}
</style>
