# Reproduce and record the examples

1. Generate the fixtures with `python scripts/generate_examples.py`.
2. Start the isolated demo with `--record-examples` on port 8791. It uses `.runtime/`, not another app's data.
3. Choose each example, click Load before and wait for its loaded status. Capture
   the page with the basemap attribution visible. Repeat with Load after.
4. Record the world content hash, case ID, phase and result in
   `examples/results/browser-recordings.json`. This repository's checked-in images
   are actual browser captures, not AI illustrations or claimed video recordings.
5. For invalid-bowtie, the after action must return 422, report rejection and leave
   the saved hash unchanged. A network error does not count as successful rejection.

The matching before/after camera bounds come from the union of both input extents.
Names and connected-component counts are separate measurements. The Great Lakes
case has five named features before and two after, but its original union has four
components because Michigan and Huron already touch in this source dataset.

Optional GPU recordings use real source PNGs downloaded from the composed map,
not fabricated basemaps. Save source/result PNGs, prompt, model revision, seed,
steps, tile coordinate, world hash and SHA256s. Label low-step results as drafts.
The optional recording runner validates image hashes, PNG dimensions, CUDA use
and successful responses, not aesthetic quality or exact coastline fidelity.

To record fresh GPU outputs after capturing source PNGs:

```sh
python scripts/record_gpu_examples.py --base http://127.0.0.1:8888 --steps 4
```

See each `examples/gpu/<case>/input.json` for source capture instructions and each
generated manifest for actual timings and limitations. GPU runs are opt-in and
are not part of the default CPU CI test job.

With recording explicitly enabled, set a source tile and click **Record source example**. The local-only API saves the PNG, exact world revision/hash and prompt under the selected allowlisted example. It is disabled in a normal demo launch. Use `--case <id>` to run one selected GPU sample, and `--seed` to record another seed; retain rejected-response manifests as evidence. The checked-in twenty-step canal variant shares the exact source of its four-step counterpart and was rejected by the model checker.
