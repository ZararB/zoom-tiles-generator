import {saveGeography,geographyState} from './geography.js';

export async function attachExamples(map,refreshStyle,editor,refreshPreview,getGL) {
  const select=document.getElementById('example-select'),status=document.getElementById('example-status');
  const response=await fetch('/api/examples');if(!response.ok)throw new Error('Examples are unavailable');
  const cases=await response.json();select.replaceChildren(...cases.map(c=>new Option(c.title,c.id)));
  const selected=()=>cases.find(c=>c.id===select.value);
  function describe(){document.getElementById('example-description').textContent=selected().description;}
  select.addEventListener('change',describe);describe();
  for(const phase of ['before','after'])document.getElementById('example-'+phase).addEventListener('click',async()=>{
    const current=selected(),buttons=[document.getElementById('example-before'),document.getElementById('example-after')];
    buttons.forEach(b=>b.disabled=true);status.dataset.ready='false';status.dataset.example=current.id;status.dataset.phase=phase;
    const unchanged=geographyState().sha256;const started=performance.now();
    try {
      const input=await (await fetch(`/api/examples/${current.id}/${phase}`)).json();
      await saveGeography(input);await refreshStyle();editor.refresh();
      const [minX,minY,maxX,maxY]=current.bounds;
      const gl=getGL();
      const idle=new Promise((resolve,reject)=>{
        const timer=setTimeout(()=>{gl.off('idle',done);reject(new Error('Map data took too long to load'));},20000);
        const done=()=>{clearTimeout(timer);resolve();};gl.once('idle',done);gl.triggerRepaint();
      });
      map.fitBounds([[minY,minX],[maxY,maxX]],{padding:[35,35],maxZoom:12,animate:false});
      await idle;
      status.textContent=`${current.title} / ${phase} loaded`;
      status.dataset.ready='true';status.dataset.worldHash=geographyState().sha256;
      status.dataset.elapsedMs=String(performance.now()-started);
      document.getElementById('prompt').value=current.prompt;refreshPreview();
    }catch(error) {
      if(current.assertion==='reject_invalid'&&phase==='after'&&error.status===422&&geographyState().sha256===unchanged) {
        status.textContent='Invalid shoreline rejected; saved map unchanged.';status.dataset.ready='true';status.dataset.rejected='true';
        status.dataset.worldHash=unchanged;
      }else{status.textContent=error.message;status.dataset.error='true';}
    }finally{buttons.forEach(b=>b.disabled=false);}
  });
}
