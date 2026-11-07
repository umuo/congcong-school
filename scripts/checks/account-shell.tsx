import assert from 'node:assert/strict';
import React from 'react';
import TestRenderer,{act} from 'react-test-renderer';
import {AppRouterContext} from 'next/dist/shared/lib/app-router-context.shared-runtime';
import {PathnameContext} from 'next/dist/shared/lib/hooks-client-context.shared-runtime';
import {CloudChildBoundary} from '../../apps/web/src/components/account/CloudChildBoundary';
import {AccountGuard} from '../../apps/web/src/components/account/AccountShell';
import {FloatingNotice} from '../../apps/web/src/components/learning/FloatingNotice';
import {CloudEconomy} from '../../apps/web/src/components/learning/CloudEconomy';
import {isEquippedCosmetic} from '../../apps/web/src/lib/learning/equipped-cosmetic';
import {CloudSessionRunner} from '../../apps/web/src/components/learning/CloudSessionRunner';
import {QuestionRenderer} from '../../apps/web/src/components/question/QuestionRenderer';
import {readAnswerDraft,writeAnswerDraft,answerDraftKey} from '../../apps/web/src/lib/learning/answer-draft';
import {CloudLearningWorkspace} from '../../apps/web/src/components/learning/CloudLearningWorkspace';
import {useLearningClient} from '../../apps/web/src/components/learning/LearningProvider';
import type {CloudLearningClient} from '../../apps/web/src/lib/learning/client';
import type {Account} from '../../apps/web/src/lib/api/client';

async function main(){
 Object.assign(globalThis,{IS_REACT_ACT_ENVIRONMENT:true});
 const values=new Map<string,string>();
 const storage={get length(){return values.size;},key:(i:number)=>[...values.keys()][i]??null,getItem:(key:string)=>values.get(key)??null,setItem:(key:string,value:string)=>{values.set(key,value);},removeItem:(key:string)=>{values.delete(key);}};
 const win=Object.assign(new EventTarget(),{sessionStorage:storage,localStorage:storage,setInterval,clearInterval,setTimeout,clearTimeout});
 const doc=Object.assign(new EventTarget(),{visibilityState:'visible',cookie:''});
 class SilentAudio extends EventTarget {currentTime=0;preload='';pause(){}load(){}removeAttribute(){} }
 Object.assign(globalThis,{window:win,document:doc,Audio:SilentAudio,self:globalThis});
 class Channel {
  static active=new Set<Channel>(); onmessage:((event:unknown)=>void)|null=null;
  constructor(public name:string){Channel.active.add(this);}postMessage(){}close(){Channel.active.delete(this);}
 }
 Object.assign(globalThis,{BroadcastChannel:Channel});
 const first={context_id:'scope-a',student_id:'student-a',role:'student',mode:'child',must_change_password:false,destination:'/learn',user:{id:'user-a',nickname:'孩子A',login_name:'a',role:'student',email:null},family:{id:'family-a',name:'家庭A',timezone:'Asia/Shanghai',role:'member'}} as Account;
 const second={...first,context_id:'scope-b',student_id:'student-b',user:{...first.user!,id:'user-b',nickname:'孩子B'},family:{...first.family!,id:'family-b'}} as Account;
 const response=(account:Account)=>new Response(JSON.stringify(account),{status:200});
 let account=first,authReads=0,authResponse:()=>Promise<Response>=async()=>response(account);
 Object.assign(globalThis,{fetch:async(path:string)=>{
  if(path==='/api/v1/auth/session'){authReads++;return authResponse();}
  if(path==='/api/v1/me/avatar')return new Response(JSON.stringify({scope_kind:'student',subject_id:account.student_id,avatar_id:'panda',revision:1,catalog_version:'test'}));
  if(path.endsWith('/profile'))return new Response(JSON.stringify({id:account.student_id,nickname:account.user?.nickname,grade:1}));
  throw Error('Unexpected request '+path);
 }});
 const redirects:string[]=[];
 const router={replace:(path:string)=>redirects.push(path),push(){},prefetch(){},refresh(){},back(){},forward(){}};
 let current!:CloudLearningClient;
 function Probe(){current=useLearningClient();return <span data-testid="protected-student">{current.scope.studentId}</span>;}
 const tree=(path:string,nestedDestination='/learn')=><AppRouterContext.Provider value={router as any}><PathnameContext.Provider value={path}><CloudChildBoundary><AccountGuard key={path} destination={nestedDestination}>{()=> <Probe/>}</AccountGuard></CloudChildBoundary></PathnameContext.Provider></AppRouterContext.Provider>;
 let view!:TestRenderer.ReactTestRenderer;
 await act(async()=>{view=TestRenderer.create(tree('/learn/'));});
 assert.equal(authReads,1,'outer and page guards share one verified identity');
 assert.equal(current.scope.studentId,'student-a');
 const original=current;
 const frame=()=>view.root.findAllByType('div').find(e=>e.props['data-account-frame'])?.props['data-account-frame'];
 const firstFrame=frame();assert.ok(firstFrame);
 let pending!:string;
 await act(async()=>{pending=original.prepare('/students/student-a/economy/actions',{kind:'daily_reward'});});
 for(const path of ['/league/','/profile/','/explore/','/learn/']){
  await act(async()=>{view.update(tree(path));});
  assert.equal(authReads,1,'ordinary navigation must not restart login checks');
  assert.equal(current,original,'learning client survives page replacement');
  assert.equal(frame(),firstFrame,'the visual account frame stays mounted');
  assert.equal(view.root.findAllByType('div').filter(e=>e.props['data-account-frame']).length,1,'nested page guard does not duplicate the shell');
  assert.deepEqual(current.projection.getSnapshot().pending,[pending]);
 }
 let resolve!: (value:Response)=>void;
 authResponse=()=>new Promise(done=>{resolve=done;});
 await act(async()=>{win.dispatchEvent(new Event('focus'));});
 assert.equal(authReads,2);
 assert.equal(view.root.findAllByProps({'data-testid':'protected-student'}).length,1,'background verification keeps the verified screen');
 assert.doesNotMatch(JSON.stringify(view.toJSON()),/正在确认登录状态/);
 await act(async()=>{resolve(response(first));});
 assert.equal(current,original);
 // A page cannot request another role under the inherited child identity.
 await act(async()=>{view.update(tree('/league/','/admin'));});
 assert.equal(view.root.findAllByProps({'data-testid':'protected-student'}).length,0);
 assert.equal(redirects.at(-1),'/learn');assert.equal(authReads,2);
 await act(async()=>{view.update(tree('/learn/'));});
 // Cross-tab identity events immediately unmount old data while checking the new Cookie.
 await act(async()=>{for(const channel of Channel.active)channel.onmessage?.({data:'changed'});});
 assert.equal(view.root.findAllByProps({'data-testid':'protected-student'}).length,0);
 assert.deepEqual(original.projection.getSnapshot().pending,[]);
 await assert.rejects(original.getProgress(),/身份已变化/);
 account=second;
 await act(async()=>{resolve(response(second));});
 assert.equal(current.scope.studentId,'student-b');assert.notEqual(current,original);
 const next=current;
 // Expired login must still clear the screen and revoke the learning client.
 authResponse=async()=>new Response(JSON.stringify({code:'AUTH_REQUIRED',message:'请重新登录'}),{status:401});
 await act(async()=>{win.dispatchEvent(new Event('focus'));});
 assert.equal(view.root.findAllByProps({'data-testid':'protected-student'}).length,0);
 assert.equal(redirects.at(-1),'/login');
 await assert.rejects(next.getProgress(),/身份已变化/);
 authResponse=async()=>response(second);
 await act(async()=>{win.dispatchEvent(new Event('csf-session-invalid'));});
 const reauthClient=current;
 await act(async()=>{win.dispatchEvent(new Event('csf-reauth-required'));});
 assert.equal(view.root.findAllByProps({'data-testid':'protected-student'}).length,0);
 assert.match(JSON.stringify(view.toJSON()),/再次验证身份/);
 await assert.rejects(reauthClient.getProgress(),/身份已变化/);
 await act(async()=>{view.unmount();});assert.equal(Channel.active.size,0);
 // Exercise the actual workspace: subject changes read configured books only,
 // including a late response after the child has already chosen another subject.
 account=first; authResponse=async()=>response(first);
 const locations={search:'?book=g1up',pathname:'/learn/'};
 Object.assign(win,{location:locations,history:{replaceState(_state:unknown,_title:string,url:string){const parsed=new URL(url,'https://example.test');locations.search=parsed.search;locations.pathname=parsed.pathname;}}});
 const subjects=[{subject_code:'math',book_id:'g1up',enabled:true},{subject_code:'chinese',book_id:'chinese-g1up',enabled:true},{subject_code:'english',book_id:'english-g3up',enabled:true},{subject_code:'science',book_id:'science-g1up',enabled:true}];
 const labels:Record<string,string>={'g1up':'数学测试课程','chinese-g1up':'语文测试课程','english-g3up':'英语测试课程','science-g1up':'科学测试课程'};
 const content=(book:string)=>[{kind:'lesson',source_id:book+'-lesson',title:labels[book],unit_number:1,question_count:6}];
 const reads:{path:string;method:string}[]=[];
 let chineseReply!: (response:Response)=>void;
 Object.assign(globalThis,{fetch:async(path:string,options:RequestInit={})=>{
  reads.push({path,method:options.method??'GET'});
  if(path==='/api/v1/auth/session')return response(first);
  if(path==='/api/v1/me/avatar')return new Response(JSON.stringify({scope_kind:'student',subject_id:first.student_id,avatar_id:'panda',revision:1,catalog_version:'test'}));
  if(path.endsWith('/profile'))return new Response(JSON.stringify({id:first.student_id,nickname:'孩子A',grade:1}));
  if(path.endsWith('/progress'))return new Response(JSON.stringify({student_id:first.student_id,revision:1,rule_version:'test',state:{xp:0,gems:0,hearts:5,completedLessons:{}},quests:[]}));
  if(path.endsWith('/learning/curriculum'))return new Response(JSON.stringify({subjects}));
  if(path.includes('/learning-sessions?'))return new Response('[]');
  const book=path.match(/\/content\/books\/([^/?]+)$/)?.[1];
  if(book==='chinese-g1up')return new Promise<Response>(resolve=>{chineseReply=resolve;});
  if(book&&labels[book])return new Response(JSON.stringify(content(book)));
  throw Error('Unexpected workspace request '+path);
 }});
 const workspaceTree=<AppRouterContext.Provider value={router as any}><PathnameContext.Provider value="/learn/"><CloudChildBoundary><AccountGuard destination="/learn">{()=> <CloudLearningWorkspace/>}</AccountGuard></CloudChildBoundary></PathnameContext.Provider></AppRouterContext.Provider>;
 await act(async()=>{view=TestRenderer.create(workspaceTree);});
 const subjectButton=(name:string)=>view.root.findAllByType('button').find(b=>b.props['aria-label']===name)!;
 assert.match(JSON.stringify(view.toJSON()),/数学测试课程/);
 assert.equal(subjectButton('数学').props['aria-pressed'],true);
 assert.equal(view.root.findAllByType('select').some(s=>s.props['aria-label']==='当前教材'),false,'children do not choose textbook editions');
 await act(async()=>{subjectButton('语文').props.onClick();});
 assert.doesNotMatch(JSON.stringify(view.toJSON()),/数学测试课程/,'old subject content is hidden while loading');
 await act(async()=>{subjectButton('英语').props.onClick();});
 assert.match(JSON.stringify(view.toJSON()),/英语测试课程/);
 await act(async()=>{chineseReply(new Response(JSON.stringify(content('chinese-g1up'))));});
 assert.match(JSON.stringify(view.toJSON()),/英语测试课程/);
 assert.doesNotMatch(JSON.stringify(view.toJSON()),/语文测试课程/,'late subject content cannot replace the selected subject');
 await act(async()=>{subjectButton('科学').props.onClick();});
 assert.match(JSON.stringify(view.toJSON()),/科学测试课程/);
 await act(async()=>{subjectButton('数学').props.onClick();});
 assert.equal(locations.search,'?book=g1up');
 assert.equal(subjectButton('数学').props['aria-pressed'],true);
 assert.equal(reads.filter(r=>r.method!=='GET').length,0,'subject selection never updates curriculum or starts a lesson');
 await act(async()=>{view.unmount();});
 const emptyExploreTree=<AppRouterContext.Provider value={router as any}><PathnameContext.Provider value="/explore/"><CloudChildBoundary><CloudLearningWorkspace initialKind="story"/></CloudChildBoundary></PathnameContext.Provider></AppRouterContext.Provider>;
 await act(async()=>{view=TestRenderer.create(emptyExploreTree);});
 assert.match(JSON.stringify(view.toJSON()),/这里暂时没有故事/);
 const returnCourseURL=new URL(view.root.findAllByType('a').find(a=>a.props.className==='forest-empty-action')!.props.href,'https://example.test');
 assert.match(returnCourseURL.pathname,/^\/learn\/?$/);assert.equal(returnCourseURL.searchParams.get('book'),'g1up');
 assert.equal(view.root.findAllByType('img').some(img=>img.props.src==='/forest/lesson-friends.webp'),false,'empty exploration avoids a decorative content card before the next action');
 await act(async()=>{view.root.findAllByType('button').find(b=>b.props.children==='听读与跟读')!.props.onClick();});
 assert.match(JSON.stringify(view.toJSON()),/这里暂时没有听读材料/);
 assert.equal(reads.filter(r=>r.method!=='GET').length,0);
 await act(async()=>{view.unmount();});
 // Real runner input must not create checkpoints or disable input between letters.
 const draftSession:any={id:'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa',student_id:first.student_id,kind:'lesson',book_id:'english-g3up',source_id:'english-test',status:'active',revision:1,cursor:0,sources:[],checkpoint:{pending:[0],attempted:[],solved:[],first_correct:0,attempt_count:0,target_unit:null,reading_kind:null,hint_levels:{},draft:{intro_page:4}},question:{uid:'word-one',version:'v1',id:1,type:'fill_blank_text',question:'What is ___ name?',options:[],score:1,difficulty:1,knowledge_point:'names',audio:null,numberTask:null,input_keyboard:{candidates:['y','o','u','r'],language:'letters',max_length:12}},feedback:null};
 const writes:any[]=[];const draftReads:string[]=[];let exited=0;
 Object.assign(globalThis,{fetch:async(path:string,options:RequestInit={})=>{
  draftReads.push(path);
  if(path==='/api/v1/auth/session')return response(first);
  if(path.endsWith('/profile'))return new Response(JSON.stringify({id:first.student_id,nickname:'孩子A',grade:1}));
  if(path.endsWith('/me/avatar'))return new Response(JSON.stringify({scope_kind:'student',subject_id:first.student_id,avatar_id:'panda',revision:1,catalog_version:'test'}));
  if(path.endsWith('/content'))return new Response(JSON.stringify([{title:'询问姓名'}]));
  if(path.endsWith('/aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa'))return new Response(JSON.stringify(draftSession));
  if(path.endsWith('/events'))return new Response('{}');
  if(path.endsWith('/attempts')){const body=JSON.parse(options.body as string);writes.push(body);draftSession.revision++;draftSession.feedback={correct:true,answer:'your',submitted_answer:body.answer,explanation:'',evidence_sentence_indices:[]};return new Response(JSON.stringify(draftSession));}
  if(path.endsWith('/checkpoint')){const body=JSON.parse(options.body as string);writes.push(body);draftSession.revision++;draftSession.checkpoint.draft={...draftSession.checkpoint.draft,...body};return new Response(JSON.stringify(draftSession));}
  throw Error('Unexpected draft request '+path);
 }});
 const runnerTree=()=> <AppRouterContext.Provider value={router as any}><PathnameContext.Provider value="/learn/"><CloudChildBoundary><Probe/><CloudSessionRunner resumeId="aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa" onExit={()=>{exited++;}}/></CloudChildBoundary></PathnameContext.Provider></AppRouterContext.Provider>;
 await act(async()=>{view=TestRenderer.create(runnerTree());});
 assert.ok(view.root.findAllByType(QuestionRenderer).length, JSON.stringify({reads:draftReads,snapshot:current.projection.getSnapshot()}));
 for(const answer of ['y','yo','you','your'])await act(async()=>{view.root.findByType(QuestionRenderer).props.onChange(answer);});
 await act(async()=>{await new Promise(resolve=>setTimeout(resolve,1100));});
 assert.equal(writes.length,0,'typing and pausing do not send a checkpoint');
 assert.equal(view.root.findByType(QuestionRenderer).props.locked,false);
 assert.equal(view.root.findByType(QuestionRenderer).props.answer,'your');
 await act(async()=>{view.unmount();});
 await act(async()=>{view=TestRenderer.create(runnerTree());});
 assert.equal(view.root.findByType(QuestionRenderer).props.answer,'your','refresh/remount restores same-tab local draft');
 await act(async()=>{view.root.findAllByType('button').find(b=>b.props.children==='返回学习首页')!.props.onClick();});
 assert.equal(writes.length,1);assert.equal(writes[0].answer,'your');assert.equal(exited,1);
 await act(async()=>{view.root.findByType(QuestionRenderer).props.onChange('your latest');});
 await act(async()=>{view.root.findAllByType('button').find(b=>b.props.children==='检查答案')!.props.onClick();});
 assert.equal(writes.length,2);assert.equal(writes[1].answer,'your latest','explicit check submits the latest local input without a preceding checkpoint');
 assert.equal(view.root.findByType(QuestionRenderer).props.phase,'checked');
 await act(async()=>{view.unmount();});
 const draftKey=answerDraftKey({contextId:'a',studentId:'s'},'session');
 writeAnswerDraft(storage,draftKey,'q',1,{answer:'y',visual:[1],evidence:[0]});
 assert.equal(readAnswerDraft(storage,draftKey,'q',1)?.answer,'y');
 assert.equal(readAnswerDraft(storage,draftKey,'q',2),null,'new server revisions reject old local draft');
 assert.equal(readAnswerDraft(storage,draftKey,'other-question',1),null);
 assert.equal(readAnswerDraft(storage,answerDraftKey({contextId:'b',studentId:'s'},'session'),'q',1),null);
 assert.equal(readAnswerDraft({getItem(){throw Error('blocked');},setItem(){},removeItem(){}},draftKey,'q',1),null);
 // Toast lifecycle and confirmed wardrobe state use the actual components.
 let expiry:(()=>void)|undefined;let cleared=0;
 Object.assign(win,{setTimeout:(fn:()=>void)=>{expiry=fn;return 1;},clearTimeout:()=>{cleared++;}});
 await act(async()=>{view=TestRenderer.create(<FloatingNotice message="操作已同步"/>);});
 assert.equal(view.root.findAllByProps({className:'forest-floating-notice'}).length,1);
 await act(async()=>{expiry!();});assert.equal(view.toJSON(),null,'toast dismisses itself');
 await act(async()=>{view.update(<FloatingNotice message="装扮已穿上"/>);});
 assert.ok(view.toJSON(),'new message is shown again');
 await act(async()=>{view.update(<FloatingNotice message="还没同步" duration={0}><button>重新保存</button></FloatingNotice>);});
 assert.equal(view.root.findAllByProps({'aria-label':'关闭提示'}).length,0,'unresolved recovery cannot be dismissed');
 assert.equal(view.root.findAllByType('button').length,1);
 await act(async()=>{view.unmount();});assert.ok(cleared);
 Object.assign(win,{setTimeout,clearTimeout});
 const wardrobeState:any={xp:190,gems:134,hearts:5,completedLessons:{},ownedCosmetics:{skin_default:true,skin_graduate:true,theme_default:true,backdrop_default:true},equippedMascotSkin:'skin_graduate',equippedTheme:'theme_default',equippedBackdrop:'backdrop_default'};
 assert.equal(isEquippedCosmetic('skin_graduate',wardrobeState),true);
 assert.equal(isEquippedCosmetic('skin_default',wardrobeState),false);
 assert.equal(isEquippedCosmetic('theme_default',wardrobeState),true);
 assert.equal(isEquippedCosmetic('backdrop_default',wardrobeState),true);
 assert.equal(isEquippedCosmetic('unknown',wardrobeState),false);
 let equipReply!: (r:Response)=>void;let equipWrites=0;
 Object.assign(globalThis,{fetch:async(path:string,options:RequestInit={})=>{
  if(path==='/api/v1/auth/session')return response(first);
  if(path.endsWith('/profile'))return new Response(JSON.stringify({id:first.student_id,nickname:'孩子A',grade:1}));
  if(path.endsWith('/me/avatar'))return new Response(JSON.stringify({scope_kind:'student',subject_id:first.student_id,avatar_id:'panda',revision:1,catalog_version:'test'}));
  if(path.endsWith('/progress'))return new Response(JSON.stringify({student_id:first.student_id,revision:1,state:wardrobeState,quests:[]}));
  if(path.endsWith('/learning/shop'))return new Response(JSON.stringify({items:[{id:'skin_default',name:'原版聪聪',cost:0},{id:'skin_graduate',name:'学士帽',cost:80},{id:'theme_default',name:'默认主题',cost:0},{id:'backdrop_default',name:'默认背景',cost:0}]}));
  if(path.endsWith('/economy/actions')){equipWrites++;return new Promise<Response>(resolve=>{equipReply=resolve;});}
  throw Error('Unexpected wardrobe request '+path);
 }});
 const wardrobeTree=<AppRouterContext.Provider value={router as any}><PathnameContext.Provider value="/profile/"><CloudChildBoundary><CloudEconomy/></CloudChildBoundary></PathnameContext.Provider></AppRouterContext.Provider>;
 await act(async()=>{view=TestRenderer.create(wardrobeTree);});
 const equipButton=(name:string)=>view.root.findAllByType('article').find(a=>a.findByType('strong').props.children===name)!.findByType('button');
 assert.equal(equipButton('学士帽').props.children,'已穿上');assert.equal(equipButton('学士帽').props.disabled,true);
 assert.equal(equipButton('原版聪聪').props.children,'穿上');
 await act(async()=>{equipButton('原版聪聪').props.onClick();});
 assert.equal(equipButton('原版聪聪').props.children,'穿上中…');
 assert.equal(equipWrites,1);
 assert.equal(equipButton('学士帽').props['aria-pressed'],true,'keep confirmed equipment until the response');
 await act(async()=>{equipReply(new Response(JSON.stringify({result:{applied:true},progress:{student_id:first.student_id,revision:2,state:{...wardrobeState,equippedMascotSkin:'skin_default'},quests:[]}})));});
 assert.equal(equipButton('原版聪聪').props.children,'已穿上');assert.equal(equipButton('原版聪聪').props.disabled,true);
 assert.equal(equipButton('学士帽').props.children,'穿上');
 assert.equal(equipButton('默认主题').props.children,'已穿上');assert.equal(equipButton('默认背景').props.children,'已穿上');
 assert.equal(view.root.findAllByProps({className:'account-message'}).length,0,'confirmation never inserts a flow message');
 assert.equal(view.root.findAllByProps({className:'forest-floating-notice'}).length,1);
 await act(async()=>{view.unmount();});
 console.log('PASS floating feedback: auto-dismiss/reappearance/cleanup; wardrobe confirmed slots, pending item, disabled equipped buttons and no inline confirmation.');
 console.log('PASS input drafts: zero typing network writes, unlocked continuous input, same-tab recovery, explicit-exit checkpoint, revision/question/identity isolation and unavailable storage.');
 console.log('PASS subject switching: four visible subjects, authorized configured textbooks, no child textbook select, late-response isolation, selection memory and read-only switching.');
 console.log('PASS persistent account shell: one initial login read, four route changes keep frame/client/pending, silent focus check, role mismatch blocked, cross-tab identity invalidation and expiry revoke old data.');
}
main().catch(error=>{console.error(error);process.exit(1);});
