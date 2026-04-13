import { View, Text, Input } from '@tarojs/components'
import './SearchBar.scss'

interface SearchBarProps {
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
}

export default function SearchBar({ value, onChange, placeholder = '搜索工具...' }: SearchBarProps) {
  return (
    <View className='search-bar'>
      <Text className='search-icon'>⌕</Text>
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
          <Text className='clear-icon'>✕</Text>
        </View>
      )}
    </View>
  )
}
