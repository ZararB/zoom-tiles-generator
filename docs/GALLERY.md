# Recorded map-edit examples

The [Middle-earth context guide](CONTEXT_AND_GENERATION.md) adds five actual
20-step CUDA requests using the application's supplied pyramid pack, plus an
[interactive explanation of context across zooms](context-explorer.html).
[Recorded results](../examples/results/middle-earth-validation.json) distinguish
the prompt-truncation failure from corrected user-directed outputs. These are
speculative raster drafts. The README shows the recovered Shire pair and
archived recursive zoom chains. [Middle-earth demos](../README.md#middle-earth-generated-zoom-tiles)

These are actual browser captures of fictional edits over the attributed vector basemap. Each pair uses the same camera bounds. Geometry checks and optional real GPU drafts are separate evidence.

| Example | What is checked | Before | After |
| --- | --- | --- | --- |
| [Lake Ontario to Lake America](../examples/cases/rename-only/after.json) | Only the name changes; editable shoreline coordinates stay identical. | ![Before Lake Ontario to Lake America](images/rename-only-before.jpg) | ![After Lake Ontario to Lake America](images/rename-only-after.jpg) |
| [Five Great Lakes into two](../examples/cases/great-lakes-merge/after.json) | Five named outlines become two expanded water bodies. Michigan and Huron already connect in the source geometry. | ![Before Five Great Lakes into two](images/great-lakes-merge-before.jpg) | ![After Five Great Lakes into two](images/great-lakes-merge-after.jpg) |
| [Join reservoirs with a canal](../examples/cases/reservoir-canal/after.json) | A narrow water connector removes the internal shorelines and joins two reservoirs. | ![Before Join reservoirs with a canal](images/reservoir-canal-before.jpg) | ![After Join reservoirs with a canal](images/reservoir-canal-after.jpg) |
| [Carve three islands](../examples/cases/three-islands/after.json) | Three land polygons cut real holes in one lake without replacing the source water feature. | ![Before Carve three islands](images/three-islands-before.jpg) | ![After Carve three islands](images/three-islands-after.jpg) |
| [Shrink a reservoir](../examples/cases/lake-recession/after.json) | Reclaimed land is confined to the old water footprint; nearby detail remains untouched. | ![Before Shrink a reservoir](images/lake-recession-before.jpg) | ![After Shrink a reservoir](images/lake-recession-after.jpg) |
| [Expand a floodplain lake](../examples/cases/flood-expansion/after.json) | Water expands over low ground; unaffected terrain and settlements retain their map detail. | ![Before Expand a floodplain lake](images/flood-expansion-before.jpg) | ![After Expand a floodplain lake](images/flood-expansion-after.jpg) |
| [Divide an inland sea](../examples/cases/inland-sea-split/after.json) | A land bridge splits one editable water feature into two connected water components. | ![Before Divide an inland sea](images/inland-sea-split-before.jpg) | ![After Divide an inland sea](images/inland-sea-split-after.jpg) |
| [Extend a coastal headland](../examples/cases/coastal-headland/after.json) | A land polygon attached to the west bank narrows a bay and creates a new shoreline. | ![Before Extend a coastal headland](images/coastal-headland-before.jpg) | ![After Extend a coastal headland](images/coastal-headland-after.jpg) |
| [Move a district border](../examples/cases/border-relocation/after.json) | Only the fictional border moves; both saved and derived water geometry remain unchanged. | ![Before Move a district border](images/border-relocation-before.jpg) | ![After Move a district border](images/border-relocation-after.jpg) |
| [Reshape a river bend](../examples/cases/river-reshaping/after.json) | A revised river corridor exposes the old bends and keeps the remaining surroundings detailed. | ![Before Reshape a river bend](images/river-reshaping-before.jpg) | ![After Reshape a river bend](images/river-reshaping-after.jpg) |
| [Reject a crossing shoreline](../examples/cases/invalid-bowtie/after.json) | A self-intersecting polygon is rejected; the current saved map must stay unchanged. | ![Before Reject a crossing shoreline](images/invalid-bowtie-before.jpg) | ![After Reject a crossing shoreline](images/invalid-bowtie-after.jpg) |

## Evidence

- [Geometry validation](../examples/results/geometry-validation.json): all 11 cases, including expected invalid-input rejection.
- [Actual browser recording metadata](../examples/results/browser-recordings.json): 22 before/after captures and saved world hashes.
- [Optional GPU evidence](../examples/results/gpu-validation.json): real CUDA runs, separate from deterministic geometry and mocked tests.

All polygons and boundaries in these examples are fictional edits. Five named Great Lakes become two; the original union has four connected components because Michigan and Huron touch.

## Actual GPU requests

Four-step images are low-quality integration drafts. Color, text and shorelines can drift; these samples are not approved map imagery. Successful PNG/provenance validation is not an aesthetic-quality score.

### three-islands

Actual CUDA inference: 4 steps, 7.047 seconds.

| Source tile | Unapproved GPU draft |
| --- | --- |
| ![Source](../examples/gpu/three-islands/source.png) | ![Draft](../examples/gpu/three-islands/result.png) |

[Input and prompt](../examples/gpu/three-islands/input.json) / [Actual response manifest](../examples/gpu/three-islands/manifest.json).

### reservoir-canal

Actual CUDA inference: 4 steps, 7.219 seconds.

| Source tile | Unapproved GPU draft |
| --- | --- |
| ![Source](../examples/gpu/reservoir-canal/source.png) | ![Draft](../examples/gpu/reservoir-canal/result.png) |

[Input and prompt](../examples/gpu/reservoir-canal/input.json) / [Actual response manifest](../examples/gpu/reservoir-canal/manifest.json).

### coastal-headland

Actual CUDA inference: 4 steps, 13.703 seconds.

| Source tile | Unapproved GPU draft |
| --- | --- |
| ![Source](../examples/gpu/coastal-headland/source.png) | ![Draft](../examples/gpu/coastal-headland/result.png) |

[Input and prompt](../examples/gpu/coastal-headland/input.json) / [Actual response manifest](../examples/gpu/coastal-headland/manifest.json).

### flood-expansion

Actual worker response: HTTP 422; **Image did not pass the model safety checker**. The checker remained enabled. No result image is claimed for this rejected request.

![Source tile for rejected request](../examples/gpu/flood-expansion/source.png)

[Input and prompt](../examples/gpu/flood-expansion/input.json) / [Actual response manifest](../examples/gpu/flood-expansion/manifest.json).

### reservoir-canal-20

Actual worker response: HTTP 422; **Image did not pass the model safety checker**. The checker remained enabled. No result image is claimed for this rejected request.

![Source tile for rejected request](../examples/gpu/reservoir-canal-20/source.png)

[Input and prompt](../examples/gpu/reservoir-canal-20/input.json) / [Actual response manifest](../examples/gpu/reservoir-canal-20/manifest.json).


## Zoom and pan recordings

The saved world hash stayed unchanged while the camera moved in three different examples. [Recorded measurements](../examples/results/navigation-recordings.json).

![great-lakes-merge zoom and pan](images/great-lakes-merge-zoom-pan.jpg)

![reservoir-canal zoom and pan](images/reservoir-canal-zoom-pan.jpg)

![three-islands zoom and pan](images/three-islands-zoom-pan.jpg)
