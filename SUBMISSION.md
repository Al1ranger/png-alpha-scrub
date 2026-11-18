**Contribution type** Builder → Intelligent Contracts

**Title** PngAlphaScrub — Consensus-Verified PNG Rewriting

**Notes / Description**

PngAlphaScrub is a reusable GenLayer primitive for stripping hidden RGB data from fully transparent PNG pixels. The leader and validators independently fetch a commit-pinned image, verify its SHA-256 and chunk CRCs, decompress the bounded image, reverse its filters, and rebuild the PNG after clearing RGB at alpha zero. Exact agreement covers the full rewritten bytes and source-bound report. Consumers retrieve the stored image by digest.

StudioNet proofs cover deployment and three rewrites. Two images with different hidden RGB and text chunks produced the same PNG, with separate provenance reports. A change at alpha 1 yielded a different output. The contract supports non-interlaced RGBA8 PNGs up to 32×32. Original GitHub files remain public.

**Evidence**

- [Repository](https://github.com/Al1ranger/png-alpha-scrub)
- [Deployed source](https://github.com/Al1ranger/png-alpha-scrub/blob/20aff7141018f05530ec0f1987e2ccbb22a9388a/contracts/PngAlphaScrub.py)
- [StudioNet contract](https://explorer-studio.genlayer.com/address/0xCf321E79f3D26494D9388C572c4Edb7733CcBF75)
- [Proof ledger](https://github.com/Al1ranger/png-alpha-scrub/blob/main/LIVE_PROOFS.md)
- [deploy](https://explorer-studio.genlayer.com/tx/0xbc0ba292514e14c614de45e08ac429b44f962236477e0b57361f1ece05a326ed)
- [alpha-original](https://explorer-studio.genlayer.com/tx/0x92c73b31f7583736528e7bea1089612bea1fb0da5d80a9a91d8de1223f0ba757)
- [alpha-variant](https://explorer-studio.genlayer.com/tx/0x68f9ce5d44d85a8b192eced03592c11ca1d6e27a5fe5b42f2bc52038c0572359)
- [visible-change](https://explorer-studio.genlayer.com/tx/0xb4add24422918896eed436454222ad041e888c2e9708cbccae68333386862851)
