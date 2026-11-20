import fs from 'node:fs';
import assert from 'node:assert/strict';
import {geographyStyle} from '../dev-ui/lib/geography.js';
import {TileCache} from '../dev-ui/lib/tile-cache.js';
import {viewportPlan} from '../dev-ui/lib/viewport-jobs.js';

const base=JSON.parse(fs.readFileSync(new URL('../dev-ui/lib/basemap-style.json',import.meta.url)));
const doc=JSON.parse(fs.readFileSync(new URL('../dev-ui/scenarios/great-lakes-two.json',import.meta.url)));
const result=geographyStyle(base,doc);
assert(!result.layers.some(l=>l.id==='geography-region'),'No opaque rectangular mask');
for(const layer of base.layers.filter(l=>l.type!=='symbol')) {
  assert.deepEqual(result.layers.find(l=>l.id===layer.id),layer,'Retain original terrain, buildings, roads and landcover');
}
const city=result.layers.find(l=>l.id==='label_city');
assert(!JSON.stringify(city.filter).includes('-94'),'Do not suppress settlements across the entire region');
assert(result.layers.some(l=>l.id==='geography-water'));
const cache=new TileCache(2);let calls=0;
const factory=async()=>{calls++;return 'tile';};
await Promise.all([cache.get('world1/6/1/1',factory),cache.get('world1/6/1/1',factory)]);
assert.equal(calls,1,'Deduplicate concurrent source requests');
await cache.get('world1/6/1/1',factory);assert.equal(calls,1);
await cache.get('world2/6/1/1',factory);assert.equal(calls,2,'World hash invalidates cache');
await cache.get('third',factory);assert.equal(cache.memory.size,2,'Bound memory');
await cache.get('world1/6/1/1',factory);assert.equal(calls,4,'Evicted entry regenerates');
await assert.rejects(cache.get('failure',async()=>{throw new Error('failed');}));
assert.equal(await cache.get('failure',async()=>'recovered'),'recovered','Failures are retryable');
const plan=viewportPlan(6,16,21,18,23);
assert.deepEqual(plan[0],{z:6,x:17,y:22,priority:0});assert.equal(plan.length,4);
assert.deepEqual(viewportPlan(0,-1,-1,1,1),[{z:0,x:0,y:0,priority:0}]);
console.log('Passed: detail retention, bounded cache/deduplication, world invalidation, center-first viewport planning.');
