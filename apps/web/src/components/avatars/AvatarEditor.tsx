"use client";
import { useCallback, useEffect, useRef, useState } from 'react';
import type { Account } from '@/lib/api/client';
import { AVATAR_UPDATED, assertAvatarScope, notifyAvatarUpdated, readAvatar, writeAvatar, type EffectiveAvatar } from '@/lib/avatars/client';
import { Avatar } from './Avatar';
import { AvatarPicker } from './AvatarPicker';
import { FloatingNotice } from '@/components/learning/FloatingNotice';
export function AvatarEditor({account,label='我的头像'}:{account:Account;label?:string}) {
  // The keyed inner instance prevents an old subject's state rendering for a new identity.
  return <ScopedEditor key={account.context_id} account={account} label={label}/>;
}
function ScopedEditor({account,label}:{account:Account;label:string}) {
  const [value,setValue]=useState<EffectiveAvatar|null>(null);
  const [editing,setEditing]=useState<EffectiveAvatar|null>(null);
  const [error,setError]=useState('');
  const [notice,setNotice]=useState('');
  const lifetime=useRef<AbortController|null>(null);
  const generation=useRef(0);
  const load=useCallback(async()=>{
    const signal=lifetime.current?.signal;
    if(!signal || signal.aborted) return;
    const request=++generation.current;
    const result=await readAvatar(account,signal);
    if(!signal.aborted && request===generation.current) {setValue(previous=>previous && previous.revision>result.revision ? previous : result);setError('');return result;}
  },[account.context_id,account.mode,account.student_id,account.user?.id]); // immutable scope, not polling object
  useEffect(()=>{
    const controller=new AbortController();lifetime.current=controller;
    const reload=(event?:Event)=>{
      const detail = event?.type===AVATAR_UPDATED ? (event as CustomEvent<EffectiveAvatar>).detail : undefined;
      if (detail) {
        // API-confirmed avatar notifications already contain the new value.
        // Keep the open picker's revision frozen; only refresh the header display.
        try { assertAvatarScope(account,detail); } catch { return; }
        if (Number.isInteger(detail.revision) && typeof detail.avatar_id==='string' && typeof detail.catalog_version==='string') {
          ++generation.current;
          setValue(previous=>previous && previous.revision>detail.revision ? previous : detail);setError('');return;
        }
      }
      void load().catch(e=>{if(!controller.signal.aborted)setError(e.message);});
    };
    reload(); window.addEventListener(AVATAR_UPDATED,reload);
    window.addEventListener('focus',reload);
    return ()=>{controller.abort();generation.current++;window.removeEventListener(AVATAR_UPDATED,reload);window.removeEventListener('focus',reload);};
  },[load]);
  async function save(id:string) {
    const signal=lifetime.current?.signal;
    if(!editing||!signal||signal.aborted) return;
    ++generation.current;
    const result=await writeAvatar(account,editing,id,signal);
    if(signal.aborted) return;
    setValue(result);setEditing(null);setError('');setNotice('头像已保存');notifyAvatarUpdated(result);
  }
  return <div className="avatar-editor">
    <FloatingNotice message={notice}/>
    {value ? <button type="button" className="secondary avatar-trigger" aria-label={`${label} · 修改头像`} onClick={()=>{setEditing(value);setError('');setNotice('');}}><Avatar id={value.avatar_id}/><span>{label.replace(/的头像$/, "").replace("我的学习头像", "我的头像")}</span></button>:<span>正在读取头像…</span>}
    {error ? <p role="status">{error}</p>:null}
    {!value && error ? <button type="button" onClick={()=>void load().catch(e=>setError(e.message))}>重试读取头像</button>:null}
    {editing ? <AvatarPicker current={editing.avatar_id} onSave={save} onCancel={()=>setEditing(null)} onReload={async()=>{const latest=await load();if(latest)notifyAvatarUpdated(latest);}}/>:null}
  </div>;
}
