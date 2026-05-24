import { useState, useEffect } from 'react';
import Taro from '@tarojs/taro';
import { View, Textarea, Button, Text, ScrollView } from '@tarojs/components';
import { markdownEditorApi } from '../../../services/markdownEditor';
import { copyText, formatApiError } from '../../../utils/mobileTool';
import Markdown from '../../../components/Markdown';
import './index.scss';

type Tab = 'edit' | 'preview';

export default function MarkdownEditorPage() {
  const [content, setContent] = useState('');
  const [activeTab, setActiveTab] = useState<Tab>('edit');
  const [ossFiles, setOssFiles] = useState<{ file_path: string; filename: string }[]>([]);
  const [showOssList, setShowOssList] = useState(false);

  useEffect(() => {
    const draft = markdownEditorApi.loadDraft();
    if (draft) setContent(draft);
  }, []);

  const handleContentChange = (value: string) => {
    setContent(value);
    markdownEditorApi.saveDraft(value);
  };

  const handleCopy = async () => {
    if (content) await copyText(content);
  };

  const handleClear = () => {
    Taro.showModal({
      title: '确认清空',
      content: '清空后无法恢复，确定吗？',
      success: (res) => {
        if (res.confirm) {
          setContent('');
          markdownEditorApi.clearDraft();
        }
      },
    });
  };

  const handleLoadOssList = async () => {
    try {
      const files = await markdownEditorApi.listOssFiles();
      setOssFiles(files.map(f => ({ file_path: f.file_path, filename: f.filename })));
      setShowOssList(true);
    } catch (err: any) {
      Taro.showToast({ title: formatApiError(err), icon: 'none' });
    }
  };

  const handleLoadOssFile = async (filePath: string) => {
    try {
      Taro.showLoading({ title: '加载中...' });
      const res = await markdownEditorApi.readOssFile(filePath);
      Taro.hideLoading();
      if (res.success) {
        setContent(res.content);
        markdownEditorApi.saveDraft(res.content);
        setShowOssList(false);
        setActiveTab('edit');
      }
    } catch (err: any) {
      Taro.hideLoading();
      Taro.showToast({ title: formatApiError(err), icon: 'none' });
    }
  };

  return (
    <View className="markdown-editor-page">
      <View className="tab-bar">
        <View
          className={`tab ${activeTab === 'edit' ? 'active' : ''}`}
          onClick={() => setActiveTab('edit')}
        >
          <Text>编辑</Text>
        </View>
        <View
          className={`tab ${activeTab === 'preview' ? 'active' : ''}`}
          onClick={() => setActiveTab('preview')}
        >
          <Text>预览</Text>
        </View>
      </View>

      {activeTab === 'edit' && (
        <View className="editor-section">
          <Textarea
            className="editor-textarea"
            value={content}
            onInput={(e) => handleContentChange(e.detail.value)}
            placeholder="输入 Markdown 内容..."
            maxlength={-1}
          />
        </View>
      )}

      {activeTab === 'preview' && (
        <ScrollView className="preview-section" scrollY>
          {content ? (
            <Markdown content={content} />
          ) : (
            <View className="empty-preview">
              <Text>暂无内容，切换到编辑页输入 Markdown</Text>
            </View>
          )}
        </ScrollView>
      )}

      <View className="toolbar">
        <Button className="tool-btn" onClick={handleCopy}>复制</Button>
        <Button className="tool-btn" onClick={handleClear}>清空</Button>
        <Button className="tool-btn" onClick={handleLoadOssList}>OSS文件</Button>
      </View>

      {showOssList && (
        <View className="oss-modal">
          <View className="oss-overlay" onClick={() => setShowOssList(false)} />
          <View className="oss-content">
            <View className="oss-header">
              <Text className="oss-title">选择文件</Text>
              <Text className="oss-close" onClick={() => setShowOssList(false)}>关闭</Text>
            </View>
            <ScrollView className="oss-list" scrollY>
              {ossFiles.length === 0 ? (
                <Text className="oss-empty">暂无文件</Text>
              ) : (
                ossFiles.map((file) => (
                  <View
                    key={file.file_path}
                    className="oss-item"
                    onClick={() => handleLoadOssFile(file.file_path)}
                  >
                    <Text className="oss-filename">{file.filename}</Text>
                  </View>
                ))
              )}
            </ScrollView>
          </View>
        </View>
      )}
    </View>
  );
}
