// The application can use the same bounded center-first plan with its tile broker.
export function viewportPlan(z,minX,minY,maxX,maxY,limit=4) {
  const n=2**z,cx=(minX+maxX)/2,cy=(minY+maxY)/2,tiles=[];
  for(let y=Math.max(0,minY);y<=Math.min(n-1,maxY);y++)for(let x=minX;x<=maxX;x++) {
    tiles.push({z,x:((x%n)+n)%n,y,priority:(x-cx)**2+(y-cy)**2});
  }
  const seen=new Set();
  return tiles.sort((a,b)=>a.priority-b.priority).filter(t=>{
    const key=`${t.z}/${t.x}/${t.y}`;if(seen.has(key))return false;seen.add(key);return true;
  }).slice(0,limit);
}

let clientId;
function client() {
  if(!clientId){clientId=sessionStorage.getItem('tile-job-client')||crypto.randomUUID();sessionStorage.setItem('tile-job-client',clientId);}
  return clientId;
}
let epoch=Date.now();
export const nextViewport=()=>++epoch;
async function jsonRequest(path,body) {
  const response=await fetch('/api/tile-jobs'+path,body?{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)}:{});
  const data=await response.json();if(!response.ok)throw new Error(data.error||`Tile jobs ${response.status}`);return data;
}
export const cancelViewport=viewport=>jsonRequest('/cancel',{client_id:client(),viewport_id:viewport});
export const submitTileJob=(payload,viewport,priority=0)=>jsonRequest('',{client_id:client(),viewport_id:viewport,priority,payload});
export const getTileJob=id=>jsonRequest('/'+id);
