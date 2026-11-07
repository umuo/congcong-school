import catalog from './catalog.json';
export const presets = catalog.presets;
export const defaultAvatar = catalog.default_id;
export function avatarPreset(id?: string | null) {
  return presets.find(p => p.id === id) ?? presets.find(p => p.id === defaultAvatar)!;
}
const palette: Record<string, [string, string, string]> = {
  panda: ['#d9f1e4','#fffdf4','#253846'], fox: ['#ffe4c3','#ea854c','#5b3c34'],
  rabbit: ['#f5e1ef','#fff8f0','#bb7188'], bear: ['#eadfcf','#b88c69','#5b453f'],
  cat: ['#e5e0fb','#b5a3dc','#564d79'], dog: ['#ffedc8','#d8a466','#674c3e'],
  tiger: ['#f9e7c9','#e8a447','#553e32'], lion: ['#f7e5be','#edbf66','#805039'],
  koala: ['#dcebf0','#aabcc7','#526775'], penguin: ['#dceafc','#354e69','#f1b754'],
  owl: ['#ece1ef','#9b819e','#584865'], frog: ['#def0d0','#8cb968','#355b4a'],
  robot: ['#e0e9ff','#819bce','#334d81'], astronaut: ['#dce7f3','#f6f8ff','#436180'],
  star: ['#e9e0fb','#f1c76b','#8c6544'], planet: ['#e1e6fa','#a09bdc','#514c88'],
};
export const painterIds = Object.keys(palette);
/** Normalized 100 × 100 drawing; caller owns DPR and canvas size. */
export function drawAvatar(ctx: CanvasRenderingContext2D, id: string) {
  id = avatarPreset(id).id;
  const [bg, fur, ink] = palette[id];
  const ellipse = (x:number,y:number,rx:number,ry:number,color:string,rotation=0) => {
    ctx.beginPath(); ctx.ellipse(x,y,rx,ry,rotation,0,Math.PI*2); ctx.fillStyle=color; ctx.fill();
  };
  const path = (points:number[][], color:string) => {
    ctx.beginPath(); points.forEach(([x,y],i) => i ? ctx.lineTo(x,y) : ctx.moveTo(x,y));
    ctx.closePath(); ctx.fillStyle=color; ctx.fill();
  };
  const line = (points:number[][], color:string, width=2.5) => {
    ctx.beginPath(); points.forEach(([x,y],i) => i ? ctx.lineTo(x,y) : ctx.moveTo(x,y));
    ctx.strokeStyle=color; ctx.lineWidth=width; ctx.lineCap='round'; ctx.lineJoin='round'; ctx.stroke();
  };
  ctx.clearRect(0,0,100,100);
  ellipse(50,50,50,50,bg);
  // Quiet background dots are shared by all sixteen designs.
  ellipse(16,35,3,3,'#ffffff88'); ellipse(83,22,4,4,'#ffffff88');
  ellipse(53,91,26,5,'#34405412');
  if (id === 'planet') {
    ellipse(50,50,28,28,fur); ellipse(43,41,8,5,'#cec9f2',-.5);
    ellipse(59,64,6,3,'#817cbc');
    ctx.beginPath(); ctx.ellipse(50,54,42,12,-.35,0,Math.PI); ctx.strokeStyle=ink; ctx.lineWidth=6; ctx.stroke();
    ellipse(37,52,2,3,ink); ellipse(54,48,2,3,ink); line([[43,60],[48,61],[52,58]],ink,2);
    return;
  }
  if (id === 'star') {
    path(Array.from({length:10},(_,i) => {const a=i*Math.PI/5-Math.PI/2,r=i%2?19:37;return [50+Math.cos(a)*r,52+Math.sin(a)*r];}),fur);
  } else if (id === 'robot') {
    line([[50,27],[50,17]],ink,3); ellipse(50,15,4,4,'#e8a05e');
    ellipse(19,52,6,10,ink); ellipse(81,52,6,10,ink);
    ctx.fillStyle=fur; ctx.beginPath(); ctx.roundRect(24,29,52,48,13); ctx.fill();
    ctx.fillStyle='#eaf3ff';ctx.beginPath();ctx.roundRect(31,40,38,22,8);ctx.fill();
    ellipse(41,51,3,4,ink);ellipse(59,51,3,4,ink);line([[43,69],[57,69]],ink,3); return;
  } else if (id === 'astronaut') {
    ellipse(50,50,35,35,fur); ellipse(50,48,27,26,ink);
    ellipse(43,40,17,15,'#7b9bb8');
    ellipse(37,36,5,8,'#d5e5ef',.5); ellipse(61,56,5,3,'#9bb9ce');
    ctx.fillStyle='#c2d3e6';ctx.fillRect(37,78,26,8); ellipse(50,82,5,2,'#7d9bb6'); return;
  } else {
    if (id === 'lion') for(let i=0;i<12;i++){const a=i*Math.PI/6;ellipse(50+Math.cos(a)*27,51+Math.sin(a)*27,12,13,ink);}
    if (['cat','fox','tiger'].includes(id)) {
      path([[23,42],[24,14],[43,33]],fur);path([[57,33],[76,14],[77,42]],fur);
      path([[27,31],[28,21],[36,32]],'#e7b6a4');path([[64,32],[72,21],[73,31]],'#e7b6a4');
    } else if(id==='rabbit') {
      ellipse(36,27,10,24,fur,-.18);ellipse(64,27,10,24,fur,.18);
      ellipse(36,25,4,16,'#e8b8ca',-.18);ellipse(64,25,4,16,'#e8b8ca',.18);
    } else if (id==='dog') {
      ellipse(25,48,12,23,ink,.25);ellipse(75,48,12,23,ink,-.25);
    } else if (['panda','bear','koala'].includes(id)) {
      ellipse(28,31,13,13,id==='panda'?ink:fur);ellipse(72,31,13,13,id==='panda'?ink:fur);
      if(id==='koala'){ellipse(27,31,8,8,'#e2e6e7');ellipse(73,31,8,8,'#e2e6e7');}
    }
    ellipse(50,55,id==='penguin'?29:31,id==='penguin'?35:29,fur);
    if(id==='fox') {path([[20,50],[50,67],[80,50],[68,76],[50,82],[32,76]],'#fff4dc');}
    if(id==='penguin') ellipse(50,62,23,25,'#fff9e9');
    if(id==='owl') {ellipse(37,49,17,20,'#fff4dc');ellipse(63,49,17,20,'#fff4dc');path([[22,36],[21,19],[42,31]],fur);path([[58,31],[79,19],[78,36]],fur);}
    if(id==='frog') {ellipse(31,34,12,13,fur);ellipse(69,34,12,13,fur);}
    if(['bear','dog','cat','lion','tiger'].includes(id)) ellipse(50,65,18,13,'#fff4dc');
    if(id==='panda'){ellipse(36,52,9,11,ink,.4);ellipse(64,52,9,11,ink,-.4);}
    if(id==='dog') ellipse(34,49,9,12,ink,-.2);
    if(id==='tiger') {path([[44,28],[50,44],[56,28]],ink);line([[22,53],[30,57]],ink,3);line([[78,53],[70,57]],ink,3);}
  }
  const eyeY=id==='frog'?36:52;
  ellipse(37,eyeY,3,4,id==='panda'?'#fffaf0':ink);ellipse(63,eyeY,3,4,id==='panda'?'#fffaf0':ink);
  if (id==='koala') ellipse(50,60,7,10,ink);
  else if (['owl','penguin'].includes(id)) path([[45,60],[55,60],[50,67]],'#e1a951');
  else if(id!=='star' && id!=='frog') ellipse(50,63,4,3,ink);
  if(!['owl','penguin'].includes(id)) {
    ctx.beginPath();ctx.arc(50,id==='frog'?54:65,8,.2,Math.PI-.2);ctx.strokeStyle=ink;ctx.lineWidth=2;ctx.stroke();
  }
  ellipse(28,64,5,3,'#e7a2a655');ellipse(72,64,5,3,'#e7a2a655');
}
