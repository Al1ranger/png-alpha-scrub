import hashlib
import json
import re
import struct
import sys
import zlib
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
CODE = ROOT / "contracts/PngAlphaScrub.py"
BASE = "Al1ranger/png-alpha-scrub/" + "a" * 40 + "/fixtures/"
REFERENCE = json.loads((ROOT / "REFERENCE.json").read_text(encoding="utf-8"))


@pytest.fixture
def scrubber(direct_deploy):
    contract = direct_deploy(str(CODE))
    return contract, sys.modules[type(contract._instance).__module__]


def fixture(name):
    return (ROOT / "fixtures" / (name + ".png")).read_bytes()


def data_in_canonical_png(blob):
    # Independent check for the known output layout and decoded RGBA bytes.
    assert blob[12:16] == b"IHDR"
    width, height = struct.unpack(">II", blob[16:24])
    size = struct.unpack(">I", blob[33:37])[0]
    assert blob[37:41] == b"IDAT"
    raw = zlib.decompress(blob[41:41 + size])
    assert len(raw) == height * (1 + width * 4)
    assert blob[45 + size:] == bytes.fromhex("0000000049454e44ae426082")
    rows = [raw[i:i + width * 4 + 1] for i in range(0, len(raw), width * 4 + 1)]
    assert all(row[0] == 0 for row in rows)
    return b"".join(row[1:] for row in rows)


def test_public_workflow_deduplicates_hidden_changes_only(scrubber, direct_vm):
    contract, mod = scrubber
    seen = []
    for name, expected in REFERENCE.items():
        body = fixture(name)
        ref = BASE + name + ".png"
        url = mod.RAW + ref
        direct_vm.mock_web(re.escape(url) + "$", {"method": "GET", "response": {
            "status": 200, "headers": {}, "body": body,
        }})
        rid = contract.scrub(ref, expected["source_sha256"])
        report = contract.get_report(rid)
        assert report == {"schema": "png-alpha-scrub/1", "source_url": url,
                          **{k: v for k, v in expected.items() if k not in ("png_hex", "rgba_hex")}}
        png = contract.get_png(report["png_id"])
        assert png == expected["png_hex"]
        assert data_in_canonical_png(bytes.fromhex(png)).hex() == expected["rgba_hex"]
        assert direct_vm.run_validator()
        forged = {"report": report, "png_hex": png[:-2] + "00"}
        assert not direct_vm.run_validator(leader_result=mod.canonical(forged))
        seen.append((rid, report["png_id"]))
    assert seen[0][0] != seen[1][0]
    assert seen[0][1] == seen[1][1] != seen[2][1]
    direct_vm.clear_mocks()
    direct_vm.mock_web(re.escape(url) + "$", {"method": "GET", "response": {
        "status": 200, "headers": {}, "body": body[:-1] + b"\x00",
    }})
    assert not direct_vm.run_validator()
    with direct_vm.expect_revert("PNG evidence unavailable"):
        contract.scrub(ref, expected["source_sha256"])
    assert contract.get_png(report["png_id"]) == png


@pytest.mark.parametrize("mutation", [
    lambda b: b[:-1],
    lambda b: b[:-1] + b"\x00",
    lambda b: b + b"x",
    lambda b: b"\x89PNG" + b[4:8],
])
def test_rejects_bad_crc_missing_and_trailing_chunks(scrubber, mutation):
    _, mod = scrubber
    with pytest.raises(ValueError):
        mod.decode_png(mutation(fixture("alpha-original")))


@pytest.mark.parametrize("raw", [b"\x00" * 10000, b"\x05\x01\x02\x03\x00", b"\x00"],
                         ids=["oversized", "invalid-filter", "truncated"])
def test_rejects_oversized_or_invalid_scanlines(scrubber, raw):
    _, mod = scrubber
    header = struct.pack(">IIBBBBB", 1, 1, 8, 6, 0, 0, 0)
    binary = (mod.SIGNATURE + mod.chunk(b"IHDR", header)
              + mod.chunk(b"IDAT", zlib.compress(raw)) + mod.chunk(b"IEND", b""))
    with pytest.raises(ValueError):
        mod.decode_png(binary)


def test_rejects_out_of_profile_headers(scrubber):
    _, mod = scrubber
    header = struct.pack(">IIBBBBB", 1, 1, 8, 6, 0, 0, 1)
    binary = mod.SIGNATURE + mod.chunk(b"IHDR", header) + mod.chunk(b"IEND", b"")
    with pytest.raises(ValueError, match="non-interlaced RGBA8"):
        mod.decode_png(binary)
