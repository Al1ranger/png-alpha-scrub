**Contribution type** Builder → Intelligent Contracts

**Title** PngAlphaScrub — Consensus-Verified PNG Rewriting

PngAlphaScrub fetches an immutable public PNG and reconstructs its actual
RGBA samples. The leader and validators independently verify the source
digest and chunk CRCs, decompress within a fixed pixel budget, reverse
all five filters, and clear RGB under alpha zero. They require exact
agreement on the complete rewritten PNG and its report before storing it.
Pixels with nonzero alpha retain their exact samples. Distinct inputs can
share one output digest when their differences are confined to alpha zero.

**Verification status** Nine local GenVM tests passed, including byte-for-byte
synthetic fixture comparisons. GitHub publication and StudioNet deployment
are pending.
