"""Start the isolated local demo without requiring CUDA or downloading model weights."""
import argparse
import os
import runpy
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--port',type=int,default=8791)
    parser.add_argument('--worker',default='http://127.0.0.1:8888')
    parser.add_argument('--record-examples',action='store_true',help='Allow explicit source recording into examples/gpu')
    args=parser.parse_args()
    os.environ['DEV_UI_PORT']=str(args.port);os.environ['TILE_WORKER_URL']=args.worker
    if args.record_examples:os.environ['ZOOM_TILE_RECORD_EXAMPLES']='1'
    if not (ROOT/'dev-ui/vendor/maplibre-gl.js').is_file():
        raise SystemExit('Run python scripts/fetch_assets.py first to install the pinned browser dependencies.')
    runpy.run_path(str(ROOT/'dev-ui/serve_dev_ui.py'),run_name='__main__')
