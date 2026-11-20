"""Optionally record example artifacts in a caller-selected MLflow tracking store."""
import os
from pathlib import Path
import json
import argparse
import mlflow

ROOT=Path(__file__).resolve().parents[1]
if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--pyramid',action='store_true',help='Also log locally recorded Middle-earth pyramid runs');args=parser.parse_args()
    data=ROOT/'.runtime';data.mkdir(exist_ok=True)
    mlflow.set_tracking_uri(os.getenv('MLFLOW_TRACKING_URI','sqlite:///'+(data/'mlflow.db').as_posix()))
    mlflow.set_experiment('zoom-tiles-generation-examples')
    with mlflow.start_run(run_name='recorded-examples') as run:
        report=json.loads((ROOT/'examples/results/geometry-validation.json').read_text(encoding='utf-8'))
        mlflow.log_metric('validated_geometry_cases',report['passed'])
        mlflow.set_tags({'pipeline':'geometry-and-optional-raster-refinement','publication':'private-development'})
        mlflow.log_artifacts(str(ROOT/'examples/results'),artifact_path='validation')
        if (ROOT/'examples/gpu').exists():mlflow.log_artifacts(str(ROOT/'examples/gpu'),artifact_path='gpu-examples')
        if args.pyramid:
            report=json.loads((ROOT/'examples/results/middle-earth-validation.json').read_text())
            mlflow.log_metric('pyramid_actual_requests',len(report['records']))
            mlflow.log_metric('pyramid_visual_quality_approved',0)
            mlflow.log_metric('pyramid_user_direction_changes_output',int(report['user_direction_changes_output_after_fix']))
            mlflow.log_artifacts(str(ROOT/'.runtime/pyramid/runs'),artifact_path='pyramid-drafts')
        print('Example artifacts recorded in MLflow run '+run.info.run_id)
