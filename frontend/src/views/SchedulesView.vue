<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import dayjs from 'dayjs'
import { Lunar } from 'lunar-javascript'
import client from '../api/client'

const weekStart = ref(dayjs().startOf('week').add(1, 'day'))
const monthDate = ref(dayjs().startOf('month'))
const viewMode = ref<'week' | 'month'>('week')
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

// 月视图的日历格子（42 格 = 6 行 × 7 列）
const monthCells = computed(() => {
  const start = monthDate.value.startOf('month').startOf('week')
  return Array.from({ length: 42 }, (_, i) => {
    const d = start.add(i, 'day')
    const lunar = Lunar.fromDate(d.toDate())
    const lunarDay = lunar.getDayInChinese()
    const festival = lunar.getFestivals()[0] || ''
    const solarFestival = getSolarFestival(d.month() + 1, d.date())
    return {
      date: d.format('YYYY-MM-DD'),
      dayNum: d.date(),
      inMonth: d.month() === monthDate.value.month(),
      isToday: d.isSame(dayjs(), 'day'),
      lunar: lunarDay === '初一' ? lunar.getMonthInChinese() + '月' : lunarDay,
      festival: festival || solarFestival,
      isLunarFestival: !!festival,
    }
  })
})

// 公历节日
function getSolarFestival(month: number, day: number): string {
  const festivals: Record<string, string> = {
    '1-1': '元旦',
    '2-14': '情人节',
    '3-8': '妇女节',
    '3-12': '植树节',
    '4-1': '愚人节',
    '5-1': '劳动节',
    '5-4': '青年节',
    '6-1': '儿童节',
    '7-1': '建党节',
    '8-1': '建军节',
    '9-10': '教师节',
    '10-1': '国庆节',
    '12-25': '圣诞节',
  }
  return festivals[`${month}-${day}`] || ''
}

function itemsOf(date: string) {
  return schedules.value
    .filter((s) => s.start_at.startsWith(date))
    .sort((a, b) => a.start_at.localeCompare(b.start_at))
}

function countOf(date: string) {
  return schedules.value.filter((s) => s.start_at.startsWith(date)).length
}

async function load() {
  loading.value = true
  try {
    let start: string, end: string
    if (viewMode.value === 'week') {
      start = days.value[0]
      end = days.value[6]
    } else {
      // 月视图加载整个月
      start = monthDate.value.startOf('month').format('YYYY-MM-DD')
      end = monthDate.value.endOf('month').format('YYYY-MM-DD')
    }
    const { data } = await client.get('/schedules', { params: { start, end } })
    schedules.value = data
  } finally {
    loading.value = false
  }
}

function shift(delta: number) {
  if (viewMode.value === 'week') {
    weekStart.value = weekStart.value.add(delta, 'week')
  } else {
    monthDate.value = monthDate.value.add(delta, 'month')
  }
  load()
}

function goToday() {
  const now = dayjs()
  weekStart.value = now.startOf('week').add(1, 'day')
  monthDate.value = now.startOf('month')
  load()
}

function switchView(mode: 'week' | 'month') {
  viewMode.value = mode
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
    note: form.value.note,
    duration_min: form.value.duration_min,
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

async function deleteSchedule(s: any, e: Event) {
  e.stopPropagation()
  await client.delete(`/schedules/${s.id}`)
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
        <!-- 视图切换 -->
        <div class="view-switch">
          <button
            class="view-btn"
            :class="{ active: viewMode === 'week' }"
            @click="switchView('week')"
          >周</button>
          <button
            class="view-btn"
            :class="{ active: viewMode === 'month' }"
            @click="switchView('month')"
          >月</button>
        </div>
        <div class="week-nav">
          <button class="nav-btn" @click="shift(-1)">‹</button>
          <span class="week-label">
            {{ viewMode === 'week'
              ? weekStart.format('M月D日') + ' - ' + weekStart.add(6, 'day').format('M月D日')
              : monthDate.format('YYYY年M月') }}
          </span>
          <button class="nav-btn" @click="shift(1)">›</button>
          <button class="today-btn" @click="goToday">今天</button>
        </div>
        <button class="btn-primary" @click="openCreate()">＋ 新建日程</button>
      </div>
    </div>

    <!-- 周视图 -->
    <div v-if="viewMode === 'week'" v-loading="loading" class="week-grid">
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
            <div class="item-header">
              <div class="item-time">⏰ {{ dayjs(s.start_at).format('HH:mm') }}</div>
              <span class="item-delete" @click.stop="deleteSchedule(s, $event)">✕</span>
            </div>
            <div class="item-title">{{ s.title }}</div>
            <div v-if="s.note" class="item-note">{{ s.note }}</div>
          </div>
          <div class="add-slot" @click="openCreate(d.date)">＋</div>
        </div>
      </div>
    </div>

    <!-- 月视图 -->
    <div v-else v-loading="loading" class="month-grid">
      <div class="month-weekdays">
        <span>日</span><span>一</span><span>二</span><span>三</span><span>四</span><span>五</span><span>六</span>
      </div>
      <div class="month-cells">
        <div
          v-for="cell in monthCells"
          :key="cell.date"
          class="month-cell"
          :class="{
            'not-in-month': !cell.inMonth,
            today: cell.isToday,
          }"
          @click="openCreate(cell.date)"
        >
          <span class="cell-day" :class="{ today: cell.isToday }">{{ cell.dayNum }}</span>
          <span class="cell-lunar" :class="{ festival: cell.festival }">
            {{ cell.festival || cell.lunar }}
          </span>
          <div class="cell-items">
            <div
              v-for="s in itemsOf(cell.date).slice(0, 2)"
              :key="s.id"
              class="cell-item"
              :class="{ done: s.status === 'done' }"
            >
              {{ dayjs(s.start_at).format('HH:mm') }} {{ s.title }}
            </div>
            <div v-if="countOf(cell.date) > 2" class="cell-more">
              +{{ countOf(cell.date) - 2 }} 更多
            </div>
          </div>
        </div>
      </div>
    </div>

    <el-dialog v-model="dialogVisible" width="440px" class="schedule-dialog">
      <template #header>
        <div class="dialog-header">
          <span class="header-emoji">📝</span>
          <span class="header-title">新建小日程</span>
        </div>
      </template>
      <el-form label-position="top" class="schedule-form">
        <el-form-item label="做什么呀？">
          <el-input v-model="form.title" placeholder="比如：看书 / 健身 / 约会" />
        </el-form-item>
        <el-form-item label="时间">
          <el-input v-model="form.start_at" placeholder="2026-09-14 14:00" />
        </el-form-item>
        <el-form-item label="时长（分钟）">
          <el-input-number v-model="form.duration_min" :min="5" :step="15" />
        </el-form-item>
        <el-form-item label="小备注">
          <el-input v-model="form.note" type="textarea" :rows="2" placeholder="想加点什么小提示吗～" />
        </el-form-item>
      </el-form>
      <template #footer>
        <div class="dialog-footer">
          <button class="cancel-btn" @click="dialogVisible = false">取消</button>
          <button class="save-btn" @click="save">保存 🎀</button>
        </div>
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
.today-btn {
  padding: 4px 12px;
  border-radius: 12px;
  border: none;
  background: linear-gradient(135deg, #b8e6d0, #9dd8ba);
  color: #2d6b4f;
  font-size: 12px;
  font-weight: 700;
  cursor: pointer;
  transition: all 0.15s;
}
.today-btn:hover {
  transform: translateY(-1px);
  box-shadow: 0 3px 8px rgba(123, 200, 164, 0.3);
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
  background: #f5f3ef;
  border-left-color: #d0c8b8;
}
.schedule-item.done .item-title {
  text-decoration: line-through;
  color: #b0a898;
}
.schedule-item.done .item-time {
  color: #b0a898;
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
.item-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.item-delete {
  font-size: 12px;
  color: #d0c8b8;
  cursor: pointer;
  opacity: 0;
  transition: all 0.12s;
  width: 18px;
  height: 18px;
  line-height: 18px;
  text-align: center;
  border-radius: 50%;
}
.schedule-item:hover .item-delete {
  opacity: 1;
}
.item-delete:hover {
  background: #fef0f0;
  color: #e07a7a;
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

/* 新建日程弹窗 */
.schedule-dialog :deep(.el-dialog) {
  border-radius: 24px;
  overflow: hidden;
  padding: 0;
}
.schedule-dialog :deep(.el-dialog__header) {
  padding: 0;
  margin: 0;
}
.dialog-header {
  background: linear-gradient(135deg, #f0faf4, #fff9f2);
  padding: 24px 24px 20px;
  display: flex;
  align-items: center;
  gap: 10px;
}
.header-emoji {
  font-size: 28px;
}
.header-title {
  font-size: 18px;
  font-weight: 700;
  color: var(--text-primary);
}
.schedule-dialog :deep(.el-dialog__body) {
  padding: 20px 24px;
}
.schedule-form :deep(.el-form-item__label) {
  font-size: 13px;
  color: var(--text-secondary);
  font-weight: 600;
  padding-bottom: 6px;
}
.schedule-form :deep(.el-input__wrapper),
.schedule-form :deep(.el-textarea__inner) {
  border-radius: 14px;
  background: #faf6f0;
  box-shadow: none;
  border: 1px solid var(--border-soft);
  padding: 8px 14px;
}
.schedule-form :deep(.el-input__wrapper:focus),
.schedule-form :deep(.el-textarea__inner:focus) {
  border-color: #7bc8a4;
  background: #fff;
}
.schedule-form :deep(.el-input-number) {
  width: 100%;
}
.schedule-form :deep(.el-input-number .el-input__wrapper) {
  border-radius: 14px;
}
.dialog-footer {
  display: flex;
  gap: 10px;
  justify-content: flex-end;
  padding: 0 24px 20px;
}
.cancel-btn {
  padding: 9px 20px;
  border-radius: 16px;
  border: 1px solid var(--border-soft);
  background: #fff;
  color: var(--text-secondary);
  font-size: 13.5px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.15s;
}
.cancel-btn:hover {
  background: #faf6f0;
}
.save-btn {
  padding: 9px 22px;
  border-radius: 16px;
  border: none;
  background: linear-gradient(135deg, #ffd4a3, #ffb5c5);
  color: #8b5a3c;
  font-size: 13.5px;
  font-weight: 700;
  cursor: pointer;
  transition: all 0.15s;
}
.save-btn:hover {
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(255, 181, 197, 0.4);
}

/* 视图切换 */
.view-switch {
  display: flex;
  background: #fff;
  border-radius: 16px;
  padding: 3px;
  border: 1px solid var(--border-soft);
}
.view-btn {
  padding: 5px 16px;
  border-radius: 13px;
  border: none;
  background: transparent;
  color: var(--text-secondary);
  font-size: 12.5px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.15s;
}
.view-btn.active {
  background: #7bc8a4;
  color: #fff;
}

/* 月视图 */
.month-grid {
  background: #fff;
  border-radius: 20px;
  border: 1px solid var(--border-soft);
  padding: 12px;
}
.month-weekdays {
  display: grid;
  grid-template-columns: repeat(7, 1fr);
  text-align: center;
  font-size: 12px;
  color: var(--text-secondary);
  font-weight: 600;
  padding-bottom: 8px;
  border-bottom: 1px solid var(--border-soft);
  margin-bottom: 8px;
}
.month-cells {
  display: grid;
  grid-template-columns: repeat(7, 1fr);
  gap: 3px;
}
.month-cell {
  min-height: 65px;
  padding: 5px 7px;
  border-radius: 10px;
  cursor: pointer;
  transition: all 0.12s;
  border: 1px solid transparent;
  display: flex;
  flex-direction: column;
}
.month-cell:hover {
  background: #faf6f0;
  border-color: var(--border-soft);
}
.month-cell.not-in-month {
  opacity: 0.35;
}
.month-cell.today {
  background: #f0f9f4;
}
.cell-day {
  display: inline-block;
  width: 24px;
  height: 24px;
  line-height: 24px;
  text-align: center;
  border-radius: 50%;
  font-size: 12.5px;
  font-weight: 600;
  color: var(--text-primary);
  margin-bottom: 2px;
}
.cell-day.today {
  background: linear-gradient(135deg, #ffd4a3, #ffb5c5);
  color: #8b5a3c;
}
.cell-lunar {
  display: block;
  font-size: 10px;
  color: #b0a898;
  margin-bottom: 4px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.cell-lunar.festival {
  color: #e07a7a;
  font-weight: 600;
}
.cell-day.today {
  background: linear-gradient(135deg, #ffd4a3, #ffb5c5);
  color: #8b5a3c;
}
.cell-items {
  display: flex;
  flex-direction: column;
  gap: 2px;
  flex: 1;
  overflow: hidden;
}
.cell-item {
  font-size: 10.5px;
  color: var(--text-primary);
  background: #f0f5f1;
  border-left: 2px solid #7bc8a4;
  padding: 1px 5px;
  border-radius: 5px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  line-height: 1.4;
}
.cell-item.done {
  background: #f5f3ef;
  border-left-color: #d0c8b8;
  text-decoration: line-through;
  color: #b0a898;
}
.cell-more {
  font-size: 10px;
  color: var(--text-secondary);
  padding: 0 5px;
  line-height: 1.2;
}
</style>
