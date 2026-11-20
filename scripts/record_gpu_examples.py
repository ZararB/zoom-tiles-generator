"""Run real optional GPU drafts from browser-captured source tiles and save proof."""
import argparse
import base64
import hashlib
import io
import json
import time
from datetime import datetime,timezone
from pathlib import Path
from urllib.parse import urlparse
import requests
from PIL import Image

ROOT=Path(__file__).resolve().parents[1]
def sha(raw):return hashlib.sha256(raw).hexdigest()
def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--base',default='http://127.0.0.1:8888')
    parser.add_argument('--steps',type=int,default=4,choices=range(1,51))
    parser.add_argument('--seed',type=int,default=42)
    parser.add_argument('--case',action='append',help='Record only this case ID; repeat for multiple cases')
    args=parser.parse_args();base=args.base.rstrip('/')
    if urlparse(base).hostname not in ('127.0.0.1','localhost','::1'):
        raise SystemExit('The example recorder only calls an explicitly local worker.')
    health=requests.get(base+'/health',timeout=10);health.raise_for_status();health=health.json()
    if not health.get('ok') or not health.get('cuda'):raise SystemExit('A ready CUDA worker is required; no fabricated fallback.')
    records=[]
    for path in sorted((ROOT/'examples/gpu').glob('*/input.json')):
        data=json.loads(path.read_text(encoding='utf-8'));source=(path.parent/'source.png').read_bytes()
        if args.case and data['case_id'] not in args.case:continue
        assert sha(source)==data['source_sha256']
        payload={k:data[k] for k in ['prompt','z','x','y','world_revision','world_sha256','scene_id']}
        payload.update({'image_base64':base64.b64encode(source).decode(),'steps':args.steps,'seed':args.seed})
        previous=path.parent/'manifest.json'
        if previous.is_file():
            existing=json.loads(previous.read_text(encoding='utf-8'))
            output=path.parent/'result.png'
            if existing.get('success') and existing.get('source_sha256')==sha(source) and existing.get('seed')==args.seed and existing.get('steps')==args.steps and output.is_file() and sha(output.read_bytes())==existing['output_sha256']:
                records.append({'case_id':data['case_id'],'status':'passed','elapsed_seconds':existing['elapsed_seconds'],'output_sha256':existing['output_sha256'],'reused_recording':True});continue
        started=time.perf_counter();response=requests.post(base+'/edit',json=payload,timeout=(10,1800))
        if not response.ok:
            rejected={'schema_version':1,'kind':'actual_worker_request','case_id':data['case_id'],'status':'rejected',
                'created_at_utc':datetime.now(timezone.utc).isoformat(),'http_status':response.status_code,
                'detail':response.json().get('detail','Worker rejected the request'),'steps':args.steps,'seed':args.seed,
                'source_sha256':sha(source),'world_sha256':data['world_sha256'],'draft_only':True}
            previous.write_text(json.dumps(rejected,indent=2),encoding='utf-8')
            records.append({'case_id':data['case_id'],'status':'rejected','http_status':response.status_code,'detail':rejected['detail']})
            print(json.dumps(records[-1]),flush=True);continue
        result=response.json();raw=base64.b64decode(result.pop('image_base64'),validate=True)
        assert result['success'] and result['world_sha256']==data['world_sha256']
        assert result['gpu_peak_allocated_bytes']>0
        with Image.open(io.BytesIO(raw)) as image:
            assert image.size==(256,256);image.verify()
        (path.parent/'result.png').write_bytes(raw)
        manifest={'schema_version':1,'kind':'actual_cuda_inference','case_id':data['case_id'],
            'created_at_utc':datetime.now(timezone.utc).isoformat(),'hardware':health['gpu'],
            'prompt':data['prompt'],'source_sha256':sha(source),'output_sha256':sha(raw),
            'client_elapsed_seconds':round(time.perf_counter()-started,3),'draft_only':True,
            'validation':'PNG integrity, world metadata and CUDA allocation checked; visual quality is not scored',**result}
        (path.parent/'manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
        records.append({'case_id':data['case_id'],'status':'passed','elapsed_seconds':result['elapsed_seconds'],'output_sha256':sha(raw)})
        print(json.dumps(records[-1]),flush=True)
    if not records:raise SystemExit('Capture examples/gpu/<case>/source.png and input.json first; see docs/RECORDING.md.')
    all_records=[]
    for path in sorted((ROOT/'examples/gpu').glob('*/manifest.json')):
        item=json.loads(path.read_text(encoding='utf-8'))
        all_records.append({k:item[k] for k in ['case_id','kind','status','success','http_status','detail','steps','seed','elapsed_seconds','output_sha256'] if k in item})
    (ROOT/'examples/results/gpu-validation.json').write_text(json.dumps({'schema_version':1,'kind':'actual_worker_requests','records':all_records},indent=2),encoding='utf-8')
if __name__=='__main__':main()
