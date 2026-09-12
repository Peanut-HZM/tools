import { useState } from 'react';
import Taro from '@tarojs/taro';
import { View, Button, Text, ScrollView } from '@tarojs/components';
import { converterApi } from '../../../services/converter';
import type { ConvertResponse } from '../../../services/converter';
import { chooseFileCompat, copyText, formatApiError } from '../../../utils/mobileTool';
import Markdown from '../../../components/Markdown';
import Loading from '../../../components/Loading';
import Icon from '../../../components/Icon';
import './index.scss';

/**
 * 玻璃光晕换肤（阶段⑧-⑨ Task 8）：
 * - 上传引导面板套全局 .glass-card（半透明底+发丝描边+磨砂模糊+投影，见 styles/_glass.scss），
 *   本地样式只保留布局/圆角，勿重复定义背景以免击穿玻璃质感；
 * - 主按钮（选择文件/复制全文/重试）套 .btn-primary 品牌渐变，按压反馈走 hover-class='btn-primary-hover'；
 * - 次按钮（转换新文件）走玻璃描边；
 * - 结果条"原始 → 输出"的 Unicode 箭头改为 Icon（chevron-right），文案语义不变；
 * - 选文件/转换/复制逻辑不变。
 */

type PageState = 'idle' | 'selecting' | 'converting' | 'error' | 'success';

export default function MarkitdownConverterPage() {
  const [pageState, setPageState] = useState<PageState>('idle');
  const [result, setResult] = useState<ConvertResponse | null>(null);
  const [errorMsg, setErrorMsg] = useState('');

  const handleSelectFile = async () => {
    try {
      const file = await chooseFileCompat({
        accept: 'document/*',
        maxSize: 20 * 1024 * 1024,
      });
      setPageState('converting');
      const res = await converterApi.convertFile(file.path);
      setResult(res);
      setPageState('success');
    } catch (err: any) {
      setErrorMsg(formatApiError(err));
      setPageState('error');
    }
  };

  const handleCopy = async () => {
    if (result?.content) {
      await copyText(result.content);
    }
  };

  const handleReset = () => {
    setResult(null);
    setPageState('idle');
    setErrorMsg('');
  };

  return (
    <View className="markitdown-converter-page">
      {pageState === 'idle' && (
        <View className="upload-section glass-card">
          <Text className="title">选择文件转换</Text>
          <Text className="subtitle">支持 Word、PDF、Excel 等格式</Text>
          <Button className="select-btn btn-primary" hoverClass="btn-primary-hover" onClick={handleSelectFile}>
            选择文件
          </Button>
          <Text className="hint">文件大小不超过 20MB</Text>
        </View>
      )}

      {pageState === 'converting' && <Loading text="正在转换..." />}

      {pageState === 'error' && (
        <View className="error-state">
          <Text className="error-text">{errorMsg}</Text>
          <Button className="retry-btn btn-primary" hoverClass="btn-primary-hover" onClick={handleReset}>重试</Button>
        </View>
      )}

      {pageState === 'success' && result && (
        <View className="result-section">
          <View className="result-header">
            <Text className="filename">{result.file_name}</Text>
            {/* 原 Unicode 箭头 → 改为 Icon（chevron-right）；Icon 为 Image 实现，不可嵌于 Text，容器改用 View */}
            <View className="meta">
              <Text className="meta-text">原始: {(result.file_size / 1024).toFixed(1)}KB</Text>
              <Icon name="chevron-right" size={14} color="#6E7A8F" />
              <Text className="meta-text">输出: {(result.output_size / 1024).toFixed(1)}KB</Text>
            </View>
          </View>
          <ScrollView className="markdown-preview" scrollY>
            <Markdown content={result.content} />
          </ScrollView>
          <View className="actions">
            <Button className="action-btn btn-primary" hoverClass="btn-primary-hover" onClick={handleCopy}>复制全文</Button>
            <Button className="action-btn secondary" onClick={handleReset}>转换新文件</Button>
          </View>
        </View>
      )}
    </View>
  );
}
