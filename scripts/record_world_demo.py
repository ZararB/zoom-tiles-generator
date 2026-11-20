"""Verify explicitly selected demo worlds; raw prompts/art remain in runtime storage."""
import argparse
import hashlib
import json
import sys
from pathlib import Path
import requests
from PIL import Image,ImageChops
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from zoom_tiles.navigation import WorldEngine
from pyramid_lab import baseline

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--world',action='append',required=True);parser.add_argument('--mlflow',action='store_true');args=parser.parse_args()
    engine=WorldEngine(ROOT/'.runtime/worlds',baseline,start_worker=False);engine.import_middle(ROOT/'.runtime/pyramid/runs')
    selected=list(dict.fromkeys(['middle-earth']+args.world));records=[]
    for wid in selected:
        world=engine.world(wid);state=requests.get('http://127.0.0.1:8796/api/worlds/'+wid+'/status',timeout=10).json();artifacts=[]
        for path in (ROOT/'.runtime/worlds'/wid/'generated').glob('*/manifest.json'):
            m=json.loads(path.read_text());raw=path.parent/'result.png';assert hashlib.sha256(raw.read_bytes()).hexdigest()==m['artifact_sha256']
            with Image.open(raw) as im:assert im.size==(256,256)
            source=path.parent/'source.png';blended=path.parent/'blended.png';edges=True
            if source.exists():
                a=Image.open(source).convert('RGB');b=Image.open(blended).convert('RGB')
                for box in ((0,0,256,1),(0,255,256,256),(0,0,1,256),(255,0,256,256)):
                    if ImageChops.difference(a.crop(box),b.crop(box)).getbbox() is not None:edges=False
                assert edges
            artifacts.append({k:m.get(k) for k in ('tile','artifact_sha256','source_origin','elapsed_seconds','imported','draft_only')})
        records.append({'id':wid,'title':world['title'],'kind':world['kind'],'revision':world['revision'],'planner':world.get('planner'),
                        'planner_metadata':world.get('planner_metadata',{}),'node_count':len(world.get('nodes',[])),
                        'research_status':world.get('research',{}).get('status'),'artifacts':artifacts,'all_artifact_hashes_match':True,
                        'source_border_pixels_preserved':True,'jobs':[{k:j.get(k) for k in ('id','tile','status','elapsed_seconds','error')} for j in state['jobs']]})
    fresh=[]
    for path in sorted((ROOT/'.runtime/pyramid/runs').glob('me-nav-*/manifest.json')):
        m=json.loads(path.read_text());assert m.get('success');assert hashlib.sha256((path.parent/'result.png').read_bytes()).hexdigest()==m['output_sha256']
        fresh.append({k:m[k] for k in ('case','target','elapsed_seconds','output_sha256','steps','seed')})
    result={'schema_version':1,'kind':'actual_local_text_and_cuda_demo','worlds':records,'new_middle_earth_requests':fresh,
            'quality_approved':False,'notes':['AI outlines are unverified, not live research.','Source labels and links remain vectors.','Edge compositing is not semantic geometry correctness.','A science overview was checker-rejected; source fallback remained visible.']}
    browser=ROOT/'.runtime/world-explorer/browser-validation.json'
    if browser.is_file():result['browser']=json.loads(browser.read_text())
    if args.mlflow:
        import mlflow
        mlflow.set_tracking_uri('sqlite:///'+(ROOT/'.runtime/mlflow.db').as_posix());mlflow.set_experiment('zoom-tiles-generator-worlds')
        with mlflow.start_run(run_name='text-worlds-and-navigable-middle-earth') as run:
            mlflow.log_metrics({'new_middle_earth_tiles':len(fresh),'demo_worlds':len(records),'quality_approved':0})
            mlflow.log_dict(result,'validation.json')
            for wid in selected:mlflow.log_artifacts(str(ROOT/'.runtime/worlds'/wid),artifact_path='worlds/'+wid)
            if (ROOT/'.runtime/world-explorer/screenshots').is_dir():mlflow.log_artifacts(str(ROOT/'.runtime/world-explorer/screenshots'),artifact_path='browser-views')
            result['mlflow_run_id']=run.info.run_id
    target=ROOT/'examples/results/world-navigation-validation.json';target.write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps({'worlds':len(records),'new_middle_earth_tiles':len(fresh),'artifacts_verified':sum(len(r['artifacts']) for r in records),'mlflow_run_id':result.get('mlflow_run_id')}))

if __name__=='__main__':main()
