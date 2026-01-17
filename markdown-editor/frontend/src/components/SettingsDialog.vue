<template>
  <div class="settings-dialog">
    <el-form label-width="140px">
      <el-divider content-position="left">{{ $t('common.settings') }}</el-divider>
      
      <el-form-item :label="$t('common.theme')">
        <el-radio-group v-model="localConfig.theme" @change="handleChange">
          <el-radio value="light">{{ $t('common.light') }}</el-radio>
          <el-radio value="dark">{{ $t('common.dark') }}</el-radio>
        </el-radio-group>
      </el-form-item>
      
      <el-form-item :label="$t('common.fontSize')">
        <el-slider
          v-model="localConfig.fontSize"
          :min="8"
          :max="32"
          :step="1"
          show-input
          @change="handleChange"
        />
      </el-form-item>
      
      <el-form-item :label="$t('common.tabSize')">
        <el-select v-model="localConfig.tabSize" @change="handleChange">
          <el-option :value="2" :label="'2 ' + $t('common.spaces')" />
          <el-option :value="4" :label="'4 ' + $t('common.spaces')" />
          <el-option :value="8" :label="'8 ' + $t('common.spaces')" />
        </el-select>
      </el-form-item>
      
      <el-form-item :label="$t('common.useSpaces')">
        <el-switch v-model="localConfig.useSpaces" @change="handleChange" />
      </el-form-item>
      
      <el-form-item :label="$t('common.showLineNumbers')">
        <el-switch v-model="localConfig.showLineNumbers" @change="handleChange" />
      </el-form-item>
      
      <el-divider content-position="left">{{ $t('common.autoSave') }}</el-divider>
      
      <el-form-item :label="$t('common.interval')">
        <el-slider
          v-model="localConfig.autoSaveInterval"
          :min="5"
          :max="300"
          :step="5"
          :format-tooltip="(val: number) => val + 's'"
          show-input
          @change="handleChange"
        />
      </el-form-item>
      
      <el-divider content-position="left">{{ $t('common.previewTheme') }}</el-divider>
      
      <el-form-item :label="$t('common.previewTheme')">
        <el-select v-model="localConfig.previewTheme" @change="handleChange">
          <el-option value="github" label="GitHub" />
          <el-option value="gitlab" label="GitLab" />
          <el-option value="default" label="Default" />
        </el-select>
      </el-form-item>
    </el-form>
    
    <div class="dialog-footer">
      <el-button @click="resetToDefaults">{{ $t('common.resetDefaults') }}</el-button>
      <el-button type="primary" @click="saveAndClose">{{ $t('common.saveAndClose') }}</el-button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { useConfigStore } from '@/stores'
import type { EditorConfig } from '@/types'
import { useI18n } from 'vue-i18n'

const { t } = useI18n()
const emit = defineEmits<{
  (e: 'close'): void
}>()

const configStore = useConfigStore()

const localConfig = ref<EditorConfig>({
  theme: 'light',
  fontSize: 14,
  autoSaveInterval: 30,
  previewTheme: 'github',
  showLineNumbers: true,
  tabSize: 2,
  useSpaces: true,
  language: 'zh-CN'
})

function handleChange() {
  configStore.updateConfig(localConfig.value)
}

async function saveAndClose() {
  try {
    await configStore.saveConfig()
    emit('close')
    ElMessage.success(t('message.configSaved'))
  } catch (e) {
    ElMessage.error(t('message.saveFail'))
  }
}

function resetToDefaults() {
  configStore.resetToDefaults()
  localConfig.value = { ...configStore.config }
  ElMessage.success(t('message.configReset'))
}

onMounted(() => {
  localConfig.value = { ...configStore.config }
})
</script>

<style scoped>
/* ========================================
   CYBERPUNK SETTINGS DIALOG STYLES
   ======================================== */
.settings-dialog {
  padding: 0 24px;
  background: #0d0d14;
}

.settings-dialog :deep(.el-divider__text) {
  font-weight: 800;
  color: #00f5ff;
  font-size: 11px;
  text-transform: uppercase;
  letter-spacing: 2px;
  background: rgba(0, 245, 255, 0.1);
  padding: 8px 20px;
  border-radius: 20px;
  border: 1px solid rgba(0, 245, 255, 0.2);
  text-shadow: 0 0 10px currentColor;
}

.settings-dialog :deep(.el-divider) {
  border-color: rgba(0, 245, 255, 0.1);
}

.settings-dialog :deep(.el-form-item__label) {
  font-weight: 600;
  color: #a0a0b8;
  font-size: 13px;
}

.settings-dialog :deep(.el-radio__label) {
  font-weight: 600;
  color: #a0a0b8;
}

.settings-dialog :deep(.el-radio__input.is-checked + .el-radio__label) {
  color: #00f5ff;
  text-shadow: 0 0 8px currentColor;
}

.settings-dialog :deep(.el-radio__inner) {
  background: rgba(0, 245, 255, 0.05);
  border-color: rgba(0, 245, 255, 0.3);
}

.settings-dialog :deep(.el-radio__input.is-checked .el-radio__inner) {
  background: #00f5ff;
  border-color: #00f5ff;
  box-shadow: 0 0 15px rgba(0, 245, 255, 0.5);
}

.settings-dialog :deep(.el-slider__runway) {
  background-color: rgba(0, 245, 255, 0.1);
  border-radius: 6px;
}

.settings-dialog :deep(.el-slider__bar) {
  background: linear-gradient(90deg, #00f5ff, #bf00ff);
  border-radius: 6px;
  box-shadow: 0 0 15px rgba(0, 245, 255, 0.4);
}

.settings-dialog :deep(.el-slider__button) {
  border-color: #00f5ff;
  background: #0d0d14;
  box-shadow: 0 0 15px rgba(0, 245, 255, 0.5);
  width: 18px;
  height: 18px;
}

.settings-dialog :deep(.el-slider__button:hover) {
  transform: scale(1.2);
}

.settings-dialog :deep(.el-select .el-input__wrapper) {
  background: rgba(0, 245, 255, 0.05);
  border: 1px solid rgba(0, 245, 255, 0.2);
  border-radius: 8px;
  box-shadow: none;
}

.settings-dialog :deep(.el-select .el-input__wrapper:hover),
.settings-dialog :deep(.el-select .el-input__wrapper.is-focus) {
  border-color: #00f5ff;
  box-shadow: 0 0 15px rgba(0, 245, 255, 0.2);
}

.settings-dialog :deep(.el-select .el-input__inner) {
  color: #e0e0e8;
}

.settings-dialog :deep(.el-switch__core) {
  background: rgba(0, 245, 255, 0.1);
  border-color: rgba(0, 245, 255, 0.2);
}

.settings-dialog :deep(.el-switch.is-checked .el-switch__core) {
  background: linear-gradient(90deg, #00f5ff, #00a8ff);
  border-color: #00f5ff;
  box-shadow: 0 0 20px rgba(0, 245, 255, 0.4);
}

.settings-dialog :deep(.el-input-number .el-input__wrapper) {
  background: rgba(0, 245, 255, 0.05);
  border: 1px solid rgba(0, 245, 255, 0.2);
  border-radius: 8px;
}

.settings-dialog :deep(.el-input-number .el-input__inner) {
  color: #00f5ff;
  font-weight: 700;
  text-shadow: 0 0 8px currentColor;
}

.dialog-footer {
  margin-top: 28px;
  padding-top: 24px;
  border-top: 1px solid rgba(0, 245, 255, 0.1);
  display: flex;
  justify-content: flex-end;
  gap: 14px;
  position: relative;
}

.dialog-footer::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 1px;
  background: linear-gradient(90deg, transparent, #00f5ff, #ff00ff, transparent);
  opacity: 0.5;
}

.dialog-footer .el-button {
  padding: 12px 24px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 1px;
  font-size: 12px;
  border-radius: 8px;
  transition: all 0.3s ease;
}

.dialog-footer :deep(.el-button:not(.el-button--primary)) {
  background: rgba(255, 0, 255, 0.1);
  border: 1px solid rgba(255, 0, 255, 0.3);
  color: #ff00ff;
}

.dialog-footer :deep(.el-button:not(.el-button--primary):hover) {
  background: rgba(255, 0, 255, 0.2);
  border-color: #ff00ff;
  box-shadow: 0 0 20px rgba(255, 0, 255, 0.3);
  transform: translateY(-2px);
}

.dialog-footer :deep(.el-button--primary) {
  background: linear-gradient(45deg, #00f5ff, #00a8ff);
  border: none;
  color: #0a0a0f;
  box-shadow: 0 0 25px rgba(0, 245, 255, 0.4);
}

.dialog-footer :deep(.el-button--primary:hover) {
  transform: translateY(-2px);
  box-shadow: 0 0 35px rgba(0, 245, 255, 0.6);
}
</style>
