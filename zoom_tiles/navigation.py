"""Local persistent worlds, lazy tiles, bounded viewport jobs and GPU draft artifacts."""
import base64
import hashlib
import io
import json
import math
import threading
import time
import uuid
from datetime import datetime,timezone
from pathlib import Path
import requests
from PIL import Image,ImageDraw
from .pyramid import PyramidGeometry,digest,plan_context
from .topic_atlas import has_topic_atlas, render_tile as render_atlas_tile
from .text_worlds import plan_text_world

def atomic_json(path,data):
    path.parent.mkdir(parents=True,exist_ok=True);tmp=path.with_name(path.name+'.'+uuid.uuid4().hex+'.tmp');tmp.write_text(json.dumps(data,indent=2),encoding='utf-8');tmp.replace(path)
def png(image):
    stream=io.BytesIO();image.save(stream,'PNG');return stream.getvalue()
def read_image(path):
    with Image.open(path) as im:return im.convert('RGB')
def edge_blend(source,result,width=24):
    """Keep source edge pixels. This is visual compositing, not a geometry guarantee."""
    mask=Image.new('L',source.size);mask.putdata([round(255*min(1,min(x,y,source.width-1-x,source.height-1-y)/width)) for y in range(source.height) for x in range(source.width)])
    return Image.composite(result.resize(source.size),source,mask)

class WorldEngine:
    def __init__(self,root,middle_baseline,worker='http://127.0.0.1:8888',start_worker=True):
        self.root=Path(root);self.root.mkdir(parents=True,exist_ok=True);self.middle_baseline=middle_baseline;self.worker=worker;self.lock=threading.RLock();self.wake=threading.Event();self.latest={};self.budgets={}
        self.jobs=json.loads((self.root/'jobs.json').read_text()) if (self.root/'jobs.json').is_file() else {}
        for job in self.jobs.values():
            if job['status'] in ('running','queued'):job['status']='queued'
        self.worlds={}
        for path in self.root.glob('*/world.json'):
            world=json.loads(path.read_text(encoding='utf-8'));self.worlds[world['id']]=world
        if 'middle-earth' not in self.worlds:
            self._save_world({'id':'middle-earth','title':'Middle-earth','kind':'middle-earth','revision':'middle-earth-native-v1',
                'geometry':{'map_width_px':7680,'map_height_px':4386,'native_max_z':2,'extended_min_z':-2,'extended_max_z':8},
                'generation_prompt':'Add dispersed hobbit dwellings, winding lanes, gardens and fields. Top-down Shire parchment map. Preserve river and road connections. Use surrounding context.',
                'nodes':[],'edges':[],'research':{'status':'existing_application_preset','sources':[]},
                'attribution':'Fan map source: Fraser Marlow / middle-earth-interactive-map.web.app. No Tolkien estate rights claimed.'})
        self.thread=None
        if start_worker:self.thread=threading.Thread(target=self._run,daemon=True);self.thread.start();self.wake.set()
    def _save_world(self,world):
        self.worlds[world['id']]=world;atomic_json(self.root/world['id']/'world.json',world)
    def create(self,prompt,ai_outline=None):
        world=plan_text_world(prompt,ai_outline);world.update(id='world-'+uuid.uuid4().hex[:12],kind='knowledge',created_at_utc=datetime.now(timezone.utc).isoformat())
        world['revision']=digest(world);world['attribution']=('Original local AI topic outline (unverified)' if ai_outline else 'Original local topic scaffold')+'; generated imagery is an unapproved draft.'
        with self.lock:self._save_world(world)
        for z,x,y in [(0,0,0),(1,0,0),(1,1,0),(1,0,1),(1,1,1)]:self.base(world['id'],z,x,y)
        return world
    def world(self,wid):
        if wid not in self.worlds:raise ValueError('Unknown world')
        return self.worlds[wid]
    def geometry(self,wid):return PyramidGeometry(**self.world(wid)['geometry'])
    def tile_dir(self,wid,z,x,y):return self.root/wid/'generated'/f'{z}-{x}-{y}'
    def metadata(self,wid,z,x,y):
        path=self.tile_dir(wid,z,x,y)/'manifest.json';return json.loads(path.read_text()) if path.is_file() else None
    def base(self,wid,z,x,y):
        world=self.world(wid);geo=self.geometry(wid);geo.validate(z,x,y)
        atlas=has_topic_atlas(world)
        version=f"{world['theme']}-atlas-v1-" if atlas else ''
        path=self.root/wid/'base'/f'{version}{z}-{x}-{y}.png'
        if path.is_file():return read_image(path)
        if world['kind']=='middle-earth':image=self.middle_baseline(z,x,y)
        elif atlas:image=render_atlas_tile(world,z,x,y,geo.span(z))
        else:
            span=geo.span(z);x0=x*span;y0=y*span;scale=256/span
            history=world['theme']=='history';image=Image.new('RGB',(256,256),'#e4d8b3' if history else '#122936');draw=ImageDraw.Draw(image)
            nodes={n['id']:n for n in world['nodes']}
            def point(n):return((n['x']-x0)*scale,(n['y']-y0)*scale)
            for a,b in world['edges']:
                if max(nodes[a]['min_z'],nodes[b]['min_z'])<=z:draw.line([point(nodes[a]),point(nodes[b])],fill='#8e7749' if history else '#568b9d',width=2)
            for n in nodes.values():
                if n['min_z']>z:continue
                px,py=point(n);radius=max(3,min(42,(90 if n['depth']<2 else 26)*scale))
                fill=['#b39152','#c6aa70','#d3be8c','#b9a16c'][n['depth']] if history else ['#e3ac66','#538b9e','#426b9b','#54827f'][n['depth']]
                draw.ellipse((px-radius,py-radius,px+radius,py+radius),fill=fill,outline='#e8d8ad' if history else '#89bdcc',width=1)
        path.parent.mkdir(parents=True,exist_ok=True);tmp=path.with_name(path.name+'.'+uuid.uuid4().hex+'.tmp');tmp.write_bytes(png(image));tmp.replace(path)
        with self.lock:
            cached=list(path.parent.glob('*.png'))
            for old in sorted(cached,key=lambda p:p.stat().st_mtime)[:max(0,len(cached)-512)]:
                if old!=path:old.unlink(missing_ok=True)
        return image
    def image(self,wid,z,x,y,mode='original'):
        self.geometry(wid).validate(z,x,y)
        path=self.tile_dir(wid,z,x,y)/('result.png' if mode=='raw' else 'blended.png')
        if mode!='original' and self.metadata(wid,z,x,y) and path.is_file():return read_image(path),'generated'
        if mode!='original':
            geo=self.geometry(wid)
            for az in range(z-1,geo.extended_min_z-1,-1):
                factor=2**(z-az);p=self.tile_dir(wid,az,x//factor,y//factor)/('result.png' if mode=='raw' else 'blended.png')
                if self.metadata(wid,az,x//factor,y//factor) and p.is_file():
                    im=read_image(p);crop=(x%factor*256/factor,y%factor*256/factor,(x%factor+1)*256/factor,(y%factor+1)*256/factor)
                    return im.transform((256,256),Image.Transform.EXTENT,crop,Image.Resampling.BICUBIC),'inherited_parent'
        return self.base(wid,z,x,y),'original'
    def _persist_jobs(self):atomic_json(self.root/'jobs.json',self.jobs)
    def submit(self,wid,tiles,client,epoch,keep=False):
        world=self.world(wid)
        if not isinstance(client,str) or not 1<=len(client)<=80 or type(epoch)is not int or epoch<0:raise ValueError('Invalid viewport identity')
        if not isinstance(tiles,list) or len(tiles)>9:raise ValueError('At most 9 tiles per request')
        coordinates=[]
        for tile in tiles:
            if not isinstance(tile,dict):raise ValueError('Tile coordinates required')
            z,x,y=(tile.get(k) for k in ('z','x','y'));self.geometry(wid).validate(z,x,y);coordinates.append((z,x,y))
        with self.lock:
            if epoch<self.latest.get(client,0):return {'jobs':[],'superseded':True}
            self.latest[client]=epoch
            for job in self.jobs.values():
                if job['status']=='queued' and not job.get('keep'):
                    job['subscribers']={c:e for c,e in job['subscribers'].items() if c!=client or e>=epoch}
                    if not job['subscribers']:job['status']='cancelled'
            selected=[]
            for z,x,y in coordinates:
                if self.metadata(wid,z,x,y):continue
                key=digest({'world':wid,'revision':world['revision'],'tile':[z,x,y],'prompt':world['generation_prompt'],'steps':20,'seed':42})
                old=self.jobs.get(key)
                if old and old['status'] in ('queued','running','completed','failed'):
                    old['subscribers'][client]=epoch;selected.append(old);continue
                if sum(j['status'] in ('queued','running') for j in self.jobs.values())>=24:break
                budget=(client,wid)
                if not keep and self.budgets.get(budget,0)>=12:break
                self.budgets[budget]=self.budgets.get(budget,0)+1
                job={'id':key,'world_id':wid,'world_revision':world['revision'],'tile':[z,x,y],'status':'queued','subscribers':{client:epoch},'keep':keep,'created':time.time()}
                self.jobs[key]=job;selected.append(job)
            self._persist_jobs();self.wake.set();return {'jobs':[{k:v for k,v in j.items() if k!='subscribers'} for j in selected], 'new_tile_budget_used':self.budgets.get((client,wid),0)}
    def status(self,wid):
        with self.lock:
            jobs=[{k:v for k,v in j.items() if k!='subscribers'} for j in self.jobs.values() if j['world_id']==wid]
        tiles=[]
        for path in (self.root/wid/'generated').glob('*/manifest.json'):
            m=json.loads(path.read_text());tiles.append({k:m.get(k) for k in ('tile','artifact_sha256','elapsed_seconds','imported','source_origin','draft_only')})
        return {'jobs':jobs[-100:],'tiles':tiles,'limits':{'queue':24,'viewport_batch':3,'new_tiles_per_client_world':12}}
    def import_middle(self,runs):
        count=0
        for p in Path(runs).glob('*/manifest.json'):
            m=json.loads(p.read_text(encoding='utf-8'))
            if p.parent.name not in ('shire-short-prompt','shire-adjacent-eval','shire-deep-eval','minas-tirith-eval') and not p.parent.name.startswith('me-nav-'):continue
            if not m.get('success') or not (p.parent/'result.png').is_file():continue
            z,x,y=m['target'];folder=self.tile_dir('middle-earth',z,x,y)
            if (folder/'manifest.json').exists():
                for name in ('source','context','parent'):
                    source_path=p.parent/(name+'.png')
                    if source_path.is_file() and not (folder/(name+'.png')).exists():(folder/(name+'.png')).write_bytes(source_path.read_bytes())
                continue
            source=read_image(p.parent/'source.png');result=read_image(p.parent/'result.png');folder.mkdir(parents=True,exist_ok=True)
            raw=(p.parent/'result.png').read_bytes();(folder/'result.png').write_bytes(raw);(folder/'blended.png').write_bytes(png(edge_blend(source,result)))
            for name in ('source','context','parent'):
                if (p.parent/(name+'.png')).is_file():(folder/(name+'.png')).write_bytes((p.parent/(name+'.png')).read_bytes())
            atomic_json(folder/'manifest.json',{'tile':[z,x,y],'imported':True,'source_origin':'recorded_native_crop','source_sha256':m['source_sha256'],'artifact_sha256':hashlib.sha256(raw).hexdigest(),'elapsed_seconds':m['elapsed_seconds'],'draft_only':True,'original_manifest':m});count+=1
        return count
    def _generate(self,job):
        wid=job['world_id'];z,x,y=job['tile'];world=self.world(wid);geo=self.geometry(wid)
        source,origin=self.image(wid,z,x,y,'blended');context=Image.new('RGB',(768,768),'#122936');dependencies={};w,h=geo.grid(z)
        for dy in (-1,0,1):
            for dx in (-1,0,1):
                if 0<=x+dx<w and 0<=y+dy<h:
                    image,kind=self.image(wid,z,x+dx,y+dy,'blended');context.paste(image,((dx+1)*256,(dy+1)*256));dependencies[f'{z}/{x+dx}/{y+dy}']={'sha256':hashlib.sha256(png(image)).hexdigest(),'origin':kind}
        payload={'image_base64':base64.b64encode(png(source)).decode(),'context_mosaic_base64':base64.b64encode(png(context)).decode(),
                 'prompt':world['generation_prompt'],'coordinate_space':'pixel','map_geometry':world['geometry'],'z':z,'x':x,'y':y,
                 'steps':20,'seed':42,'world_revision':world['revision'],'world_sha256':digest(world),'scene_id':wid}
        folder=self.tile_dir(wid,z,x,y);folder.mkdir(parents=True,exist_ok=True)
        (folder/'source.png').write_bytes(png(source));(folder/'context.png').write_bytes(png(context))
        atomic_json(folder/'request.json',{k:v for k,v in payload.items() if k not in ('image_base64','context_mosaic_base64')})
        deadline=time.monotonic()+900
        while True:
            response=requests.post(self.worker+'/edit',json=payload,timeout=(10,600))
            if response.status_code==429 and time.monotonic()<deadline:time.sleep(5);continue
            if not response.ok:
                try:detail=response.json().get('detail','Request rejected')
                except ValueError:detail='Request rejected'
                atomic_json(folder/'rejection.json',{'http_status':response.status_code,'detail':detail,'tile':[z,x,y],
                    'world_revision':world['revision'],'source_sha256':hashlib.sha256(png(source)).hexdigest(),'draft_only':True})
                raise ValueError(f'Worker rejected tile ({response.status_code}): {detail}')
            break
        data=response.json();raw=base64.b64decode(data.pop('image_base64'),validate=True)
        with Image.open(io.BytesIO(raw)) as im:
            if im.size!=(256,256):raise ValueError('Invalid result dimensions')
            result=im.convert('RGB')
        if data.get('world_revision')!=world['revision'] or self.world(wid)['revision']!=job['world_revision']:raise ValueError('Stale world result')
        for name,image in [('source',source),('context',context),('blended',edge_blend(source,result))]:(folder/(name+'.png')).write_bytes(png(image))
        (folder/'result.png').write_bytes(raw)
        manifest={'tile':[z,x,y],'world_revision':world['revision'],'artifact_sha256':hashlib.sha256(raw).hexdigest(),'source_origin':origin,
                  'context_dependencies':dependencies,'context_plan':plan_context(geo,z,x,y),'source_sha256':hashlib.sha256(png(source)).hexdigest(),
                  'draft_only':True,'edge_compositing':'24px feather; original border pixels retained; no semantic geometry guarantee',**data}
        atomic_json(folder/'manifest.json',manifest);return manifest
    def _run(self):
        while True:
            with self.lock:
                queued=[j for j in self.jobs.values() if j['status']=='queued'];queued.sort(key=lambda j:(j.get('keep',False),j['created']))
                job=queued[0] if queued else None
                if job:job['status']='running';self._persist_jobs()
            if not job:self.wake.wait(2);self.wake.clear();continue
            try:
                result=self._generate(job)
                with self.lock:job.update(status='completed',artifact_sha256=result['artifact_sha256'],elapsed_seconds=result.get('elapsed_seconds'))
            except Exception as error:
                with self.lock:job.update(status='failed',error=str(error)[:240])
            with self.lock:self._persist_jobs()
