"""Single-GPU, viewport-prioritized refinement with a bounded persistent result cache.

Vector rendering never waits on this queue. Production can replace this local
adapter with its job broker while retaining the API and artifact keys.
"""
import base64
import hashlib
import json
import threading
import time
import urllib.request
from pathlib import Path


class TileJobs:
    def __init__(self,root,worker,execute=None,identity=None):
        self.root=Path(root);self.worker=worker.rstrip('/')
        self.lock=threading.RLock();self.jobs={};self.latest={};self.sequence=0
        self.thread=None;self.execute=execute or self._execute
        self.identity=identity or self._identity;self.model=None;self.model_time=0

    def _identity(self):
        if not self.model or time.monotonic()-self.model_time>15:
            with urllib.request.urlopen(self.worker+'/health',timeout=5) as response:
                health=json.load(response)
            if not health.get('ok') or not health.get('cuda'):raise ValueError('GPU worker is not ready')
            self.model={k:health.get(k) for k in ('model_id','revision','inference_size','offload')}
            self.model_time=time.monotonic()
        return self.model

    def _execute(self,payload):
        request=urllib.request.Request(self.worker+'/edit',data=json.dumps(payload).encode(),
            headers={'Content-Type':'application/json'},method='POST')
        with urllib.request.urlopen(request,timeout=1800) as response:return json.load(response)

    def _path(self,key):return self.root/(key+'.json')

    def submit(self,body):
        client=body.get('client_id');viewport=body.get('viewport_id');payload=body.get('payload')
        if not isinstance(client,str) or not 1<=len(client)<=80:raise ValueError('client_id required')
        if type(viewport) is not int or not 0<=viewport<=2**53:raise ValueError('Invalid viewport_id')
        if not isinstance(payload,dict):raise ValueError('Tile payload required')
        if not isinstance(payload.get('prompt'),str) or not 1<=len(payload['prompt'])<=2000:raise ValueError('Prompt required')
        source=payload.get('image_base64');context=payload.get('context_mosaic_base64','')
        if not isinstance(source,str) or not source or len(source)>6_000_000:raise ValueError('Source image required')
        if not isinstance(context,str) or len(context)>6_000_000:raise ValueError('Context is too large')
        for value in (source,context):
            try:base64.b64decode(value,validate=True)
            except Exception as exc:raise ValueError('Invalid image encoding') from exc
        if type(payload.get('steps',20)) is not int or not 1<=payload.get('steps',20)<=50:raise ValueError('Invalid steps')
        if type(payload.get('seed',42)) is not int:raise ValueError('Invalid seed')
        z,x,y=(payload.get(k) for k in ('z','x','y'))
        coordinate_space=payload.get('coordinate_space','slippy')
        if coordinate_space=='pixel':
            from .pyramid import PyramidGeometry
            PyramidGeometry(**payload.get('map_geometry',{})).validate(z,x,y)
        elif coordinate_space!='slippy' or any(type(v) is not int for v in (z,x,y)) or not 0<=z<=18 or not 0<=x<2**z or not 0<=y<2**z:raise ValueError('Invalid tile coordinate')
        model=self.identity()
        descriptor={k:payload.get(k) for k in ('z','x','y','coordinate_space','map_geometry','world_sha256','scene_id','map_name_override','prompt')}
        descriptor.update({'model':model,'pipeline':'detail-preserving-v2','steps':payload.get('steps',20),
            'seed':payload.get('seed',42),'source_sha256':hashlib.sha256(base64.b64decode(source)).hexdigest(),
            'context_sha256':hashlib.sha256(base64.b64decode(context)).hexdigest()})
        key=hashlib.sha256(json.dumps(descriptor,sort_keys=True,separators=(',',':')).encode()).hexdigest()
        priority=body.get('priority',0)
        if type(priority) not in (int,float) or not 0<=priority<=10000:raise ValueError('Invalid priority')
        with self.lock:
            if viewport<self.latest.get(client,0):raise ValueError('Superseded viewport')
            self.latest[client]=viewport
            for job in self.jobs.values():
                if job['status']=='queued':
                    job['subscribers']={c:v for c,v in job['subscribers'].items() if c!=client or v==viewport}
                    if not job['subscribers']:job['status']='cancelled';job.pop('payload',None)
            if self._path(key).exists():
                return {'id':key,'status':'completed','cache_hit':True,'descriptor':descriptor}
            existing=self.jobs.get(key)
            if existing and existing['status'] in ('queued','running'):
                existing['subscribers'][client]=viewport
                existing['priority']=min(existing['priority'],priority)
                return self._public(existing)
            if sum(j['status']=='queued' for j in self.jobs.values())>=32:raise ValueError('Queue is full')
            self.sequence+=1
            job={'id':key,'status':'queued','cache_hit':False,'priority':priority,'sequence':self.sequence,
                'subscribers':{client:viewport},'payload':payload,'descriptor':descriptor,'created_at':time.time()}
            self.jobs[key]=job
            if len(self.jobs)>512:
                for old in list(self.jobs):
                    if len(self.jobs)<=384:break
                    if self.jobs[old]['status'] not in ('queued','running'):del self.jobs[old]
            if not self.thread or not self.thread.is_alive():
                self.thread=threading.Thread(target=self._drain,daemon=True);self.thread.start()
            return self._public(job)

    def _public(self,job):return {k:v for k,v in job.items() if k not in ('payload','subscribers','sequence')}

    def get(self,key):
        with self.lock:
            if self._path(key).exists():return json.loads(self._path(key).read_text(encoding='utf-8'))
            job=self.jobs.get(key)
            return self._public(job) if job else None

    def cancel(self,client,viewport):
        if not isinstance(client,str) or type(viewport) is not int or not 0<=viewport<=2**53:raise ValueError('Invalid cancellation')
        with self.lock:
            if viewport<self.latest.get(client,0):return self.stats()
            self.latest[client]=max(viewport,self.latest.get(client,0))
            for job in self.jobs.values():
                if job['status']=='queued':
                    # A delayed cancel for the new frontier must retain work that
                    # has already subscribed at that epoch (or a newer one).
                    job['subscribers']={c:v for c,v in job['subscribers'].items() if c!=client or v>=viewport}
                    if not job['subscribers']:job['status']='cancelled';job.pop('payload',None)
            return self.stats()

    def stats(self):
        with self.lock:
            return {'queued':sum(j['status']=='queued' for j in self.jobs.values()),
                'running':sum(j['status']=='running' for j in self.jobs.values()),
                'cached':len(list(self.root.glob('*.json'))),'limit_queued':32,'concurrency':1}

    def _drain(self):
        while True:
            with self.lock:
                queued=[j for j in self.jobs.values() if j['status']=='queued']
                if not queued:self.thread=None;return
                job=min(queued,key=lambda j:(j['priority'],-j['sequence']))
                job['status']='running';payload=job.pop('payload')
            try:
                result=self.execute(payload)
                if not result.get('success') or not result.get('image_base64'):raise ValueError('Worker returned no image')
                if result.get('model_revision') and result['model_revision']!=job['descriptor']['model'].get('revision'):
                    raise ValueError('Worker model changed while queued; resubmit with current model')
                raw=base64.b64decode(result['image_base64'],validate=True)
                record={'id':job['id'],'status':'completed','cache_hit':False,'descriptor':job['descriptor'],
                    'completed_at':time.time(),'output_sha256':hashlib.sha256(raw).hexdigest(),'result':result}
                self.root.mkdir(parents=True,exist_ok=True)
                with self.lock:
                    target=self._path(job['id']);temporary=target.with_suffix('.tmp')
                    temporary.write_text(json.dumps(record),encoding='utf-8');temporary.replace(target)
                    files=sorted(self.root.glob('*.json'),key=lambda p:p.stat().st_mtime)
                    total=sum(p.stat().st_size for p in files)
                    while len(files)>256 or total>256*1024*1024:
                        path=files.pop(0);total-=path.stat().st_size;path.unlink()
                    job['status']='completed'
            except Exception as exc:
                with self.lock:job['status']='failed';job['error']=str(exc)[:500]
