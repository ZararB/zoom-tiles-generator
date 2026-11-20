"""Render documentation diagrams directly from the tested context planner."""
import sys
from pathlib import Path
from html import escape
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from zoom_tiles.pyramid import PyramidGeometry, plan_context

ROOT=Path(__file__).resolve().parents[1]
geo=PyramidGeometry(7680,4386,2)
parts=['<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="920" viewBox="0 0 1200 920" role="img" aria-label="Tile context at three zoom levels">',
       '<rect width="1200" height="920" fill="#101924"/>',
       '<style>text{font-family:Arial,sans-serif;fill:#e7edf5} .muted{fill:#b5c5d8} .small{font-size:14px} .label{font-size:18px}</style>',
       '<text x="36" y="45" font-size="28">One location. Different zoom. Explicit context.</text>',
       '<text x="36" y="76" class="label muted">Existing Middle-earth preset • source pixel (2772, 1258) • no Earth wrapping</text>']
for column,z in enumerate((2,4,6)):
    _,x,y=geo.at_pixel(z,2772,1258);plan=plan_context(geo,z,x,y)
    left=36+column*392
    parts.append(f'<text x="{left}" y="125" font-size="24">Directory z={z}</text>')
    parts.append(f'<text x="{left}" y="152" class="small muted">Target {z}/{x}/{y} • {geo.span(z):g} source px / tile</text>')
    for dy in (-1,0,1):
        for dx in (-1,0,1):
            bx=left+(dx+1)*112;by=177+(dy+1)*80
            fill='#df9c42' if dx==dy==0 else '#244b64'
            parts.append(f'<rect x="{bx}" y="{by}" width="108" height="76" rx="7" fill="{fill}"/>')
            parts.append(f'<text x="{bx+8}" y="{by+30}" class="small">{z}/{x+dx}/{y+dy}</text>')
            parts.append(f'<text x="{bx+8}" y="{by+53}" class="small">{"TARGET" if dx==dy==0 else "neighbor"}</text>')
    parent=plan['ancestors'][0];uv=parent['target_crop_uv']
    parts.append(f'<text x="{left}" y="453" class="label">Parent {parent["z"]}/{parent["x"]}/{parent["y"]}</text>')
    for qy in (0,1):
        for qx in (0,1):
            chosen=qx==int(uv[0]*2) and qy==int(uv[1]*2)
            parts.append(f'<rect x="{left+qx*65}" y="{472+qy*58}" width="62" height="55" fill="{"#df9c42" if chosen else "#344356"}"/>')
    parts.append(f'<text x="{left+145}" y="494" class="small">Orange quadrant</text><text x="{left+145}" y="516" class="small">seeds the target.</text>')
    native=plan['native_cover'][0]
    parts.append(f'<text x="{left}" y="619" class="small muted">Native fallback: {native["z"]}/{native["x"]}/{native["y"]}</text>')
parts += ['<rect x="36" y="656" width="1128" height="224" rx="12" fill="#1b2c3d"/>',
          '<text x="60" y="690" font-size="21">What actually reaches the current image model</text>',
          '<text x="60" y="724" class="label">3×3 mosaic → compressed into the top 256×128 pixels</text>',
          '<text x="60" y="755" class="label">Target source → compressed into the bottom 256×128 pixels → generated bottom half cropped</text>',
          '<text x="60" y="792" class="small muted">Parent/native/child selection is implemented in the new planner. The present worker accepts one context image.</text>',
          '<text x="60" y="818" class="small muted">It does not receive separate multi-scale tensors. Child and generated-neighbor references are used only when available.</text>',
          '<text x="60" y="849" class="small muted">Research + user direction → geometry proposal → validate / persist → render shared geometry → optional raster styling.</text>', '</svg>']
path=ROOT/'docs/images/context-selection.svg';path.write_text('\n'.join(parts),encoding='utf-8');print(path.name)
