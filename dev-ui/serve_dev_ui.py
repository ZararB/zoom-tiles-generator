#!/usr/bin/env python3
"""
Serve dev-ui static files and proxy /api/tile-worker/* → local pod_server (CORS-safe).
"""
from __future__ import annotations

import json
import os
import sys
import threading
import uuid
import re
import base64
import hashlib
import io
from PIL import Image
from datetime import datetime, timezone
import urllib.error
import urllib.request
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from zoom_tiles.geometry import normalize_geography
from zoom_tiles.jobs import TileJobs

ROOT = Path(__file__).resolve().parent
WORKER = os.environ.get("TILE_WORKER_URL", "http://127.0.0.1:8888").rstrip("/")
PORT = int(os.environ.get("DEV_UI_PORT", "8791"))
DATA = Path(os.environ.get('ZOOM_TILE_DATA_DIR', str(ROOT.parent / '.runtime')))
DATA.mkdir(parents=True,exist_ok=True)
RECORDINGS = ROOT.parent/'examples/gpu'
MAP_EDITS = DATA / 'map-edits.json'
MAP_EDIT_LOCK = threading.Lock()
GEOGRAPHY = DATA / 'geography-edits.json'
PROPOSALS = DATA / 'geography-proposals'
TILE_JOBS = TileJobs(DATA/'tile-job-cache',WORKER)


class DevUiHandler(SimpleHTTPRequestHandler):
    extensions_map = {**SimpleHTTPRequestHandler.extensions_map, '.js': 'text/javascript', '.css': 'text/css'}
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def end_headers(self) -> None:
        self.send_header("X-Content-Type-Options", "nosniff")
        # Revalidate local source files after edits. Generated tiles have their
        # own bounded revision-keyed cache and remain reusable across navigation.
        self.send_header('Cache-Control','no-cache')
        super().end_headers()

    def log_message(self, fmt: str, *args) -> None:
        sys.stderr.write("[dev-ui] " + (fmt % args) + "\n")

    def do_OPTIONS(self) -> None:
        self.send_response(204)
        self.end_headers()

    def do_GET(self) -> None:
        if self.path=='/api/examples':
            self._json(json.loads((ROOT.parent/'examples/catalog.json').read_text(encoding='utf-8')));return
        example_match=re.fullmatch(r'/api/examples/([a-z0-9-]+)/(before|after)',self.path)
        if example_match:
            catalog=json.loads((ROOT.parent/'examples/catalog.json').read_text(encoding='utf-8'))
            if example_match.group(1) not in {case['id'] for case in catalog}:
                self._json({'error':'Unknown example'},status=404);return
            path=ROOT.parent/'examples/cases'/example_match.group(1)/(example_match.group(2)+'.json')
            self._json(json.loads(path.read_text(encoding='utf-8')));return
        if self.path=='/api/tile-jobs':self._json(TILE_JOBS.stats());return
        job_match=re.fullmatch(r'/api/tile-jobs/([a-f0-9]{64})',self.path)
        if job_match:
            result=TILE_JOBS.get(job_match.group(1))
            self._json(result or {'error':'Unknown job'},status=200 if result else 404);return
        if self.path == '/api/geography/proposals':
            self._json([json.loads(path.read_text(encoding='utf-8')) for path in sorted(PROPOSALS.glob('*.json'))])
            return
        if self.path == '/api/geography':
            initial=normalize_geography({'features':[],'enabled':False});initial['revision']='initial'
            self._json(json.loads(GEOGRAPHY.read_text(encoding='utf-8')) if GEOGRAPHY.exists() else initial)
            return
        if self.path == '/api/map-edits':
            state = json.loads(MAP_EDITS.read_text(encoding='utf-8')) if MAP_EDITS.exists() else {
                'version': 1, 'feature': 'lake-ontario', 'lake_name': 'Lake America', 'enabled': False}
            self._json(state)
            return
        if self.path == "/api/tile-worker/health":
            self._proxy("GET", "/health", None)
            return
        super().do_GET()

    def do_POST(self) -> None:
        if self.path=='/api/record-source':
            if os.environ.get('ZOOM_TILE_RECORD_EXAMPLES')!='1':self._json({'error':'Start with --record-examples to save fixtures'},status=403);return
            if self.headers.get('Origin') not in (None,f'http://127.0.0.1:{PORT}',f'http://localhost:{PORT}'):
                self.send_error(403);return
            try:
                length=int(self.headers.get('Content-Length','0'))
                if not 0<length<=6_000_000:raise ValueError('Invalid recording size')
                body=json.loads(self.rfile.read(length));catalog=json.loads((ROOT.parent/'examples/catalog.json').read_text(encoding='utf-8'))
                case=next((c for c in catalog if c['id']==body.get('case_id')),None)
                if not case or case['assertion']=='reject_invalid':raise ValueError('Choose a valid example')
                world=json.loads(GEOGRAPHY.read_text(encoding='utf-8'))
                if case['id']!=world.get('scenario'):raise ValueError('Load this example before recording it')
                if body.get('world_sha256')!=world['sha256'] or body.get('world_revision')!=world['revision']:
                    self._json({'error':'World changed; refresh the source'},status=409);return
                z,x,y=(body.get(k) for k in ('z','x','y'))
                if any(type(v) is not int for v in (z,x,y)) or not 0<=z<=18 or not 0<=x<2**z or not 0<=y<2**z:raise ValueError('Invalid tile coordinate')
                raw=base64.b64decode(body['image_base64'],validate=True)
                if len(raw)>4_194_304:raise ValueError('Source too large')
                with Image.open(io.BytesIO(raw)) as image:
                    if image.format!='PNG' or image.size!=(256,256):raise ValueError('A 256px PNG source is required')
                    image.verify()
                folder=RECORDINGS/case['id'];folder.mkdir(parents=True,exist_ok=True)
                (folder/'source.png').write_bytes(raw)
                record={'schema_version':1,'case_id':case['id'],'scene_id':world['scenario'],'prompt':case['prompt'],
                    'z':z,'x':x,'y':y,'world_sha256':world['sha256'],'world_revision':world['revision'],
                    'source_sha256':hashlib.sha256(raw).hexdigest(),'capture':'actual composed slippy tile recorded by the example viewer'}
                (folder/'input.json').write_text(json.dumps(record,indent=2),encoding='utf-8');self._json(record,status=201)
            except (ValueError,KeyError,TypeError,OSError) as exc:self._json({'error':str(exc)},status=422)
            return
        if self.path in {'/api/tile-jobs','/api/tile-jobs/cancel'}:
            if self.headers.get('Origin') not in (None,f'http://127.0.0.1:{PORT}',f'http://localhost:{PORT}'):
                self.send_error(403);return
            try:
                length=int(self.headers.get('Content-Length','0'))
                if not 0<length<=12_000_000:raise ValueError('Invalid job body size')
                body=json.loads(self.rfile.read(length))
                if self.path.endswith('/cancel'):
                    self._json(TILE_JOBS.cancel(body.get('client_id'),body.get('viewport_id')));return
                world=json.loads(GEOGRAPHY.read_text(encoding='utf-8'))
                payload=body.get('payload',{})
                if payload.get('world_sha256')!=world['sha256'] or payload.get('world_revision')!=world['revision']:
                    self._json({'error':'World changed; reload before generating'},status=409);return
                self._json(TILE_JOBS.submit(body),status=202)
            except (ValueError,TypeError,KeyError,AttributeError) as exc:self._json({'error':str(exc)},status=422)
            except Exception as exc:self._json({'error':str(exc)[:300]},status=503)
            return
        proposal_apply=re.fullmatch(r'/api/geography/proposals/([a-f0-9]{32})/apply',self.path)
        if self.path in {'/api/geography','/api/geography/undo','/api/geography/proposals'} or proposal_apply:
            if self.headers.get('Origin') not in (None,f'http://127.0.0.1:{PORT}',f'http://localhost:{PORT}'):
                self.send_error(403); return
            try:
                length=int(self.headers.get('Content-Length','0'))
                if not 0<length<=3_000_000: raise ValueError('Geometry document exceeds 3 MB')
                body=json.loads(self.rfile.read(length))
                with MAP_EDIT_LOCK:
                    current=json.loads(GEOGRAPHY.read_text(encoding='utf-8')) if GEOGRAPHY.exists() else normalize_geography({'features':[],'enabled':False})
                    if not GEOGRAPHY.exists():current['revision']='initial'
                    if body.get('expected_revision')!=current['revision']:
                        self._json({'error':'World changed since it was loaded. Reload before saving.'},status=409);return
                    if self.path == '/api/geography/proposals':
                        candidate=normalize_geography(body['document'])
                        ident=uuid.uuid4().hex
                        proposal={'id':ident,'stage':'draft','base_revision':current['revision'],
                                  'model_version_id':str(body.get('model_version_id','unregistered'))[:120],
                                  'mlflow_run_id':str(body.get('mlflow_run_id',''))[:80],
                                  'document':candidate}
                        PROPOSALS.mkdir(parents=True,exist_ok=True)
                        (PROPOSALS/(ident+'.json')).write_text(json.dumps(proposal),encoding='utf-8')
                        self._json(proposal,status=201);return
                    if proposal_apply:
                        proposal_path=PROPOSALS/(proposal_apply.group(1)+'.json')
                        if not proposal_path.exists():self._json({'error':'Unknown proposal'},status=404);return
                        proposal=json.loads(proposal_path.read_text(encoding='utf-8'))
                        if proposal['stage']!='draft' or proposal['base_revision']!=current['revision']:
                            self._json({'error':'Proposal is stale or already applied; create a fresh draft.'},status=409);return
                        body=proposal['document']
                    history=GEOGRAPHY.parent/'geography-history'
                    history.mkdir(parents=True,exist_ok=True)
                    if self.path.endswith('/undo'):
                        snapshots=sorted(history.glob('*.json'))
                        if not snapshots: raise ValueError('No earlier geography revision')
                        snapshot=snapshots[-1]
                        result=normalize_geography(json.loads(snapshot.read_text(encoding='utf-8')))
                        # Keep undo evidence instead of deleting user edits.
                        snapshot.rename(snapshot.with_suffix('.restored'))
                    else:
                        result=normalize_geography(body)
                        stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
                        (history/(stamp+'.json')).write_text(json.dumps(current),encoding='utf-8')
                    temporary=GEOGRAPHY.with_suffix('.tmp')
                    temporary.write_text(json.dumps(result,ensure_ascii=False),encoding='utf-8')
                    os.replace(temporary,GEOGRAPHY)
                    if proposal_apply:
                        proposal['stage']='applied';proposal['applied_revision']=result['revision']
                        proposal_path.write_text(json.dumps(proposal),encoding='utf-8')
                self._json(result)
            except (ValueError,KeyError,TypeError,AttributeError) as exc:
                self._json({'error':str(exc)},status=422)
            return
        if self.path == '/api/map-edits':
            if self.headers.get('Origin') not in (None, f'http://127.0.0.1:{PORT}', f'http://localhost:{PORT}'):
                self.send_error(403)
                return
            try:
                length = int(self.headers.get('Content-Length', '0'))
                if not 0 < length <= 4096: raise ValueError('Invalid body size')
                body = json.loads(self.rfile.read(length))
                name = body['lake_name'].strip()
                if not 1 <= len(name) <= 80 or type(body['enabled']) is not bool: raise ValueError('Invalid map name')
                state = {'version':1, 'feature':'lake-ontario', 'lake_name':name, 'enabled':body['enabled'],
                         'updated_at':datetime.now(timezone.utc).isoformat()}
                with MAP_EDIT_LOCK:
                    MAP_EDITS.parent.mkdir(exist_ok=True)
                    temporary = MAP_EDITS.with_suffix('.tmp')
                    temporary.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding='utf-8')
                    os.replace(temporary, MAP_EDITS)
                self._json(state)
            except (ValueError, KeyError, TypeError, AttributeError):
                self._json({'error':'Provide a lake name (1–80 characters) and an enabled flag.'}, status=422)
            return
        if self.path == "/api/tile-worker/edit":
            if self.headers.get('Origin') not in (None, f'http://127.0.0.1:{PORT}', f'http://localhost:{PORT}'):
                self.send_error(403, 'Same-origin requests required')
                return
            try:
                length = int(self.headers.get("Content-Length", "0"))
            except ValueError:
                self.send_error(400)
                return
            if not 0 < length <= 12_000_000:
                self.send_error(413)
                return
            body = self.rfile.read(length) if length else b""
            self._proxy("POST", "/edit", body)
            return
        self.send_error(404)

    def _json(self, value, status=200):
        raw = json.dumps(value, ensure_ascii=False).encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(raw)))
        self.send_header('Cache-Control', 'no-store')
        self.end_headers()
        self.wfile.write(raw)

    def _proxy(self, method: str, worker_path: str, body: bytes | None) -> None:
        url = f"{WORKER}{worker_path}"
        req = urllib.request.Request(
            url,
            data=body,
            method=method,
            headers={"Content-Type": "application/json"} if body else {},
        )
        try:
            with urllib.request.urlopen(req, timeout=1800) as resp:
                data = resp.read()
                self.send_response(resp.status)
                self.send_header("Content-Type", resp.headers.get("Content-Type", "application/json"))
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)
        except urllib.error.HTTPError as exc:
            payload = exc.read()
            self.send_response(exc.code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)
        except Exception as exc:
            msg = json.dumps({"error": str(exc), "worker": url}).encode("utf-8")
            self.send_response(502)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(msg)))
            self.end_headers()
            self.wfile.write(msg)


def main() -> None:
    httpd = ThreadingHTTPServer(("127.0.0.1", PORT), DevUiHandler)
    print(f"[dev-ui] http://127.0.0.1:{PORT}/ -> worker {WORKER}", flush=True)
    httpd.serve_forever()


if __name__ == "__main__":
    main()
