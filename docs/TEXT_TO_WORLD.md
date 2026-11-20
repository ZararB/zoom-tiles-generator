# Text-created worlds and navigable generated tiles

```sh
python scripts/serve_world_explorer.py
# http://127.0.0.1:8796/world-explorer.html
```

World Explorer runs locally with the API described below.

## Create a map from plain text

Enter a request, such as “A map of science, organized into fields and subfields”
or “A map of history, organized around societies, trade, culture and technology”.

- **Local AI planner:** optional existing Qwen3 1.7B GGUF with a llama.cpp CPU
  runtime. It generates a schema-constrained topic outline. Labels, branches and
  counts are validated; model hash, policy, seed and timing are recorded. The
  planner does not research sources or verify facts.
- **Fast scaffold:** curated science/history outlines or a scaffold derived from
  user-supplied topic text. The planner identity is explicit in the world record.

The outline becomes a deterministic pixel-space topic atlas: stable node IDs,
positions, parents, edges and reveal zooms are saved. These are conceptual
relationships, not measured geography or claims of exhaustive coverage.

Creation immediately renders five source seed tiles at directory levels 0 and 1.
Other source tiles are drawn lazily at levels 0–7. The overview is usable before
GPU work completes. Subfields appear as the user zooms. Search jumps to saved
topics. Names and links are vector overlays, so raster generation cannot move
or rename them. Initial semantic depth is finite: deeper raster generation does
not invent new researched facts or expand the topic graph by itself.

The optional planner reads `ZOOM_TEXT_MODEL_PATH` and `ZOOM_LLAMA_COMPLETION`.
For this workspace it also detects an existing sibling `.local-query-model/`
installation. No model/runtime binary is distributed in this repository. The
configured CLI must support the Qwen chat template and llama.cpp schema flags.
The CPU planner uses two threads and a 180-second bound. GPU image work remains
on the existing localhost worker. No paid API is required.

The built-in **Map of science** uses an illustrated tile backdrop. Seven field
illustrations and a compass mark the overview. Zooming into Physics reveals a
smaller Mechanics illustration at its saved topic location. Topic names, search
targets, and connections still use the saved graph. The AI-generated atlas
artwork ships with the project and loads in the **Original / structured source**
layer without any image service or GPU worker.

The **Media & entertainment** example uses the same renderer with its own
artwork. Search for Film to see its projector landmark and the Film production
clapboard. Both examples pair a curated outline with a bundled illustration
sheet. Free-form prompts and local AI outlines can make navigable topic maps.
Matching illustrations for arbitrary topics would need a separate artwork
step.

## Navigate like a tile map

Drag to pan, scroll or use +/− to zoom, search for topics/places, or fit the map.
Original, raw AI draft, blended draft and full-map swipe comparison are separate
layers. World, layer, auto-generation preference and camera survive browser
reloads; the world definition and artifacts survive server restarts.

After 1.2 seconds of settled navigation, the browser selects up to three missing
visible targets nearest the camera. A local single-worker broker deduplicates
requests, keeps at most 24 active/queued jobs, applies a 12-new-tile per
client/world session budget and drops obsolete queued subscriptions. Running
work can finish into its immutable world cache. Initial seed jobs remain pinned.
These local counters are **not** a production billing or authorization boundary.

The model receives a 3×3 mosaic and source PNG. Already-generated nearby tiles
are eligible as context. A missing fine tile can inherit the exact crop of a
generated ancestor; otherwise the original/structured source is used. The actual
source origin and each context artifact hash are recorded in the manifest.
The context plan is a reference list; the current image model still receives one
mosaic rather than separate multi-scale conditioning tensors.

Raw results are retained. A separate 24px edge-feather composite keeps original
source-border pixels, making transitions less abrupt. This is visual compositing,
not a guarantee of road, coastline, semantic or parent/child geometry correctness.
Both generated layers remain drafts. A rejected result does not replace source
imagery; failed jobs are not automatically retried on every pan.

## Expanded Middle-earth test

Seven new real 20-step CUDA requests extend the earlier Shire results into a
complete 3×3 patch at directory z4, x42–44/y18–20. The explorer also imports the
earlier finer Shire and Minas Tirith results. An additional viewport-generated
tile expands the neighborhood further. Original source tiles remain available
outside the generated patch and at every supported zoom.

Middle-earth uses the existing app preset: 7680×4386 source pixels, native
directory z0–2, extended z−2–8, no wrapping. The provided Shire landmark is
(2772,1258). These are pixel coordinates; x can exceed 2^z. Full-map fit renders
the native pyramid and does not run expensive synchronous diffusion on tile GET.

## Local API

| Endpoint | Behavior |
|---|---|
| `GET /api/planner` | Local text-planner availability |
| `GET /api/worlds` | Saved worlds and source geometry |
| `POST /api/worlds` | `{prompt, use_local_ai}` creates a world and queues its initial GPU draft |
| `GET /api/worlds/{id}` | Saved nodes, edges, prompt, revision and provenance |
| `GET /api/worlds/{id}/tiles/{z}/{x}/{y}.png?mode=original|raw|blended` | Non-generating tile read; returns an available result or source/ancestor fallback |
| `POST /api/worlds/{id}/viewport` | `{client_id, epoch, tiles:[{z,x,y}]}` queues bounded visible work |
| `GET /api/worlds/{id}/status` | Jobs and generated artifacts |

Mutations require the exact loopback page origin. The server is bound to
127.0.0.1; it is not an authenticated public service. World prompts, local model
output, world state and generated images stay in ignored `.runtime/` storage.
CPU source cache is capped at 512 tiles/world; browser bitmaps at 192. Generated
artifacts are retained and require a production retention/object-storage policy.

## Known limits

The text model can make poor or incomplete conceptual groupings. No citations are
fabricated and no live research is claimed. The image model can alter style,
reinterpret text and produce perspective imagery. One AI-science overview was
rejected by the model checker; its source map remained usable. History refinement
and navigation-generated child imagery completed. Model checks stay enabled.

World jobs persist locally but lack distributed leases, transactional outboxes,
cross-process fairness and durable billing. An interrupted request can be retried
after restart. A production integration needs resolved artifact provenance and
cache keys that include model and pipeline versions.
