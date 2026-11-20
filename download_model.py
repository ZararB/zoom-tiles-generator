"""Download pinned, hash-verified FP16 weights using resumable range transfers."""
import hashlib
import json
import os
import shutil
import time
from concurrent.futures import ThreadPoolExecutor
from settings import MODEL_ID, MODEL_PATH, REVISION
import requests
from huggingface_hub import HfApi, hf_hub_url, get_hf_file_metadata

CHUNK = 16 * 1024 * 1024
MIN_FREE_GIB = float(os.getenv('CUSTOM_MAP_TILE_MIN_FREE_GIB', '12'))


def download_file(file):
    name = file.rfilename
    destination = MODEL_PATH / name
    destination.parent.mkdir(parents=True, exist_ok=True)
    expected = file.lfs.sha256 if file.lfs else None
    if destination.is_file():
        with destination.open('rb') as source:
            digest = hashlib.file_digest(source, 'sha256').hexdigest()
        if expected and digest == expected:
            print('verified', name, flush=True)
            return
        if not expected and destination.stat().st_size == file.size:
            return
    url = hf_hub_url(MODEL_ID, name, revision=REVISION)
    metadata = get_hf_file_metadata(url)
    if not expected:
        response = requests.get(url, timeout=60)
        if response.status_code != 200:
            raise RuntimeError(f'Configuration download failed: {name} HTTP {response.status_code}')
        destination.write_bytes(response.content)
        return
    parts = destination.parent / (destination.name + '.parts')
    parts.mkdir(exist_ok=True)
    size = file.size

    def fetch(index):
        start = index * CHUNK
        end = min(size, start + CHUNK)-1
        part = parts / f'{index:05d}'
        length = end-start+1
        if part.is_file() and part.stat().st_size == length:
            return part
        for attempt in range(4):
            try:
                temp = part.with_suffix('.tmp')
                offset = temp.stat().st_size if temp.exists() else 0
                if offset > length:
                    temp.unlink()
                    offset = 0
                if offset == length:
                    os.replace(temp, part)
                    return part
                resume = start + offset
                with requests.get(metadata.location, headers={'Range': f'bytes={resume}-{end}'},
                                  stream=True, timeout=(20, 90)) as response:
                    if response.status_code != 206 or not response.headers.get('Content-Range', '').startswith(f'bytes {resume}-{end}/'):
                        raise RuntimeError('Server did not return the requested byte range')
                    with temp.open('ab') as output:
                        for block in response.iter_content(1024*1024):
                            output.write(block)
                    if temp.stat().st_size != length:
                        raise RuntimeError('Incomplete range transfer')
                    os.replace(temp, part)
                    print(f'{name}: chunk {index+1}/{(size+CHUNK-1)//CHUNK}', flush=True)
                    return part
            except Exception:
                if attempt == 3:
                    raise RuntimeError(f'Range download failed for {name}, chunk {index}') from None
                time.sleep(attempt+1)
    count = (size+CHUNK-1)//CHUNK
    existing = sum(path.stat().st_size for path in parts.iterdir() if path.is_file())
    required = max(0, size-existing) + size
    if shutil.disk_usage(MODEL_PATH).free-required < MIN_FREE_GIB*1024**3:
        raise RuntimeError(f'Model download paused to preserve {MIN_FREE_GIB:g} GiB of free disk space')
    print('downloading', name, size, 'bytes', flush=True)
    with ThreadPoolExecutor(max_workers=32) as executor:
        ordered = list(executor.map(fetch, range(count)))
    temp = destination.with_suffix('.assembling')
    digest = hashlib.sha256()
    with temp.open('wb') as output:
        for part in ordered:
            with part.open('rb') as source:
                for block in iter(lambda: source.read(1024*1024), b''):
                    digest.update(block)
                    output.write(block)
    if digest.hexdigest() != expected:
        raise RuntimeError(f'Weight checksum mismatch: {name}')
    os.replace(temp, destination)
    for part in ordered:
        part.unlink()
    parts.rmdir()
    print('verified', name, flush=True)


if __name__ == '__main__':
    info = HfApi().model_info(MODEL_ID, revision=REVISION, files_metadata=True)
    selected = [f for f in info.siblings if (
        f.rfilename == 'model_index.json' or f.rfilename.endswith('/config.json') or
        f.rfilename.endswith('.fp16.safetensors') or f.rfilename.startswith('tokenizer/') or
        f.rfilename in {'scheduler/scheduler_config.json', 'feature_extractor/preprocessor_config.json'})]
    MODEL_PATH.mkdir(parents=True, exist_ok=True)
    for file in selected:
        download_file(file)
    (MODEL_PATH / 'download-manifest.json').write_text(json.dumps({
        'model_id': MODEL_ID, 'revision': REVISION,
        'files': [{'path': f.rfilename, 'bytes': f.size, 'sha256': f.lfs.sha256 if f.lfs else None} for f in selected]
    }, indent=2))
    print('Model ready:', MODEL_PATH, flush=True)
