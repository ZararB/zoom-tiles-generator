// Bounded, revision-keyed source tile cache. GPU outputs have a separate server cache.
export class TileCache {
  constructor(limit=128) {this.limit=limit;this.memory=new Map();this.pending=new Map();this.hits=0;this.misses=0;}
  async get(key,create) {
    if(this.memory.has(key)) {
      const value=this.memory.get(key);this.memory.delete(key);this.memory.set(key,value);this.hits++;return value;
    }
    if(this.pending.has(key)){this.hits++;return this.pending.get(key);}
    this.misses++;
    const work=(async()=>{
      const value=await create();this.memory.set(key,value);
      while(this.memory.size>this.limit)this.memory.delete(this.memory.keys().next().value);
      return value;
    })();
    this.pending.set(key,work);
    try{return await work;}finally{this.pending.delete(key);}
  }
}

export const sourceTileCache=new TileCache(128);
const STORAGE='zoom-tiles-source-v1';
let storage;
export async function cachedSource(key,create) {
  return sourceTileCache.get(key,async()=>{
    // Browser storage is optional; failure or quota exhaustion falls back to RAM.
    let cache,url;
    try {
      if(typeof caches!=='undefined') {
        storage||=caches.open(STORAGE);cache=await storage;
        const digest=await crypto.subtle.digest('SHA-256',new TextEncoder().encode(key));
        url=new URL('/_source_tiles/'+Array.from(new Uint8Array(digest),b=>b.toString(16).padStart(2,'0')).join(''),location.origin).href;
        const hit=await cache.match(url);if(hit){sourceTileCache.hits++;return hit.blob();}
      }
    }catch{cache=null;}
    const blob=await create();
    if(cache)try {
      await cache.put(url,new Response(blob,{headers:{'Content-Type':'image/png'}}));
      const keys=await cache.keys();await Promise.all(keys.slice(0,Math.max(0,keys.length-192)).map(k=>cache.delete(k)));
    }catch{}
    return blob;
  });
}
