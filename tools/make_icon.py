"""Build the favicon assets from the source emblem.

Run from the repo root:

    python tools/make_icon.py

Reads dotnay/assets/nayla_art.png (the canonical artwork) and writes
dotnay/assets/nayla.png (256x256) plus dotnay/assets/nayla.ico (multi-size).
Uses only the standard library.
"""

from __future__ import annotations

import struct
import zlib
from pathlib import Path

ASSETS = Path(__file__).resolve().parent.parent / "dotnay" / "assets"
SOURCE = ASSETS / "nayla_art.png"
ICON_SIZE = 256
FILL = 1.0  # fraction of the icon the artwork should occupy
ICO_SIZES = (16, 24, 32, 48, 64, 128, 256)


def read_png(path: Path):
    """Decode an 8-bit, non-interlaced RGBA PNG into rows of (r, g, b, a)."""
    data = path.read_bytes()
    if data[:8] != b"\x89PNG\r\n\x1a\n":
        raise ValueError(f"{path} is not a PNG")

    pos = 8
    width = height = 0
    idat = bytearray()
    while pos < len(data):
        length = struct.unpack(">I", data[pos:pos + 4])[0]
        tag = data[pos + 4:pos + 8]
        body = data[pos + 8:pos + 8 + length]
        pos += 12 + length
        if tag == b"IHDR":
            width, height, depth, color, _comp, _filt, interlace = struct.unpack(
                ">IIBBBBB", body
            )
            if depth != 8 or color != 6 or interlace != 0:
                raise ValueError("expected an 8-bit, non-interlaced RGBA PNG")
        elif tag == b"IDAT":
            idat += body
        elif tag == b"IEND":
            break

    raw = zlib.decompress(bytes(idat))
    stride = width * 4
    rows = []
    previous = bytearray(stride)
    offset = 0
    for _ in range(height):
        kind = raw[offset]
        offset += 1
        line = bytearray(raw[offset:offset + stride])
        offset += stride
        if kind == 1:  # Sub
            for i in range(4, stride):
                line[i] = (line[i] + line[i - 4]) & 0xFF
        elif kind == 2:  # Up
            for i in range(stride):
                line[i] = (line[i] + previous[i]) & 0xFF
        elif kind == 3:  # Average
            for i in range(stride):
                left = line[i - 4] if i >= 4 else 0
                line[i] = (line[i] + ((left + previous[i]) >> 1)) & 0xFF
        elif kind == 4:  # Paeth
            for i in range(stride):
                left = line[i - 4] if i >= 4 else 0
                up = previous[i]
                corner = previous[i - 4] if i >= 4 else 0
                estimate = left + up - corner
                da = abs(estimate - left)
                db = abs(estimate - up)
                dc = abs(estimate - corner)
                if da <= db and da <= dc:
                    nearest = left
                elif db <= dc:
                    nearest = up
                else:
                    nearest = corner
                line[i] = (line[i] + nearest) & 0xFF
        elif kind != 0:
            raise ValueError(f"unsupported PNG filter {kind}")
        rows.append([tuple(line[i:i + 4]) for i in range(0, stride, 4)])
        previous = line

    return width, height, rows


def content_bbox(rows, cut: int = 16, fraction: float = 0.045):
    """Bounding box of the dense artwork, ignoring sparse drifting sparks."""
    height, width = len(rows), len(rows[0])
    threshold = max(2, round(fraction * max(width, height)))
    column = [0] * width
    row = [0] * height
    for y in range(height):
        source_row = rows[y]
        count = 0
        for x in range(width):
            if source_row[x][3] > cut:
                column[x] += 1
                count += 1
        row[y] = count
    xs = [x for x in range(width) if column[x] >= threshold]
    ys = [y for y in range(height) if row[y] >= threshold]
    if not xs or not ys:
        return (0, 0, width - 1, height - 1)
    return (min(xs), min(ys), max(xs), max(ys))


def centered_square(rows, box, fill: float = FILL):
    """Crop a square around the artwork so it fills `fill` of the frame."""
    height, width = len(rows), len(rows[0])
    min_x, min_y, max_x, max_y = box
    center_x = (min_x + max_x) / 2
    center_y = (min_y + max_y) / 2
    content = max(max_x - min_x + 1, max_y - min_y + 1)
    side = int(content / fill + 0.999)
    left = round(center_x - side / 2)
    top = round(center_y - side / 2)
    result = []
    for oy in range(side):
        source_y = top + oy
        row = []
        for ox in range(side):
            source_x = left + ox
            if 0 <= source_x < width and 0 <= source_y < height:
                row.append(rows[source_y][source_x])
            else:
                row.append((0, 0, 0, 0))
        result.append(row)
    return result


def resample(rows, size: int):
    """Area-average rows down to a size x size image, preserving alpha."""
    source_height = len(rows)
    source_width = len(rows[0])
    result = []
    for oy in range(size):
        y0, y1 = oy * source_height // size, (oy + 1) * source_height // size
        row = []
        for ox in range(size):
            x0, x1 = ox * source_width // size, (ox + 1) * source_width // size
            red = green = blue = alpha = count = 0
            for y in range(y0, y1):
                source_row = rows[y]
                for x in range(x0, x1):
                    pr, pg, pb, pa = source_row[x]
                    red += pr * pa
                    green += pg * pa
                    blue += pb * pa
                    alpha += pa
                    count += 1
            if alpha == 0:
                row.append((0, 0, 0, 0))
            else:
                row.append(
                    (red // alpha, green // alpha, blue // alpha, alpha // count)
                )
        result.append(row)
    return result


def png_bytes(pixels) -> bytes:
    """Encode RGBA pixels as a PNG."""

    def chunk(tag: bytes, data: bytes) -> bytes:
        crc = zlib.crc32(tag + data) & 0xFFFFFFFF
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", crc)

    height, width = len(pixels), len(pixels[0])
    raw = bytearray()
    for row in pixels:
        raw.append(0)  # no filter
        for red, green, blue, alpha in row:
            raw += bytes((red, green, blue, alpha))

    header = struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0)
    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", header)
        + chunk(b"IDAT", zlib.compress(bytes(raw), 9))
        + chunk(b"IEND", b"")
    )


def bmp_bytes(pixels) -> bytes:
    """Encode RGBA pixels as a 32-bit BMP/DIB entry for an ICO."""
    height, width = len(pixels), len(pixels[0])
    info = struct.pack(
        "<IiiHHIIiiII", 40, width, height * 2, 1, 32, 0, width * height * 4, 0, 0, 0, 0
    )
    body = bytearray()
    for row in reversed(pixels):  # BMP rows are bottom-up
        for red, green, blue, alpha in row:
            body += bytes((blue, green, red, alpha))
    mask_row = ((width + 31) // 32) * 4
    body += b"\x00" * (mask_row * height)  # opaque AND mask, alpha does the work
    return info + bytes(body)


def ico_bytes(entries: list[tuple[int, bytes]]) -> bytes:
    header = struct.pack("<HHH", 0, 1, len(entries))
    offset = 6 + 16 * len(entries)
    directory = bytearray()
    for size, blob in entries:
        dimension = 0 if size >= 256 else size
        directory += struct.pack(
            "<BBBBHHII", dimension, dimension, 0, 0, 1, 32, len(blob), offset
        )
        offset += len(blob)
    return header + bytes(directory) + b"".join(blob for _, blob in entries)


def main() -> None:
    if not SOURCE.exists():
        raise SystemExit(f"missing source artwork: {SOURCE}")

    _width, _height, source = read_png(SOURCE)
    framed = centered_square(source, content_bbox(source))
    base = resample(framed, ICON_SIZE)
    (ASSETS / "nayla.png").write_bytes(png_bytes(base))

    entries: list[tuple[int, bytes]] = []
    for size in ICO_SIZES:
        pixels = base if size == ICON_SIZE else resample(base, size)
        if size <= 64:
            entries.append((size, bmp_bytes(pixels)))
        else:
            entries.append((size, png_bytes(pixels)))
    (ASSETS / "nayla.ico").write_bytes(ico_bytes(entries))

    print(f"wrote {ASSETS / 'nayla.png'}")
    print(f"wrote {ASSETS / 'nayla.ico'}")


if __name__ == "__main__":
    main()
