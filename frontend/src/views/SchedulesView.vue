<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import dayjs from 'dayjs'
import client from '../api/client'

const weekStart = ref(dayjs().startOf('week').add(1, 'day'))
const schedules = ref<any[]>([])
const loading = ref(false)
const dialogVisible = ref(false)
const form = ref({ title: '', start_at: '', duration_min: 30, note: '' })

const days = computed(() =>
  Array.from({ length: 7 }, (_, i) => weekStart.value.add(i, 'day').format('YYYY-MM-DD')),
)
const dayLabels = computed(() =>
  days.value.map((d) => ({
    date: d,
    weekday: ['日', '一', '二', '三', '四', '五', '六'][dayjs(d).day()],
    dayNum: dayjs(d).date(),
    isToday: dayjs(d).isSame(dayjs(), 'day'),
  })),
)

function itemsOf(date: string) {
  return schedules.value
    .filter((s) => s.start_at.startsWith(date))
    .sort((a, b) => a.start_at.localeCompare(b.start_at))
}

async function load() {
  loading.value = true
  try {
    const { data } = await client.get('/schedules', {
      params: { start: days.value[0], end: days.value[6] },
    })
    schedules.value = data
  } finally {
    loading.value = false
  }
}

function shiftWeek(delta: number) {
  weekStart.value = weekStart.value.add(delta, 'week')
  load()
}

function openCreate(date?: string) {
  form.value = {
    title: '',
    start_at: date ? `${date} 09:00` : dayjs().format('YYYY-MM-DD HH:mm'),
    duration_min: 30,
    note: '',
  }
  dialogVisible.value = true
}

async function save() {
  if (!form.value.title.trim()) return
  await client.post('/schedules', {
    title: form.value.title,
    start_at: form.value.start_at,
  })
  dialogVisible.value = false
  await load()
}

async function toggle(s: any) {
  const wasDone = s.status === 'done'
  await client.patch(`/schedules/${s.id}`, { status: wasDone ? 'upcoming' : 'done' })
  if (!wasDone) s.justDone = true
  await load()
}

onMounted(load)
</script>

<template>
  <div class="page">
    <div class="page-head">
      <div>
        <h2 class="page-title">日程 📅</h2>
        <div class="page-subtitle">本周安排一目了然</div>
      </div>
      <div class="head-actions">
        <div class="week-nav">
          <button class="nav-btn" @click="shiftWeek(-1)">‹</button>
          <span class="week-label">{{ weekStart.format('M月D日') }} - {{ weekStart.add(6, 'day').format('M月D日') }}</span>
          <button class="nav-btn" @click="shiftWeek(1)">›</button>
        </div>
        <button class="btn-primary" @click="openCreate()">＋ 新建日程</button>
      </div>
    </div>

    <div v-loading="loading" class="week-grid">
      <div v-for="d in dayLabels" :key="d.date" class="day-col" :class="{ today: d.isToday }">
        <div class="day-head">
          <span class="weekday">周{{ d.weekday }}</span>
          <span class="daynum" :class="{ today: d.isToday }">{{ d.dayNum }}</span>
        </div>
        <div class="day-items">
          <div
            v-for="s in itemsOf(d.date)"
            :key="s.id"
            class="schedule-item"
            :class="{ done: s.status === 'done', pop: s.justDone }"
            @click="toggle(s)"
          >
            <div class="item-time">⏰ {{ dayjs(s.start_at).format('HH:mm') }}</div>
            <div class="item-title">{{ s.title }}</div>
            <div v-if="s.note" class="item-note">{{ s.note }}</div>
          </div>
          <div class="add-slot" @click="openCreate(d.date)">＋</div>
        </div>
      </div>
    </div>

    <el-dialog v-model="dialogVisible" title="新建日程 ✨" width="420px" class="cute-dialog">
      <el-form label-position="top">
        <el-form-item label="做什么呀？">
          <el-input v-model="form.title" placeholder="比如：看书 / 健身 / 约会" />
        </el-form-item>
        <el-form-item label="时间">
          <el-input v-model="form.start_at" placeholder="2026-09-14 14:00" />
        </el-form-item>
        <el-form-item label="时长（分钟）">
          <el-input-number v-model="form.duration_min" :min="5" :step="15" />
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="form.note" type="textarea" :rows="2" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <button class="btn-primary" @click="save">保存 🎀</button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.page-head {
  display: flex;
  justify-content: space-between;
  align-items: flex-end;
  margin-bottom: 18px;
  flex-wrap: wrap;
  gap: 12px;
}
.head-actions {
  display: flex;
  align-items: center;
  gap: 10px;
}
.week-nav {
  display: flex;
  align-items: center;
  gap: 6px;
  background: #fff;
  padding: 5px 12px;
  border-radius: 16px;
  border: 1px solid var(--border-soft);
}
.nav-btn {
  width: 26px;
  height: 26px;
  border-radius: 50%;
  border: none;
  background: #f5f0e8;
  color: var(--text-secondary);
  font-size: 16px;
  cursor: pointer;
  transition: all 0.15s;
  display: flex;
  align-items: center;
  justify-content: center;
}
.nav-btn:hover {
  background: #e8e0d0;
}
.week-label {
  font-size: 13px;
  font-weight: 700;
  color: var(--text-primary);
  min-width: 110px;
  text-align: center;
}
.btn-primary {
  padding: 9px 20px;
  border-radius: 16px;
  border: none;
  background: linear-gradient(135deg, #b8e6d0, #9dd8ba);
  color: #2d6b4f;
  font-size: 13.5px;
  font-weight: 700;
  cursor: pointer;
  transition: all 0.15s;
}
.btn-primary:hover {
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(123, 200, 164, 0.35);
}
.week-grid {
  display: grid;
  grid-template-columns: repeat(7, 1fr);
  gap: 10px;
}
.day-col {
  background: #fff;
  border-radius: 18px;
  padding: 14px 10px;
  min-height: 340px;
  border: 1px solid var(--border-soft);
  display: flex;
  flex-direction: column;
}
.day-col.today {
  background: linear-gradient(180deg, #f0f9f4 0%, #fff 70px);
  border-color: #c8e6d5;
}
.day-head {
  text-align: center;
  margin-bottom: 10px;
  padding-bottom: 8px;
  border-bottom: 1px dashed #f0ebe3;
}
.weekday {
  display: block;
  font-size: 11px;
  color: var(--text-secondary);
  margin-bottom: 3px;
}
.daynum {
  display: inline-block;
  width: 30px;
  height: 30px;
  line-height: 30px;
  border-radius: 50%;
  font-size: 14px;
  font-weight: 700;
  color: var(--text-primary);
}
.daynum.today {
  background: linear-gradient(135deg, #ffd4a3, #ffb5c5);
  color: #8b5a3c;
}
.day-items {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.schedule-item {
  background: #faf8f3;
  border-left: 3px solid #7bc8a4;
  border-radius: 12px;
  padding: 9px 11px;
  cursor: pointer;
  transition: all 0.15s;
}
.schedule-item:hover {
  background: #f0f5f1;
  transform: translateX(2px);
}
.schedule-item.done {
  opacity: 0.45;
}
.schedule-item.pop {
  animation: pop 0.5s ease;
}
@keyframes pop {
  0% { transform: scale(1); }
  40% { transform: scale(1.08); background: #f0f9f4; }
  100% { transform: scale(1); }
}
.schedule-item.done .item-title {
  text-decoration: line-through;
}
.item-time {
  font-size: 11px;
  color: #3d8b6a;
  font-weight: 700;
  margin-bottom: 3px;
}
.item-title {
  font-size: 12.5px;
  font-weight: 600;
  color: var(--text-primary);
  line-height: 1.4;
}
.item-note {
  font-size: 11px;
  color: var(--text-secondary);
  margin-top: 3px;
}
.add-slot {
  text-align: center;
  color: #d0c8b8;
  font-size: 18px;
  padding: 8px;
  border-radius: 12px;
  cursor: pointer;
  transition: all 0.15s;
  border: 1.5px dashed #e8e0d0;
}
.add-slot:hover {
  color: #7bc8a4;
  border-color: #7bc8a4;
  background: #f0f9f4;
}
.cute-dialog :deep(.el-dialog) {
  border-radius: 20px;
}
</style>
