/**
 * MarkdownEditorTool - Wrapper component with providers and auth guard
 */
import { AuthGuard } from '../Auth';
import { FileProvider } from '../../stores/fileStore';
import { EditorProvider } from '../../stores/editorStore';
import { ConfigProvider } from '../../stores/configStore';
import { MarkdownEditor } from '../MarkdownEditor';

export default function MarkdownEditorTool() {
  return (
    <AuthGuard>
      <FileProvider>
        <EditorProvider>
          <ConfigProvider>
            <MarkdownEditor />
          </ConfigProvider>
        </EditorProvider>
      </FileProvider>
    </AuthGuard>
  );
}
