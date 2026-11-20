import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent
os.environ.setdefault('HF_HOME', str(Path(os.getenv('ZOOM_TILE_MODEL_CACHE', str(ROOT / '.cache' / 'models')))))
os.environ.setdefault('HF_HUB_DISABLE_TELEMETRY', '1')
os.environ.setdefault('HF_HUB_DISABLE_XET', '1')
MODEL_ID = 'timbrooks/instruct-pix2pix'
REVISION = '31519b5cb02a7fd89b906d88731cd4d6a7bbf88d'
MODEL_PATH = Path(os.getenv('ZOOM_TILE_MODEL_CACHE', str(ROOT / '.cache' / 'models'))) / 'pinned-model'
SIZE = int(os.getenv('CUSTOM_MAP_RUNPOD_INFERENCE_SIZE', '256'))
STEPS = int(os.getenv('CUSTOM_MAP_RUNPOD_STEPS', '20'))
GUIDANCE = float(os.getenv('CUSTOM_MAP_RUNPOD_GUIDANCE', '7.5'))
IMAGE_GUIDANCE = float(os.getenv('CUSTOM_MAP_RUNPOD_IMAGE_GUIDANCE', '1.2'))
OFFLOAD = os.getenv('CUSTOM_MAP_TILE_OFFLOAD', 'sequential')
if SIZE < 128 or SIZE > 512 or SIZE % 64:
    raise ValueError('Inference size must be a multiple of 64 between 128 and 512')
if not 1 <= STEPS <= 50 or OFFLOAD not in {'sequential', 'model'}:
    raise ValueError('Invalid steps or offload mode')
