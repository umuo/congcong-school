import { subjectChoices, availableSubjectBook } from "../../apps/web/src/lib/learning/subjects";
import { clickFeedback } from "../../apps/web/src/lib/learning/interaction-feedback";
import { orderBookItems } from "../../apps/web/src/lib/learning/book-labels";
import assert from "node:assert/strict";
import { nextActivity, activityTitle, type CourseItem } from "../../apps/web/src/lib/learning/next-activity";
import { bindPreferences, getAudioPreferences, setAudioPreferences, preferencesPersisted } from "../../apps/web/src/lib/learning/preferences";
import { setMuted, setEffectsMuted, suppressEffects, playSfx } from "../../apps/web/src/lib/sfx";
import { CloudLearningClient } from "../../apps/web/src/lib/learning/client";

async function main() {
const curriculum = [
 {subject_code:"math",book_id:"g1up-2026",enabled:true},
 {subject_code:"chinese",book_id:"chinese-g1up",enabled:true},
 {subject_code:"english",book_id:"english-g3up",enabled:false},
 {subject_code:"science",book_id:null,enabled:true},
];
assert.deepEqual(subjectChoices(curriculum).map(s=>[s.label,s.bookId]),[["语文","chinese-g1up"],["数学","g1up-2026"],["英语",null],["科学",null]]);
assert.equal(availableSubjectBook(curriculum,"g1up-2026"),"g1up-2026");
assert.equal(availableSubjectBook(curriculum,"forbidden-book","chinese-g1up"),"chinese-g1up");
assert.equal(availableSubjectBook(curriculum,"english-g3up"),"chinese-g1up");
assert.equal(availableSubjectBook([],"g1up-2026"),"");
let clicks=0;
const control={matches:()=>false,closest:()=>null};
const target={closest:()=>control} as unknown as Element;
const intent=new Event("click");
clickFeedback(intent,target,false,()=>{clicks++;}); clickFeedback(intent,target,false,()=>{clicks++;});assert.equal(clicks,1);
clickFeedback(new Event("click"),target,true,()=>{clicks++;});assert.equal(clicks,1);
const disabled={closest:()=>({...control,matches:()=>true})} as unknown as Element;
clickFeedback(new Event("click"),disabled,false,()=>{clicks++;});assert.equal(clicks,1);
const ownsFeedback={closest:()=>({...control,closest:()=>({})})} as unknown as Element;
clickFeedback(new Event("click"),ownsFeedback,false,()=>{clicks++;});assert.equal(clicks,1);
assert.doesNotThrow(()=>clickFeedback(new Event("click"),target,false,()=>{throw Error("no audio");}));
assert.deepEqual(orderBookItems("chinese-g1up",[{unit_number:5},{unit_number:1},{unit_number:3}]).map(i=>i.unit_number),[1,3,5]);
assert.equal(orderBookItems("g1up-2026",[{unit_number:1},{unit_number:101}])[0].unit_number,101);
const lessons: CourseItem[] = ["first", "second"].map(source_id => ({kind:"lesson",source_id,title:source_id,unit_number:1,question_count:3}));
const active = {id:"original-session",kind:"reading",book_id:"math",source_id:"reading-a",created_at:"2026-11-02"};

assert.equal(activityTitle('review'),'复习练习');
assert.equal(activityTitle('challenge'),'单元挑战');
assert.equal(activityTitle('reading'),'听读练习');
assert.equal(activityTitle('number_review'),'数感练习');
assert.equal(activityTitle(undefined),'上次的练习');
assert.equal(nextActivity('math',lessons,{},[{...active,source_id:'first'}]).item,undefined,'a reading session cannot borrow a same-ID lesson title');

assert.equal(nextActivity("math",lessons,{},[active]).type,"resume");
assert.deepEqual(nextActivity("math",lessons,{},[active]),{type:"resume",id:"original-session",item:undefined});
assert.deepEqual(nextActivity("math",lessons,{first:true},[{...active,book_id:"other"}]),{type:"lesson",item:lessons[1]});
assert.deepEqual(nextActivity("math",lessons,{first:true,second:true},[]),{type:"review"});
const saved = new Map<string,string>();
const storage = {getItem:(key:string)=>saved.get(key)??null,setItem:(key:string,value:string)=>{saved.set(key,value);}};
bindPreferences("student:a",storage);setAudioPreferences({muted:true,autoNarrate:true,reducedMotion:true});
bindPreferences("student:b",storage);assert.equal(getAudioPreferences().muted,false);
setAudioPreferences({muted:false,autoNarrate:false});
bindPreferences("student:a",storage);assert.deepEqual(getAudioPreferences(),{muted:true,autoNarrate:true,reducedMotion:true});
bindPreferences("user:parent",storage);assert.equal(getAudioPreferences().muted,false);
bindPreferences("student:b",storage);assert.equal(getAudioPreferences().autoNarrate,false);
assert.deepEqual([...saved.keys()].sort(),["csf-preferences-v1:student:a","csf-preferences-v1:student:b"]);
setMuted(true);bindPreferences("student:legacy",storage);assert.equal(getAudioPreferences().muted,true);assert.equal(getAudioPreferences().autoNarrate,false);setMuted(false);
bindPreferences("student:restricted",{getItem(){throw Error("blocked");},setItem(){throw Error("blocked");}});
setAudioPreferences({muted:true,autoNarrate:false});assert.equal(preferencesPersisted(),false);assert.equal(getAudioPreferences().muted,true);
// Audio-free environments and overlapping owners must always remain operable.
const releaseA=suppressEffects(), releaseB=suppressEffects();playSfx("tap");releaseA();playSfx("complete");releaseB();
// Exercise the real synthesizer gate with a deterministic audio-capable device.
let starts=0;
const parameter=()=>({value:0,setValueAtTime(){},linearRampToValueAtTime(){},exponentialRampToValueAtTime(){}});
const node=()=>({gain:parameter(),frequency:parameter(),Q:parameter(),threshold:parameter(),knee:parameter(),ratio:parameter(),attack:parameter(),release:parameter(),delayTime:parameter(),connect(){},start(){starts++;},stop(){}});
class AudioDevice {
 state="running";currentTime=0;destination={};
 createGain=node;createBiquadFilter=node;createDynamicsCompressor=node;createDelay=node;createOscillator=node;createBufferSource=node;
 createBuffer(_channels:number,length:number){return {getChannelData:()=>new Float32Array(length)};}
 sampleRate=8000;
 resume(){this.state="running";return Promise.resolve();}
 suspend(){this.state="suspended";return Promise.resolve();}
}
const previousWindow=Object.getOwnPropertyDescriptor(globalThis,"window");
Object.defineProperty(globalThis,"window",{value:{AudioContext:AudioDevice},configurable:true});
setMuted(false);setEffectsMuted(false);
const speech=suppressEffects(), recording=suppressEffects();
playSfx("tap");assert.equal(starts,0);
speech();playSfx("complete");assert.equal(starts,0);
recording();playSfx("tap");assert.ok(starts>0);
const beforeMute=starts;setEffectsMuted(true);playSfx("tap");assert.equal(starts,beforeMute);
setEffectsMuted(false);setMuted(true);playSfx("tap");assert.equal(starts,beforeMute);setMuted(false);
if(previousWindow)Object.defineProperty(globalThis,"window",previousWindow);else Reflect.deleteProperty(globalThis,"window");
const calls: {path:string; method:string}[]=[];
const account={context_id:"context",student_id:"a",mode:"child" as const,must_change_password:false};
const transport: NonNullable<ConstructorParameters<typeof CloudLearningClient>[1]> = async <T>(path:string,options?:RequestInit) => {
  calls.push({path,method:options?.method ?? "GET"});
  return (path==="/auth/session" ? account : [active]) as T;
};
const client=new CloudLearningClient(account,transport);
await client.getActiveSessions({book_id:"math"});
assert.ok(calls.some(c=>c.path.endsWith("learning-sessions?book_id=math")));
assert.ok(calls.every(c=>c.method==="GET"));
assert.deepEqual(client.projection.getSnapshot().pending,[]);
client.dispose(false);
console.log("PASS forest: original-session selection, first unfinished/review, read-only queries, independent scoped preferences, restricted storage and legacy mute.");

}
main().catch(error=>{console.error(error);process.exitCode=1;});
