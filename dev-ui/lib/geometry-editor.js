import {loadGeography,geographyState,saveGeography,proposeAndApply} from './geography.js';

export async function attachGeographyEditor(map,refreshStyle,refreshPreview) {
  await loadGeography();
  const $=id=>document.getElementById(id);
  const status=$('geography-status'),select=$('geometry-feature'),name=$('geometry-name');
  let mode=null,points=[],preview=null,handles=L.layerGroup().addTo(map),selectedOutline=null;
  let editing=false,selectedId=null,saving=false;
  const selected=()=>geographyState().features.find(f=>f.id===selectedId);
  function clearPreview() { if(preview)map.removeLayer(preview);preview=null; }
  function resetDrawing() {mode=null;points=[];clearPreview();map.doubleClickZoom.enable();}
  function show() {
    const doc=geographyState();
    select.replaceChildren(new Option('Choose a feature',''));
    for(const feature of doc.features) select.add(new Option(`${feature.properties.kind}: ${feature.properties.name}`,feature.id));
    select.value=selectedId||'';
    name.value=selected()?.properties.name||'';
    $('geography-visible').checked=doc.enabled;
    const s=doc.summary;
    status.dataset.waterBodies=String(s.connected_water_bodies);
    status.dataset.revision=doc.revision;
    status.dataset.enabled=String(doc.enabled);
    status.textContent=`${doc.enabled?'Active':'Hidden'} · ${s.connected_water_bodies} connected water bodies · ${s.land_features} land features · ${s.borders} borders · saved`;
    document.getElementById('name-panel').hidden=doc.enabled&&doc.features.some(f=>f.properties.role==='replacement-region');
  }
  async function commit(doc,undo=false,proposal=false) {
    if(saving) throw new Error('A save is already in progress');
    saving=true;status.textContent='Validating and saving geography…';
    try {
      if(proposal)await proposeAndApply(doc);else await saveGeography(doc,undo);
      await refreshStyle();show();drawHandles();
      void refreshPreview().catch(()=>{});
    } catch(error) {show();drawHandles();status.textContent=error.message;throw error;}
    finally {saving=false;}
  }
  function featurePaths(geometry) {
    const paths=[];
    function visit(value,path) {
      if(typeof value[0]==='number') {paths.push(path);return;}
      value.forEach((item,i)=>{
        if(i===value.length-1&&Array.isArray(item)&&typeof item[0]==='number'&&JSON.stringify(item)===JSON.stringify(value[0]))return;
        visit(item,[...path,i]);
      });
    }
    visit(geometry.coordinates,[]);return paths;
  }
  function atPath(geometry,path) {return path.reduce((value,key)=>value[key],geometry.coordinates);}
  function moveVertex(geometry,path,coordinate) {
    let parent=geometry.coordinates;
    for(const key of path.slice(0,-1))parent=parent[key];
    const index=path.at(-1),closed=geometry.type!=='LineString'&&JSON.stringify(parent[0])===JSON.stringify(parent.at(-1));
    parent[index]=coordinate;
    if(closed&&index===0)parent[parent.length-1]=[...coordinate];
  }
  function drawHandles() {
    handles.clearLayers();if(selectedOutline)map.removeLayer(selectedOutline);selectedOutline=null;
    const feature=selected();if(!editing||!feature)return;
    selectedOutline=L.geoJSON(feature,{style:{color:'#c65b28',weight:2,fillOpacity:0}}).addTo(map);
    for(const path of featurePaths(feature.geometry)) {
      const coord=atPath(feature.geometry,path);
      const marker=L.marker([coord[1],coord[0]],{draggable:true,keyboard:false,
        icon:L.divIcon({className:'geometry-vertex',iconSize:[10,10],iconAnchor:[5,5]})}).addTo(handles);
      marker.getElement().setAttribute('aria-hidden','true');
      marker.on('dragend',async()=>{
        const position=marker.getLatLng(),doc=structuredClone(geographyState());
        moveVertex(doc.features.find(f=>f.id===selectedId).geometry,path,[position.lng,position.lat]);
        try {await commit(doc);}catch{}
      });
    }
  }
  function begin(kind) {
    resetDrawing();editing=false;selectedId=null;drawHandles();mode=kind;map.doubleClickZoom.disable();
    select.value='';name.value=`New ${kind}`;
    status.textContent=`Draw ${kind}: click the map to add points, then Finish shape. Escape cancels.`;
  }
  for(const kind of ['water','land','border']) $('draw-'+kind).addEventListener('click',()=>begin(kind));
  $('cancel-geometry').addEventListener('click',()=>{resetDrawing();show();});
  $('undo-point').addEventListener('click',()=>{points.pop();updatePreview();});
  function updatePreview() {
    clearPreview();if(!points.length)return;
    preview=(mode==='border'?L.polyline(points):L.polygon(points)).setStyle({color:'#d47636',weight:3,fillOpacity:.25}).addTo(map);
    status.textContent=`Drawing ${mode}: ${points.length} points`;
  }
  $('finish-geometry').addEventListener('click',async()=>{
    if(!mode||points.length<(mode==='border'?2:3)){status.textContent='Add at least 3 polygon points or 2 border points.';return;}
    const kind=mode,coords=points.map(p=>[p.lng,p.lat]);if(kind!=='border')coords.push([...coords[0]]);
    const id=crypto.randomUUID(),doc=structuredClone(geographyState());
    doc.enabled=true;doc.scenario='custom';doc.features.push({type:'Feature',id,
      properties:{kind,name:name.value.trim()||`New ${kind}`},
      geometry:{type:kind==='border'?'LineString':'Polygon',coordinates:kind==='border'?coords:[coords]}});
    try{selectedId=id;await commit(doc);resetDrawing();}catch{}
  });
  select.addEventListener('change',()=>{selectedId=select.value;name.value=selected()?.properties.name||'';drawHandles();});
  $('edit-vertices').addEventListener('click',()=>{resetDrawing();editing=!editing;drawHandles();status.textContent=editing?'Drag an orange vertex; valid edits save when released.':'Vertex editing off';});
  $('save-feature').addEventListener('click',async()=>{
    if(!selected())return;const doc=structuredClone(geographyState());
    doc.features.find(f=>f.id===selectedId).properties.name=name.value.trim();
    try{await commit(doc);}catch{}
  });
  $('delete-feature').addEventListener('click',async()=>{
    if(!selected())return;const doc=structuredClone(geographyState());doc.features=doc.features.filter(f=>f.id!==selectedId);
    selectedId=null;try{await commit(doc);}catch{}
  });
  $('undo-geography').addEventListener('click',async()=>{try{await commit({},true);}catch{}});
  $('geography-visible').addEventListener('change',async()=>{
    const doc=structuredClone(geographyState());doc.enabled=$('geography-visible').checked;try{await commit(doc);}catch{}
  });
  $('load-two-lakes').addEventListener('click',async()=>{
    try {
      const response=await fetch('./scenarios/great-lakes-two.json');if(!response.ok)throw new Error('Scenario is unavailable');
      selectedId='great-lakes-west';editing=false;resetDrawing();await commit(await response.json(),false,true);focus();
    }catch(error){status.textContent=error.message;}
  });
  function focus() {
    show();
    const doc=geographyState(),water=doc.features.filter(f=>f.properties.kind==='water');
    const features=water.length?water:doc.features;
    if(features.length)map.fitBounds(L.geoJSON({type:'FeatureCollection',features}).getBounds(),{padding:[30,30],maxZoom:8,animate:false});
  }
  $('focus-geography').addEventListener('click',focus);
  $('export-geography').addEventListener('click',()=>{
    const blob=new Blob([JSON.stringify(geographyState(),null,2)],{type:'application/geo+json'}),url=URL.createObjectURL(blob);
    const a=document.createElement('a');a.href=url;a.download='custom-geography.geojson';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
  });
  window.addEventListener('keydown',event=>{if(event.key==='Escape'){resetDrawing();show();}});
  show();
  return {refresh(){editing=false;selectedId=null;resetDrawing();drawHandles();show();},captureClick(latlng){if(!mode)return false;points.push(latlng);updatePreview();return true;}};
}
