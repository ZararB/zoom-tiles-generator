"""Read-only loopback gallery of explicitly selected real generation artifacts."""
import json
import re
from http.server import SimpleHTTPRequestHandler,ThreadingHTTPServer
from generation_results import ROOT,CASES,catalog,folder

class Handler(SimpleHTTPRequestHandler):
    def __init__(self,*args,**kwargs):super().__init__(*args,directory=str(ROOT/'docs'),**kwargs)
    def do_GET(self):
        if self.path=='/api/generation-results':
            raw=json.dumps(catalog()).encode();self.send_response(200);self.send_header('Content-Type','application/json');self.send_header('Cache-Control','no-store');self.send_header('Content-Length',str(len(raw)));self.end_headers();self.wfile.write(raw);return
        match=re.fullmatch(r'/api/generation-artifact/([a-z0-9-]+)/(source|result|context|parent)\.png',self.path)
        if match:
            case,name=match.groups();kind=next((k for c,t,k in CASES if c==case),None)
            if kind is None:self.send_error(404);return
            path=folder(case,kind)/(name+'.png')
            if not path.is_file():self.send_error(404);return
            raw=path.read_bytes();self.send_response(200);self.send_header('Content-Type','image/png');self.send_header('Content-Length',str(len(raw)));self.end_headers();self.wfile.write(raw);return
        super().do_GET()

if __name__=='__main__':
    print('Actual tile results: http://127.0.0.1:8795/generation-results.html',flush=True)
    ThreadingHTTPServer(('127.0.0.1',8795),Handler).serve_forever()
