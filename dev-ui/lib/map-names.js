import { renamedStyle, geometrySignature, ORIGINAL_LAKE_NAME, LABEL_SOURCE, LABEL_LAYER } from './label-style.js';
import {loadGeography,geographyState,geographyStyle} from './geography.js';
import {cachedSource} from './tile-cache.js';

let state;
let baseStyle;
let renderer;
let renderVersion = '';
let renderQueue = Promise.resolve();

export async function loadMapState() {
  if (!state) {
    const response = await fetch('/api/map-edits');
    if (!response.ok) throw new Error('Could not load saved map names');
    state = await response.json();
  }
  if (!baseStyle) {
    const response = await fetch(new URL('./basemap-style.json', import.meta.url));
    if (!response.ok) throw new Error('Could not load the vector map style');
    baseStyle = await response.json();
  }
  return state;
}

export async function currentStyle() {
  await loadMapState();
  await loadGeography();
  return geographyStyle(renamedStyle(baseStyle,state),geographyState());
}

export function nameOverride() {
  return {feature_id:'lake-ontario',name:state?.lake_name||'Lake America',enabled:Boolean(state?.enabled)};
}

function waitForIdle(gl, action) {
  return new Promise((resolve, reject) => {
    const done = () => { clearTimeout(timer); resolve(); };
    const timer = setTimeout(() => { gl.off('idle', done); reject(new Error('Vector tiles took too long to load')); }, 25000);
    gl.once('idle', done);
    if (action) action();
    gl.triggerRepaint();
  });
}

export function renderVectorTile(z, x, y, {signal}={}) {
  if(signal?.aborted)return Promise.reject(new DOMException('Superseded viewport','AbortError'));
  const version=JSON.stringify({pipeline:'detail-preserving-v2',names:state,geography:geographyState()?.sha256});
  const key=JSON.stringify({version,z,x,y});
  return cachedSource(key,()=>{
  // One reusable off-screen canvas avoids creating a WebGL context for every mosaic tile.
  const work = renderQueue.catch(() => {}).then(async () => {
    if(signal?.aborted)throw new DOMException('Superseded viewport','AbortError');
    await loadMapState();
    await loadGeography();
    if(version!==JSON.stringify({pipeline:'detail-preserving-v2',names:state,geography:geographyState()?.sha256}))throw new Error('Map changed; retry source tile');
    const center = [((x + .5) / 2 ** z) * 360 - 180,
      Math.atan(Math.sinh(Math.PI * (1 - 2 * (y + .5) / 2 ** z))) * 180 / Math.PI];
    if (!renderer) {
      const container = document.createElement('div');
      container.className = 'vector-tile-renderer';
      container.setAttribute('aria-hidden', 'true');
      document.body.append(container);
      renderer = new maplibregl.Map({container, style: await currentStyle(), center, zoom: z - 1,minZoom:-1,
        interactive: false, attributionControl: false, pixelRatio: 1,
        canvasContextAttributes: {preserveDrawingBuffer: true, antialias: false}});
      await waitForIdle(renderer);
      renderVersion = version;
    } else {
      const nextStyle=renderVersion!==version?await currentStyle():null;
      await waitForIdle(renderer, () => {
        if (nextStyle) renderer.setStyle(nextStyle);
        renderer.jumpTo({center, zoom: z - 1});
      });
      renderVersion = version;
    }
    return new Promise((resolve, reject) => renderer.getCanvas().toBlob(blob =>
      blob ? resolve(blob) : reject(new Error('Could not export source tile')), 'image/png'));
  });
  renderQueue = work;
  return work;
  });
}

export async function attachNameEditor(map, getLayer, chooseVector, refreshPreview) {
  await loadMapState();
  const input = document.getElementById('lake-name');
  const status = document.getElementById('name-status');
  const apply = document.getElementById('apply-name');
  const reset = document.getElementById('reset-name');
  input.value = state.lake_name;

  function showStatus(gl) {
    const style = gl.getStyle();
    if (!style?.layers) return;
    const unchanged = geometrySignature(baseStyle) === geometrySignature(style);
    status.dataset.geometryUnchanged = String(unchanged);
    status.dataset.savedName = state.enabled ? state.lake_name : ORIGINAL_LAKE_NAME;
    status.dataset.enabled = String(state.enabled);
    status.textContent = `${state.enabled ? state.lake_name : ORIGINAL_LAKE_NAME} · saved locally · ${geographyState()?.enabled ? 'custom geography active' : unchanged ? 'shoreline unchanged' : 'checking map geometry'}`;
    document.querySelector('#provider option[value="osm"]').disabled = state.enabled||geographyState()?.enabled;
  }

  async function updateStyle() {
    await chooseVector();
    const gl = getLayer().getMaplibreMap();
    const style=await currentStyle();
    gl.setStyle(style);
    gl.once('idle',()=>{status.dataset.mapReady=String(gl.areTilesLoaded());showStatus(gl);});
    showStatus(gl);
  }

  async function save(enabled) {
    const name = input.value.trim();
    if (!name || name.length > 80) { status.textContent = 'Enter a lake name between 1 and 80 characters.'; return; }
    apply.disabled = reset.disabled = true;
    try {
      const response = await fetch('/api/map-edits', {method:'POST', headers:{'Content-Type':'application/json'},
        body:JSON.stringify({lake_name:name, enabled})});
      if (!response.ok) throw new Error('Could not save the map name');
      state = await response.json();
      await updateStyle();
      void refreshPreview().catch(error => { status.textContent += ` · source preview: ${error.message}`; });
    } catch (error) { status.textContent = error.message; }
    finally { apply.disabled = reset.disabled = false; }
  }
  apply.addEventListener('click', () => void save(true));
  reset.addEventListener('click', () => void save(false));
  document.getElementById('focus-lake').addEventListener('click', () => {
    map.fitBounds([[43.1,-79.95],[44.55,-75.9]], {padding:[24,24], maxZoom:8, animate:false});
  });
  await updateStyle();
  return {refresh:updateStyle};
}
