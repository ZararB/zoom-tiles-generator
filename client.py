"""Generate one tile or a manifest-backed batch using the local /edit contract."""
import argparse
import base64
import hashlib
import io
import json
import time
from datetime import datetime, timezone
from pathlib import Path
import requests
from PIL import Image, ImageDraw


def png64(image):
    buffer = io.BytesIO()
    image.save(buffer, format='PNG')
    return base64.b64encode(buffer.getvalue()).decode()


def generate(base, payload, destination):
    response = requests.post(base.rstrip('/')+'/edit', json=payload, timeout=(10, 1800))
    response.raise_for_status()
    result = response.json()
    if not result.get('success'):
        raise RuntimeError('Worker did not return a successful result')
    raw = base64.b64decode(result.pop('image_base64'), validate=True)
    with Image.open(io.BytesIO(raw)) as image:
        image.verify()
    destination.write_bytes(raw)
    return {**result, 'file': destination.name, 'bytes': len(raw),
            'prompt': payload['prompt'],
            'source_sha256': hashlib.sha256(base64.b64decode(payload['image_base64'])).hexdigest(),
            'context_sha256': hashlib.sha256(base64.b64decode(payload['context_mosaic_base64'])).hexdigest() if payload.get('context_mosaic_base64') else None,
            'sha256': hashlib.sha256(raw).hexdigest()}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--base', default='http://127.0.0.1:8888')
    parser.add_argument('--image', type=Path)
    parser.add_argument('--mosaic', type=Path)
    parser.add_argument('--prompt', default='Turn this map into a hand-painted green terrain map. Preserve the river and all road positions.')
    parser.add_argument('--steps', type=int, default=20)
    parser.add_argument('--seed', type=int, default=42)
    parser.add_argument('--batch', type=Path, help='JSONL rows with image_path, prompt, optional context_path, z/x/y')
    parser.add_argument('--out', type=Path)
    args = parser.parse_args()
    run_id = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    folder = args.out or Path(__file__).resolve().parent / 'artifacts' / run_id
    folder.mkdir(parents=True, exist_ok=True)
    health = requests.get(args.base.rstrip('/')+'/health', timeout=15).json()
    if not health.get('ok') or not health.get('cuda'):
        raise RuntimeError('A ready CUDA tile worker is required')
    outputs = []
    started = time.monotonic()
    if args.batch:
        jobs = [json.loads(line) for line in args.batch.read_text().splitlines() if line.strip()]
        for index, row in enumerate(jobs):
            image_path = (args.batch.parent / row['image_path']).resolve()
            with Image.open(image_path) as image:
                source = png64(image.convert('RGB'))
            payload = {'image_base64': source, 'prompt': row['prompt'], 'steps': args.steps,
                       'seed': args.seed, **{k: row[k] for k in ('z', 'x', 'y') if k in row}}
            if row.get('context_path'):
                with Image.open(args.batch.parent / row['context_path']) as image:
                    payload['context_mosaic_base64'] = png64(image.convert('RGB'))
            outputs.append(generate(args.base, payload, folder / f'tile-{index:05d}.png'))
    else:
        if args.image:
            with Image.open(args.image) as image:
                tile = image.convert('RGB')
        else:
            tile = Image.new('RGB', (256, 256), '#e2dbbe')
            draw = ImageDraw.Draw(tile)
            draw.polygon([(0, 0), (85, 0), (110, 80), (80, 180), (110, 256), (0, 256)], fill='#4c92b0')
            draw.line([(110, 0), (150, 100), (256, 180)], fill='#faf6ed', width=9)
            draw.line([(256, 30), (150, 100), (130, 256)], fill='#faf6ed', width=6)
        tile.save(folder / 'source.png')
        payload = {'image_base64': png64(tile), 'prompt': args.prompt,
                   'steps': args.steps, 'seed': args.seed, 'z': 10, 'x': 163, 'y': 395}
        if args.mosaic:
            with Image.open(args.mosaic) as image:
                payload['context_mosaic_base64'] = png64(image.convert('RGB'))
        outputs.append(generate(args.base, payload, folder / 'tile.png'))
    manifest = {'run_id': run_id, 'worker_id': 'win-gpu-tiles-01', 'health': health,
                'outputs': outputs, 'elapsed_seconds': round(time.monotonic()-started, 3),
                'steps': args.steps, 'smoke_test': not bool(args.image or args.batch),
                'production_attached': False}
    (folder / 'manifest.json').write_text(json.dumps(manifest, indent=2))
    print(json.dumps({'manifest': str(folder / 'manifest.json'), 'outputs': outputs}, indent=2))


if __name__ == '__main__':
    main()
