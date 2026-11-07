import assert from 'node:assert/strict';
import React from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import TestRenderer, {act} from 'react-test-renderer';
import { Avatar } from '../../apps/web/src/components/avatars/Avatar';
import { AvatarEditor } from '../../apps/web/src/components/avatars/AvatarEditor';
import { AvatarPicker, AvatarChoices } from '../../apps/web/src/components/avatars/AvatarPicker';
import { drawAvatar, painterIds, presets, avatarPreset } from '../../apps/web/src/lib/avatars/draw';
import { notifyAvatarUpdated, assertAvatarScope, readAvatar, writeAvatar } from '../../apps/web/src/lib/avatars/client';
import type { Account } from '../../apps/web/src/lib/api/client';
import { CloudLearningClient } from '../../apps/web/src/lib/learning/client';

async function main(){
  Object.assign(globalThis,{IS_REACT_ACT_ENVIRONMENT:true});
  const operations:string[]=[];
  const ctx=new Proxy({}, {get:(_,key)=>typeof key==='string'? (..._args:unknown[])=>operations.push(key):undefined,
    set:()=>true}) as CanvasRenderingContext2D;
  assert.deepEqual([...painterIds].sort(),presets.map(p=>p.id).sort());
  for(const p of presets) {const before=operations.length;drawAvatar(ctx,p.id);assert.ok(operations.length>before+15);}
  assert.equal(avatarPreset('unknown').id,'panda');
  const choices=renderToStaticMarkup(<AvatarChoices value="cat" onChange={()=>{}} name="avatar"/>);
  const names=[...choices.matchAll(/<input[^>]*name="([^"]+)"/g)].map(m=>m[1]);
  assert.equal(names.length,16);assert.deepEqual([...new Set(names)],['avatar']);
  const html=renderToStaticMarkup(<Avatar id="unknown" size={32}/>);
  assert.match(html,/熊猫头像/);assert.match(html,/data-avatar-id="panda"/);assert.match(html,/>熊猫</);
  const events=new EventTarget();
  const storageData=new Map<string,string>();
  const storage={get length(){return storageData.size;}, key:(i:number)=>[...storageData.keys()][i]??null,
    getItem:(k:string)=>storageData.get(k)??null,setItem:(k:string,v:string)=>{storageData.set(k,v);},removeItem:(k:string)=>{storageData.delete(k);}};
  Object.assign(globalThis,{window:Object.assign(events,{devicePixelRatio:2,sessionStorage:storage,
    setTimeout,clearTimeout,matchMedia:()=>({addEventListener(){},removeEventListener(){}})}),document:{cookie:''}});
  // DPR drawing at two CSS sizes; no animation or browser-only SSR requirement.
  for(const dpr of [1,2,3]) for(const size of [32,88]) {
    window.devicePixelRatio=dpr;
    const node={width:0,height:0,getContext:()=>ctx};
    let tree!:TestRenderer.ReactTestRenderer;
    await act(async()=>{tree=TestRenderer.create(<Avatar id="fox" size={size}/>,{createNodeMock:()=>node});});
    assert.equal(node.width,size*dpr);assert.equal(node.height,size*dpr);
    await act(async()=>{tree.unmount();});
  }
  let unavailable!:TestRenderer.ReactTestRenderer;
  await act(async()=>{unavailable=TestRenderer.create(<Avatar id="fox"/>,{createNodeMock:()=>({getContext:()=>null})});});
  assert.match(JSON.stringify(unavailable.toJSON()),/熊猫/);
  await act(async()=>{unavailable.unmount();});
  let saves=0,cancels=0,selected='';
  let picker!:TestRenderer.ReactTestRenderer;
  const render=(onSave:(id:string)=>Promise<void>)=><AvatarPicker current="panda" onSave={onSave} onCancel={()=>{cancels++;}} onReload={async()=>{}}/>;
  await act(async()=>{picker=TestRenderer.create(render(async id=>{saves++;selected=id;}));});
  assert.equal(picker.root.findByType('dialog').props.role,'dialog');
  assert.equal(picker.root.findByType('dialog').props['aria-modal'],'true');
  const radio=picker.root.findAllByType('input').find(n=>n.props.value==='robot')!;
  await act(async()=>{radio.props.onChange();});
  const button=(text:string)=>picker.root.findAllByType('button').find(n=>n.children.join('')===text)!;
  await act(async()=>{button('取消').props.onClick();});assert.equal(cancels,1);assert.equal(saves,0);
  await act(async()=>{await button('保存头像').props.onClick();});assert.equal(selected,'robot');
  await act(async()=>{picker.update(render(async()=>{throw Error('暂时无法连接服务');}));});
  await act(async()=>{await button('保存头像').props.onClick();});
  assert.equal(button('保存头像').props.disabled,false);assert.match(JSON.stringify(picker.toJSON()),/暂时无法连接服务/);
  await act(async()=>{picker.update(render(async()=>{throw Object.assign(Error('资料冲突'),{code:'REVISION_CONFLICT'});}));});
  await act(async()=>{await button('保存头像').props.onClick();});
  assert.equal(button('保存头像').props.disabled,true);assert.match(JSON.stringify(picker.toJSON()),/资料冲突/);
  await act(async()=>{picker.unmount();});
  const account={context_id:'context-a',mode:'child',student_id:'student-a',user:null} as Account;
  const avatar={scope_kind:'student' as const,subject_id:'student-a',avatar_id:'robot',revision:1,catalog_version:'avatars-1'};
  assert.throws(()=>assertAvatarScope({...account,student_id:'student-b'},avatar),/身份/);
  // Pending bytes and original key survive the dedicated notification and avatar PUT.
  const client=new CloudLearningClient({...account,must_change_password:false},undefined,storage);
  client.prepare('/students/student-a/economy/actions',{kind:'daily_reward'});
  const pending=[...storageData];assert.equal(pending.length,1);
  let notices=0;events.addEventListener('csf-avatar-updated',()=>{notices++;});
  notifyAvatarUpdated(avatar);assert.equal(notices,1);assert.deepEqual([...storageData],pending);
  const requests:{url:string;body:unknown;headers:Headers}[]=[];
  let resolver:((r:Response)=>void)|undefined;
  globalThis.fetch=async(url,init)=>{requests.push({url:String(url),body:init?.body,headers:new Headers(init?.headers)});return new Response(JSON.stringify({...avatar,revision:2}));};
  const controller=new AbortController();
  assert.equal((await writeAvatar(account,avatar,'robot',controller.signal)).revision,2);
  assert.equal(requests[0].headers.get('If-Match'),'1');assert.equal(requests[0].headers.get('X-CSF-Learning-Context'),'context-a');
  assert.equal(requests[0].body,JSON.stringify({avatar_id:'robot'}));
  assert.deepEqual([...storageData],pending);
  globalThis.fetch=async()=>new Promise<Response>(r=>{resolver=r;});
  const late=readAvatar(account,controller.signal);controller.abort();resolver!(new Response(JSON.stringify(avatar)));
  await assert.rejects(late,/取消/);
  // A successful write whose response was lost is resolved by a fresh GET, never an automatic overwrite.
  globalThis.fetch=async()=>{throw Error('lost response');};
  await assert.rejects(writeAvatar(account,avatar,'robot',new AbortController().signal),/连接/);
  globalThis.fetch=async()=>new Response(JSON.stringify({...avatar,revision:2}));
  assert.equal((await readAvatar(account,new AbortController().signal)).revision,2);
  assert.deepEqual([...storageData],pending);
  let editor!:TestRenderer.ReactTestRenderer;
  globalThis.fetch=async()=>new Response(JSON.stringify(avatar));
  await act(async()=>{editor=TestRenderer.create(<AvatarEditor account={account}/>);});
  assert.match(JSON.stringify(editor.toJSON()),/修改头像/);
  // A focus refresh while the picker is open must not upgrade its editing revision.
  await act(async()=>{editor.root.findAllByType('button').find(n=>String(n.props['aria-label'] ?? '').includes('修改头像'))!.props.onClick();});
  globalThis.fetch=async()=>new Response(JSON.stringify({...avatar,avatar_id:'owl',revision:2}));
  await act(async()=>{events.dispatchEvent(new Event('focus'));});
  let editVersion='';
  globalThis.fetch=async(_url,init)=>{editVersion=new Headers(init?.headers).get('If-Match')??'';return new Response(JSON.stringify({code:'REVISION_CONFLICT',message:'conflict'}),{status:409});};
  await act(async()=>{editor.root.findAllByType('button').find(n=>n.children.join('')==='保存头像')!.props.onClick();});
  assert.equal(editVersion,'1');assert.match(JSON.stringify(editor.toJSON()),/尚未保存/);
  globalThis.fetch=async()=>new Response(JSON.stringify({...avatar,avatar_id:'owl',revision:2}));
  const previousNotices=notices;
  await act(async()=>{await editor.root.findAllByType('button').find(n=>n.children.join('')==='读取最新头像')!.props.onClick();});
  assert.equal(notices,previousNotices+1);assert.deepEqual([...storageData],pending);
  const saveRequests:string[]=[];
  globalThis.fetch=async(_url,init)=>{saveRequests.push(init?.method??'GET');return new Response(JSON.stringify({...avatar,avatar_id:'robot',revision:3}));};
  await act(async()=>{editor.root.findAllByType('button').find(n=>String(n.props['aria-label']??'').includes('修改头像'))!.props.onClick();});
  await act(async()=>{await editor.root.findByType(AvatarPicker).props.onSave('robot');});
  assert.deepEqual(saveRequests,['PUT'],'confirmed save notification reuses the response instead of fetching the avatar again');
  assert.match(JSON.stringify(editor.toJSON()),/robot/);
  globalThis.fetch=async()=>new Promise<Response>(r=>{resolver=r;});
  await act(async()=>{editor.update(<AvatarEditor account={{...account,context_id:'context-b',student_id:'student-b'}}/>);});
  // Old scoped instance unmounted, then the B request is itself cancelled.
  await act(async()=>{editor.unmount();});
  await act(async()=>{resolver!(new Response(JSON.stringify({...avatar,subject_id:'student-b'})));});
  assert.deepEqual([...storageData],pending);
  client.dispose();
  console.log('PASS avatars: 16 painters, SSR/fallback, DPR 1/2/3, preview/cancel/save/conflict, scope/abort/lost response, unchanged pending bytes.');
}
void main().catch(e=>{console.error(e);process.exitCode=1;});
