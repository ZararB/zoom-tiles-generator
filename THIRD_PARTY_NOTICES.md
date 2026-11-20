# Third-party notices

The root MIT license covers original project code, not a relicensing of upstream
dependencies, map data, styles, fonts, sprites or model weights.

| Component | Source / retained notice |
| --- | --- |
| MapLibre GL JS 5.24.0 | BSD-3-Clause; `dev-ui/vendor/maplibre-LICENSE.txt`; pinned download manifest |
| MapLibre GL Leaflet bridge 0.1.4 | `dev-ui/vendor/bridge-LICENSE`; pinned download manifest |
| Leaflet 1.9.4 | BSD-2-Clause; `docs/licenses/Leaflet-LICENSE.txt`; loaded from the pinned CDN URL |
| OpenFreeMap style and upstream Liberty components | `docs/licenses/OpenFreeMap-styles-LICENSE.md`; the retained notice lists upstream component terms |
| OpenStreetMap-derived basemap data | OpenStreetMap contributors, OpenMapTiles; retain the attribution displayed by the map and the data provider's terms |
| Middle-earth preview tiles | Source artwork by Fraser Marlow via middle-earth-interactive-map.web.app. The included source and derived GPU previews are for private development review. The project claims no underlying Tolkien estate rights. |
| Natural Earth five-lake outlines | Public domain; `dev-ui/scenarios/source.json` records the original URL and SHA256 |
| InstructPix2Pix | Downloaded separately from `timbrooks/instruct-pix2pix` at the revision in settings.py; consult its upstream model card, license and underlying model terms. No weights are distributed here. |

Natural Earth terms: https://www.naturalearthdata.com/about/terms-of-use/

Style source: https://github.com/hyperknot/openfreemap-styles

Basemap provider: https://openfreemap.org/

Model card: https://huggingface.co/timbrooks/instruct-pix2pix

Screenshots are actual rendered fictional edits over the attributed basemap.
The application screenshot includes map attribution and is not a generated claim
about real boundaries, flooding or infrastructure.


## Optional local text planning

The optional text planner can use a separately installed Qwen3 GGUF and llama.cpp runtime. Neither the model weights nor runtime binaries are distributed here. They retain their upstream licenses and must be configured by the host. Model-generated outlines are unverified and are not a substitute for cited research.
