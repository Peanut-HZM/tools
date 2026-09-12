import { View, Input } from '@tarojs/components'
import Icon from '../Icon'
import './SearchBar.scss'

/**
 * 搜索栏 — 玻璃光晕换肤（阶段⑧-⑨ Task 7）：
 * 搜索/清除的 Unicode 字形（⌕/✕）换为 SVG Icon（烘色中性 ink 系），
 * Icon（Image）不可嵌于 Text，直接作为 flex 子项渲染。搜索逻辑不变。
 */

interface SearchBarProps {
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
}

export default function SearchBar({ value, onChange, placeholder = '搜索工具...' }: SearchBarProps) {
  return (
    <View className='search-bar'>
      <Icon name='search' size={16} color='#6E7A8F' className='search-icon' />
      <Input
        className='search-input'
        placeholder={placeholder}
        value={value}
        onInput={(e) => onChange(e.detail.value)}
        placeholderClass='search-placeholder'
      />
      {value && (
        <View
          className='search-clear'
          onClick={() => onChange('')}
        >
          <Icon name='close' size={16} color='#6E7A8F' className='clear-icon' />
        </View>
      )}
    </View>
  )
}
