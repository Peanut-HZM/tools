/**
 * MarkdownEditorTool - Wrapper component with providers and auth guard
 */
import { AuthGuard } from '../Auth';
import { FileProvider } from '../../stores/fileStore';
import { EditorProvider } from '../../stores/editorStore';
import { ExcelEditorProvider } from '../../stores/excelEditorStore';
import { ConfigProvider } from '../../stores/configStore';
import { MarkdownEditor } from '../MarkdownEditor';

export default function MarkdownEditorTool() {
  return (
    <AuthGuard>
      <FileProvider>
        <EditorProvider>
          <ExcelEditorProvider>
            <ConfigProvider>
              <MarkdownEditor />
            </ConfigProvider>
          </ExcelEditorProvider>
        </EditorProvider>
      </FileProvider>
    </AuthGuard>
  );
}
