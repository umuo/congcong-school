import { api, type Account } from '../api/client';
export interface EffectiveAvatar { scope_kind:'user'|'student';subject_id:string;avatar_id:string;revision:number;catalog_version:string }
export const AVATAR_UPDATED = 'csf-avatar-updated';
export function avatarSubject(account:Account) {
  return account.mode==='child' ? {kind:'student',id:account.student_id} : {kind:'user',id:account.user?.id};
}
export function assertAvatarScope(account:Account, value:EffectiveAvatar) {
  const scope=avatarSubject(account);
  if(value.scope_kind!==scope.kind || value.subject_id!==scope.id) throw Error('头像身份已变化，请刷新页面');
  return value;
}
export function notifyAvatarUpdated(value:EffectiveAvatar) {
  // Separate from csf-session: never invalidate pending learning operations.
  window.dispatchEvent(new CustomEvent(AVATAR_UPDATED,{detail:value}));
}
export async function readAvatar(account:Account, signal:AbortSignal) {
  const value=await api<EffectiveAvatar>('/me/avatar',{signal,headers:{'X-CSF-Learning-Context':account.context_id}});
  if(signal.aborted) throw new DOMException('已取消','AbortError');
  return assertAvatarScope(account,value);
}
export async function writeAvatar(account:Account, current:EffectiveAvatar, avatar_id:string, signal:AbortSignal) {
  assertAvatarScope(account,current);
  const value=await api<EffectiveAvatar>('/me/avatar',{method:'PUT',signal,
    headers:{'If-Match':String(current.revision),'X-CSF-Learning-Context':account.context_id},body:JSON.stringify({avatar_id})});
  if(signal.aborted) throw new DOMException('已取消','AbortError');
  return assertAvatarScope(account,value);
}
