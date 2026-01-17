/**
 * MarkdownEditorTool - Wrapper component with providers and auth guard
 */
import { AuthGuard } from '../Auth';
import { FileProvider } from '../../stores/fileStore';
import { EditorProvider } from '../../stores/editorStore';
import { ConfigProvider } from '../../stores/configStore';
import { I18nProvider } from '../../i18n/I18nProvider';
import { MarkdownEditor } from '../MarkdownEditor';

export default function MarkdownEditorTool() {
  return (
    <AuthGuard>
      <I18nProvider>
        <FileProvider>
          <EditorProvider>
            <ConfigProvider>
              <MarkdownEditor />
            </ConfigProvider>
          </EditorProvider>
        </FileProvider>
      </I18nProvider>
    </AuthGuard>
  );
}
