<script setup lang="ts">
import { ref, watch, onMounted } from 'vue'

const props = defineProps<{ value: number; duration?: number }>()
const display = ref(0)
let raf = 0

function animate(from: number, to: number) {
  cancelAnimationFrame(raf)
  const start = performance.now()
  const dur = props.duration || 800
  function step(now: number) {
    const t = Math.min(1, (now - start) / dur)
    const eased = 1 - Math.pow(1 - t, 3)
    display.value = Math.round(from + (to - from) * eased)
    if (t < 1) raf = requestAnimationFrame(step)
  }
  raf = requestAnimationFrame(step)
}

onMounted(() => animate(0, props.value))
watch(() => props.value, (n, o) => animate(o || 0, n))
</script>

<template>
  <span>{{ display }}</span>
</template>
