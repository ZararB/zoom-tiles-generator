"""Serve the explainer and accept explicit browser video recordings on loopback."""
import argparse
import json
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
OUTPUT=ROOT/'.runtime/animations'

class Handler(SimpleHTTPRequestHandler):
    def __init__(self,*args,**kwargs):super().__init__(*args,directory=str(ROOT/'docs'),**kwargs)
    def do_POST(self):
        if self.headers.get('Origin') not in (f'http://127.0.0.1:{self.server.server_port}',f'http://localhost:{self.server.server_port}'):
            self.send_error(403);return
        names={'/api/animation-export/make-every-level.webm':'make-every-level.webm',
               '/api/animation-export/context-generation-poster.png':'context-generation-poster.png',
               '/api/animation-export/hierarchy-poster.png':'hierarchy-poster.png',
               '/api/animation-export/stacked-every-level.webm':'stacked-every-level.webm',
               '/api/animation-export/stacked-context-poster.png':'stacked-context-poster.png',
               '/api/animation-export/stacked-hierarchy-poster.png':'stacked-hierarchy-poster.png'}
        name=names.get(self.path)
        if not name:self.send_error(404);return
        try:length=int(self.headers.get('Content-Length','0'))
        except ValueError:self.send_error(400);return
        if not 0<length<=80_000_000:self.send_error(413);return
        raw=self.rfile.read(length)
        if len(raw)!=length or (name.endswith('.png') and not raw.startswith(b'\x89PNG\r\n\x1a\n')) or (name.endswith('.webm') and not raw.startswith(b'\x1aE\xdf\xa3')):
            self.send_error(422);return
        OUTPUT.mkdir(parents=True,exist_ok=True);temporary=OUTPUT/(name+'.tmp');temporary.write_bytes(raw);temporary.replace(OUTPUT/name)
        body=json.dumps({'saved':name,'bytes':length}).encode();self.send_response(201);self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(body)));self.end_headers();self.wfile.write(body)

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--port',type=int,default=8793);args=parser.parse_args()
    print(f'Animation preview: http://127.0.0.1:{args.port}/animation.html',flush=True)
    ThreadingHTTPServer(('127.0.0.1',args.port),Handler).serve_forever()
