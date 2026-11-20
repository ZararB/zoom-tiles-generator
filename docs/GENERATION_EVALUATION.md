# Actual generation in isometric and other views

The results viewer displays **real CUDA outputs**, not the illustrative animation
map. Run `python scripts/serve_generation_results.py` and open
`http://127.0.0.1:8795/generation-results.html`.

Select a case, then choose:

- **Isometric neighborhood**: actual source/context PNGs projected as flat tiles,
  with the generated center outlined. This does not imply 3D height data.
- **Top-down neighborhood**: the same images without projection, useful for
  checking boundaries and style discontinuities.
- **Source/generated comparison**: original and generated PNGs at equal scale.
- **Exploded inputs/result**: parent reference, recorded context, source and
  generated image. These have different spatial extents, normalized for display.

The generated-coverage slider reveals the original center tile. Switching modes
and coverage preserves the output hash and never requests another inference.
Single-tile Earth recordings explicitly show that a surrounding mosaic was not
recorded; the viewer does not fabricate missing context.

## Real tests

Three fresh Middle-earth tests used the existing application's preset and native
tile source, the pinned InstructPix2Pix model, 20 steps and seed42:

| Case | Target | GPU seconds | Source edge mismatch | Generated edge mismatch |
|---|---|---:|---:|---:|
| Adjacent Shire tile | 4/44/19 | 41.797 | 11.42 | 55.50 |
| Deeper Shire tile | 5/86/39 | 34.360 | 6.11 | 73.47 |
| Minas Tirith inference | 4/73/41 | 55.297 | 3.93 | 80.23 |

The gallery also includes the earlier default and garden-directed Shire outputs,
two legacy four-step Earth cases, and a new twenty-step coastal control.
The coastal control completed in 128.188 seconds. Its colors are less extreme
than the four-step result, but labels and roads still distort. These are observed
single-request times, not a throughput or latency guarantee.
Minas Tirith uses an explicitly inferred stone-city direction; no canonical
layout or researched building positions are asserted.

**Inference succeeded; visual acceptance did not.** Generated greenery and
settlement texture can look plausible in isolation, but the image model changes
the source style, reinterprets baked text as terrain and fails to preserve shared
geometry. The deeper Shire test even produces an oblique road scene despite the
top-down prompt. Isometric display does not fix these defects.

The edge-color diagnostic is the mean absolute RGB difference between each edge
of the tile and the adjacent one-pixel strip in its recorded 3×3 context. Units
are 0–255. The original source is scored against those same neighboring strips
as a baseline. It is an **image-boundary diagnostic**, not a road-connectivity,
water-boundary or canon accuracy score. All five Middle-earth context centers
match their saved source pixels exactly. All displayed output hashes are checked
against the original inference manifests.

## Reproduce and record

```sh
python scripts/pyramid_lab.py --case shire-adjacent-eval --x 44 --y 19 --steps 20
python scripts/pyramid_lab.py --case shire-deep-eval --z 5 --x 86 --y 39 --direction "Small gardens and narrow rural lanes; keep existing road connections." --steps 20
python scripts/pyramid_lab.py --case minas-tirith-eval --region "Minas Tirith" --x 73 --y 41 --direction "Stone city, curved streets, small courtyards; preserve visible terrain and water." --steps 20
python scripts/evaluate_recordings.py --rerun-earth
python scripts/evaluate_recordings.py --mlflow
```

The verified Shire source and draft at `4/43/19` are included with this private
repository and load in the viewer on a fresh checkout. The other recorded
Middle-earth cases need their PNGs and manifests in local `.runtime/` storage.
The evaluation report is
`examples/results/generation-evaluation.json`. Optional MLflow logging records
the real requests and screenshots in a separate local experiment. There are
no mocked images in this gallery.

## What the tests justify changing next

Use shared, saved geometry as the continuity layer; style it with explicit
spatial masks and a suitable conditioned model. Separate vector labels from
baked raster text. Prefer regional/metatile generation with shared edge
constraints over independent unconstrained tile edits. Keep drafts unapproved
until semantic and boundary checks pass. The current model is useful for
exploration, but these tests do not establish production-ready map generation.
