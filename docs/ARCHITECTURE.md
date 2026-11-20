# Architecture and application boundary

`zoom_tiles/geometry.py` validates editable GeoJSON and derives render-only water,
land patches, interior labels, topology counts and geodesic area. Its content hash
excludes timestamps and provenance. `features` are editable; `render_features` are
derived. Baseline water footprints are a separate input.

`dev-ui/lib/geography.js` composes those features into the pinned MapLibre style.
It retains base terrain/road/building layers and suppresses symbols only within
actual edited water. New water overlays flooded detail. Reclaimed-land patches
are restricted to former baseline water; there is no regional opaque rectangle.

`dev-ui/lib/map-names.js` handles the name-only Lake Ontario example and a reusable
offscreen tile renderer. The source tile has 256 pixels, so its MapLibre camera
zoom is slippy zoom minus one. Source rendering and the visible map use the same
geometry/style composition.

`tile-cache.js` has a bounded 128-entry RAM cache and optional 192-entry browser
cache. Concurrent requests for the same source share work. Keys contain pipeline,
world hash, names and coordinate. Preview updates are debounced by 300 ms and
stale results are discarded.

`zoom_tiles/jobs.py` keeps at most one inference active, bounds the queue to 32
jobs and stores up to 256 results / 256 MiB. Requests are deduplicated by source,
context, world, prompt, coordinate, model, seed and step hashes. Cached results
retain their generation revision. Viewport subscriptions cancel obsolete queued
work; active requests finish into cache. This local broker is not durable across
restart, distributed or tenant-aware.

`pod_server.py` is the optional CUDA worker. It composes context above source for
image-to-image inference, crops the source half, resizes it back, and returns
model/seed/steps/world/image metadata. Its echoed world hash is provenance, not a
server-side proof that a client supplied the correct pixels.

## Local HTTP contracts

| Route | Meaning |
| --- | --- |
| GET/POST `/api/geography` | Read or validate/save current local world; writes require expected_revision |
| POST `/api/geography/undo` | Restore an earlier saved snapshot as a new revision |
| GET/POST `/api/geography/proposals` | Inspect or create validated drafts |
| POST `/api/geography/proposals/{id}/apply` | Apply a draft only against its unchanged base |
| GET `/api/examples` | Example catalog |
| GET `/api/examples/{id}/{before,after}` | Allowlisted raw fixture document |
| POST `/api/tile-jobs` | Queue current-world inference or reuse a cached result |
| GET `/api/tile-jobs/{id}` | Job/result lookup |
| POST `/api/tile-jobs/cancel` | Cancel queued subscriptions for a client |
| GET `/api/tile-worker/health` | Same-origin proxy to optional worker readiness |
| POST `/api/tile-worker/edit` | Compatibility proxy to direct inference |

Invalid geometry returns 422; revision conflicts return 409. Geometry writes are
serialized and atomic within the local server. These endpoints have no production
authentication; bind them only to localhost.

For an application backend, scope every map, proposal, artifact and subscription
to its authorized owner/tenant. Use DB transactions for revisions and an outbox
for durable dispatch, a broker with leases/retries/fairness, and immutable object
storage for images. Workers create drafts; authorized application actions apply
them. Serve image URLs/status separately rather than repeatedly polling base64.

Regional dependency hashes should include changed geometry, old/new label effects,
style/basemap versions and neighboring context. A cache hit must remain valid even
when unrelated features change elsewhere. Add race-safe monotonic viewport epochs
when distributing the broker; the prototype is not a production distributed
protocol. Enforce authoritative masks and cross-tile/zoom QA before promoting AI
textures onto the map.
