/** 登录生命周期通知；不导入本地档案或权威 progress store。 */
const listeners = new Set<() => void>();
export const CLOUD_PENDING_PREFIX = "csf-cloud-pending-v1:";
export const CLOUD_REPORT_PREFIX = "csf-cloud-reports-v1:";
export function onLearningInvalidated(listener: () => void) {
  listeners.add(listener);
  return () => { listeners.delete(listener); };
}
export function invalidateLearning() {
  // 即使学习组件已卸载，也清理同标签页留存的待提交数据。
  try {
    const storage = window.sessionStorage;
    for (let i = storage.length - 1; i >= 0; i--) {
      const key = storage.key(i);
      if (key?.startsWith(CLOUD_PENDING_PREFIX) || key?.startsWith(CLOUD_REPORT_PREFIX)) storage.removeItem(key);
    }
  } catch { /* SSR 或浏览器限制存储；活动实例仍需清理内存。 */ }
  for (const listener of listeners) listener();
}
