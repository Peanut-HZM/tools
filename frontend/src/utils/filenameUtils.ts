/**
 * 文件名工具函数
 * 用于生成带时间戳的唯一文件名
 */

/**
 * 判断文件名是否已经带有扩展名
 *
 * 规则（与后端 os.path.splitext 语义保持一致）：
 * - `report.md` → 有扩展名
 * - `example.kubeconfig` → 有扩展名（不会再被追加 `.md`）
 * - `README` → 无扩展名（默认按 `.md` 处理）
 * - `.gitignore` → 视为无扩展名的隐藏文件（末尾点号不算扩展名）
 *
 * @param filename - 文件名（可含路径，仅按最后一段判断）
 * @returns 是否存在扩展名
 */
export const hasFileExtension = (filename: string): boolean => {
  const baseName = filename.split('/').pop() ?? '';
  const lastDot = baseName.lastIndexOf('.');
  // lastDot <= 0：没有点号，或是以点开头的隐藏文件（`.gitignore`）
  // lastDot === baseName.length - 1：以点结尾（如 `foo.`），不算扩展名
  return lastDot > 0 && lastDot < baseName.length - 1;
};

/**
 * 为没有扩展名的文件名补上默认扩展名
 *
 * 仅当文件名**完全没有扩展名**时才追加默认扩展名；
 * 已经带扩展名（如 `example.kubeconfig`、`a.txt`）的文件名保持原样。
 *
 * @param filename - 原始文件名
 * @param defaultExtension - 默认扩展名（不含点号），默认为 'md'
 * @returns 处理后的文件名
 *
 * @example
 * ensureFileExtension('README') // 'README.md'
 * ensureFileExtension('example.kubeconfig') // 'example.kubeconfig'
 */
export const ensureFileExtension = (
  filename: string,
  defaultExtension = 'md'
): string => {
  const trimmed = filename.trim();
  if (!trimmed) return trimmed;
  if (hasFileExtension(trimmed)) return trimmed;
  const ext = defaultExtension.replace(/^\./, '');
  return ext ? `${trimmed}.${ext}` : trimmed;
};

/**
 * 取文件名的扩展名（不含点号）
 *
 * @param filename - 文件名（可含路径，仅按最后一段判断）
 * @returns 扩展名；没有扩展名时返回空串
 *
 * @example
 * getFileExtension('a.md') // 'md'
 * getFileExtension('README') // ''
 */
export const getFileExtension = (filename: string): string => {
  const baseName = filename.split('/').pop() ?? '';
  const lastDot = baseName.lastIndexOf('.');
  if (lastDot <= 0 || lastDot === baseName.length - 1) return '';
  return baseName.slice(lastDot + 1);
};

/**
 * 计算重命名后的文件名
 *
 * 规则：
 * - 新名字自带扩展名 → 原样使用（允许借此修改扩展名）
 * - 新名字没有扩展名 → 沿用原文件的扩展名（`a.md` → `b` 得到 `b.md`）
 * - 原文件本身也没有扩展名 → 保持新名字原样，不强制补 `.md`
 *
 * @param newName - 用户输入的新名字
 * @param originalName - 原文件名
 * @returns 最终文件名
 *
 * @example
 * resolveRenameName('b', 'a.md') // 'b.md'
 * resolveRenameName('b.txt', 'a.md') // 'b.txt'
 */
export const resolveRenameName = (
  newName: string,
  originalName: string
): string => {
  const trimmed = newName.trim();
  if (!trimmed) return trimmed;
  if (hasFileExtension(trimmed)) return trimmed;
  const originalExt = getFileExtension(originalName);
  return originalExt ? `${trimmed}.${originalExt}` : trimmed;
};

/**
 * 生成带时分秒的时间戳文件名
 *
 * @param prefix - 文件名前缀，默认为 'course-export'
 * @param extension - 文件扩展名，默认为 'json'
 * @returns 格式：{prefix}-YYYYMMDD-HHMMSS.{extension}
 *
 * @example
 * generateTimestampFilename() // 'course-export-20260312-143025.json'
 * generateTimestampFilename('backup', 'zip') // 'backup-20260312-143025.zip'
 */
export const generateTimestampFilename = (
  prefix = 'course-export',
  extension = 'json'
): string => {
  const now = new Date();
  const year = now.getFullYear();
  const month = String(now.getMonth() + 1).padStart(2, '0');
  const day = String(now.getDate()).padStart(2, '0');
  const hours = String(now.getHours()).padStart(2, '0');
  const minutes = String(now.getMinutes()).padStart(2, '0');
  const seconds = String(now.getSeconds()).padStart(2, '0');

  const timestamp = `${year}${month}${day}-${hours}${minutes}${seconds}`;

  return `${prefix}-${timestamp}.${extension}`;
};

/**
 * 生成仅日期格式的时间戳文件名（向后兼容）
 *
 * @param prefix - 文件名前缀，默认为 'course-export'
 * @param extension - 文件扩展名，默认为 'json'
 * @returns 格式：{prefix}-YYYY-MM-DD.{extension}
 *
 * @deprecated 使用 generateTimestampFilename 代替
 */
export const generateDateFilename = (
  prefix = 'course-export',
  extension = 'json'
): string => {
  const now = new Date();
  const year = now.getFullYear();
  const month = String(now.getMonth() + 1).padStart(2, '0');
  const day = String(now.getDate()).padStart(2, '0');

  const date = `${year}-${month}-${day}`;

  return `${prefix}-${date}.${extension}`;
};
