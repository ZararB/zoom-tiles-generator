"""Record a current Earth control, verify real artifacts and optionally log MLflow."""
import argparse
import base64
import hashlib
import json
import shutil
import time
from datetime import datetime,timezone
import requests
from generation_results import ROOT,catalog

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--rerun-earth',action='store_true');parser.add_argument('--mlflow',action='store_true');args=parser.parse_args()
    output=ROOT/'.runtime/evaluation';output.mkdir(parents=True,exist_ok=True)
    if args.rerun_earth:
        source=ROOT/'examples/gpu/coastal-headland';original=json.loads((source/'input.json').read_text(encoding='utf-8'))
        folder=output/'runs/earth-coastal-20';folder.mkdir(parents=True,exist_ok=True);shutil.copyfile(source/'source.png',folder/'source.png')
        raw=(folder/'source.png').read_bytes();payload={k:original[k] for k in ('prompt','z','x','y','world_revision','world_sha256','scene_id')}
        payload.update(image_base64=base64.b64encode(raw).decode(),steps=20,seed=42)
        start=time.monotonic();response=requests.post('http://127.0.0.1:8888/edit',json=payload,timeout=(10,900));data=response.json()
        record={'case':'earth-coastal-20','target':[original[k] for k in ('z','x','y')],'image_prompt':original['prompt'],'source_sha256':hashlib.sha256(raw).hexdigest(),
                'http_status':response.status_code,'created_at_utc':datetime.now(timezone.utc).isoformat(),'draft_only':True,'geometry_generated':False,
                'client_elapsed_seconds':round(time.monotonic()-start,3),'steps':20,'seed':42}
        if response.ok:
            image=base64.b64decode(data.pop('image_base64'),validate=True);(folder/'result.png').write_bytes(image);record.update(data);record['output_sha256']=hashlib.sha256(image).hexdigest()
        else:record.update(success=False,detail=data.get('detail','Rejected'))
        (folder/'manifest.json').write_text(json.dumps(record,indent=2),encoding='utf-8');print(json.dumps(record),flush=True)
    report=catalog()
    for record in report['records']:
        if record['success']:
            assert record['integrity']['source_hash_matches'] and record['integrity']['output_hash_matches']
            assert record['integrity']['output_dimensions']==[256,256]
    views=output/'browser-views.json'
    if views.exists():report['browser']=json.loads(views.read_text(encoding='utf-8'))
    report['summary']={'recorded_cases':len(report['records']),'inference_successes':sum(r['success'] for r in report['records']),
                       'quality_approved':0,'fresh_requests':4,'fresh_middle_earth_cases':['shire-adjacent-eval','shire-deep-eval','minas-tirith-eval']}
    if args.mlflow:
        import mlflow
        mlflow.set_tracking_uri('sqlite:///'+(ROOT/'.runtime/mlflow.db').as_posix());mlflow.set_experiment('zoom-tiles-generator-evaluation')
        with mlflow.start_run(run_name='actual-isometric-and-other-views') as run:
            mlflow.set_tags({'kind':'actual-cuda-artifact-evaluation','quality':'unapproved','projection':'flat-raster-isometric'})
            mlflow.log_metrics({k:v for k,v in report['summary'].items() if isinstance(v,int)})
            mlflow.log_dict(report,'evaluation.json')
            if (output/'screenshots').is_dir():mlflow.log_artifacts(str(output/'screenshots'),artifact_path='actual-browser-views')
            for case in report['summary']['fresh_middle_earth_cases']:mlflow.log_artifacts(str(ROOT/'.runtime/pyramid/runs'/case),artifact_path='fresh-cuda/'+case)
            if (output/'runs').is_dir():mlflow.log_artifacts(str(output/'runs'),artifact_path='earth-control')
            report['mlflow_run_id']=run.info.run_id
    (output/'results.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    (ROOT/'examples/results/generation-evaluation.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps(report['summary']),flush=True)

if __name__=='__main__':main()
