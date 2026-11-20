"""Loopback application adapter: text worlds + navigable original/AI tile layers."""
import json
import re
import sys
import threading
import time
import os
from http.server import SimpleHTTPRequestHandler,ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit,parse_qs
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from zoom_tiles.navigation import WorldEngine,png
from pyramid_lab import FIXTURES, baseline
from zoom_tiles.local_planner import LocalPlanner

LOCAL=ROOT.parent/'.local-query-model'
PLANNER=LocalPlanner(ROOT/'.runtime/text-planner',os.getenv('ZOOM_TEXT_MODEL_PATH',str(LOCAL/'Qwen3-1.7B-Q8_0.gguf')),
                     os.getenv('ZOOM_LLAMA_COMPLETION',str(LOCAL/'runtime/llama-completion.exe')))

ENGINE=WorldEngine(ROOT/'.runtime/worlds',baseline)
ENGINE.import_middle(ROOT/'.runtime/pyramid/runs')
ENGINE.import_middle(FIXTURES / 'recordings')

class Handler(SimpleHTTPRequestHandler):
    def __init__(self,*args,**kwargs):super().__init__(*args,directory=str(ROOT/'docs'),**kwargs)
    def reply(self,data,status=200):
        raw=json.dumps(data).encode();self.send_response(status);self.send_header('Content-Type','application/json');self.send_header('Cache-Control','no-store');self.send_header('Content-Length',str(len(raw)));self.end_headers();self.wfile.write(raw)
    def do_GET(self):
        parsed=urlsplit(self.path);path=parsed.path
        try:
            if path=='/api/planner':self.reply({'local_ai_available':PLANNER.available,'model':'Qwen3 1.7B / CPU','research':'unverified outline; no live research'});return
            if path=='/api/worlds':self.reply(list(ENGINE.worlds.values()));return
            match=re.fullmatch(r'/api/worlds/([a-z0-9-]+)(/status)?',path)
            if match:self.reply(ENGINE.status(match[1]) if match[2] else ENGINE.world(match[1]));return
            match=re.fullmatch(r'/api/worlds/([a-z0-9-]+)/tiles/(-?\d+)/(\d+)/(\d+)\.png',path)
            if match:
                wid=match[1];z,x,y=map(int,match.groups()[1:]);mode=parse_qs(parsed.query).get('mode',['original'])[0]
                if mode not in ('original','raw','blended'):raise ValueError('Unknown layer mode')
                image,origin=ENGINE.image(wid,z,x,y,mode);raw=png(image);self.send_response(200);self.send_header('Content-Type','image/png');self.send_header('Cache-Control','no-store');self.send_header('X-Tile-Origin',origin);self.send_header('Content-Length',str(len(raw)));self.end_headers();self.wfile.write(raw);return
            if path.startswith('/api/'):self.reply({'error':'Unknown endpoint'},404);return
            super().do_GET()
        except ValueError as error:self.reply({'error':str(error)},422)
        except (BrokenPipeError,ConnectionResetError):pass
        except Exception as error:self.reply({'error':str(error)[:240]},503)
    def do_POST(self):
        if self.headers.get('Origin') not in ('http://127.0.0.1:8796','http://localhost:8796'):
            self.reply({'error':'Same-origin local UI required'},403);return
        try:
            length=int(self.headers.get('Content-Length','0'))
            if not 0<length<=100000:raise ValueError('Invalid body size')
            body=json.loads(self.rfile.read(length))
            if not isinstance(body,dict):raise ValueError('JSON object required')
            if self.path=='/api/worlds':
                if type(body.get('use_local_ai',False)) is not bool:raise ValueError('use_local_ai must be boolean')
                outline=PLANNER.plan(body.get('prompt')) if body.get('use_local_ai') else None
                world=ENGINE.create(body.get('prompt'),outline)
                ENGINE.submit(world['id'],[{'z':0,'x':0,'y':0}],'initial-'+world['id'],0,keep=True)
                self.reply(world,201);return
            match=re.fullmatch(r'/api/worlds/([a-z0-9-]+)/(viewport|generate)',self.path)
            if match:
                tiles=body.get('tiles',[])
                if len(tiles)>3:raise ValueError('At most 3 visible targets per settled viewport')
                self.reply(ENGINE.submit(match[1],tiles,body.get('client_id'),body.get('epoch')),202);return
            self.reply({'error':'Unknown endpoint'},404)
        except (ValueError,TypeError,KeyError) as error:self.reply({'error':str(error)},422)

def watch_imports():
    while True:
        time.sleep(10)
        try:ENGINE.import_middle(ROOT/'.runtime/pyramid/runs')
        except Exception:pass

if __name__=='__main__':
    threading.Thread(target=watch_imports,daemon=True).start()
    print('World explorer: http://127.0.0.1:8796/world-explorer.html',flush=True)
    ThreadingHTTPServer(('127.0.0.1',8796),Handler).serve_forever()
