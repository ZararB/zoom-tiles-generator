import { blobToBase64, fetchTilePng, BASEMAP } from './lib/basemap.js';
import { buildMosaicPng } from './lib/mosaic.js';
import { workerHealth } from './lib/worker-client.js';
import { currentStyle, attachNameEditor, nameOverride } from './lib/map-names.js';
import {attachGeographyEditor} from './lib/geometry-editor.js';
import {geographyState} from './lib/geography.js';
import {sourceTileCache} from './lib/tile-cache.js';
import {viewportPlan,nextViewport,cancelViewport,submitTileJob,getTileJob} from './lib/viewport-jobs.js';
import {attachExamples} from './lib/examples.js';

const TORONTO = { lat: 43.6532, lng: -79.3832, zoom: 8 };

function latLngToTile(lat, lng, z) {
  const n = 2 ** z;
  const x = Math.floor(((lng + 180) / 360) * n);
  const latRad = (lat * Math.PI) / 180;
  const y = Math.floor(
    ((1 - Math.log(Math.tan(latRad) + 1 / Math.cos(latRad)) / Math.PI) / 2) * n,
  );
  return { x, y };
}

const el = {
  preset: document.getElementById('preset'),
  health: document.getElementById('health-badge'),
  tileBadge: document.getElementById('tile-badge'),
  provider: document.getElementById('provider'),
  useMosaic: document.getElementById('use-mosaic'),
  z: document.getElementById('z'),
  x: document.getElementById('x'),
  y: document.getElementById('y'),
  prompt: document.getElementById('prompt'),
  btnRun: document.getElementById('btn-run'),
  btnRefresh: document.getElementById('btn-refresh'),
  btnDownload: document.getElementById('btn-download'),
  srcPreview: document.getElementById('src-preview'),
  dstPreview: document.getElementById('dst-preview'),
  log: document.getElementById('log'),
  error: document.getElementById('error'),
};

let lastResultBlob = null;
let lastResultTile = null;
let lastSourceBlob=null,lastSourceTile=null,lastResultManifest=null;
let lastSourceWorld;
let workerReady = false;
let running = false;
let map;
let geographyEditor;
let previewSequence=0,previewBusy=false,previewTimer,refineTimer,viewportEpoch=nextViewport();
const renderStatus=document.getElementById('render-status'),refineStatus=document.getElementById('refinement-status');
const autoRefine=document.getElementById('auto-refine');
autoRefine.checked=localStorage.getItem('auto-refine')==='true';

function log(line) {
  const t = new Date().toISOString().slice(11, 19);
  el.log.textContent = `[${t}] ${line}\n${el.log.textContent}`.slice(0, 4000);
}

function setError(msg) {
  if (!msg) {
    el.error.hidden = true;
    el.error.textContent = '';
    return;
  }
  el.error.hidden = false;
  el.error.textContent = msg;
}

function updateTileBadge() {
  el.tileBadge.textContent = `z/x/y: ${el.z.value}/${el.x.value}/${el.y.value}`;
}

function setPreview(container, blobOrNull) {
  container.innerHTML = '';
  if (!blobOrNull) {
    container.innerHTML = '<span>—</span>';
    return;
  }
  const img = document.createElement('img');
  img.src = URL.createObjectURL(blobOrNull);
  img.onload = () => URL.revokeObjectURL(img.src);
  container.appendChild(img);
}

async function refreshHealth() {
  try {
    const h = await workerHealth();
    workerReady = Boolean(h.ok && h.cuda);
    el.health.textContent = workerReady ? `worker: GPU ready · ${h.model_id}` : 'worker: loading model';
    el.health.className = 'badge ' + (workerReady ? 'ok' : 'bad');
  } catch (e) {
    el.health.textContent = 'worker: offline';
    el.health.className = 'badge bad';
    workerReady = false;
  }
  el.btnRun.disabled = running || !workerReady;
}

async function loadSourcePreview() {
  const sequence=++previewSequence;
  const provider = el.provider.value;
  const z = Number(el.z.value);
  const x = Number(el.x.value);
  const y = Number(el.y.value);
  const sourceWorld={revision:geographyState()?.revision,sha256:geographyState()?.sha256,scenario:geographyState()?.scenario};
  const blob = await fetchTilePng(provider, z, x, y);
  if(sequence!==previewSequence)return blob;
  setPreview(el.srcPreview, blob);
  lastSourceBlob=blob;lastSourceTile={z,x,y};document.getElementById('btn-download-source').disabled=false;
  el.srcPreview.dataset.tile=`${z}/${x}/${y}`;el.srcPreview.dataset.worldHash=geographyState()?.sha256||'';
  lastSourceWorld=sourceWorld;document.getElementById('btn-record-source').disabled=false;
  return blob;
}

function scheduleViewport() {
  clearTimeout(previewTimer);clearTimeout(refineTimer);
  ++previewSequence;viewportEpoch=nextViewport();
  // Cancel queued work immediately. An active GPU request finishes into the cache.
  void cancelViewport(viewportEpoch).catch(()=>{});
  const renderPreview=async()=>{
    if(running)return;
    if(previewBusy){previewTimer=setTimeout(renderPreview,100);return;}
    previewBusy=true;const token=previewSequence,start=performance.now();
    try {
      await loadSourcePreview();
      if(token+1===previewSequence) {
        renderStatus.textContent=`Source tile ${(performance.now()-start).toFixed(0)} ms · cache ${sourceTileCache.hits} hits / ${sourceTileCache.misses} misses`;
        renderStatus.dataset.cacheHits=String(sourceTileCache.hits);
        renderStatus.dataset.sourceMs=String(performance.now()-start);
      }
    }catch(error){renderStatus.textContent=`Source preview: ${error.message}`;}
    finally{previewBusy=false;}
  };
  previewTimer=setTimeout(renderPreview,300);
  if(autoRefine.checked&&!running) {
    setPreview(el.dstPreview,null);lastResultBlob=null;lastResultManifest=null;
    el.btnDownload.disabled=true;document.getElementById('btn-download-manifest').disabled=true;
    const epoch=viewportEpoch;
    refineTimer=setTimeout(()=>void refineViewport(epoch),900);
  }
}

async function displayResult(resp,coords,prompt,extra={}) {
  if(!resp.success||!resp.image_base64)throw new Error('Worker returned no image');
  const bytes=Uint8Array.from(atob(resp.image_base64),c=>c.charCodeAt(0));
  lastResultBlob=new Blob([bytes],{type:'image/png'});lastResultTile=coords;
  const {image_base64:discarded,...metadata}=resp;
  const digest=await crypto.subtle.digest('SHA-256',bytes);
  lastResultManifest={schema_version:1,...metadata,prompt,coordinates:coords,...extra,
    output_sha256:Array.from(new Uint8Array(digest),b=>b.toString(16).padStart(2,'0')).join(''),created_at:new Date().toISOString()};
  setPreview(el.dstPreview,lastResultBlob);el.btnDownload.disabled=false;
  document.getElementById('btn-download-manifest').disabled=false;
}

async function refineViewport(epoch) {
  if(epoch!==viewportEpoch||!autoRefine.checked||running||!workerReady)return;
  const live=()=>epoch===viewportEpoch&&autoRefine.checked&&!running;
  try {
    const z=map.getZoom(),bounds=map.getPixelBounds();
    const tiles=viewportPlan(z,Math.floor(bounds.min.x/256),Math.floor(bounds.min.y/256),Math.floor((bounds.max.x-1)/256),Math.floor((bounds.max.y-1)/256));
    const world=structuredClone(geographyState()),prompt=el.prompt.value.trim();
    const jobs=[];
    refineStatus.textContent=`Preparing ${tiles.length} visible AI previews · map stays interactive`;
    for(const tile of tiles) {
      if(!live())return;
      const blob=await fetchTilePng('vector',tile.z,tile.x,tile.y);
      if(!live())return;
      const image_base64=await blobToBase64(blob);
      const job=await submitTileJob({...tile,image_base64,prompt,steps:4,seed:42,
        world_revision:world.revision,world_sha256:world.sha256,scene_id:world.scenario,map_name_override:nameOverride()},epoch,tile.priority);
      jobs.push({...tile,id:job.id});
    }
    let displayed;
    const poll=async()=>{
      if(!live())return;
      const results=await Promise.all(jobs.map(async job=>({...job,state:await getTileJob(job.id)})));
      if(!live())return;
      const completed=results.filter(r=>r.state.status==='completed');
      const failed=results.filter(r=>r.state.status==='failed');
      refineStatus.textContent=`AI previews ${completed.length}/${jobs.length} ready · ${failed.length} failed · one GPU job at a time`;
      refineStatus.dataset.completed=String(completed.length);refineStatus.dataset.total=String(jobs.length);
      const nearest=completed[0];
      if(nearest?.state.result&&displayed!==nearest.id) {
        displayed=nearest.id;await displayResult(nearest.state.result,{z:nearest.z,x:nearest.x,y:nearest.y},prompt,
          {job_id:nearest.id,preview_only:true,source_sha256:nearest.state.descriptor.source_sha256});
      }
      if(completed.length+failed.length<jobs.length)refineTimer=setTimeout(()=>void poll().catch(error=>{refineStatus.textContent=error.message;}),1200);
    };
    await poll();
  }catch(error){if(live())refineStatus.textContent=`AI queue: ${error.message}`;}
}
autoRefine.addEventListener('change',()=>{
  localStorage.setItem('auto-refine',String(autoRefine.checked));scheduleViewport();
  if(!autoRefine.checked)refineStatus.textContent='AI queue paused. Detailed map navigation stays live.';
});

async function runEdit() {
  if (running || !workerReady) return;
  running = true;
  clearTimeout(refineTimer);viewportEpoch=nextViewport();await cancelViewport(viewportEpoch).catch(()=>{});
  setError(null);
  el.btnRun.disabled = true;
  const controls = [el.provider, el.useMosaic, el.z, el.x, el.y, el.prompt, el.preset, el.btnRefresh,
    ...document.querySelectorAll('#geography-panel button, #geography-panel input, #geography-panel select, #name-panel button, #name-panel input')];
  controls.forEach((control) => { control.disabled = true; });
  const t0 = performance.now();
  try {
    const provider = el.provider.value;
    const z = Number(el.z.value);
    const x = Number(el.x.value);
    const y = Number(el.y.value);
    const prompt = el.prompt.value.trim();
    if (!prompt) throw new Error('Prompt required');

    log('Fetching source tile…');
    const sourceBlob = await loadSourcePreview();
    const image_base64 = await blobToBase64(sourceBlob);

    let context_mosaic_base64 = '';
    if (el.useMosaic.checked) {
      log('Building 3×3 mosaic…');
      const { pngBlob } = await buildMosaicPng(provider, z, x, y, 1);
      context_mosaic_base64 = await blobToBase64(pngBlob);
    }

    log('Generating on the GPU…');
    const submitted = await submitTileJob({
      image_base64,
      prompt,
      context_mosaic_base64,
      z,
      x,
      y,
      world_revision:geographyState()?.revision,
      world_sha256:geographyState()?.sha256,
      scene_id:geographyState()?.scenario,
      map_name_override:nameOverride(),
      steps:20,seed:42,
    },viewportEpoch,0);
    let job=await getTileJob(submitted.id);
    log(submitted.cache_hit?'Reusing cached GPU tile':'GPU job queued; waiting for result…');
    while(job.status==='queued'||job.status==='running') {
      await new Promise(resolve=>setTimeout(resolve,1200));job=await getTileJob(submitted.id);
    }
    if(job.status!=='completed')throw new Error(job.error||'GPU job did not complete');
    const resp=job.result;

    if (!resp.success || !resp.image_base64) {
      throw new Error('Worker returned no image');
    }

    await displayResult(resp,{z,x,y},prompt,{job_id:job.id,cache_hit:submitted.cache_hit,source_sha256:job.descriptor.source_sha256});

    const sec = ((performance.now() - t0) / 1000).toFixed(1);
    log(`Done in ${sec}s · provider=${resp.provider || '?'}`);
  } catch (e) {
    const msg = e instanceof Error ? e.message : String(e);
    setError(msg);
    log(`ERROR: ${msg}`);
  } finally {
    running = false;
    controls.forEach((control) => { control.disabled = false; });
    el.btnRun.disabled = !workerReady;
  }
}

async function initMap() {
  map = L.map('map', { zoomControl: true, maxZoom: 18, worldCopyJump: true }).setView([TORONTO.lat, TORONTO.lng], TORONTO.zoom);

  const syncBasemapLayer = async () => {
    const key = el.provider.value;
    if (key === 'vector') return L.maplibreGL({style: await currentStyle(), interactive:false});
    const p = BASEMAP[key] || BASEMAP.osm;
    return L.tileLayer(p.leaflet, {
      attribution: p.attribution,
      maxZoom: 19,
    });
  };

  let layer = (await syncBasemapLayer()).addTo(map);

  el.provider.addEventListener('change', async () => {
    map.removeLayer(layer);
    layer = (await syncBasemapLayer()).addTo(map);
  });

  const nameEditor=await attachNameEditor(map, () => layer, async () => {
    if (el.provider.value !== 'vector') {
      el.provider.value = 'vector';
      map.removeLayer(layer);
      layer = (await syncBasemapLayer()).addTo(map);
    }
  }, async()=>scheduleViewport());
  geographyEditor=await attachGeographyEditor(map,nameEditor.refresh,async()=>scheduleViewport());
  await attachExamples(map,nameEditor.refresh,geographyEditor,scheduleViewport,()=>layer.getMaplibreMap());
  const gl=layer.getMaplibreMap?.();
  let moveStarted=performance.now();
  map.on('movestart zoomstart',()=>{moveStarted=performance.now();});
  gl?.on('idle',()=>{
    renderStatus.dataset.mapMs=String(performance.now()-moveStarted);
    renderStatus.dataset.worldHash=geographyState()?.sha256||'';
  });

  map.on('click', (ev) => {
    if (running) return;
    if (geographyEditor?.captureClick(ev.latlng)) return;
    const z = map.getZoom();
    const p = map.project(ev.latlng, z);
    const tileSize = 256;
    const n = 2 ** z;
    const x = ((Math.floor(p.x / tileSize) % n) + n) % n;
    const y = Math.min(n - 1, Math.max(0, Math.floor(p.y / tileSize)));
    el.z.value = String(z);
    el.x.value = String(x);
    el.y.value = String(y);
    updateTileBadge();
    log(`Picked tile ${z}/${x}/${y}`);
    void loadSourcePreview().catch((e) => log(String(e)));
  });

  map.on('zoomend moveend', () => {
    if (running) return;
    const c = map.getCenter();
    const z = map.getZoom();
    const p = map.project(c, z);
    const n = 2 ** z;
    const x = ((Math.floor(p.x / 256) % n) + n) % n;
    const y = Math.min(n - 1, Math.max(0, Math.floor(p.y / 256)));
    el.z.value = String(z);
    el.x.value = String(x);
    el.y.value = String(y);
    updateTileBadge();
    scheduleViewport();
  });
}

el.btnRun.addEventListener('click', () => void runEdit());
el.btnRefresh.addEventListener('click', () => {
  void loadSourcePreview()
    .then(() => log('Source refreshed'))
    .catch((e) => setError(String(e)));
});
el.btnDownload.addEventListener('click', () => {
  if (!lastResultBlob) return;
  const a = document.createElement('a');
  a.href = URL.createObjectURL(lastResultBlob);
  a.download = `tile_${lastResultTile.z}_${lastResultTile.x}_${lastResultTile.y}.png`;
  a.click();
  URL.revokeObjectURL(a.href);
});

function downloadBlob(blob,filename) {
  const url=URL.createObjectURL(blob),a=document.createElement('a');a.href=url;a.download=filename;a.click();
  setTimeout(()=>URL.revokeObjectURL(url),1000);
}
document.getElementById('btn-download-source').addEventListener('click',()=>{
  if(lastSourceBlob)downloadBlob(lastSourceBlob,`source_${lastSourceTile.z}_${lastSourceTile.x}_${lastSourceTile.y}.png`);
});
document.getElementById('btn-record-source').addEventListener('click',async()=>{
  if(!lastSourceBlob||!lastSourceWorld)return;
  try {
    const response=await fetch('/api/record-source',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({
      ...lastSourceTile,case_id:lastSourceWorld.scenario,world_sha256:lastSourceWorld.sha256,world_revision:lastSourceWorld.revision,
      image_base64:await blobToBase64(lastSourceBlob)})});
    const data=await response.json();if(!response.ok)throw new Error(data.error);
    el.srcPreview.dataset.recorded=data.case_id;log('Recorded source example: '+data.case_id);
  }catch(error){setError(error.message);}
});
document.getElementById('btn-download-manifest').addEventListener('click',()=>{
  if(lastResultManifest)downloadBlob(new Blob([JSON.stringify(lastResultManifest,null,2)],{type:'application/json'}),'tile-generation-manifest.json');
});

['z', 'x', 'y'].forEach((id) => {
  document.getElementById(id).addEventListener('change', updateTileBadge);
});

async function loadPresets() {
  try {
    const res = await fetch('./prompt-presets.json');
    const presets = await res.json();
    el.preset.innerHTML = presets
      .map((p) => `<option value="${p.id}">${p.label}</option>`)
      .join('');
    el.preset.addEventListener('change', () => {
      const pick = presets.find((p) => p.id === el.preset.value);
      if (pick) el.prompt.value = pick.prompt;
    });
  } catch {
    log('Presets not loaded (optional)');
  }
}

el.btnRun.disabled = true;
await initMap();
{
  const { x, y } = latLngToTile(TORONTO.lat, TORONTO.lng, TORONTO.zoom);
  el.z.value = String(TORONTO.zoom);
  el.x.value = String(x);
  el.y.value = String(y);
}
updateTileBadge();
void loadPresets();
void refreshHealth();
setInterval(() => void refreshHealth(), 15000);

scheduleViewport();
