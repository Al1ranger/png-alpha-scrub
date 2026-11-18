# PngAlphaScrub

PngAlphaScrub rebuilds a PNG with zero RGB under every fully transparent
pixel. Each pixel with nonzero alpha keeps its exact input samples,
including pixels with alpha 1. Consumers can retrieve the actual rewritten
PNG and verify its digest.

Anyone can call `scrub("owner/repo/commit/path.png", sha256)`. The leader
and validators independently download the commit-pinned file, check the
source digest and chunk CRCs, bound inflation to the expected pixel grid,
and reverse all five PNG filters. They apply the same pixel rule and build
a new PNG using fixed scanlines and one stored DEFLATE block. Exact equality
of the source-bound report and the entire output PNG is required before
storage. [PNG specification](https://www.w3.org/TR/png-3/)

`get_report(report_id)` returns the input provenance, dimensions, number
of transparent and changed pixels, and the output digest. `get_png(png_id)`
returns the image as hex. Two inputs that differ only under alpha zero
can share one stored output while retaining independent reports.

The contract accepts non-interlaced RGBA8 images up to 32×32. It accepts
only a bounded set of text and time chunks, which the output omits. Images
with colour profiles, animation, or other unsupported chunks are rejected.
The original GitHub object remains public. The contract acts on the newly
constructed PNG bytes.

The authored fixtures use all five filters and split compressed image data
over two chunks. They demonstrate equal output for hidden-colour changes and
different output for a change at alpha 1.

```sh
python scripts/make_fixtures.py
python -m pip install -r requirements-dev.txt
python -m pytest tests -q
genvm-lint check contracts/PngAlphaScrub.py
```

The StudioNet proof runner expects a public repository commit containing
the fixtures and the pinned JS SDK from `npm ci`. Set a configured StudioNet
signer in the deployment harness and run `node scripts/prove.mjs <commit>`.
The `--verify-only` mode checks existing receipts and reads.

[StudioNet proofs](LIVE_PROOFS.md) · [Submission](SUBMISSION.md)
