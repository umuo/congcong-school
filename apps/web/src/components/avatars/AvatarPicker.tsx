"use client";
import { useEffect, useId, useRef, useState } from 'react';
import { playSfx } from '@/lib/sfx';
import { Avatar } from './Avatar';
import { avatarPreset, presets } from '@/lib/avatars/draw';
export function AvatarChoices({ value, onChange, disabled=false, name: fieldName }: {value:string;onChange:(id:string)=>void;disabled?:boolean;name?:string}) {
  const generatedName = useId();
  const name = fieldName ?? generatedName;
  return <fieldset data-sound-handled className="avatar-choices" disabled={disabled}><legend>选择内置头像</legend>
    <div className="avatar-grid">{presets.map(p => <label className="avatar-choice" key={p.id}>
      <input type="radio" name={name} value={p.id} checked={value===p.id} onChange={()=>{playSfx("tap");onChange(p.id);}} />
      <Avatar id={p.id} size={48}/><span>{p.name}{value===p.id?' ✓':''}</span>
    </label>)}</div>
  </fieldset>;
}
export function AvatarPicker({ current, onSave, onCancel, onReload }: { current:string;onSave:(id:string)=>Promise<void>;onCancel:()=>void;onReload:()=>Promise<void> }) {
  const dialog = useRef<HTMLDialogElement>(null);
  const cancel = useRef(onCancel); cancel.current = onCancel;
  useEffect(() => {
    const node = dialog.current;
    if (!node) return;
    const trigger = document.activeElement instanceof HTMLElement ? document.activeElement : null;
    if (!node.open) node.showModal();
    // Enter on the title, not the first radio: focus must not look like a second selection.
    node.querySelector<HTMLElement>("h2")?.focus({ preventScroll: true });
    return () => { node.close(); trigger?.focus(); };
  }, []);
  const [selected,setSelected] = useState(current);
  const [busy,setBusy] = useState(false);
  const [error,setError] = useState('');
  const [conflict,setConflict] = useState(false);
  async function save() {
    setBusy(true); setError('');
    try { await onSave(selected); }
    catch(e) {setError(e instanceof Error?e.message:'保存失败，请重试');setConflict((e as {code?:string}).code==='REVISION_CONFLICT');}
    finally {setBusy(false);}
  }
  return <dialog ref={dialog} role="dialog" aria-modal="true" className="avatar-picker" aria-label="修改头像" onCancel={e=>{e.preventDefault();if(!busy)cancel.current();}}>
    <h2 tabIndex={-1}>挑选你的森林伙伴</h2>
    <div className="avatar-preview"><Avatar id={selected} size={88}/><p>预览：{avatarPreset(selected).name}<small>保存后才会更新</small></p></div>
    <AvatarChoices value={selected} onChange={setSelected} disabled={busy}/>
    {error ? <p role="alert">{error}</p>:null}
    <div className="account-actions">
      <button type="button" disabled={busy||conflict||!presets.some(p=>p.id===selected)} onClick={()=>void save()}>{busy?'正在保存…':'保存头像'}</button>
      <button type="button" className="secondary" onClick={onCancel} disabled={busy}>取消</button>
      <button type="button" className="secondary" disabled={busy} onClick={async()=>{
        setBusy(true);try{await onReload();onCancel();}catch(e){setError(e instanceof Error?e.message:'读取失败');}finally{setBusy(false);}
      }}>读取最新头像</button>
    </div>
  </dialog>;
}
