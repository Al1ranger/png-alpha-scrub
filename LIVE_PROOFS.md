# StudioNet proofs

[StudioNet contract](https://explorer-studio.genlayer.com/address/0xCf321E79f3D26494D9388C572c4Edb7733CcBF75) · [Deployed source](https://github.com/Al1ranger/png-alpha-scrub/blob/20aff7141018f05530ec0f1987e2ccbb22a9388a/contracts/PngAlphaScrub.py) · [Pinned fixtures](https://github.com/Al1ranger/png-alpha-scrub/tree/20aff7141018f05530ec0f1987e2ccbb22a9388a/fixtures) · [Receipt and readback data](https://github.com/Al1ranger/png-alpha-scrub/blob/main/PROOFS.json)

The deployed source matches the pinned commit. Normalized source SHA-256 is `dc55c5a93a750c79dde9eb9669c6dde38b21016e32078ec922ebdc4f90af7db9`.
All four receipts finalized with successful execution and majority agreement.

| Transaction | Agree votes | Report ID | Rewritten PNG SHA-256 |
| --- | ---: | --- | --- |
| [deploy](https://explorer-studio.genlayer.com/tx/0xbc0ba292514e14c614de45e08ac429b44f962236477e0b57361f1ece05a326ed) | 5 | — | — |
| [alpha-original](https://explorer-studio.genlayer.com/tx/0x92c73b31f7583736528e7bea1089612bea1fb0da5d80a9a91d8de1223f0ba757) | 3 | `63f112783029021ed6025bd5470e9032983125e45ec4c2a0f7a0644982187f18` | `b6e7e5c2b97b05e63582c4aec335c21a3c56622c0c409ca48ed622c8ddaee366` |
| [alpha-variant](https://explorer-studio.genlayer.com/tx/0x68f9ce5d44d85a8b192eced03592c11ca1d6e27a5fe5b42f2bc52038c0572359) | 3 | `1b4163123c33587f922418d9fd746e935329c0014fe54e222f72052ee19b4764` | `b6e7e5c2b97b05e63582c4aec335c21a3c56622c0c409ca48ed622c8ddaee366` |
| [visible-change](https://explorer-studio.genlayer.com/tx/0xb4add24422918896eed436454222ad041e888c2e9708cbccae68333386862851) | 3 | `42a2e3bf75f08a64a3b90f12d912b985aa14e09ecd975f43e4c241cfd7e6c296` | `890d8732d3c5f8a8e710ed6804296169078cbc66a6bfee6c438076162aad5397` |

Each readback matched the expected PNG bytes. An independent Node.js decoder checked each RGBA sample.
The first two images share one output despite different transparent RGB samples and text chunks.
The third changes one red sample at alpha 1 and yields a distinct output.
A read against an unknown PNG digest reverted.
