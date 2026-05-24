import { useState } from 'react';
import Taro from '@tarojs/taro';
import { View, Button, Text, ScrollView } from '@tarojs/components';
import { converterApi } from '../../services/converter';
import type { ConvertResponse } from '../../services/converter';
import { chooseFileCompat, copyText, formatApiError } from '../../utils/mobileTool';
import Markdown from '../../components/Markdown';
import Loading from '../../components/Loading';
import './index.scss';

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
        <View className="upload-section">
          <Text className="title">选择文件转换</Text>
          <Text className="subtitle">支持 Word、PDF、Excel 等格式</Text>
          <Button className="select-btn" onClick={handleSelectFile}>
            选择文件
          </Button>
          <Text className="hint">文件大小不超过 20MB</Text>
        </View>
      )}

      {pageState === 'converting' && <Loading text="正在转换..." />}

      {pageState === 'error' && (
        <View className="error-state">
          <Text className="error-text">{errorMsg}</Text>
          <Button className="retry-btn" onClick={handleReset}>重试</Button>
        </View>
      )}

      {pageState === 'success' && result && (
        <View className="result-section">
          <View className="result-header">
            <Text className="filename">{result.file_name}</Text>
            <Text className="meta">原始: {(result.file_size / 1024).toFixed(1)}KB → 输出: {(result.output_size / 1024).toFixed(1)}KB</Text>
          </View>
          <ScrollView className="markdown-preview" scrollY>
            <Markdown content={result.content} />
          </ScrollView>
          <View className="actions">
            <Button className="action-btn" onClick={handleCopy}>复制全文</Button>
            <Button className="action-btn secondary" onClick={handleReset}>转换新文件</Button>
          </View>
        </View>
      )}
    </View>
  );
}
