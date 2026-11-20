const $=id=>document.getElementById(id),canvas=$('map'),ctx=canvas.getContext('2d');
const client='browser-'+crypto.randomUUID();let world=null,worlds=[],camera={x:2772,y:1258,z:4},width=900,height=700,epoch=0,loadEpoch=0,settleTimer=null,drag=null,dirty=true,activeRequests=0,signature='',lastStatus=null;
$('auto').checked=localStorage.getItem('zoom-world-auto')!=='0';if(localStorage.getItem('zoom-world-layer'))$('layer').value=localStorage.getItem('zoom-world-layer');
const cache=new Map(),pending=new Set(),queue=[],landmarks=[{label:'The Shire',x:2772,y:1258},{label:'Rivendell',x:3922,y:1096},{label:'Minas Tirith',x:4720,y:2641},{label:'Barad-dûr',x:5613,y:2466},{label:'Grey Havens',x:249,y:1094}];
const science='A map of science, organized into fields and subfields, with connections between related ideas.';
const entertainment='A map of media and entertainment, organized into film, television, music, video games, audio, publishing and live entertainment.';
const hasAtlas=world=>world.planner==='curated_demo_outline'&&['science','entertainment'].includes(world.theme);
const history='A map of history, organized around societies, trade, culture, technology and global connections.';
async function api(path,body){const response=await fetch('/api'+path,body===undefined?{cache:'no-store'}:{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});const data=await response.json();if(!response.ok)throw Error(data.error||response.statusText);return data}
function scale(){return 2**(camera.z-world.geometry.native_max_z)}
function directoryZ(){return Math.max(world.geometry.extended_min_z,Math.min(world.geometry.extended_max_z,Math.round(camera.z)))}
function visible(){if(!world)return[];const z=directoryZ(),span=256*2**(world.geometry.native_max_z-z),s=scale(),left=camera.x-width/2/s,top=camera.y-height/2/s,w=Math.ceil(world.geometry.map_width_px/span),h=Math.ceil(world.geometry.map_height_px/span),out=[];
 for(let y=Math.max(0,Math.floor(top/span));y<Math.min(h,Math.ceil((top+height/s)/span));y++)for(let x=Math.max(0,Math.floor(left/span));x<Math.min(w,Math.ceil((left+width/s)/span));x++)out.push({z,x,y,span,px:(x*span-camera.x)*s+width/2,py:(y*span-camera.y)*s+height/2,size:span*s,distance:Math.hypot(x+.5-camera.x/span,y+.5-camera.y/span)});
 return out.sort((a,b)=>a.distance-b.distance).slice(0,80)}
function tileKey(mode,t){return`${world.id}|${mode}|${t.z}/${t.x}/${t.y}`}
function getTile(mode,t){const key=tileKey(mode,t);if(cache.has(key))return cache.get(key);if(!pending.has(key)){pending.add(key);queue.push({key,mode,t,wid:world.id});pump()}return null}
function pump(){while(activeRequests<8&&queue.length){const item=queue.shift();activeRequests++;fetch(`/api/worlds/${item.wid}/tiles/${item.t.z}/${item.t.x}/${item.t.y}.png?mode=${item.mode}`).then(async response=>{if(!response.ok)throw Error('Tile unavailable');const origin=response.headers.get('X-Tile-Origin'),bitmap=await createImageBitmap(await response.blob());cache.set(item.key,{bitmap,origin});while(cache.size>192){const first=cache.keys().next().value;cache.get(first).bitmap.close();cache.delete(first)}dirty=true}).catch(()=>{}).finally(()=>{activeRequests--;pending.delete(item.key);pump()})}}
function drawLayer(mode,tiles,clip){ctx.save();if(clip){ctx.beginPath();ctx.rect(...clip);ctx.clip()}for(const tile of tiles){const loaded=getTile(mode,tile);if(loaded){ctx.drawImage(loaded.bitmap,tile.px,tile.py,tile.size+.5,tile.size+.5);if(loaded.origin==='generated'){ctx.strokeStyle='#f9731660';ctx.lineWidth=1;ctx.strokeRect(tile.px,tile.py,tile.size,tile.size)}}else{ctx.fillStyle='#262626';ctx.fillRect(tile.px,tile.py,tile.size,tile.size)}}ctx.restore()}
function drawAtlasLabels(nodes, scale) {
 const screen = new Map(nodes.map(node => [
  node.id, [(node.x - camera.x) * scale + width / 2, (node.y - camera.y) * scale + height / 2],
 ]));
 ctx.save();
 for (const [parent, child] of world.edges) {
  const a = screen.get(parent), b = screen.get(child);
  if (!a || !b) continue;
  ctx.beginPath(); ctx.moveTo(...a); ctx.lineTo(...b);
  ctx.setLineDash([2, 5]);
  ctx.strokeStyle = parent === 'root' ? '#df935d80' : '#c6967770';
  ctx.lineWidth = 1;
  ctx.stroke();
 }
 ctx.setLineDash([]);
 ctx.textAlign = 'center';
 ctx.textBaseline = 'middle';
 const placed = [];
 for (const node of nodes) {
  const [x, y] = screen.get(node.id);
  if (x < 0 || x > width || y < 0 || y > height) continue;
  const primary = node.depth < 2;
  const fontSize = node.depth === 0 ? 19 : primary ? 15 : 12;
  ctx.font = `${primary ? 650 : 500} ${fontSize}px system-ui`;
  const label = node.label;
  const w = ctx.measureText(label).width + (primary ? 24 : 14), h = fontSize + 10;
  const top = y + (primary ? Math.min(48, 6 + 250 * scale) : 7);
  const left = x - w / 2;
  if (left < 4 || left + w > width - 4 || top + h > height - 4 ||
      placed.some(([l, t, r, b]) => left < r && left + w > l && top < b && top + h > t)) continue;
  placed.push([left, top, left + w, top + h]);
  ctx.beginPath(); ctx.arc(x, y, primary ? 3.5 : 2.5, 0, Math.PI * 2);
  ctx.fillStyle = primary ? '#ffaa6c' : '#bd8b65'; ctx.fill();
  ctx.beginPath(); ctx.roundRect(left, top, w, h, primary ? 6 : 4);
  ctx.fillStyle = primary ? '#1e140df5' : '#1a120de8'; ctx.fill();
  if (primary) { ctx.strokeStyle = '#a26036'; ctx.stroke(); }
  ctx.fillStyle = primary ? '#fff1dd' : '#efcdb4'; ctx.fillText(label, x, top + h / 2);
 }
 ctx.restore();
}
function drawLabels(){const s=scale(),z=directoryZ(),nodes=world.kind==='knowledge'?world.nodes.filter(n=>n.min_z<=z):landmarks,placed=[];
 if(hasAtlas(world)){drawAtlasLabels(nodes,s);return;}
 if(world.kind==='knowledge'){const indexed=new Map(nodes.map(n=>[n.id,n]));for(const [aid,bid]of world.edges){const a=indexed.get(aid),b=indexed.get(bid);if(!a||!b)continue;ctx.beginPath();ctx.moveTo((a.x-camera.x)*s+width/2,(a.y-camera.y)*s+height/2);ctx.lineTo((b.x-camera.x)*s+width/2,(b.y-camera.y)*s+height/2);ctx.strokeStyle='#000000a0';ctx.lineWidth=4;ctx.stroke();ctx.strokeStyle=world.theme==='history'?'#d4d4d4cc':'#595959cc';ctx.lineWidth=1.5;ctx.stroke()}}

 for(const n of nodes){const px=(n.x-camera.x)*s+width/2,py=(n.y-camera.y)*s+height/2;if(px<0||py<0||px>width||py>height)continue;const size=n.depth===0?18:n.depth===1?15:13;ctx.font=`${n.depth<2?600:400} ${size}px system-ui`;const label=n.label.length>42?n.label.slice(0,39)+'…':n.label,tw=ctx.measureText(label).width,b=[px-tw/2-7,py+8,tw+14,size+10];if(b[0]<4||b[1]<4||b[0]+b[2]>width-4||b[1]+b[3]>height-4)continue;if(placed.some(p=>b[0]<p[0]+p[2]&&b[0]+b[2]>p[0]&&b[1]<p[1]+p[3]&&b[1]+b[3]>p[1]))continue;placed.push(b);ctx.fillStyle='#000000e6';ctx.fillRect(...b);ctx.fillStyle='#f97316';ctx.beginPath();ctx.arc(px,py,3,0,Math.PI*2);ctx.fill();ctx.textAlign='center';ctx.fillStyle='#ffffff';ctx.fillText(label,px,py+size+10)}ctx.textAlign='left'}
function draw(){ctx.fillStyle='#0d0d0d';ctx.fillRect(0,0,width,height);if(!world)return;const tiles=visible(),mode=$('layer').value;
 if(mode==='compare'){const split=width*Number($('swipe').value)/100;drawLayer('original',tiles,[0,0,split,height]);drawLayer('blended',tiles,[split,0,width-split,height]);ctx.fillStyle='#f97316';ctx.fillRect(split-1,0,2,height)}else drawLayer(mode,tiles);drawLabels();
 $('zoom').textContent=`Zoom ${camera.z.toFixed(2)} · directory z${directoryZ()}`;
 const generated=tiles.filter(t=>cache.get(tileKey(mode==='compare'?'blended':mode,t))?.origin==='generated').length,inherited=tiles.filter(t=>cache.get(tileKey(mode==='compare'?'blended':mode,t))?.origin==='inherited_parent').length;
 $('map-status').textContent=`${world.title} · ${generated} generated / ${inherited} inherited / ${tiles.length} visible tiles · drag to pan, scroll to zoom`;
 canvas.dataset.world=world.id;canvas.dataset.zoom=camera.z.toFixed(2);canvas.dataset.center=JSON.stringify([Math.round(camera.x),Math.round(camera.y)]);canvas.dataset.generatedVisible=generated;canvas.dataset.layer=mode;canvas.dataset.visibleTiles=tiles.length;canvas.dataset.ready=tiles.every(t=>(mode==='compare'?['original','blended']:[mode]).every(m=>cache.has(tileKey(m,t))))?'true':'false';
}
function frame(){if(dirty){draw();dirty=false}requestAnimationFrame(frame)}requestAnimationFrame(frame);
new ResizeObserver(entries=>{const rect=entries[0].contentRect;width=rect.width;height=rect.height;const dpr=Math.min(devicePixelRatio||1,2);canvas.width=Math.round(width*dpr);canvas.height=Math.round(height*dpr);ctx.setTransform(dpr,0,0,dpr,0,0);dirty=true}).observe(canvas.parentElement);
function moved(){dirty=true;if(world)localStorage.setItem('zoom-world-view',JSON.stringify({world:world.id,camera}));clearTimeout(settleTimer);settleTimer=setTimeout(()=>{if($('auto').checked)submitVisible(3)},1200)}
function zoom(delta,point={x:width/2,y:height/2}){if(!world)return;const old=scale(),wx=camera.x+(point.x-width/2)/old,wy=camera.y+(point.y-height/2)/old;camera.z=Math.max(world.geometry.extended_min_z,Math.min(world.geometry.extended_max_z,camera.z+delta));const next=scale();camera.x=wx-(point.x-width/2)/next;camera.y=wy-(point.y-height/2)/next;moved()}
canvas.addEventListener('wheel',event=>{event.preventDefault();const r=canvas.getBoundingClientRect();zoom(event.deltaY<0?.25:-.25,{x:event.clientX-r.left,y:event.clientY-r.top})},{passive:false});
canvas.onpointerdown=event=>{canvas.setPointerCapture(event.pointerId);drag={x:event.clientX,y:event.clientY}};canvas.onpointermove=event=>{if(!drag||!world)return;camera.x-=(event.clientX-drag.x)/scale();camera.y-=(event.clientY-drag.y)/scale();camera.x=Math.max(0,Math.min(world.geometry.map_width_px,camera.x));camera.y=Math.max(0,Math.min(world.geometry.map_height_px,camera.y));drag={x:event.clientX,y:event.clientY};moved()};canvas.onpointerup=canvas.onpointercancel=()=>{drag=null};
$('plus').onclick=()=>zoom(1);$('minus').onclick=()=>zoom(-1);
function fit(){if(!world)return;camera.x=world.geometry.map_width_px/2;camera.y=world.geometry.map_height_px/2;camera.z=Math.max(world.geometry.extended_min_z,Math.min(world.geometry.extended_max_z,world.geometry.native_max_z+Math.log2(Math.min(width/world.geometry.map_width_px,height/world.geometry.map_height_px)*.85)));moved()}
$('fit').onclick=fit;$('layer').onchange=()=>{localStorage.setItem('zoom-world-layer',$('layer').value);$('swipe-label').hidden=$('layer').value!=='compare';dirty=true};$('swipe').oninput=()=>{dirty=true};
async function loadWorld(id){const token=++loadEpoch;const next=await api('/worlds/'+id);if(token!==loadEpoch)return;world=next;signature='';lastStatus=null;epoch++;let saved=null;try{saved=JSON.parse(localStorage.getItem('zoom-world-view'))}catch{}if(saved?.world===id&&['x','y','z'].every(k=>Number.isFinite(saved.camera?.[k])))camera={...saved.camera};else if(world.kind==='middle-earth')camera={x:2772,y:1258,z:4};else fit();$('attribution').textContent=world.attribution+(hasAtlas(world)?' Atlas illustrations are AI-generated.':'');$('world-info').textContent=world.kind==='knowledge'?`${world.nodes.length} saved topic nodes · ${world.planner} · initial source levels ready. Research status: ${world.research.status}.`:'Existing application Middle-earth preset · original source remains available; AI imagery is a draft layer.';dirty=true;moved();await poll()}
async function loadList(selected){worlds=await api('/worlds');$('world').replaceChildren();for(const w of worlds){const option=document.createElement('option');option.value=w.id;option.textContent=w.title;$('world').append(option)}let remembered=null;try{remembered=JSON.parse(localStorage.getItem('zoom-world-view'))?.world}catch{}$('world').value=selected||(worlds.some(w=>w.id===remembered)?remembered:'middle-earth');await loadWorld($('world').value)}
$('world').onchange=()=>loadWorld($('world').value).catch(error=>$('create-status').textContent=error.message);
for(const [id,prompt] of Object.entries({science,history,entertainment})) {
 $(id).onclick=()=>{$('prompt').value=prompt;if(id!=='history')$('text-ai').checked=false;};
}
$('create').onclick=async()=>{const b=$('create');b.disabled=true;$('create-status').textContent='Planning the saved topic world and seed tiles (local AI can take a minute)…';try{const next=await api('/worlds',{prompt:$('prompt').value,use_local_ai:$('text-ai').checked});await loadList(next.id);$('create-status').textContent='Map ready. Initial GPU refinement is queued; source tiles are already navigable.'}catch(error){$('create-status').textContent=error.message}finally{b.disabled=false}};
function find(){if(!world)return;const query=$('search').value.toLowerCase().trim(),nodes=world.kind==='knowledge'?world.nodes:landmarks,node=nodes.find(n=>n.label.toLowerCase()===query)||nodes.find(n=>n.depth!==0&&n.label.toLowerCase().includes(query))||nodes.find(n=>n.label.toLowerCase().includes(query));if(node&&query){camera.x=node.x;camera.y=node.y;camera.z=world.kind==='knowledge'?Math.min(world.geometry.extended_max_z,Math.max(3,(node.min_z||0)+1)):4;moved()}else $('create-status').textContent='No matching saved topic or place.'}
$('find').onclick=find;$('search').onkeydown=e=>{if(e.key==='Enter')find()};
async function submitVisible(count){if(!world)return;if(world.kind==='middle-earth'&&directoryZ()<=world.geometry.native_max_z)return;const have=new Set(lastStatus?.tiles.map(t=>t.tile.join('/'))||[]),tiles=visible().filter(t=>!have.has([t.z,t.x,t.y].join('/'))).slice(0,count).map(({z,x,y})=>({z,x,y}));try{const result=await api(`/worlds/${world.id}/viewport`,{tiles,client_id:client,epoch:++epoch});if(!result.jobs.length&&tiles.length)$('create-status').textContent='No new job queued: session budget reached, queue full, or tile already running.';await poll()}catch(error){$('create-status').textContent=error.message}}
$('generate').onclick=()=>submitVisible(1);$('auto').onchange=()=>{localStorage.setItem('zoom-world-auto',$('auto').checked?'1':'0');clearTimeout(settleTimer);if($('auto').checked)moved();else if(world)api(`/worlds/${world.id}/viewport`,{tiles:[],client_id:client,epoch:++epoch}).catch(()=>{})};
async function poll(){if(!world)return;const id=world.id;try{const data=await api(`/worlds/${id}/status`);if(world.id!==id)return;lastStatus=data;const next=JSON.stringify(data.tiles.map(t=>[t.tile,t.artifact_sha256]));if(next!==signature){signature=next;for(const [key,item]of cache)if(key.startsWith(id+'|')&&!key.startsWith(id+'|original|')){item.bitmap.close();cache.delete(key)}dirty=true}const counts={};for(const j of data.jobs)counts[j.status]=(counts[j.status]||0)+1;$('jobs').textContent=`${data.tiles.length} generated tiles saved · ${counts.running||0} running · ${counts.queued||0} queued · ${counts.failed||0} failed. Draft imagery; edge blending preserves border pixels, not semantic geometry.`;const failed=data.jobs.filter(j=>j.status==='failed').at(-1);if(failed)$('jobs').textContent+=' Last error: '+failed.error;canvas.dataset.completedTiles=data.tiles.length}catch(error){$('jobs').textContent=error.message}}
setInterval(poll,2500);loadList().catch(error=>$('create-status').textContent=error.message);

api('/planner').then(info=>{$('text-ai').checked=info.local_ai_available;$('text-ai').disabled=!info.local_ai_available;$('planner-status').textContent=info.local_ai_available?'Local AI available: '+info.model+' · unverified outline.':'Fast topic scaffold; configure a local model to enable AI planning.'}).catch(()=>{$('planner-status').textContent='Fast topic scaffold mode.'});
