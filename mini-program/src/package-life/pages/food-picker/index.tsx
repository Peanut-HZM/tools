import { useState, useRef, useEffect } from 'react'
import Taro from '@tarojs/taro'
import { View, Text, Image, Input } from '@tarojs/components'
import {
  loadFoods,
  addFood,
  updateFood,
  deleteFood,
  persistImage,
  removeImageFile,
  pickRandomFoods,
} from '../../../services/foodPicker'
import type { FoodItem } from '../../../services/foodPicker'
import EmptyState from '../../../components/EmptyState'
import Icon from '../../../components/Icon'
import './index.scss'

/**
 * "今天吃什么"工具页。
 *
 * 结构：抽取区（模式切换 + 滚动抽取舞台 + 主按钮）→ 美味清单（两列卡片网格）
 *       → 底部弹层编辑器（新增/编辑/删除，图片可选）。
 * 视觉：卡片套全局 .glass-card，弹层套 .glass-panel（见 markdown-editor 的弹层惯例）；
 *       无图美食以 emoji 兜底展示（按名称 hash 稳定取值，同一美食每次相同）。
 * 数据：全部走本地存储（services/foodPicker.ts），无需登录、离线可用。
 */

/** 无图美食的 emoji 兜底池（按名称 hash 稳定取值） */
const FOOD_EMOJIS = [
  '🍜', '🍕', '🍣', '🍔', '🍟', '🥗', '🍝', '🍲', '🍢', '🥘',
  '🍛', '🍖', '🦐', '🥟', '🍱', '🍰', '🌮', '🥩', '🍗', '🥐',
]

function emojiFor(name: string): string {
  let hash = 0
  for (let i = 0; i < name.length; i++) {
    hash = (hash * 31 + name.charCodeAt(i)) >>> 0
  }
  return FOOD_EMOJIS[hash % FOOD_EMOJIS.length]
}

/** 抽取模式：随机一个 / 随机多个 */
type PickMode = 'single' | 'multi'

/** 抽取舞台状态：待抽取 → 滚动中 → 出结果 */
type PickPhase = 'idle' | 'rolling' | 'done'

export default function FoodPickerPage() {
  // ===== 清单数据 =====
  const [foods, setFoods] = useState<FoodItem[]>([])
  useEffect(() => {
    setFoods(loadFoods())
  }, [])

  // ===== 抽取区状态 =====
  const [mode, setMode] = useState<PickMode>('single')
  const [pickCount, setPickCount] = useState(3)
  const [phase, setPhase] = useState<PickPhase>('idle')
  const [displayIdx, setDisplayIdx] = useState(0)
  const [results, setResults] = useState<FoodItem[]>([])
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null)
  // 抽取会话号：清单变动（保存/删除）时 +1，使旧会话的定格回调失效
  const drawSessionRef = useRef(0)

  // 卸载时清理滚动定时器
  useEffect(() => {
    return () => {
      if (timerRef.current) clearInterval(timerRef.current)
    }
  }, [])

  // ===== 编辑弹层状态 =====
  const [editorOpen, setEditorOpen] = useState(false)
  const [editing, setEditing] = useState<FoodItem | null>(null) // null = 新增
  const [formName, setFormName] = useState('')
  const [formNote, setFormNote] = useState('')
  const [formImage, setFormImage] = useState<string | undefined>(undefined)
  // 本次会话新生成、尚未随保存落库的持久化图片（取消时需清理，避免孤儿文件）
  const pendingNewImageRef = useRef<string | undefined>(undefined)

  /** 取消进行中的抽取：清单变动后旧结果失效，回到待抽取态 */
  const cancelDraw = () => {
    drawSessionRef.current++
    if (timerRef.current) {
      clearInterval(timerRef.current)
      timerRef.current = null
    }
    setPhase('idle')
    setResults([])
  }

  /** 滚动抽取：先随机轮播约 1.6s，再定格到预抽结果 */
  const startDraw = () => {
    if (foods.length === 0) {
      Taro.showToast({ title: '先添加几个美食吧', icon: 'none' })
      return
    }
    const count = mode === 'single' ? 1 : pickCount
    const picked = pickRandomFoods(foods, count)
    const session = ++drawSessionRef.current

    setPhase('rolling')
    if (timerRef.current) clearInterval(timerRef.current)
    timerRef.current = setInterval(() => {
      setDisplayIdx(Math.floor(Math.random() * foods.length))
    }, 90)
    setTimeout(() => {
      // 会话已被取消（清单变动）时不再定格旧结果
      if (session !== drawSessionRef.current) return
      if (timerRef.current) {
        clearInterval(timerRef.current)
        timerRef.current = null
      }
      setResults(picked)
      setPhase('done')
    }, 1600)
  }

  // ===== 编辑弹层操作 =====
  const openEditor = (item?: FoodItem) => {
    setEditing(item || null)
    setFormName(item?.name || '')
    setFormNote(item?.note || '')
    setFormImage(item?.image)
    pendingNewImageRef.current = undefined
    setEditorOpen(true)
  }

  /** 关闭弹层：清理本次会话未保存的新图片 */
  const closeEditor = () => {
    if (pendingNewImageRef.current) {
      removeImageFile(pendingNewImageRef.current)
    }
    pendingNewImageRef.current = undefined
    setEditorOpen(false)
  }

  /** 选图（可选）：临时文件复制到 USER_DATA_PATH 持久化后才可展示与留存 */
  const handleChooseImage = async () => {
    try {
      const res = await Taro.chooseImage({
        count: 1,
        sizeType: ['compressed'],
        sourceType: ['album', 'camera'],
      })
      const saved = await persistImage(res.tempFilePaths[0])
      // 连续换图时清理上一张未保存的新图
      if (pendingNewImageRef.current && pendingNewImageRef.current !== saved) {
        removeImageFile(pendingNewImageRef.current)
      }
      pendingNewImageRef.current = saved
      setFormImage(saved)
    } catch (err: any) {
      if (err?.errMsg !== 'chooseImage:fail cancel') {
        Taro.showToast({ title: err?.message || '选择图片失败', icon: 'none' })
      }
    }
  }

  /** 移除已选图片：新图直接删文件；老图只从表单摘除（保存时再删文件） */
  const handleRemoveImage = () => {
    if (pendingNewImageRef.current === formImage) {
      removeImageFile(formImage)
      pendingNewImageRef.current = undefined
    }
    setFormImage(undefined)
  }

  const handleSave = () => {
    const name = formName.trim()
    if (!name) {
      Taro.showToast({ title: '给美食起个名字吧', icon: 'none' })
      return
    }
    if (editing) {
      const oldImage = editing.image
      updateFood(editing.id, name, formNote, formImage)
      // 编辑时换了图或删了图：清理被替换的旧文件
      if (oldImage && oldImage !== formImage) {
        removeImageFile(oldImage)
      }
    } else {
      addFood(name, formNote, formImage)
    }
    pendingNewImageRef.current = undefined
    setFoods(loadFoods())
    setEditorOpen(false)
    // 清单变化后旧结果失效，取消进行中的抽取
    cancelDraw()
    Taro.showToast({ title: editing ? '已保存' : '已添加', icon: 'success' })
  }

  const handleDelete = () => {
    if (!editing) return
    Taro.showModal({
      title: '删除美食',
      content: `确定把「${editing.name}」从清单里删掉吗？`,
      confirmColor: '#F87171',
      success: (res) => {
        if (res.confirm) {
          // 若本次会话刚换过新图，deleteFood 删的是旧文件，新图需单独清理
          if (pendingNewImageRef.current) {
            removeImageFile(pendingNewImageRef.current)
          }
          deleteFood(editing.id)
          pendingNewImageRef.current = undefined
          setFoods(loadFoods())
          setEditorOpen(false)
          cancelDraw()
        }
      },
    })
  }

  // ===== 渲染 =====
  const rollingItem = foods[displayIdx]

  return (
    <View className='food-picker-page safe-area-bottom'>
      {/* ===== 抽取区 ===== */}
      <View className='draw-card glass-card'>
        {/* 模式切换 */}
        <View className='mode-segment'>
          <View
            className={`mode-option ${mode === 'single' ? 'mode-option--active' : ''}`}
            onClick={() => setMode('single')}
          >
            <Text>随机一个</Text>
          </View>
          <View
            className={`mode-option ${mode === 'multi' ? 'mode-option--active' : ''}`}
            onClick={() => setMode('multi')}
          >
            <Text>随机多个</Text>
          </View>
        </View>

        {/* 多选数量（仅"随机多个"模式显示） */}
        {mode === 'multi' && (
          <View className='count-row'>
            <Text className='count-label'>抽几个</Text>
            <View className='count-chips'>
              {[2, 3, 4, 5].map((n) => (
                <View
                  key={n}
                  className={`count-chip ${pickCount === n ? 'count-chip--active' : ''}`}
                  onClick={() => setPickCount(n)}
                >
                  <Text>{n}</Text>
                </View>
              ))}
            </View>
          </View>
        )}

        {/* 抽取舞台 */}
        <View className='pick-stage'>
          {phase === 'idle' && (
            <View className='stage-idle'>
              <Icon name='dice' size={56} color='#8B9BFF' />
              <Text className='stage-hint'>
                {foods.length > 0 ? '点击下方按钮，帮你拿主意' : '清单还是空的，先去添加美食'}
              </Text>
            </View>
          )}

          {phase === 'rolling' && rollingItem && (
            <View className='stage-rolling'>
              <Text className='stage-rolling-emoji'>{emojiFor(rollingItem.name)}</Text>
              <Text className='stage-rolling-name' numberOfLines={1}>{rollingItem.name}</Text>
            </View>
          )}

          {phase === 'done' && mode === 'single' && results[0] && (
            <View className='stage-result'>
              <View className='result-single result-pop'>
                {results[0].image ? (
                  <Image className='result-single-img' src={results[0].image} mode='aspectFill' />
                ) : (
                  <Text className='result-single-emoji'>{emojiFor(results[0].name)}</Text>
                )}
                <Text className='result-single-name' numberOfLines={1}>{results[0].name}</Text>
                {results[0].note && (
                  <Text className='result-single-note' numberOfLines={1}>{results[0].note}</Text>
                )}
              </View>
              <Text className='result-caption'>就决定是它了！</Text>
            </View>
          )}

          {phase === 'done' && mode === 'multi' && (
            <View className='stage-result'>
              <View className='result-multi'>
                {results.map((item, idx) => (
                  <View key={item.id} className='result-multi-item result-pop' style={{ animationDelay: `${idx * 90}ms` }}>
                    <Text className='result-multi-idx'>{idx + 1}</Text>
                    {item.image ? (
                      <Image className='result-multi-img' src={item.image} mode='aspectFill' />
                    ) : (
                      <Text className='result-multi-emoji'>{emojiFor(item.name)}</Text>
                    )}
                    <Text className='result-multi-name' numberOfLines={1}>{item.name}</Text>
                  </View>
                ))}
              </View>
              <Text className='result-caption'>从这几个里挑一个吧</Text>
            </View>
          )}
        </View>

        {/* 抽取按钮（品牌渐变主按钮 + hover 按压反馈，全局类见 _glass.scss） */}
        <View
          className='draw-btn btn-primary'
          hoverClass='btn-primary-hover'
          hoverStayTime={100}
          onClick={startDraw}
        >
          <Icon name='dice' size={18} color='#FFFFFF' />
          <Text>{phase === 'done' ? '再抽一次' : '开始抽取'}</Text>
        </View>
      </View>

      {/* ===== 清单区 ===== */}
      <View className='list-section'>
        <View className='list-header'>
          <Text className='list-title'>我的美味清单</Text>
          <View className='list-count'>
            <Text className='list-count-num'>{foods.length}</Text>
          </View>
          <View
            className='add-btn'
            hoverClass='add-btn-hover'
            hoverStayTime={100}
            onClick={() => openEditor()}
          >
            <Icon name='plus' size={14} color='#8B9BFF' />
            <Text>添加</Text>
          </View>
        </View>

        {foods.length === 0 ? (
          <EmptyState
            icon={<Icon name='utensils' size={48} color='#6E7A8F' />}
            title='还没有收录美食'
            description='把你爱吃的加进来，纠结时让手气决定'
          />
        ) : (
          <View className='food-grid'>
            {foods.map((item) => (
              <View
                key={item.id}
                className='food-card glass-card'
                hoverClass='food-card-hover'
                hoverStayTime={100}
                onClick={() => openEditor(item)}
              >
                <View className='food-card-cover'>
                  {item.image ? (
                    <Image className='food-card-img' src={item.image} mode='aspectFill' />
                  ) : (
                    <Text className='food-card-emoji'>{emojiFor(item.name)}</Text>
                  )}
                </View>
                <View className='food-card-info'>
                  <Text className='food-card-name' numberOfLines={1}>{item.name}</Text>
                  {item.note && (
                    <Text className='food-card-note' numberOfLines={1}>{item.note}</Text>
                  )}
                </View>
              </View>
            ))}
          </View>
        )}
      </View>

      {/* ===== 编辑弹层（遮罩 + 底部滑出面板） ===== */}
      {editorOpen && (
        <View className='editor-layer'>
          <View className='editor-mask' onClick={closeEditor} />
          <View className='editor-sheet glass-panel'>
            <View className='editor-header'>
              <Text className='editor-title'>{editing ? '编辑美食' : '添加美食'}</Text>
              <View className='editor-close' onClick={closeEditor}>
                <Icon name='close' size={18} color='#6E7A8F' />
              </View>
            </View>

            <View className='editor-body'>
              {/* 图片（可选） */}
              <View className='editor-image-row'>
                {formImage ? (
                  <View className='image-preview'>
                    <Image className='image-preview-img' src={formImage} mode='aspectFill' />
                    <View className='image-remove' onClick={handleRemoveImage}>
                      <Icon name='close' size={12} color='#FFFFFF' />
                    </View>
                  </View>
                ) : (
                  <View className='image-add' onClick={handleChooseImage}>
                    <Icon name='image' size={22} color='#6E7A8F' />
                    <Text className='image-add-text'>照片</Text>
                  </View>
                )}
                <Text className='image-hint'>图片可选 · 拍张照更有食欲</Text>
              </View>

              {/* 名称 */}
              <View className='editor-field'>
                <Text className='field-label'>名称</Text>
                <Input
                  className='field-input'
                  value={formName}
                  maxlength={20}
                  placeholder='如：兰州拉面'
                  placeholderClass='field-placeholder'
                  onInput={(e) => setFormName(e.detail.value)}
                />
              </View>

              {/* 备注 */}
              <View className='editor-field'>
                <Text className='field-label'>备注（可选）</Text>
                <Input
                  className='field-input'
                  value={formNote}
                  maxlength={50}
                  placeholder='如：少辣、那家老店'
                  placeholderClass='field-placeholder'
                  onInput={(e) => setFormNote(e.detail.value)}
                />
              </View>
            </View>

            <View className='editor-actions safe-area-bottom'>
              {editing && (
                <View className='editor-delete' hoverClass='editor-delete-hover' hoverStayTime={100} onClick={handleDelete}>
                  <Icon name='trash' size={16} color='#F87171' />
                  <Text>删除</Text>
                </View>
              )}
              <View className='editor-cancel' hoverClass='editor-cancel-hover' hoverStayTime={100} onClick={closeEditor}>
                <Text>取消</Text>
              </View>
              <View className='editor-save btn-primary' hoverClass='btn-primary-hover' hoverStayTime={100} onClick={handleSave}>
                <Text>保存</Text>
              </View>
            </View>
          </View>
        </View>
      )}
    </View>
  )
}
