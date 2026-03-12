/**
 * 文件名工具函数
 * 用于生成带时间戳的唯一文件名
 */

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
