"""Use the existing app's pixel-space preset and real native tiles for GPU tests.

Native artwork and model outputs stay in ignored .runtime by default. No Django,
credits, routing or authoritative AI geometry is simulated by this adapter.
"""
import argparse
import base64
import hashlib
import io
import json
import sys
import time
import uuid
from pathlib import Path
from datetime import datetime, timezone

import requests
from PIL import Image, ImageDraw
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from zoom_tiles.pyramid import PyramidGeometry, plan_context, generation_brief

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / 'examples/pyramid/middle-earth'
DATA = ROOT / '.runtime/pyramid'
PRESET = json.loads((FIXTURES/'preset.json').read_text())
GEO = PyramidGeometry(**{k: PRESET[k] for k in ('map_width_px','map_height_px','native_max_z','extended_min_z','extended_max_z')})


def png(image):
    stream=io.BytesIO(); image.save(stream,'PNG'); return stream.getvalue()


def native(z,x,y):
    if not 0<=z<=GEO.native_max_z: raise ValueError('Native zoom only')
    GEO.validate(z,x,y); path=DATA/'native'/f'{z}-{x}-{y}.jpg'
    if path.is_file(): return Image.open(io.BytesIO(path.read_bytes())).convert('RGB')
    response=requests.get(PRESET['upstream_url_template'].format(z=z,x=x,y=y),timeout=(10,45))
    response.raise_for_status()
    if len(response.content)>2_000_000: raise ValueError('Oversized upstream tile')
    with Image.open(io.BytesIO(response.content)) as image:
        if image.size!=(256,256): raise ValueError('Unexpected upstream tile size')
        result=image.convert('RGB');result.load()
    path.parent.mkdir(parents=True,exist_ok=True);temporary=path.with_name(path.name+'.'+uuid.uuid4().hex+'.tmp');temporary.write_bytes(response.content);temporary.replace(path)
    return result


def baseline(z,x,y):
    GEO.validate(z,x,y)
    if z<0:
        factor=2**(-z); canvas=Image.new('RGB',(256*factor,256*factor),'#e9ddbf')
        w,h=GEO.grid(0)
        for dy in range(factor):
            for dx in range(factor):
                nx,ny=x*factor+dx,y*factor+dy
                if nx<w and ny<h:canvas.paste(native(0,nx,ny),(dx*256,dy*256))
        return canvas.resize((256,256),Image.Resampling.LANCZOS)
    nz=min(z,GEO.native_max_z);factor=2**(z-nz)
    image=native(nz,x//factor,y//factor)
    crop=(x%factor*256/factor,y%factor*256/factor,(x%factor+1)*256/factor,(y%factor+1)*256/factor)
    return image.transform((256,256),Image.Transform.EXTENT,crop,Image.Resampling.BICUBIC)


def prepare(z,x,y,user_direction='',region='The Shire'):
    plan=plan_context(GEO,z,x,y);source=baseline(z,x,y)
    mosaic=Image.new('RGB',(768,768),'#e9ddbf');hashes={}
    w,h=GEO.grid(z)
    for dy in (-1,0,1):
        for dx in (-1,0,1):
            if 0<=x+dx<w and 0<=y+dy<h:
                tile=baseline(z,x+dx,y+dy);mosaic.paste(tile,((dx+1)*256,(dy+1)*256))
                hashes[f'{z}/{x+dx}/{y+dy}']=hashlib.sha256(png(tile)).hexdigest()
    # Parent is retained separately, not silently claimed to be a second model input.
    parent=baseline(z-1,x//2,y//2) if z>GEO.extended_min_z else source
    hashes['parent']=hashlib.sha256(png(parent)).hexdigest()
    research=json.loads((FIXTURES/'research.json').read_text()) if region=='The Shire' else {
        'region':region,'sources':[],'claims':[],
        'inferences':['Detail is inferred from native imagery and the explicit test direction; no researched canonical layout is asserted.'],
        'constraints':['Preserve visible water and road connections; generated detail remains a draft.']}
    brief=generation_brief(plan,research,user_direction,'middle-earth-test-v1',hashes)
    return source,mosaic,parent,brief


def run(case,z,x,y,direction='',steps=20,worker='http://127.0.0.1:8888',region='The Shire'):
    if not case.replace('-','').isalnum():raise ValueError('Invalid case ID')
    source,mosaic,parent,brief=prepare(z,x,y,direction,region)
    folder=DATA/'runs'/case;folder.mkdir(parents=True,exist_ok=True)
    for name,image in [('source',source),('context',mosaic),('parent',parent)]: (folder/(name+'.png')).write_bytes(png(image))
    (folder/'brief.json').write_text(json.dumps(brief,indent=2),encoding='utf-8')
    # The full cited research remains in the brief. CLIP has only 77 tokens:
    # send an explicit compact interpretation, with user direction first.
    prompt=((direction or 'Add dispersed hobbit dwellings, winding lanes, gardens and fields.')+
            ' Top-down Shire parchment map. Research-inspired rural settlement. Preserve river and road connections. No modern buildings. Use surrounding context.') if region=='The Shire' else (
            (direction or 'Add plausible fantasy settlement detail.')+f' Top-down fantasy map near {region}. Preserve roads, water, terrain. Use surrounding context.')
    if len(prompt)>2000:raise ValueError('Combined research and user prompt exceeds worker limit')
    payload={'image_base64':base64.b64encode(png(source)).decode(),'context_mosaic_base64':base64.b64encode(png(mosaic)).decode(),
             'coordinate_space':'pixel','map_geometry':GEO.__dict__,'z':z,'x':x,'y':y,'prompt':prompt,
             'steps':steps,'seed':42,'scene_id':'middle-earth','world_revision':'middle-earth-test-v1','world_sha256':brief['sha256']}
    health=requests.get(worker+'/health',timeout=10).json()
    if not health.get('cuda') or not health.get('ok'):raise RuntimeError('Ready CUDA worker required')
    start=time.monotonic();response=requests.post(worker+'/edit',json=payload,timeout=(10,900))
    record={'case':case,'region':region,'target':[z,x,y],'http_status':response.status_code,'steps':steps,'seed':42,'brief_sha256':brief['sha256'],'image_prompt':prompt,
            'user_direction':direction,'created_at_utc':datetime.now(timezone.utc).isoformat(),'draft_only':True,
            'client_elapsed_seconds':round(time.monotonic()-start,3),'hardware':health['gpu'],
            'geometry_generated':False,'context_sent':'same-zoom 3x3 native-derived mosaic; ancestor saved separately',
            'source_sha256':hashlib.sha256(png(source)).hexdigest()}
    result=response.json()
    if response.ok:
        raw=base64.b64decode(result.pop('image_base64'),validate=True)
        with Image.open(io.BytesIO(raw)) as image:
            if image.size!=(256,256):raise ValueError('Wrong output size')
            image.verify()
        if result.get('coordinate_space')!='pixel' or result.get('x')!=x:raise ValueError('Worker did not honor pixel-space contract')
        (folder/'result.png').write_bytes(raw);record.update(result);record['output_sha256']=hashlib.sha256(raw).hexdigest()
        comparison=Image.new('RGB',(1024,310),'#f2ead7');draw=ImageDraw.Draw(comparison)
        for index,(label,image) in enumerate([('Source crop',source),('3x3 context',mosaic),('Parent (reference)',parent),('AI raster draft',Image.open(io.BytesIO(raw)))]):
            comparison.paste(image.resize((256,256)),(index*256,30));draw.text((index*256+8,8),label,fill='black')
        draw.text((8,291),'Fan artwork: Fraser Marlow upstream. Generated detail is speculative; not canonical.',fill='black')
        comparison.save(folder/'comparison.jpg',quality=90)
    else:record['detail']=result.get('detail','Worker rejected request')
    (folder/'manifest.json').write_text(json.dumps(record,indent=2),encoding='utf-8')
    print(json.dumps(record),flush=True);return record


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--case',default='shire-context');parser.add_argument('--z',type=int,default=4)
    parser.add_argument('--x',type=int,default=43);parser.add_argument('--y',type=int,default=19)
    parser.add_argument('--direction',default='');parser.add_argument('--steps',type=int,default=20,choices=range(1,51))
    parser.add_argument('--region',default='The Shire')
    args=parser.parse_args();run(args.case,args.z,args.x,args.y,args.direction,args.steps,region=args.region)
