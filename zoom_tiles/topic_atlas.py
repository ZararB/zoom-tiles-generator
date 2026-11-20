"""Paint curated topic atlases in world coordinates across tile boundaries."""
from functools import lru_cache
from math import ceil, floor
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter

_ASSETS = Path(__file__).with_name("assets")
_CELLS = {
    "science": (
        "Physics", "Chemistry", "Biology", "Mathematics", "Earth & space",
        "Computing", "Human sciences", "Mechanics", "Map of science",
    ),
    "entertainment": (
        "Film", "Television & streaming", "Music", "Video games", "Audio & podcasts",
        "Publishing", "Live entertainment", "Film production", "Media & entertainment",
    ),
}
_BACKGROUND = "#140f0c"


def has_topic_atlas(world):
    return world.get("theme") in _CELLS and world.get("planner") == "curated_demo_outline"


@lru_cache(maxsize=18)
def _artwork(theme, index):
    with Image.open(_ASSETS / f"{theme}-atlas.webp") as sheet:
        column, row = index % 3, index // 3
        art = sheet.crop((
            column * sheet.width // 3, row * sheet.height // 3,
            (column + 1) * sheet.width // 3, (row + 1) * sheet.height // 3,
        )).convert("RGB")
    # Feather the dark edges into the atlas without leaving square sprite borders.
    opacity = Image.new("L", art.size)
    inset = round(min(art.size) * .12)
    ImageDraw.Draw(opacity).ellipse(
        (inset, inset, art.width - inset, art.height - inset), fill=210,
    )
    opacity = opacity.filter(ImageFilter.GaussianBlur(inset / 2))
    art.putalpha(opacity)
    return art


def _stamp(tile, art, px, py, size):
    left, top = px - size / 2, py - size / 2
    x0, y0 = max(0, floor(left)), max(0, floor(top))
    x1, y1 = min(tile.width, ceil(left + size)), min(tile.height, ceil(top + size))
    if x0 >= x1 or y0 >= y1:
        return
    sx, sy = art.width / size, art.height / size
    patch = art.transform(
        (x1 - x0, y1 - y0), Image.Transform.AFFINE,
        (sx, 0, (x0 - left) * sx, 0, sy, (y0 - top) * sy),
        resample=Image.Resampling.BICUBIC,
    )
    tile.paste(patch, (x0, y0), patch)


def render_tile(world, z, x, y, span):
    """Keep each illustration centered on its existing topic coordinates."""
    tile = Image.new("RGB", (256, 256), _BACKGROUND)
    draw = ImageDraw.Draw(tile)
    scale = tile.width / span
    interval = 256 if z >= 2 else 512
    start_x, start_y = x * span, y * span
    margin = 2 / scale
    for wx in range(ceil((start_x - margin) / interval) * interval, ceil(start_x + span + margin), interval):
        for wy in range(ceil((start_y - margin) / interval) * interval, ceil(start_y + span + margin), interval):
            px, py = (wx - start_x) * scale, (wy - start_y) * scale
            draw.line((px - 2, py, px + 2, py), fill="#3a271c")
            draw.line((px, py - 2, px, py + 2), fill="#3a271c")

    theme = world["theme"]
    cells = {label: index for index, label in enumerate(_CELLS[theme])}
    for node in world["nodes"]:
        index = cells.get(node["label"])
        if index is None or node["min_z"] > z:
            continue
        px = (node["x"] - start_x) * scale
        py = (node["y"] - start_y) * scale
        size = (960, 1060, 360)[node["depth"]] * scale
        if -size / 2 < px < tile.width + size / 2 and -size / 2 < py < tile.height + size / 2:
            _stamp(tile, _artwork(theme, index), px, py, size)
    return tile
