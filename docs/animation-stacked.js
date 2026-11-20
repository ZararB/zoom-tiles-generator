import {canvas,ctx,C,clamp,ease,text,line,path,projection,corners,tile,grid,arc} from './animation-art.js';
const DURATION=36,W=1920,H=1080,X=92;
// All planes have the same x, scale and inclination. Only their source crop differs.
const levels=[
 {name:'REGION',description:'The original geography.',world:[0,0,1,1],detail:0,y:780},
 {name:'SETTLEMENT',description:'Roads, rivers, neighborhoods.',world:[.32,.28,.4,.4],detail:1,y:565},
 {name:'STREET',description:'Lanes, buildings, gardens.',world:[.46,.38,.17,.17],detail:2,y:350},
 {name:'PARCEL',description:'Finer detail, same world.',world:[.50,.425,.07,.07],detail:2,y:135}
];
const views=levels.map(level=>({x:1310,y:level.y,s:490,tilt:.165}));
const el=id=>document.getElementById(id);
const preview=new URLSearchParams(location.search),start=Number(preview.get('t'));
let seconds=Number.isFinite(start)?clamp(start,0,DURATION):0,playing=!preview.has('paused')&&!matchMedia('(prefers-reduced-motion: reduce)').matches,last=performance.now(),chapter=-1,recording=false,recordStart=0,contextPoster=false,hierarchyPoster=false,renderedTime=-1;

function childBounds(index){const p=levels[index].world,c=levels[index+1].world;return[(c[0]-p[0])/p[2],(c[1]-p[1])/p[3],c[2]/p[2],c[3]/p[3]]}
function links(index,active,t){
 const a=corners(views[index],childBounds(index)),b=corners(views[index+1],[0,0,1,1]);
 const color=active?C.orange:C.secondary,width=active?6:4.5,dots=[2,10];
 ctx.save();ctx.lineCap='round';
 for(let i=0;i<4;i++){
  // A dark underlay keeps the dots legible as they cross terrain and other rays.
  line(a[i],b[i],C.bg,width+4,dots);
  ctx.shadowColor=active?C.orange+'a0':C.secondary+'60';ctx.shadowBlur=active?9:5;
  line(a[i],b[i],color,width,dots);ctx.shadowBlur=0;
  for(const point of [a[i],b[i]]){ctx.beginPath();ctx.arc(...point,active?6.5:5,0,Math.PI*2);ctx.fillStyle=color;ctx.fill()}
 }
 if(active){for(let i=0;i<4;i++){const p=(t*.3+i*.25)%1;ctx.beginPath();ctx.arc(a[i][0]+(b[i][0]-a[i][0])*p,a[i][1]+(b[i][1]-a[i][1])*p,6,0,Math.PI*2);ctx.fillStyle=C.orange;ctx.fill()}}
 path(ctx,a);ctx.strokeStyle=active?C.orange:C.secondary+'bb';ctx.lineWidth=active?3.5:2.2;ctx.stroke();ctx.restore();
}
function scene(t){
 const part=t<10?0:t<20?1:t<30?2:3,local=t%10,active=part===2?Math.min(3,Math.floor(local/2.4)):part===1?2:part===3?3:-1;
 ctx.fillStyle=C.bg;ctx.fillRect(0,0,W,H);
 const glow=ctx.createRadialGradient(1320,520,10,1320,520,820);glow.addColorStop(0,'#4d241085');glow.addColorStop(1,'#00000000');ctx.fillStyle=glow;ctx.fillRect(700,0,1220,H);
 line([714,75],[714,1000],C.line);
 // A quiet axis reinforces the unchanged horizontal alignment of every level.
 line([1310,110],[1310,1005],C.secondary+'18',1,[4,12]);
 for(let i=0;i<4;i++){
  const n=part===0?(t<2.8?1:t<5.6?2:4):4,alpha=part===0?.6+.4*ease(t/1.5-i*.12):1;
  if(i===2&&part===1){
   const v=views[i],p=ease((local-3.2)/3.2),cells=[];for(let y=0;y<3;y++)for(let x=0;x<3;x++)cells.push({x,y});cells.sort((a,b)=>a.x+a.y-b.x-b.y);
   for(const {x,y}of cells)tile(v,[x/3,y/3,1/3,1/3],2,{world:levels[i].world,gap:8,reveal:x===1&&y===1?0:1});
   const target=projection(v,.5,.5,0);
   if(local<7.3){for(const {x,y}of cells){if(x===1&&y===1)continue;arc(projection(v,(x+.5)/3,(y+.5)/3,0),[target[0],target[1]-18],(local*.32+(x+y)*.12)%1)}arc([600,586],[target[0]-20,target[1]-42],local*.22,C.orange);arc(projection(views[1],.55,.47,0),[target[0]+20,target[1]-24],local*.25,C.secondary)}
   if(p>0)tile(v,[1/3,1/3,1/3,1/3],2,{world:levels[i].world,raise:(1-p)*115,outline:C.orange,reveal:p,alpha:Math.min(1,p*2)});
  }else grid(views[i],n,levels[i].detail,{world:levels[i].world,gap:part===0?ease((t-2.8)/.7)*8:8,alpha});
  if(active===i){path(ctx,corners(views[i],[0,0,1,1]));ctx.strokeStyle=C.orange+'b0';ctx.lineWidth=2;ctx.stroke()}
 }
 // Keep each connection visible above all of the map planes it crosses.
 for(let i=0;i<3;i++)links(i,part===2&&active===i+1,t);
 // Every visible word belongs to this one left-hand column.
 text('ZOOM TILES GENERATOR',X,67,22,C.secondary,500);
 text('Don’t just',X,155,62,C.ink,500);text('make a map.',X,229,62,C.ink,500);text('Make every level.',X,319,60,C.orange,500);
 text('A connected world.',X,373,25,C.muted);text('At every scale.',X,410,25,C.muted);
 const copy=part===0?['01 / HIERARCHY','Tiles within tiles.','One parent. Four children.','Different zooms. One aligned stack.']:part===1?['02 / CONTEXT','Generate the next tile.',local<6.4?'Read the surrounding tiles.':'New detail settles into the grid.',local<6.4?'Research + “More gardens.”':'Validate it. Save it. Reuse it.']:part===2?['03 / CONTINUITY','Zoom into the same world.','Carry geometry between levels.','Let new detail inherit its context.']:['GENERATE EVERY LEVEL','A world that reveals itself.','From region to settlement.','From street to the next possibility.'];
 text(copy[0],X,495,22,C.orange,500);text(copy[1],X,543,32,C.ink,500);text(copy[2],X,585,25,C.muted);text(copy[3],X,624,25,C.muted);
 if(part===1)text('NEIGHBORS + PARENT + YOUR BRIEF',X,667,21,C.secondary,500);
 if(part===3)text('Explore the chapters below.',X,667,24,C.secondary,500);
 for(let row=0;row<4;row++){const i=3-row,y=727+row*64,isActive=i===active;ctx.fillStyle=isActive?C.orange:C.secondary+'bb';ctx.fillRect(X,y-18,7,38);text(`0${i}`,X+24,y,22,isActive?C.orange:C.muted,500);text(levels[i].name,X+80,y,23,isActive?C.orange:C.ink,600);text(levels[i].description,X+80,y+27,22,C.muted)}
 line([X,1008],[650,1008],C.line);ctx.fillStyle=C.orange;ctx.fillRect(X,1007,558*clamp(t/DURATION),2);text('CONCEPT / SHARED GEOMETRY IN DEVELOPMENT',X,1040,20,C.muted);
 return part;
}
const captions=['Four map levels share one horizontal alignment, stacked vertically from region to parcel detail.','The missing street tile uses its neighbors, parent, research and user direction as context.','The same world persists as each increasingly detailed level is highlighted.','Don’t just make a map. Make every level.'];
function render(t){renderedTime=t;const part=scene(t);if(part!==chapter){chapter=part;el('caption').textContent=captions[part];document.querySelectorAll('[data-start]').forEach(b=>b.setAttribute('aria-pressed',Number(b.dataset.start)===part*10?'true':'false'))}const active=part===2?Math.min(3,Math.floor((t%10)/2.4)):part===1?2:part===3?3:-1;document.querySelectorAll('[data-level]').forEach(row=>{const selected=Number(row.dataset.level)===active;row.classList.toggle('active',selected);if(selected)row.setAttribute('aria-current','true');else row.removeAttribute('aria-current')});el('position').value=t;el('clock').textContent=`00:${String(Math.floor(t)).padStart(2,'0')} / 00:36`;canvas.dataset.scene=part;canvas.dataset.time=t.toFixed(2)}
function sync(){el('play').textContent=playing?'Pause':'Play';el('play').setAttribute('aria-label',playing?'Pause animation':'Play animation')}
el('play').onclick=()=>{if(seconds>=DURATION)seconds=0;playing=!playing;sync()};el('replay').onclick=()=>{seconds=0;playing=true;sync()};el('position').oninput=()=>{seconds=Number(el('position').value);playing=false;sync();render(seconds)};
document.querySelectorAll('[data-start]').forEach(b=>b.onclick=()=>{seconds=Number(b.dataset.start);playing=true;sync();render(seconds)});
async function save(blob,name){const response=await fetch('/api/animation-export/'+name,{method:'POST',body:blob});if(!response.ok)throw Error('Run the updated animation preview server to save this variation.');return response.json()}
el('record').onclick=()=>{if(recording)return;const button=el('record');button.disabled=true;try{
 const type=['video/webm;codecs=vp9','video/webm;codecs=vp8','video/webm'].find(t=>MediaRecorder.isTypeSupported(t));if(!type)throw Error('WebM recording is not supported.');
 const stream=canvas.captureStream(30),recorder=new MediaRecorder(stream,{mimeType:type,videoBitsPerSecond:6500000}),chunks=[];
 recording=true;contextPoster=false;hierarchyPoster=false;recordStart=performance.now();seconds=0;playing=true;sync();document.querySelectorAll('#play,#replay,#position,[data-start]').forEach(e=>e.disabled=true);el('export-status').textContent='Recording the aligned stack variation…';
 recorder.ondataavailable=e=>{if(e.data.size)chunks.push(e.data)};recorder.onstop=async()=>{stream.getTracks().forEach(t=>t.stop());recording=false;document.querySelectorAll('#play,#replay,#position,[data-start]').forEach(e=>e.disabled=false);try{await save(new Blob(chunks,{type}),'stacked-every-level.webm');el('export-status').textContent='Saved: .runtime/animations/stacked-every-level.webm'}catch(error){el('export-status').textContent=error.message}button.disabled=false};recorder.start(1000);setTimeout(()=>{if(recorder.state==='recording')recorder.stop()},36150);
 }catch(error){recording=false;button.disabled=false;el('export-status').textContent=error.message}};
function frame(now){const delta=Math.min((now-last)/1000,.1);last=now;if(playing){seconds=recording?Math.min(DURATION,(now-recordStart)/1000):Math.min(DURATION,seconds+delta);if(seconds===DURATION){playing=false;sync()}}if(seconds!==renderedTime)render(seconds);if(recording&&!contextPoster&&seconds>17){contextPoster=true;canvas.toBlob(blob=>{if(blob)save(blob,'stacked-context-poster.png').catch(()=>{})},'image/png')}if(recording&&!hierarchyPoster&&seconds>25){hierarchyPoster=true;canvas.toBlob(blob=>{if(blob)save(blob,'stacked-hierarchy-poster.png').catch(()=>{})},'image/png')}requestAnimationFrame(frame)}sync();render(seconds);requestAnimationFrame(frame);
