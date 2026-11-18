# { "Depends": "py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6" }
import hashlib
import json
import re
import zlib

from genlayer import TreeMap, gl

SIGNATURE = b"\x89PNG\r\n\x1a\n"
PROFILE = b"\x08\x06\x00\x00\x00"
RAW = "https://raw.githubusercontent.com/"
METADATA = {b"tEXt", b"zTXt", b"iTXt", b"tIME"}


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def sha(data):
    return hashlib.sha256(data).hexdigest()


def source_url(ref):
    if not isinstance(ref, str) or len(ref) > 220:
        raise ValueError("Invalid repository reference")
    parts = ref.split("/")
    if len(parts) < 4 or not re.fullmatch(r"[a-zA-Z0-9_-]{1,39}", parts[0]):
        raise ValueError("Invalid repository owner")
    if not re.fullmatch(r"[a-zA-Z0-9_-][a-zA-Z0-9_.-]{0,99}", parts[1]):
        raise ValueError("Invalid repository name")
    if not re.fullmatch(r"[a-f0-9]{40}", parts[2]):
        raise ValueError("Expected commit hash")
    if not all(re.fullmatch(r"[a-zA-Z0-9_-][a-zA-Z0-9_.-]{0,95}", part) for part in parts[3:]):
        raise ValueError("Invalid PNG path")
    if not parts[-1].endswith(".png"):
        raise ValueError("Expected a PNG file")
    return RAW + ref


def paeth(left, up, corner):
    estimate = left + up - corner
    distances = abs(estimate - left), abs(estimate - up), abs(estimate - corner)
    if distances[0] <= min(distances[1], distances[2]):
        return left
    return up if distances[1] <= distances[2] else corner


def undo_filters(raw, width, height):
    stride = width * 4
    pixels = bytearray()
    prior = bytearray(stride)
    for row in range(height):
        offset = row * (stride + 1)
        selector = raw[offset]
        if selector > 4:
            raise ValueError("Invalid PNG scanline filter")
        current = bytearray(stride)
        for i in range(stride):
            left = current[i - 4] if i >= 4 else 0
            up = prior[i]
            corner = prior[i - 4] if i >= 4 else 0
            prediction = 0
            if selector == 1:
                prediction = left
            elif selector == 2:
                prediction = up
            elif selector == 3:
                prediction = (left + up) // 2
            elif selector == 4:
                prediction = paeth(left, up, corner)
            current[i] = (raw[offset + 1 + i] + prediction) & 255
        pixels.extend(current)
        prior = current
    return pixels


def decode_png(body):
    if not isinstance(body, bytes) or not 8 <= len(body) <= 65536 or body[:8] != SIGNATURE:
        raise ValueError("Invalid or oversized PNG body")
    cursor, count = 8, 0
    width, height = 0, 0
    idat_seen, idat_closed, ended = False, False, False
    compressed = bytearray()
    while cursor < len(body):
        count += 1
        if count > 64 or cursor + 12 > len(body):
            raise ValueError("Invalid number or framing of PNG chunks")
        size = int.from_bytes(body[cursor:cursor + 4], "big")
        kind = body[cursor + 4:cursor + 8]
        last = cursor + 8 + size
        if last + 4 > len(body):
            raise ValueError("Truncated PNG chunk")
        data = body[cursor + 8:last]
        if zlib.crc32(kind + data) != int.from_bytes(body[last:last + 4], "big"):
            raise ValueError("PNG chunk checksum mismatch")
        cursor = last + 4

        if count == 1:
            if kind != b"IHDR" or size != 13 or data[8:] != PROFILE:
                raise ValueError("Expected non-interlaced RGBA8")
            width = int.from_bytes(data[:4], "big")
            height = int.from_bytes(data[4:8], "big")
            if not 1 <= width <= 32 or not 1 <= height <= 32:
                raise ValueError("PNG dimensions outside the profile")
        elif kind == b"IDAT":
            if idat_closed:
                raise ValueError("IDAT chunks must be consecutive")
            idat_seen = True
            compressed.extend(data)
        elif kind == b"IEND":
            if size != 0 or cursor != len(body):
                raise ValueError("Invalid PNG end")
            ended = True
            break
        elif kind in METADATA:
            if idat_seen:
                idat_closed = True
        else:
            raise ValueError("PNG chunk outside the supported profile")
    if not ended or not compressed:
        raise ValueError("Missing PNG end or image data")
    expected = height * (1 + width * 4)
    inflater = zlib.decompressobj()
    raw = inflater.decompress(bytes(compressed), expected + 1)
    if len(raw) != expected or not inflater.eof or inflater.unused_data or inflater.unconsumed_tail:
        raise ValueError("Invalid inflated length or zlib stream")
    return width, height, undo_filters(raw, width, height)


def chunk(kind, payload):
    return len(payload).to_bytes(4, "big") + kind + payload + zlib.crc32(kind + payload).to_bytes(4, "big")


def encode_png(width, height, pixels):
    stride = width * 4
    raw = b"".join(b"\x00" + bytes(pixels[i:i + stride]) for i in range(0, len(pixels), stride))
    size = len(raw)
    # A single stored DEFLATE block makes the output independent of compression heuristics.
    stored = b"\x78\x01\x01" + size.to_bytes(2, "little") + (65535 - size).to_bytes(2, "little")
    compressed = stored + raw + zlib.adler32(raw).to_bytes(4, "big")
    header = width.to_bytes(4, "big") + height.to_bytes(4, "big") + PROFILE
    return SIGNATURE + chunk(b"IHDR", header) + chunk(b"IDAT", compressed) + chunk(b"IEND", b"")


def scrub_pixels(body, url, commitment):
    if not isinstance(body, bytes) or len(body) > 65536 or sha(body) != commitment:
        raise ValueError("Source commitment mismatch")
    width, height, pixels = decode_png(body)
    transparent, changed = 0, 0
    for index in range(0, len(pixels), 4):
        if pixels[index + 3] == 0:
            transparent += 1
            if any(pixels[index:index + 3]):
                changed += 1
                pixels[index:index + 3] = b"\x00" * 3
    output = encode_png(width, height, pixels)
    report = {"schema": "png-alpha-scrub/1", "source_url": url, "source_sha256": commitment,
              "width": width, "height": height, "transparent_pixels": transparent,
              "changed_pixels": changed, "png_id": sha(output)}
    return {"report": report, "png_hex": output.hex()}


class PngAlphaScrub(gl.Contract):
    reports: TreeMap[str, str]
    images: TreeMap[str, str]

    def __init__(self):
        pass

    @gl.public.write
    def scrub(self, ref: str, expected_sha256: str) -> str:
        if not isinstance(expected_sha256, str) or not re.fullmatch(r"[a-f0-9]{64}", expected_sha256):
            raise gl.vm.UserError("Expected a commit-pinned PNG and exact SHA-256")
        try:
            url = source_url(ref)
        except ValueError:
            raise gl.vm.UserError("Expected a commit-pinned PNG and exact SHA-256")

        def evaluate():
            try:
                response = gl.nondet.web.get(url)
                if response.status == 200:
                    return canonical(scrub_pixels(response.body, url, expected_sha256))
            except Exception:
                raise gl.vm.UserError("PNG evidence unavailable, corrupt or out of profile")
            raise gl.vm.UserError("PNG source returned an unsuccessful response")

        def validate(leader):
            if not isinstance(leader, gl.vm.Return):
                return False
            try:
                return evaluate() == leader.calldata
            except Exception:
                return False

        agreed = json.loads(gl.vm.run_nondet_unsafe(evaluate, validate))
        report = agreed["report"]
        report_json = canonical(report)
        report_id = sha(report_json.encode("ascii"))
        if report["png_id"] not in self.images:
            self.images[report["png_id"]] = agreed["png_hex"]
        if report_id not in self.reports:
            self.reports[report_id] = report_json
        return report_id

    @gl.public.view
    def get_report(self, report_id: str) -> dict:
        if report_id not in self.reports:
            raise gl.vm.UserError("Unknown scrub report")
        return json.loads(self.reports[report_id])

    @gl.public.view
    def get_png(self, png_id: str) -> str:
        if png_id not in self.images:
            raise gl.vm.UserError("Unknown sanitized PNG")
        return self.images[png_id]
