<script setup lang="ts">
import { ref, watch } from 'vue'

const props = defineProps<{ trigger: number }>()
const visible = ref(false)
const particles = ref<Array<{ left: number; delay: number; duration: number; color: string; size: number; rotate: number }>>([])

const colors = ['#ffb5c5', '#ffd4a3', '#b8e6d0', '#d4c5f0', '#ffe08a', '#ff9eb5']

function fire() {
  particles.value = Array.from({ length: 40 }, () => ({
    left: Math.random() * 100,
    delay: Math.random() * 0.3,
    duration: 1.2 + Math.random() * 0.8,
    color: colors[Math.floor(Math.random() * colors.length)],
    size: 6 + Math.random() * 8,
    rotate: Math.random() * 360,
  }))
  visible.value = true
  setTimeout(() => { visible.value = false }, 2200)
}

watch(() => props.trigger, (n, o) => {
  if (n > o) fire()
})
</script>

<template>
  <div v-if="visible" class="confetti">
    <span
      v-for="(p, i) in particles"
      :key="i"
      class="particle"
      :style="{
        left: p.left + '%',
        animationDelay: p.delay + 's',
        animationDuration: p.duration + 's',
        background: p.color,
        width: p.size + 'px',
        height: p.size + 'px',
        transform: `rotate(${p.rotate}deg)`,
      }"
    ></span>
  </div>
</template>

<style scoped>
.confetti {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  height: 100vh;
  pointer-events: none;
  z-index: 9999;
  overflow: hidden;
}
.particle {
  position: absolute;
  top: -20px;
  border-radius: 3px;
  animation: confetti-fall linear forwards;
}
@keyframes confetti-fall {
  0% {
    transform: translateY(0) rotate(0deg);
    opacity: 1;
  }
  100% {
    transform: translateY(100vh) rotate(720deg);
    opacity: 0;
  }
}
</style>
