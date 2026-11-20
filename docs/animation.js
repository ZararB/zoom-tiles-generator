import {canvas,ctx,C,clamp,ease,mix,text,line,path,rounded,label,projection,corners,tile,grid,arc} from './animation-art.js';
const W=1600,H=1000,DURATION=36;
function base(t,chapter){ctx.clearRect(0,0,W,H);ctx.fillStyle=C.bg;ctx.fillRect(0,0,W,H);const grad=ctx.createRadialGradient(850,570,10,850,570,800);grad.addColorStop(0,'#4d241088');grad.addColorStop(1,'#00000000');ctx.fillStyle=grad;ctx.fillRect(0,0,W,H);
 for(let i=-8;i<14;i++){line([800+i*90,290],[80+i*90,920],'#d4d4d40b');line([800+i*90,290],[1520+i*90,920],'#d4d4d40b')}
 text('Don’t just make a map.',80,95,57,C.ink,500);text('Make every level.',80,164,57,C.orange,500);
 text('ZOOM TILES',1518,76,16,C.secondary,500,'right');text('GENERATOR',1518,101,16,C.secondary,500,'right');
 text(['01 / TILES WITHIN TILES','02 / CONTEXT BECOMES DETAIL','03 / ONE WORLD, EVERY LEVEL'][Math.min(chapter,2)],84,235,16,C.muted,500);
 line([80,948],[1520,948],C.line);ctx.fillStyle=C.orange;ctx.fillRect(80,947,1440*clamp(t/DURATION),2);text('CONCEPT ANIMATION · ORIGINAL ILLUSTRATIVE MAP',80,980,11,C.muted);text('GENERATE EVERY LEVEL',1520,980,11,C.secondary,500,'right')}
function structure(t){
 const view={x:800,y:330,s:610};let n=t<3?1:t<6?2:4;const transition=t<3?ease(t/.8):t<6?ease((t-3)/.9):ease((t-6)/.9);
 const gap=(n===1?0:22)*transition,raise=22+Math.sin(t*.65)*4;
 // Briefly retain the previous plane while the child grid opens.
 if(n>1&&transition<1)grid(view,n/2,n===2?0:1,{raise,alpha:1-transition});
 grid(view,n,n===1?0:n===2?1:2,{gap,raise,alpha:n===1?1:transition,wave:n===4?4:0,highlight:t>7?[2,1]:null});
 label('ONE MAP',85,340);text(`${n*n}`,85,400,50,C.orange,500);text(n===1?'parent tile':'aligned tiles',85,430,18,C.muted);text('1 → 4 → 16 → …',85,475,18,C.secondary);
 text('Same geography.',1285,750,20,C.ink,500);text('Finer divisions.',1285,780,20,C.muted);text('More room for detail.',1285,810,20,C.muted);
}
function context(t){
 const view={x:800,y:355,s:530},p=ease((t-3.5)/2.8),center=projection(view,.5,.5,28);const cells=[];
 for(let y=0;y<3;y++)for(let x=0;x<3;x++)cells.push({x,y});cells.sort((a,b)=>a.x+a.y-b.x-b.y);
 for(const {x,y}of cells){if(x===1&&y===1){tile(view,[x/3,y/3,1/3,1/3],0,{raise:28,reveal:0,gap:16});continue}tile(view,[x/3,y/3,1/3,1/3],2,{raise:28,gap:16});}
 if(t<7.5){for(const {x,y}of cells){if(x===1&&y===1)continue;arc(projection(view,(x+.5)/3,(y+.5)/3,35),[center[0],center[1]-35],(t*.3+(x+y)*.12)%1)}}
 if(p>0){tile(view,[1/3,1/3,1/3,1/3],2,{raise:28+(1-p)*165,outline:C.orange,reveal:p,alpha:Math.min(1,p*2)});}
 label('SURROUNDING TILES',83,345,C.secondary);text('Roads',83,388,22);text('Rivers',83,423,22);text('Terrain + style',83,458,22);
 const infoX=1260;label('PLACE RESEARCH',infoX,335,C.secondary);text('What belongs here?',infoX,370,19);label('USER DIRECTION',infoX,435,C.orange);text('“More gardens.”',infoX,470,19);
 if(t<7.5){arc([infoX-18,367],[center[0]+30,center[1]-110],t*.24,C.secondary);arc([infoX-18,467],[center[0]+30,center[1]-75],t*.26,C.orange)}
 const captions=t<3.5?['Read the neighborhood.','Carry the boundaries forward.']:p<1?['Infer a plausible next tile.','Context + constraints + user intent.']:['New detail, grounded in context.','A draft to validate and save.'];
 text(captions[0],800,870,25,C.ink,500,'center');text(captions[1],800,905,19,C.muted,400,'center');
}
function continuity(t){
 const move=ease(t/2),v0={x:520,y:535,s:350},v1={x:870,y:395-30*move,s:310},v2={x:1195,y:320-50*move,s:235};
 const w0=[0,0,1,1],w1=[.34,.3,.38,.38],w2=[.48,.42,.10,.10];
 grid(v0,4,0,{world:w0,raise:0,gap:5});
 const selected0=[.34,.3,.38,.38],p0=corners(v0,selected0);path(ctx,p0);ctx.strokeStyle=C.orange;ctx.lineWidth=3;ctx.stroke();
 const dest1=corners(v1,[0,0,1,1]);for(let i=0;i<4;i++)line(p0[i],dest1[i],C.orange+'70',1,[5,7]);
 grid(v1,2,1,{world:w1,raise:0,gap:9,alpha:move});
 const selected1=[(.48-.34)/.38,(.42-.3)/.38,.10/.38,.10/.38],p1=corners(v1,selected1);
 if(move>.8){path(ctx,p1);ctx.strokeStyle=C.orange;ctx.lineWidth=2;ctx.stroke();const dest2=corners(v2,[0,0,1,1]);for(let i=0;i<4;i++)line(p1[i],dest2[i],C.orange+'70',1,[5,7]);grid(v2,2,2,{world:w2,alpha:ease((t-1.8)/1.5),gap:12});}
 label('REGION',165,775,C.secondary);text('The world stays connected.',165,811,22);label('SETTLEMENT',760,735,C.secondary);text('Inherited roads and terrain.',760,770,20);label('STREET DETAIL',1210,615,C.orange);text('New plausible geometry.',1210,650,19);
 text('One saved world. More detail at every scale.',800,890,26,C.ink,500,'center');text('Shared geometry is the intended continuity layer — still in development.',800,922,17,C.muted,400,'center');
}
function ending(t){
 ctx.fillStyle=C.bg;ctx.fillRect(0,0,W,H);const v={x:800,y:540,s:310};grid(v,4,2,{gap:12,raise:Math.sin(t*.65)*5,alpha:.65});
 text('Don’t just make a map.',800,205,58,C.ink,500,'center');text('Make every level.',800,292,83,C.orange,500,'center');text('A world that keeps revealing itself.',800,355,25,C.muted,400,'center');
 text('ZOOM TILES GENERATOR',800,875,17,C.secondary,500,'center');text('CONTEXT → GENERATION → A CONSISTENT WORLD',800,914,12,C.muted,400,'center');
}
let seconds=0,playing=!matchMedia('(prefers-reduced-motion: reduce)').matches,last=performance.now(),chapter=-1,recording=false,posterSent=false,hierarchyPosterSent=false,recordStart=0;
const el=id=>document.getElementById(id),captions=['One map becomes a hierarchy. Each tile can divide into four children.','Neighboring tiles, place research and user direction inform a new tile.','Accepted detail belongs to the same saved world, so zoom levels agree.','Don’t just make a map. Make every level.'];
function render(t){const next=Math.min(3,Math.floor(t/10));base(t,next);if(next===0)structure(t);else if(next===1)context(t-10);else if(next===2)continuity(t-20);else ending(t-30);if(next!==chapter){chapter=next;el('caption').textContent=captions[next];document.querySelectorAll('[data-start]').forEach(b=>b.setAttribute('aria-pressed',Number(b.dataset.start)===Math.min(next,2)*10?'true':'false'))}el('position').value=t;el('clock').textContent=`00:${String(Math.floor(t)).padStart(2,'0')} / 00:36`;canvas.dataset.scene=String(next);canvas.dataset.time=t.toFixed(2)}
function syncPlay(){el('play').textContent=playing?'Pause':'Play';el('play').setAttribute('aria-label',playing?'Pause animation':'Play animation')}
el('play').onclick=()=>{if(seconds>=DURATION)seconds=0;playing=!playing;syncPlay()};
el('replay').onclick=()=>{seconds=0;playing=true;syncPlay()};el('position').oninput=()=>{seconds=Number(el('position').value);playing=false;syncPlay();render(seconds)};
document.querySelectorAll('[data-start]').forEach(b=>b.onclick=()=>{seconds=Number(b.dataset.start);playing=true;syncPlay();render(seconds)});
async function save(blob,name){const r=await fetch('/api/animation-export/'+name,{method:'POST',body:blob});if(!r.ok)throw Error('Start scripts/serve_animation.py to save exports.');return r.json()}
el('record').onclick=async()=>{
 if(recording)return;const button=el('record');button.disabled=true;
 try{if(!canvas.captureStream||!window.MediaRecorder)throw Error('This browser does not support canvas video recording.');
 const type=['video/webm;codecs=vp9','video/webm;codecs=vp8','video/webm'].find(t=>MediaRecorder.isTypeSupported(t));if(!type)throw Error('WebM recording unavailable.');
 const stream=canvas.captureStream(30),recorder=new MediaRecorder(stream,{mimeType:type,videoBitsPerSecond:6500000}),chunks=[];
 recording=true;posterSent=false;hierarchyPosterSent=false;recordStart=performance.now();seconds=0;playing=true;document.querySelectorAll('#play,#replay,#position,[data-start]').forEach(e=>e.disabled=true);syncPlay();el('export-status').textContent='Recording the complete 36-second animation…';
 recorder.ondataavailable=e=>{if(e.data.size)chunks.push(e.data)};
 recorder.onstop=async()=>{stream.getTracks().forEach(t=>t.stop());recording=false;document.querySelectorAll('#play,#replay,#position,[data-start]').forEach(e=>e.disabled=false);try{await save(new Blob(chunks,{type}),'make-every-level.webm');el('export-status').textContent='Saved: .runtime/animations/make-every-level.webm';}catch(error){el('export-status').textContent=error.message}button.disabled=false};
 recorder.start(1000);window.setTimeout(()=>{if(recorder.state==='recording')recorder.stop()},(DURATION+.15)*1000);
 }catch(error){recording=false;button.disabled=false;el('export-status').textContent=error.message}
};
function frame(now){const delta=Math.min((now-last)/1000,.1);last=now;if(playing){seconds=recording?Math.min(DURATION,(now-recordStart)/1000):Math.min(DURATION,seconds+delta);if(seconds===DURATION){playing=false;syncPlay()}}render(seconds);
 if(recording&&!posterSent&&seconds>17){posterSent=true;canvas.toBlob(blob=>{if(blob)save(blob,'context-generation-poster.png').catch(()=>{})},'image/png')}
 if(recording&&!hierarchyPosterSent&&seconds>25){hierarchyPosterSent=true;canvas.toBlob(blob=>{if(blob)save(blob,'hierarchy-poster.png').catch(()=>{})},'image/png')}
 requestAnimationFrame(frame)}syncPlay();render(0);requestAnimationFrame(frame);
