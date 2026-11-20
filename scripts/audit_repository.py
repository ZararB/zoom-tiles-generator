"""Check release-selected content without printing possible secret values."""
import json
from pathlib import Path
import re

ROOT=Path(__file__).resolve().parents[1]
EXCLUDED={'.git','.runtime','.venv','.cache','__pycache__','node_modules','artifacts','logs','build','dist'}
DOWNLOADED={'dev-ui/vendor/maplibre-gl.js','dev-ui/vendor/maplibre-gl.css','dev-ui/vendor/leaflet-maplibre-gl.js'}
PATTERNS=[rb'AKIA[0-9A-Z]{16}',rb'gh[pousr]_[A-Za-z0-9]{20,}',rb'github_pat_[A-Za-z0-9_]{20,}',
    rb'sk-[A-Za-z0-9]{24,}',rb'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----',
    rb'C:\\Users\\',rb'192\.168\.[0-9]+\.[0-9]+']

def selected_files():
    for path in ROOT.rglob('*'):
        relative=path.relative_to(ROOT)
        if not path.is_file() or any(p in EXCLUDED or p.endswith('.egg-info') for p in relative.parts):continue
        if relative.as_posix() in DOWNLOADED:continue
        yield path

def main():
    findings=[];count=0
    for path in selected_files():
        name=path.relative_to(ROOT).as_posix();count+=1
        if path.name.startswith('.env') and path.name!='.env.example':findings.append({'file':name,'kind':'environment_file'})
        if path.suffix.lower() in {'.db','.sqlite','.sqlite3','.safetensors','.ckpt','.pt','.exe'}:findings.append({'file':name,'kind':'private_or_large_runtime_artifact'})
        # The audit tool's own pattern definitions are deliberately literal signatures.
        if name=='scripts/audit_repository.py':continue
        raw=path.read_bytes()
        if any(re.search(pattern,raw) for pattern in PATTERNS):findings.append({'file':name,'kind':'credential_or_machine_specific_signature'})
    result={'status':'passed' if not findings else 'failed','files_checked':count,
        'scope':'release-selected files; runtime/model/browser dependency caches excluded','findings':findings}
    (ROOT/'examples/results/repository-audit.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps(result,indent=2))
    if findings:raise SystemExit(1)
if __name__=='__main__':main()
