"""Generate known RGBA rasters, with each PNG filter and separate IDAT chunks."""
import hashlib
import json
import struct
import zlib
from pathlib import Path

SIGNATURE = b"\x89PNG\r\n\x1a\n"
WIDTH, HEIGHT = 7, 5
ROOT = Path(__file__).resolve().parents[1]


def chunk(kind, data):
    return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data))


def png(data, note=None, level=6):
    header = struct.pack(">IIBBBBB", WIDTH, HEIGHT, 8, 6, 0, 0, 0)
    compressed = zlib.compress(data, level)
    pieces = [compressed] if note is None else [compressed[:13], compressed[13:]]
    text = b"" if note is None else chunk(b"tEXt", b"Comment\x00" + note)
    return (SIGNATURE + chunk(b"IHDR", header) + text
            + b"".join(chunk(b"IDAT", payload) for payload in pieces) + chunk(b"IEND", b""))


def filter_row(row, previous, mode):
    def estimate(i):
        a, b, c = (row[i - 4] if i >= 4 else 0), previous[i], (previous[i - 4] if i >= 4 else 0)
        if mode < 4:
            return (0, a, b, (a + b) // 2)[mode]
        return min((a, b, c), key=lambda x: abs(a + b - c - x))
    return bytes((mode,)) + bytes((value - estimate(i)) % 256 for i, value in enumerate(row))


def samples(variant, visible_change=False):
    result = []
    for i in range(WIDTH * HEIGHT):
        alpha = (0, 1, 128, 255)[i % 4]
        rgb = (i * 53 % 256, i * 41 % 256, (i * 13 + 7) % 256)
        if not alpha and variant:
            rgb = (1 + i, 10 + i, 20 + i)
        if i == 1 and visible_change:
            rgb = (rgb[0] ^ 1, *rgb[1:])
        result.append(bytes((*rgb, alpha)))
    return result


def scanlines(pixels, use_filters):
    width = WIDTH * 4
    rgba = b"".join(pixels)
    rows = [rgba[i:i + width] for i in range(0, len(rgba), width)]
    prior = [bytes(width), *rows]
    return b"".join(filter_row(row, prior[i], i if use_filters else 0) for i, row in enumerate(rows))


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def build():
    outputs = {}
    for name, variant, visible in (
        ("alpha-original", False, False), ("alpha-variant", True, False), ("visible-change", True, True),
    ):
        pixels = samples(variant, visible)
        source = png(scanlines(pixels, True), name.encode("ascii"))
        cleaned = [pixel if pixel[3] else b"\x00" * 4 for pixel in pixels]
        result = png(scanlines(cleaned, False), level=0)
        outputs[name] = {
            "source_sha256": digest(source), "width": WIDTH, "height": HEIGHT,
            "transparent_pixels": sum(pixel[3] == 0 for pixel in pixels),
            "changed_pixels": sum(a != b for a, b in zip(pixels, cleaned)),
            "png_id": digest(result), "png_hex": result.hex(), "rgba_hex": b"".join(cleaned).hex(),
        }
        (ROOT / "fixtures" / (name + ".png")).write_bytes(source)
    assert outputs["alpha-original"]["png_id"] == outputs["alpha-variant"]["png_id"]
    assert outputs["alpha-original"]["png_id"] != outputs["visible-change"]["png_id"]
    (ROOT / "REFERENCE.json").write_text(json.dumps(outputs, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    build()
