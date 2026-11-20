# What are zoom tiles?

A 76-second introduction in the Napknstack palette. The first three scenes use a fictional map to show how a tile grid subdivides and how the same bridge and river remain anchored as streets appear. The science sequence uses real captures from the local World Explorer with its curated outline and structured source tiles. The three world-type cards are original illustrations.

## Edit in Final Cut Pro

Open `artifacts/zoom-tiles-intro/` at the project root. Import **What are zoom tiles.fcpxml** into a Final Cut library. The XML references six 1080p30 scene clips in `clips/` by their local paths. Keep that folder in place during import. If you move the package, regenerate the XML or relink the clips.

- Read `recording-script.md` for the VO timing and OBS cues. The host can appear at 00:00–00:04 and 01:10–01:16. The lower-left area of both graphics is open for a keyed overlay.
- Use `scratch-preview.mp4` to rehearse pacing. Record the host and final narration, then use `master-silent.mp4` or the individual scene clips in the final edit.
- Import `captions.srt` after laying down narration and adjust the cue edges to the final takes. `scratch-narration.wav` and `sound-cues.wav` start at zero and can be added separately. The sound cues are original synthesized hits.

| Time | Picture |
| --- | --- |
| 00:00–00:10 | Opening question and the map separating into levels |
| 00:10–00:23 | One, four, and sixteen tiles |
| 00:23–00:37 | One bridge anchors the region-to-street zoom |
| 00:37–00:50 | Knowledge maps, imaginary places, and game worlds |
| 00:50–01:04 | World Explorer science overview, Physics search, and closer subfields |
| 01:04–01:16 | Closing question and OBS host cue |

The narration uses level zero and the 1 → 4 → 16 grid progression as the example. Available Google Maps zoom levels vary by location and map type. [Google Maps tile overlay documentation](https://developers.google.com/maps/documentation/android-sdk/tileoverlay)

## Revise and render locally

Edit `story.json` for the spoken lines, time windows, and scene durations. Edit `film.js` for the Canvas motion and on-screen text. The storyboard and caption timings come from the same JSON. The renderer samples each scene at 30 frames per second.

From the repo root, run these in separate terminals:

```sh
.venv/bin/python scripts/serve_world_explorer.py
.venv/bin/python -m http.server 8798 --bind 127.0.0.1
```

With Chrome, Node, Playwright Core, and FFmpeg installed, run:

```sh
node content/zoom-tiles-intro/render.mjs
.venv/bin/python content/zoom-tiles-intro/assemble.py
```

Set `ZTILES_PLAYWRIGHT_CORE` to the path of an existing Playwright Core installation if it sits outside this repo. The film preview is at `http://127.0.0.1:8798/content/zoom-tiles-intro/?demo` after capture. Omit `?demo` to preview the animation with placeholders. Append `--reuse-demo` to skip capturing the Science map again. Pass a scene slug, such as `05-science-demo`, to render only that scene. Assembly uses the macOS Samantha voice for the timing reference.
