"""Optional local CUDA image-to-image worker. Geometry remains authoritative."""
import base64
import binascii
import io
import logging
import time
import warnings
from contextlib import asynccontextmanager
from threading import Lock
from typing import Annotated, Literal

from settings import MODEL_ID, MODEL_PATH, REVISION, SIZE, STEPS, GUIDANCE, IMAGE_GUIDANCE, OFFLOAD
import torch
from fastapi import FastAPI, HTTPException
from PIL import Image, UnidentifiedImageError
from pydantic import BaseModel, Field

logger = logging.getLogger('tile-worker')
Image.MAX_IMAGE_PIXELS = 4_194_304
lock = Lock()
pipe = None


def decode_image(value):
    try:
        if value.startswith('data:'):
            value = value.split(',', 1)[1]
        raw = base64.b64decode(value, validate=True)
        if len(raw) > 4_194_304:
            raise ValueError('Image exceeds 4 MiB')
        with warnings.catch_warnings():
            warnings.simplefilter('error', Image.DecompressionBombWarning)
            with Image.open(io.BytesIO(raw)) as image:
                if image.width > 2048 or image.height > 2048:
                    raise ValueError('Image dimensions exceed 2048')
                image.load()
                return image.convert('RGB')
    except (ValueError, IndexError, binascii.Error, UnidentifiedImageError, OSError,
            Image.DecompressionBombError, Image.DecompressionBombWarning) as exc:
        raise HTTPException(422, 'Invalid or oversized base64 image') from exc


def compose(tile, mosaic=None):
    if mosaic is None:
        return tile.resize((SIZE, SIZE), Image.Resampling.LANCZOS)
    canvas = Image.new('RGB', (SIZE, SIZE))
    canvas.paste(mosaic.resize((SIZE, SIZE // 2), Image.Resampling.LANCZOS), (0, 0))
    canvas.paste(tile.resize((SIZE, SIZE // 2), Image.Resampling.LANCZOS), (0, SIZE // 2))
    return canvas


@asynccontextmanager
async def lifespan(app):
    global pipe
    if not torch.cuda.is_available():
        raise RuntimeError('CUDA required; CPU fallback is disabled')
    from diffusers import StableDiffusionInstructPix2PixPipeline
    torch.set_num_threads(4)
    loaded = StableDiffusionInstructPix2PixPipeline.from_pretrained(
        str(MODEL_PATH), variant='fp16', torch_dtype=torch.float16,
        use_safetensors=True, local_files_only=True,
    )
    # Pascal GPUs have no Tensor Cores or modern fused-attention kernels.
    loaded.enable_attention_slicing('max')
    loaded.enable_vae_slicing()
    if OFFLOAD == 'sequential':
        loaded.enable_sequential_cpu_offload()
    else:
        loaded.enable_model_cpu_offload()
    pipe = loaded
    yield
    pipe = None
    torch.cuda.empty_cache()


app = FastAPI(title='Zoom Tile Generation CUDA worker', lifespan=lifespan)


class PlaceNameOverride(BaseModel):
    feature_id: Annotated[str, Field(min_length=1,max_length=80)]
    name: Annotated[str, Field(min_length=1,max_length=80)]
    enabled: bool


class Edit(BaseModel):
    image_base64: Annotated[str, Field(min_length=4, max_length=5_600_000)]
    prompt: Annotated[str, Field(min_length=1, max_length=2000)]
    context_mosaic_base64: Annotated[str | None, Field(max_length=5_600_000)] = None
    coordinate_space: Literal['slippy', 'pixel'] = 'slippy'
    map_geometry: dict | None = None
    z: Annotated[int | None, Field(ge=-8, le=24)] = None
    x: Annotated[int | None, Field(ge=0)] = None
    y: Annotated[int | None, Field(ge=0)] = None
    seed: Annotated[int, Field(ge=0, le=2**32 - 1)] = 42
    steps: Annotated[int | None, Field(ge=1, le=50)] = None
    world_revision: Annotated[str | None, Field(max_length=100)] = None
    world_sha256: Annotated[str | None, Field(pattern='^[a-f0-9]{64}$')] = None
    scene_id: Annotated[str | None, Field(max_length=80)] = None
    map_name_override: PlaceNameOverride | None = None


@app.get('/health')
def health():
    return {'ok': pipe is not None, 'model_id': MODEL_ID, 'revision': REVISION,
            'cuda': torch.cuda.is_available(), 'gpu': torch.cuda.get_device_name(0),
            'inference_size': SIZE, 'offload': OFFLOAD, 'busy': lock.locked()}


@app.post('/edit')
def edit(body: Edit):
    if pipe is None:
        raise HTTPException(503, 'Model is not ready')
    if body.coordinate_space == 'pixel':
        from zoom_tiles.pyramid import PyramidGeometry
        try:
            PyramidGeometry(**(body.map_geometry or {})).validate(body.z, body.x, body.y)
        except (ValueError, TypeError) as exc:
            raise HTTPException(422, 'Invalid pixel-space tile geometry') from exc
    elif body.z is not None and (body.z < 0 or any(v is not None and v >= 2**body.z for v in (body.x, body.y))):
        raise HTTPException(422, 'Tile coordinates exceed zoom bounds')
    tile = decode_image(body.image_base64)
    mosaic = decode_image(body.context_mosaic_base64) if body.context_mosaic_base64 else None
    tokenizer = getattr(pipe, 'tokenizer', None)
    if tokenizer is not None:
        tokens = tokenizer(body.prompt, truncation=False)['input_ids']
        if len(tokens) > tokenizer.model_max_length:
            raise HTTPException(422, f'Prompt has {len(tokens)} tokens; model limit is {tokenizer.model_max_length}. Summarize before generating; instructions must not be silently truncated.')
    if not lock.acquire(blocking=False):
        raise HTTPException(429, 'GPU is busy; retry later', headers={'Retry-After': '10'})
    started = time.monotonic()
    try:
        if torch.cuda.is_initialized():
            torch.cuda.reset_peak_memory_stats()
        with torch.inference_mode():
            result = pipe(prompt=body.prompt, image=compose(tile, mosaic),
                          num_inference_steps=body.steps or STEPS, guidance_scale=GUIDANCE,
                          image_guidance_scale=IMAGE_GUIDANCE,
                          generator=torch.Generator(device='cpu').manual_seed(body.seed))
        if result.nsfw_content_detected and any(result.nsfw_content_detected):
            raise HTTPException(422, 'Image did not pass the model safety checker')
        output = result.images[0]
        if mosaic is not None:
            output = output.crop((0, output.height // 2, output.width, output.height))
        output = output.resize(tile.size, Image.Resampling.LANCZOS)
        buffer = io.BytesIO()
        output.save(buffer, format='PNG')
        return {'success': True, 'image_base64': base64.b64encode(buffer.getvalue()).decode(),
                'provider': 'runpod_pod_instruct_pix2pix', 'model_id': MODEL_ID,
                'coordinate_space': body.coordinate_space, 'map_geometry': body.map_geometry,
                'model_revision': REVISION, 'z': body.z, 'x': body.x, 'y': body.y,
                'seed': body.seed, 'steps': body.steps or STEPS,
                'world_revision':body.world_revision,'world_sha256':body.world_sha256,'scene_id':body.scene_id,
                'map_name_override':body.map_name_override.model_dump() if body.map_name_override else None,
                'gpu_peak_allocated_bytes': torch.cuda.max_memory_allocated() if torch.cuda.is_initialized() else 0,
                'context_used': mosaic is not None, 'elapsed_seconds': round(time.monotonic()-started, 3)}
    except torch.cuda.OutOfMemoryError as exc:
        torch.cuda.empty_cache()
        raise HTTPException(503, 'GPU memory exhausted; retry after freeing VRAM') from exc
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception('Tile generation failed')
        raise HTTPException(500, 'Tile generation failed; inspect local worker logs') from exc
    finally:
        lock.release()
