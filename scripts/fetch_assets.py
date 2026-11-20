"""Install pinned browser assets with SHA256 verification; never downloads model weights."""
import hashlib
import json
import os
from pathlib import Path
import requests

ROOT=Path(__file__).resolve().parents[1]
def main():
    vendor=ROOT/'dev-ui/vendor'
    for entry in json.loads((vendor/'manifest.json').read_text(encoding='utf-8')):
        path=vendor/entry['file']
        if path.exists() and hashlib.sha256(path.read_bytes()).hexdigest()==entry['sha256']:continue
        response=requests.get(entry['url'],timeout=60);response.raise_for_status()
        if hashlib.sha256(response.content).hexdigest()!=entry['sha256']:raise RuntimeError('Asset checksum mismatch: '+entry['file'])
        temporary=path.with_suffix(path.suffix+'.tmp');temporary.write_bytes(response.content);os.replace(temporary,path)
    print('Pinned browser assets verified.')
if __name__=='__main__':main()
