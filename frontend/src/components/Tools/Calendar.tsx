import { ArrowLeft, CalendarDays, ChevronLeft, ChevronRight, Loader2, X } from 'lucide-react';
import { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { API_BASE_URL } from '../../config/api';
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/Select";

interface HolidayDay {
  name: string;
  date: string;
  isOffDay: boolean;
}

interface HolidayData {
  days: HolidayDay[];
}

interface LunarData {
  date: string;
  lunar_year: number;
  lunar_month: number;
  lunar_day: number;
  is_leap_month: boolean;
  lunar_month_name: string;
  lunar_day_name: string;
  gan_zhi_year: string;
  sheng_xiao: string;
  lunar_festival: string;
  solar_festival: string;
}

interface DayInfo {
  date: Date;
  dateStr: string;
  day: number;
  isCurrentMonth: boolean;
  isToday: boolean;
  isWeekend: boolean;
  holiday?: {
    name: string;
    isOffDay: boolean;
  };
  lunar?: LunarData;
}

export default function Calendar() {
  const navigate = useNavigate();
  const today = new Date();
  const [currentYear, setCurrentYear] = useState(today.getFullYear());
  const [currentMonth, setCurrentMonth] = useState(today.getMonth());
  const [holidays, setHolidays] = useState<Map<string, { name: string; isOffDay: boolean }>>(new Map());
  const [lunarData, setLunarData] = useState<Map<string, LunarData>>(new Map());
  const [loading, setLoading] = useState(false);
  const [selectedDate, setSelectedDate] = useState<string | null>(null);

  // 格式化日期为 YYYY-MM-DD
  const formatDate = (date: Date): string => {
    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, '0');
    const day = String(date.getDate()).padStart(2, '0');
    return `${year}-${month}-${day}`;
  };

  // 获取假期数据
  const fetchHolidaysForYear = useCallback(async (year: number): Promise<Map<string, { name: string; isOffDay: boolean }>> => {
    try {
      const response = await fetch(`${API_BASE_URL}/tools/holidays/${year}`);
      if (response.ok) {
        const data: HolidayData = await response.json();
        const holidayMap = new Map<string, { name: string; isOffDay: boolean }>();
        data.days.forEach((day) => {
          holidayMap.set(day.date, { name: day.name, isOffDay: day.isOffDay });
        });
        return holidayMap;
      }
    } catch (err) {
      console.error(`获取 ${year} 年假期数据失败:`, err);
    }
    return new Map();
  }, []);

  // 获取农历数据
  const fetchLunarData = useCallback(async (startDate: string, endDate: string): Promise<Map<string, LunarData>> => {
    try {
      const response = await fetch(
        `${API_BASE_URL}/tools/lunar/range?start=${startDate}&end=${endDate}`
      );
      if (response.ok) {
        const data = await response.json();
        const lunarMap = new Map<string, LunarData>();
        data.lunar_data.forEach((item: LunarData) => {
          lunarMap.set(item.date, item);
        });
        return lunarMap;
      }
    } catch (err) {
      console.error('获取农历数据失败:', err);
    }
    return new Map();
  }, []);

  // 获取当前月份需要的所有数据
  useEffect(() => {
    const fetchAllData = async () => {
      setLoading(true);

      // 计算日历显示的日期范围
      const firstDay = new Date(currentYear, currentMonth, 1);
      const startDayOfWeek = firstDay.getDay();
      const startDate = new Date(currentYear, currentMonth, 1 - startDayOfWeek);
      const endDate = new Date(currentYear, currentMonth + 1, 42 - startDayOfWeek - new Date(currentYear, currentMonth + 1, 0).getDate());

      // 计算需要获取哪些年份的假期数据
      const yearsNeeded = new Set<number>();
      yearsNeeded.add(currentYear);
      if (currentMonth === 0) yearsNeeded.add(currentYear - 1);
      if (currentMonth === 11) yearsNeeded.add(currentYear + 1);

      // 获取假期数据
      const allHolidays = new Map<string, { name: string; isOffDay: boolean }>();
      for (const year of yearsNeeded) {
        const yearHolidays = await fetchHolidaysForYear(year);
        yearHolidays.forEach((value, key) => {
          allHolidays.set(key, value);
        });
      }
      setHolidays(allHolidays);

      // 获取农历数据
      const lunar = await fetchLunarData(formatDate(startDate), formatDate(endDate));
      setLunarData(lunar);

      setLoading(false);
    };

    fetchAllData();
  }, [currentYear, currentMonth, fetchHolidaysForYear, fetchLunarData]);

  // 获取月份的所有日期
  const getMonthDays = (): DayInfo[] => {
    const days: DayInfo[] = [];
    const firstDay = new Date(currentYear, currentMonth, 1);
    const lastDay = new Date(currentYear, currentMonth + 1, 0);
    const startDayOfWeek = firstDay.getDay();
    const daysInMonth = lastDay.getDate();

    // 上个月的日期
    const prevMonthLastDay = new Date(currentYear, currentMonth, 0).getDate();
    for (let i = startDayOfWeek - 1; i >= 0; i--) {
      const day = prevMonthLastDay - i;
      const date = new Date(currentYear, currentMonth - 1, day);
      const dateStr = formatDate(date);
      days.push({
        date,
        dateStr,
        day,
        isCurrentMonth: false,
        isToday: false,
        isWeekend: date.getDay() === 0 || date.getDay() === 6,
        holiday: holidays.get(dateStr),
        lunar: lunarData.get(dateStr),
      });
    }

    // 当前月的日期
    for (let day = 1; day <= daysInMonth; day++) {
      const date = new Date(currentYear, currentMonth, day);
      const dateStr = formatDate(date);
      const isToday =
        date.getDate() === today.getDate() &&
        date.getMonth() === today.getMonth() &&
        date.getFullYear() === today.getFullYear();
      days.push({
        date,
        dateStr,
        day,
        isCurrentMonth: true,
        isToday,
        isWeekend: date.getDay() === 0 || date.getDay() === 6,
        holiday: holidays.get(dateStr),
        lunar: lunarData.get(dateStr),
      });
    }

    // 下个月的日期
    const remainingDays = 42 - days.length;
    for (let day = 1; day <= remainingDays; day++) {
      const date = new Date(currentYear, currentMonth + 1, day);
      const dateStr = formatDate(date);
      days.push({
        date,
        dateStr,
        day,
        isCurrentMonth: false,
        isToday: false,
        isWeekend: date.getDay() === 0 || date.getDay() === 6,
        holiday: holidays.get(dateStr),
        lunar: lunarData.get(dateStr),
      });
    }

    return days;
  };

  const goToPrevMonth = () => {
    if (currentMonth === 0) {
      setCurrentYear(currentYear - 1);
      setCurrentMonth(11);
    } else {
      setCurrentMonth(currentMonth - 1);
    }
  };

  const goToNextMonth = () => {
    if (currentMonth === 11) {
      setCurrentYear(currentYear + 1);
      setCurrentMonth(0);
    } else {
      setCurrentMonth(currentMonth + 1);
    }
  };

  const goToToday = () => {
    setCurrentYear(today.getFullYear());
    setCurrentMonth(today.getMonth());
    setSelectedDate(formatDate(today));
  };

  const handleDateClick = (dayInfo: DayInfo) => {
    setSelectedDate(dayInfo.dateStr);
    if (!dayInfo.isCurrentMonth) {
      setCurrentYear(dayInfo.date.getFullYear());
      setCurrentMonth(dayInfo.date.getMonth());
    }
  };

  const monthNames = [
    '一月', '二月', '三月', '四月', '五月', '六月',
    '七月', '八月', '九月', '十月', '十一月', '十二月'
  ];

  const weekDays = ['日', '一', '二', '三', '四', '五', '六'];
  const days = getMonthDays();

  // 获取选中日期的信息
  const selectedDayInfo = selectedDate ? days.find(d => d.dateStr === selectedDate) : null;

  // 获取农历显示文本（优先显示节日）
  const getLunarDisplay = (dayInfo: DayInfo): string => {
    if (!dayInfo.lunar) return '';

    // 优先显示农历节日
    if (dayInfo.lunar.lunar_festival) {
      return dayInfo.lunar.lunar_festival;
    }
    // 其次显示公历节日
    if (dayInfo.lunar.solar_festival) {
      return dayInfo.lunar.solar_festival;
    }
    // 初一显示月份
    if (dayInfo.lunar.lunar_day === 1) {
      return dayInfo.lunar.lunar_month_name;
    }
    // 其他显示农历日
    return dayInfo.lunar.lunar_day_name;
  };

  // 判断是否是节日
  const isFestival = (dayInfo: DayInfo): boolean => {
    return !!(dayInfo.lunar?.lunar_festival || dayInfo.lunar?.solar_festival);
  };

  return (
    <div className="text-ink">
      {/* 顶部工具栏 */}
      <div className="bg-surface-1 border-b border-border px-4 py-3 flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Button
            variant="ghost"
            onClick={() => navigate('/')}
            className="flex items-center gap-2"
          >
            <ArrowLeft className="w-4 h-4" />
            <span className="hidden sm:inline">返回</span>
          </Button>
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 bg-red-500 rounded flex items-center justify-center">
              <CalendarDays className="w-4 h-4 text-white" />
            </div>
            <h1 className="text-lg font-bold">万年历</h1>
          </div>
        </div>

        {/* 当前农历年份信息 */}
        {days[15]?.lunar && (
          <div className="text-sm text-ink-muted">
            {days[15].lunar.gan_zhi_year}年 ({days[15].lunar.sheng_xiao}年)
          </div>
        )}
      </div>

      {/* 日历主体 */}
      <div className="container mx-auto px-4 py-6 max-w-4xl">
        {/* 月份导航 */}
        <Card className="p-4 mb-4">
          <div className="flex items-center justify-between">
            <Button
              variant="ghost"
              size="icon"
              onClick={goToPrevMonth}
            >
              <ChevronLeft className="w-5 h-5" />
            </Button>

            <div className="flex items-center gap-4">
              <Select value={String(currentYear)} onValueChange={(v) => setCurrentYear(Number(v))}>
                <SelectTrigger className="w-28">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {Array.from({ length: 30 }, (_, i) => today.getFullYear() - 15 + i).map((year) => (
                    <SelectItem key={year} value={String(year)}>{year}年</SelectItem>
                  ))}
                </SelectContent>
              </Select>

              <Select value={String(currentMonth)} onValueChange={(v) => setCurrentMonth(Number(v))}>
                <SelectTrigger className="w-24">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {monthNames.map((name, index) => (
                    <SelectItem key={index} value={String(index)}>{name}</SelectItem>
                  ))}
                </SelectContent>
              </Select>

              <Button
                onClick={goToToday}
                size="sm"
              >
                今天
              </Button>
            </div>

            <Button
              variant="ghost"
              size="icon"
              onClick={goToNextMonth}
            >
              <ChevronRight className="w-5 h-5" />
            </Button>
          </div>
        </Card>

        {/* 图例 */}
        <Card className="p-3 mb-4 flex items-center gap-4 text-sm flex-wrap">
          <div className="flex items-center gap-2">
            <span className="w-3 h-3 bg-green-500 rounded"></span>
            <span className="text-ink-muted">法定假日</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="w-3 h-3 bg-orange-500 rounded"></span>
            <span className="text-ink-muted">调休上班</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="w-3 h-3 bg-accent rounded"></span>
            <span className="text-ink-muted">今天</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-pink-400 text-xs">节</span>
            <span className="text-ink-muted">传统节日</span>
          </div>
        </Card>

        {/* 选中日期详情 */}
        {selectedDayInfo && (
          <Card className="p-4 mb-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-4">
                <div className="text-2xl font-bold">{selectedDayInfo.day}</div>
                <div>
                  <div className="text-lg">{selectedDayInfo.dateStr}</div>
                  {selectedDayInfo.lunar && (
                    <div className="text-sm text-ink-muted">
                      农历 {selectedDayInfo.lunar.lunar_month_name}{selectedDayInfo.lunar.lunar_day_name}
                      <span className="ml-2">
                        {selectedDayInfo.lunar.gan_zhi_year}年 {selectedDayInfo.lunar.sheng_xiao}
                      </span>
                    </div>
                  )}
                </div>
              </div>
              <div className="flex items-center gap-2">
                {selectedDayInfo.holiday && (
                  <span className={`px-2 py-1 rounded text-sm ${
                    selectedDayInfo.holiday.isOffDay
                      ? 'bg-green-500/20 text-green-400'
                      : 'bg-orange-500/20 text-orange-400'
                  }`}>
                    {selectedDayInfo.holiday.name} - {selectedDayInfo.holiday.isOffDay ? '休息' : '上班'}
                  </span>
                )}
                {selectedDayInfo.lunar?.lunar_festival && (
                  <span className="px-2 py-1 rounded text-sm bg-pink-500/20 text-pink-400">
                    {selectedDayInfo.lunar.lunar_festival}
                  </span>
                )}
                {selectedDayInfo.lunar?.solar_festival && (
                  <span className="px-2 py-1 rounded text-sm bg-accent/20 text-accent">
                    {selectedDayInfo.lunar.solar_festival}
                  </span>
                )}
                <Button
                  variant="ghost"
                  size="icon"
                  onClick={() => setSelectedDate(null)}
                >
                  <X className="w-4 h-4" />
                </Button>
              </div>
            </div>
          </Card>
        )}

        {loading && (
          <div className="text-center py-4 text-ink-muted">
            <Loader2 className="w-4 h-4 mr-2 animate-spin" />
            加载数据中...
          </div>
        )}

        {/* 日历表格 */}
        <Card className="overflow-hidden">
          {/* 星期标题 */}
          <div className="grid grid-cols-7 bg-surface-2">
            {weekDays.map((day, index) => (
              <div
                key={day}
                className={`py-3 text-center font-medium ${
                  index === 0 || index === 6 ? 'text-danger' : 'text-ink-muted'
                }`}
              >
                {day}
              </div>
            ))}
          </div>

          {/* 日期格子 */}
          <div className="grid grid-cols-7">
            {days.map((dayInfo, index) => {
              const isSelected = selectedDate === dayInfo.dateStr;
              const hasHoliday = !!dayInfo.holiday;
              const lunarDisplay = getLunarDisplay(dayInfo);
              const hasFestival = isFestival(dayInfo);

              return (
                <div
                  key={index}
                  onClick={() => handleDateClick(dayInfo)}
                  className={`
                    min-h-[80px] p-2 border-t border-border relative cursor-pointer
                    transition-all duration-150
                    ${!dayInfo.isCurrentMonth ? 'bg-surface-1/50' : 'bg-surface-1'}
                    ${dayInfo.isToday ? 'ring-2 ring-accent ring-inset' : ''}
                    ${isSelected ? 'ring-2 ring-accent-secondary ring-inset bg-accent-secondary/10' : ''}
                    ${!isSelected && !dayInfo.isToday ? 'hover:bg-surface-2/50' : ''}
                  `}
                >
                  {/* 日期数字和假期标记 */}
                  <div className="flex items-start justify-between">
                    <span
                      className={`
                        text-lg font-medium inline-flex items-center justify-center
                        ${!dayInfo.isCurrentMonth ? 'text-ink-faint' : ''}
                        ${dayInfo.isCurrentMonth && dayInfo.isWeekend && !dayInfo.isToday ? 'text-danger' : ''}
                        ${dayInfo.isCurrentMonth && !dayInfo.isWeekend && !dayInfo.isToday ? 'text-ink' : ''}
                        ${dayInfo.isToday ? 'bg-accent text-white w-7 h-7 rounded-full' : ''}
                      `}
                    >
                      {dayInfo.day}
                    </span>

                    {/* 假期标记 */}
                    {hasHoliday && (
                      <span
                        className={`
                          text-xs px-1.5 py-0.5 rounded font-medium
                          ${dayInfo.holiday!.isOffDay
                            ? 'bg-green-500 text-white'
                            : 'bg-orange-500 text-white'}
                          ${!dayInfo.isCurrentMonth ? 'opacity-50' : ''}
                        `}
                      >
                        {dayInfo.holiday!.isOffDay ? '休' : '班'}
                      </span>
                    )}
                  </div>

                  {/* 农历/节日显示 */}
                  {lunarDisplay && (
                    <div className="mt-1">
                      <span className={`
                        text-xs truncate block
                        ${hasFestival ? 'text-pink-400 font-medium' : ''}
                        ${!hasFestival && dayInfo.isCurrentMonth ? 'text-ink-faint' : ''}
                        ${!hasFestival && !dayInfo.isCurrentMonth ? 'text-ink-faint' : ''}
                      `}>
                        {lunarDisplay}
                      </span>
                    </div>
                  )}

                  {/* 法定假期名称 */}
                  {hasHoliday && dayInfo.isCurrentMonth && (
                    <div className="mt-0.5">
                      <span className={`
                        text-xs truncate block
                        ${dayInfo.holiday!.isOffDay ? 'text-green-400' : 'text-orange-400'}
                      `}>
                        {dayInfo.holiday!.name}
                      </span>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </Card>

        {/* 使用说明 */}
        <Card className="p-4 text-sm text-ink-muted">
          <p className="mb-2">💡 使用提示：</p>
          <ul className="list-disc list-inside space-y-1 ml-2">
            <li>点击日期可以选中并查看详情</li>
            <li>点击上/下月的灰色日期可以快速切换月份</li>
            <li>绿色"休"标记表示法定假日休息</li>
            <li>橙色"班"标记表示调休需要上班</li>
            <li>粉色文字表示传统节日（春节、中秋等）</li>
            <li>农历初一显示月份名称</li>
          </ul>
        </Card>
      </div>
    </div>
  );
}