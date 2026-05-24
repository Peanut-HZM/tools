import { useState, useEffect, useCallback } from 'react'
import Taro from '@tarojs/taro'
import { View, Text } from '@tarojs/components'
import { request } from '../../services/request'
import './index.scss'

interface HolidayDay {
  name: string
  date: string
  isOffDay: boolean
}

interface HolidayData {
  days: HolidayDay[]
}

interface LunarData {
  date: string
  lunar_year: number
  lunar_month: number
  lunar_day: number
  is_leap_month: boolean
  lunar_month_name: string
  lunar_day_name: string
  gan_zhi_year: string
  sheng_xiao: string
  lunar_festival: string
  solar_festival: string
}

interface CalendarDay {
  date: number
  month: number
  year: number
  dateStr: string
  isCurrentMonth: boolean
  isToday: boolean
  isSelected: boolean
  isWeekend: boolean
  dayOfWeek: number
  holiday?: { name: string; isOffDay: boolean }
  lunar?: LunarData
}

export default function Calendar() {
  const [currentDate, setCurrentDate] = useState(new Date())
  const [selectedDate, setSelectedDate] = useState<string | null>(null)
  const [calendarDays, setCalendarDays] = useState<CalendarDay[]>([])
  const [holidays, setHolidays] = useState<Map<string, { name: string; isOffDay: boolean }>>(new Map())
  const [lunarData, setLunarData] = useState<Map<string, LunarData>>(new Map())
  const [loading, setLoading] = useState(false)

  const today = new Date()
  const year = currentDate.getFullYear()
  const month = currentDate.getMonth()

  // 格式化日期
  const formatDate = useCallback((date: Date): string => {
    const y = date.getFullYear()
    const m = String(date.getMonth() + 1).padStart(2, '0')
    const d = String(date.getDate()).padStart(2, '0')
    return `${y}-${m}-${d}`
  }, [])

  // 获取假期数据
  const fetchHolidaysForYear = useCallback(async (y: number): Promise<Map<string, { name: string; isOffDay: boolean }>> => {
    try {
      const data: HolidayData = await request(`/tools/holidays/${y}`, { needAuth: false })
      const holidayMap = new Map<string, { name: string; isOffDay: boolean }>()
      data.days?.forEach((day) => {
        holidayMap.set(day.date, { name: day.name, isOffDay: day.isOffDay })
      })
      return holidayMap
    } catch (err) {
      console.error(`获取 ${y} 年假期数据失败:`, err)
      return new Map()
    }
  }, [])

  // 获取农历数据
  const fetchLunarData = useCallback(async (startDate: string, endDate: string): Promise<Map<string, LunarData>> => {
    try {
      const data = await request(`/tools/lunar/range?start=${startDate}&end=${endDate}`, { needAuth: false })
      const lunarMap = new Map<string, LunarData>()
      data.lunar_data?.forEach((item: LunarData) => {
        lunarMap.set(item.date, item)
      })
      return lunarMap
    } catch (err) {
      console.error('获取农历数据失败:', err)
      return new Map()
    }
  }, [])

  // 获取农历显示文本
  const getLunarDisplay = useCallback((day: CalendarDay): string => {
    if (!day.lunar) return ''
    if (day.lunar.lunar_festival) return day.lunar.lunar_festival
    if (day.lunar.solar_festival) return day.lunar.solar_festival
    if (day.lunar.lunar_day === 1) return day.lunar.lunar_month_name
    return day.lunar.lunar_day_name
  }, [])

  // 获取月份日期
  const generateCalendarDays = useCallback((): CalendarDay[] => {
    const firstDay = new Date(year, month, 1)
    const lastDay = new Date(year, month + 1, 0)
    const startDayOfWeek = firstDay.getDay()

    const days: CalendarDay[] = []

    // 上月补齐
    const prevMonthLastDay = new Date(year, month, 0).getDate()
    for (let i = startDayOfWeek - 1; i >= 0; i--) {
      const d = prevMonthLastDay - i
      const date = new Date(year, month - 1, d)
      const dateStr = formatDate(date)
      days.push({
        date: d,
        month: month - 1,
        year: month === 0 ? year - 1 : year,
        dateStr,
        isCurrentMonth: false,
        isToday: false,
        isSelected: selectedDate === dateStr,
        isWeekend: date.getDay() === 0 || date.getDay() === 6,
        dayOfWeek: date.getDay(),
        holiday: holidays.get(dateStr),
        lunar: lunarData.get(dateStr),
      })
    }

    // 当月
    for (let d = 1; d <= lastDay.getDate(); d++) {
      const date = new Date(year, month, d)
      const dateStr = formatDate(date)
      const isToday = d === today.getDate() && month === today.getMonth() && year === today.getFullYear()
      days.push({
        date: d,
        month,
        year,
        dateStr,
        isCurrentMonth: true,
        isToday,
        isSelected: selectedDate === dateStr,
        isWeekend: date.getDay() === 0 || date.getDay() === 6,
        dayOfWeek: date.getDay(),
        holiday: holidays.get(dateStr),
        lunar: lunarData.get(dateStr),
      })
    }

    // 下月补齐
    const remaining = 42 - days.length
    for (let d = 1; d <= remaining; d++) {
      const date = new Date(year, month + 1, d)
      const dateStr = formatDate(date)
      days.push({
        date: d,
        month: month + 1,
        year: month === 11 ? year + 1 : year,
        dateStr,
        isCurrentMonth: false,
        isToday: false,
        isSelected: selectedDate === dateStr,
        isWeekend: date.getDay() === 0 || date.getDay() === 6,
        dayOfWeek: date.getDay(),
        holiday: holidays.get(dateStr),
        lunar: lunarData.get(dateStr),
      })
    }

    return days
  }, [year, month, holidays, lunarData, selectedDate, formatDate, today])

  // 获取当前月份数据
  useEffect(() => {
    const fetchAllData = async () => {
      setLoading(true)

      // 计算日历显示的日期范围
      const firstDay = new Date(year, month, 1)
      const startDayOfWeek = firstDay.getDay()
      const startDate = new Date(year, month, 1 - startDayOfWeek)
      const lastDay = new Date(year, month + 1, 0)
      const remainingDays = 42 - (startDayOfWeek + lastDay.getDate())
      const endDate = new Date(year, month + 1, remainingDays)

      // 获取假期数据
      const yearsNeeded = new Set<number>()
      yearsNeeded.add(year)
      if (month === 0) yearsNeeded.add(year - 1)
      if (month === 11) yearsNeeded.add(year + 1)

      const allHolidays = new Map<string, { name: string; isOffDay: boolean }>()
      for (const y of yearsNeeded) {
        const yearHolidays = await fetchHolidaysForYear(y)
        yearHolidays.forEach((value, key) => {
          allHolidays.set(key, value)
        })
      }
      setHolidays(allHolidays)

      // 获取农历数据
      const lunar = await fetchLunarData(formatDate(startDate), formatDate(endDate))
      setLunarData(lunar)

      setLoading(false)
    }

    fetchAllData()
  }, [year, month, fetchHolidaysForYear, fetchLunarData, formatDate])

  // 生成日历
  useEffect(() => {
    setCalendarDays(generateCalendarDays())
  }, [generateCalendarDays])

  // 选择日期
  const handleSelectDate = (day: CalendarDay) => {
    setSelectedDate(day.dateStr)
    if (!day.isCurrentMonth) {
      setCurrentDate(new Date(day.year, day.month, 1))
    }
  }

  // 上一月
  const handlePrevMonth = () => {
    setCurrentDate(new Date(year, month - 1, 1))
  }

  // 下一月
  const handleNextMonth = () => {
    setCurrentDate(new Date(year, month + 1, 1))
  }

  // 回到今天
  const handleToday = () => {
    setCurrentDate(new Date())
    setSelectedDate(formatDate(new Date()))
  }

  // 格式化头部
  const formatHeader = () => {
    const months = ['1月', '2月', '3月', '4月', '5月', '6月', '7月', '8月', '9月', '10月', '11月', '12月']
    return `${year}年 ${months[month]}`
  }

  // 获取选中日期的信息
  const selectedDayInfo = selectedDate ? calendarDays.find(d => d.dateStr === selectedDate) : null

  // 星期标题
  const weekdays = ['日', '一', '二', '三', '四', '五', '六']

  // 农历年份信息
  const lunarYearInfo = selectedDayInfo?.lunar || calendarDays.find(d => d.isCurrentMonth && d.lunar)?.lunar

  return (
    <View className='calendar-page'>
      {/* 日历头部 */}
      <View className='calendar-header'>
        <Text className='nav-btn' onClick={handlePrevMonth}>‹</Text>
        <Text className='month-title'>{formatHeader()}</Text>
        <Text className='nav-btn' onClick={handleNextMonth}>›</Text>
      </View>

      {/* 农历年份信息 */}
      {lunarYearInfo && (
        <View className='lunar-year-info'>
          <Text className='lunar-year-text'>{lunarYearInfo.gan_zhi_year}年 ({lunarYearInfo.sheng_xiao}年)</Text>
        </View>
      )}

      {/* 快捷按钮 */}
      <View className='today-btn-wrapper'>
        <Text className='today-btn' onClick={handleToday}>今天</Text>
      </View>

      {/* 图例 */}
      <View className='legend-bar'>
        <View className='legend-item'>
          <View className='legend-dot legend-green' />
          <Text className='legend-text'>法定假日</Text>
        </View>
        <View className='legend-item'>
          <View className='legend-dot legend-orange' />
          <Text className='legend-text'>调休上班</Text>
        </View>
        <View className='legend-item'>
          <View className='legend-dot legend-blue' />
          <Text className='legend-text'>今天</Text>
        </View>
        <View className='legend-item'>
          <Text className='legend-festival'>节</Text>
          <Text className='legend-text'>传统节日</Text>
        </View>
      </View>

      {/* 选中日期详情 */}
      {selectedDayInfo && (
        <View className='selected-detail'>
          <View className='detail-left'>
            <Text className='detail-day'>{selectedDayInfo.date}</Text>
          </View>
          <View className='detail-right'>
            <Text className='detail-date'>{selectedDayInfo.dateStr}</Text>
            {selectedDayInfo.lunar && (
              <Text className='detail-lunar'>
                农历 {selectedDayInfo.lunar.lunar_month_name}{selectedDayInfo.lunar.lunar_day_name}
                <Text className='detail-ganzhi'>{selectedDayInfo.lunar.gan_zhi_year}年 {selectedDayInfo.lunar.sheng_xiao}</Text>
              </Text>
            )}
            <View className='detail-tags'>
              {selectedDayInfo.holiday && (
                <Text className={`detail-tag ${selectedDayInfo.holiday.isOffDay ? 'tag-green' : 'tag-orange'}`}>
                  {selectedDayInfo.holiday.name} - {selectedDayInfo.holiday.isOffDay ? '休息' : '上班'}
                </Text>
              )}
              {selectedDayInfo.lunar?.lunar_festival && (
                <Text className='detail-tag tag-pink'>{selectedDayInfo.lunar.lunar_festival}</Text>
              )}
              {selectedDayInfo.lunar?.solar_festival && (
                <Text className='detail-tag tag-cyan'>{selectedDayInfo.lunar.solar_festival}</Text>
              )}
            </View>
          </View>
          <Text className='detail-close' onClick={() => setSelectedDate(null)}>✕</Text>
        </View>
      )}

      {/* 星期标题 */}
      <View className='weekday-row'>
        {weekdays.map((day) => (
          <Text key={day} className={`weekday-text ${day === '日' || day === '六' ? 'weekend' : ''}`}>{day}</Text>
        ))}
      </View>

      {/* 日历网格 */}
      {loading ? (
        <View className='loading-state'>
          <Text className='loading-text'>加载数据中...</Text>
        </View>
      ) : (
        <View className='calendar-grid'>
          {calendarDays.map((day) => {
            const lunarDisplay = getLunarDisplay(day)
            const hasHoliday = !!day.holiday
            const isFestival = !!(day.lunar?.lunar_festival || day.lunar?.solar_festival)

            return (
              <View
                key={day.dateStr}
                className={`calendar-day
                  ${!day.isCurrentMonth ? 'other-month' : ''}
                  ${day.isToday ? 'today' : ''}
                  ${day.isSelected ? 'selected' : ''}
                `}
                onClick={() => handleSelectDate(day)}
              >
                {/* 日期数字 */}
                <View className='day-top'>
                  <Text className={`day-number
                    ${day.isToday ? 'today-number' : ''}
                    ${!day.isCurrentMonth ? 'other-number' : ''}
                    ${day.isCurrentMonth && day.isWeekend && !day.isToday ? 'weekend-number' : ''}
                  `}>
                    {day.date}
                  </Text>
                  {/* 假期标记 */}
                  {hasHoliday && (
                    <Text className={`holiday-badge ${day.holiday!.isOffDay ? 'badge-green' : 'badge-orange'}`}>
                      {day.holiday!.isOffDay ? '休' : '班'}
                    </Text>
                  )}
                </View>
                {/* 农历/节日 */}
                {lunarDisplay && (
                  <Text className={`lunar-text
                    ${isFestival ? 'lunar-festival' : ''}
                    ${!isFestival && day.isCurrentMonth ? 'lunar-normal' : ''}
                    ${!isFestival && !day.isCurrentMonth ? 'lunar-other' : ''}
                  `}>
                    {lunarDisplay}
                  </Text>
                )}
                {/* 法定假期名称 */}
                {hasHoliday && day.isCurrentMonth && (
                  <Text className={`holiday-name ${day.holiday!.isOffDay ? 'name-green' : 'name-orange'}`}>
                    {day.holiday!.name}
                  </Text>
                )}
              </View>
            )
          })}
        </View>
      )}

      {/* 底部说明 */}
      <View className='usage-tips'>
        <Text className='tips-title'>💡 使用提示：</Text>
        <Text className='tips-text'>• 点击日期选中并查看详情</Text>
        <Text className='tips-text'>• 点击上/下月的灰色日期可切换月份</Text>
        <Text className='tips-text'>• 绿色"休"=法定假日，橙色"班"=调休上班</Text>
        <Text className='tips-text'>• 粉色文字=传统节日（春节、中秋等）</Text>
      </View>
    </View>
  )
}
