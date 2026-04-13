import { View, Text, ScrollView } from '@tarojs/components'
import './CategoryTabs.scss'

interface CategoryItem {
  key: string;
  label: string;
}

interface CategoryTabsProps {
  categories: CategoryItem[];
  active: string;
  onChange: (key: string) => void;
}

export default function CategoryTabs({ categories, active, onChange }: CategoryTabsProps) {
  return (
    <ScrollView
      className='category-tabs'
      scrollX
      scrollWithAnimation
      showScrollbar={false}
    >
      <View className='tabs-inner'>
        {categories.map((cat) => (
          <View
            key={cat.key}
            className={`tab-item ${active === cat.key ? 'active' : ''}`}
            onClick={() => onChange(cat.key)}
          >
            <Text className='tab-text'>{cat.label}</Text>
            {active === cat.key && <View className='tab-indicator' />}
          </View>
        ))}
      </View>
    </ScrollView>
  )
}
