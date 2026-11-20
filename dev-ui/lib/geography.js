let documentState;
export const GEOGRAPHY_SOURCE = 'custom-geography';
export const GEOGRAPHY_LABELS = 'custom-geography-labels';

export async function loadGeography() {
  if (!documentState) {
    const response=await fetch('/api/geography');
    if (!response.ok) throw new Error('Could not load custom geography');
    documentState=await response.json();
  }
  return documentState;
}
export function geographyState() { return documentState; }
export async function saveGeography(doc,undo=false) {
  const response=await fetch(undo?'/api/geography/undo':'/api/geography',{
    method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({...doc,expected_revision:documentState?.revision||'initial'})});
  const data=await response.json();
  if(!response.ok) {const error=new Error(data.error||'Geometry could not be saved');error.status=response.status;throw error;}
  documentState=data;
  return data;
}

export async function proposeAndApply(doc) {
  // This path is called by an explicit user action; model workers only create drafts.
  const proposalResponse=await fetch('/api/geography/proposals',{method:'POST',headers:{'Content-Type':'application/json'},
    body:JSON.stringify({document:doc,expected_revision:documentState?.revision||'initial',
      model_version_id:'great-lakes-merge-v1',mlflow_run_id:doc.provenance?.mlflow_run_id||''})});
  const proposal=await proposalResponse.json();
  if(!proposalResponse.ok)throw new Error(proposal.error||'Proposal validation failed');
  const response=await fetch(`/api/geography/proposals/${proposal.id}/apply`,{method:'POST',headers:{'Content-Type':'application/json'},
    body:JSON.stringify({expected_revision:documentState?.revision||'initial'})});
  const result=await response.json();
  if(!response.ok)throw new Error(result.error||'Proposal could not be applied');
  documentState=result;return result;
}

export function geographyStyle(input,doc) {
  const style=structuredClone(input);
  if(!doc?.enabled||!doc.features.length) return style;
  const masks=doc.features.filter(f=>f.properties.role==='replacement-region');
  const water=(doc.render_features||doc.features).filter(f=>f.properties.kind==='water');
  const suppression=water;
  // Preserve the original land detail. Hide symbols only where new water covers
  // them, plus obsolete names of the lakes explicitly replaced by this scene.
  const oldNames=(doc.base_water_features||[]).map(f=>f.properties.name);
  for(const layer of style.layers) {
    if(layer.type==='symbol'&&layer.id!=='custom-lake-name-label'&&suppression.length) {
      const outside=['all',...suppression.map(f=>['!', ['within',f.geometry]])];
      layer.filter=layer.filter?['all',layer.filter,outside]:outside;
    }
    if(layer['source-layer']==='water_name'&&oldNames.length) {
      const names=['!', ['in',['coalesce',['get','name:en'],['get','name_en'],['get','name'],''],['literal',oldNames]]];
      layer.filter=layer.filter?['all',layer.filter,names]:names;
    }
  }
  if(masks.length) {
    style.layers=style.layers.filter(l=>l.id!=='custom-lake-name-label');
    delete style.sources['custom-lake-name'];
  }
  style.sources[GEOGRAPHY_SOURCE]={type:'geojson',data:{type:'FeatureCollection',features:doc.render_features||doc.features}};
  style.sources[GEOGRAPHY_LABELS]={type:'geojson',data:{type:'FeatureCollection',features:doc.labels||[]}};
  const source=GEOGRAPHY_SOURCE;
  style.layers.push(
    {id:'geography-water',type:'fill',source,filter:['==',['get','kind'],'water'],paint:{'fill-color':'#8db9df'}},
    {id:'geography-land',type:'fill',source,filter:['all',['==',['get','kind'],'land'],['!=',['get','role'],'replacement-region']],paint:{'fill-color':['case',['==',['get','role'],'reclaimed-land'],'#f8f4f0','#d7e6bf']}},
    {id:'geography-shorelines',type:'line',source,filter:['==',['get','kind'],'water'],paint:{'line-color':'#427aa0','line-width':['interpolate',['linear'],['zoom'],4,1,10,2]}},
    {id:'geography-borders',type:'line',source,filter:['==',['get','kind'],'border'],paint:{'line-color':'#9e5268','line-width':2,'line-dasharray':[4,3]}},
    {id:'geography-water-labels',type:'symbol',source:GEOGRAPHY_LABELS,layout:{'text-field':['get','name'],'text-font':['Noto Sans Italic'],'text-size':16,'text-max-width':10,'text-allow-overlap':true,'text-ignore-placement':true},paint:{'text-color':'#254e70','text-halo-color':'#eaf5ff','text-halo-width':1.4}},
  );
  return style;
}
