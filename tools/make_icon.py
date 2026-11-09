"""Generate the burning-N favicon (PNG + ICO) using only the stdlib.

Run from the repo root:

    python tools/make_icon.py

A 32x32 pixel grid: a red-hot "N" with flame tongues rising off its top
edge and a few drifting embers. Outputs dotnay/assets/nayla.png (256x256)
and dotnay/assets/nayla.ico (multi-size).
"""

from __future__ import annotations

import struct
import zlib
from pathlib import Path

GRID = 32
ASSETS = Path(__file__).resolve().parent.parent / "dotnay" / "assets"

# The N sits low on the grid so there is room for flames above it.
TOP, BOTTOM = 9, 30
LEFT_STEM = (9, 13)
RIGHT_STEM = (26, 30)

# Colour of the N itself, left to right (orange -> red).
BODY_STOPS = [
    (9, (255, 150, 0)),
    (18, (255, 70, 16)),
    (30, (214, 24, 10)),
]

# Height of the flame tongue above each column of the N (x = 9..30).
FLAME_HEIGHTS = (3, 2, 4, 2, 3, 2, 4, 3, 2, 3, 4, 2, 3, 2, 4, 3, 2, 3, 2, 4, 3, 2)

# Detached embers / sparks.
SPARKS = [
    (5, 8), (8, 5), (11, 4), (14, 2), (18, 5), (21, 3), (24, 2), (28, 4),
    (31, 7), (3, 16), (4, 22), (2, 27), (6, 29), (7, 19),
]


def lerp(first, second, amount):
    return tuple(
        max(0, min(255, round(a + (b - a) * amount))) for a, b in zip(first, second)
    )


def body_color(x: int):
    """Interpolate the red-hot gradient across the N."""
    for (left_x, left), (right_x, right) in zip(BODY_STOPS, BODY_STOPS[1:]):
        if x <= right_x:
            span = right_x - left_x
            return lerp(left, right, 0 if span == 0 else (x - left_x) / span)
    return BODY_STOPS[-1][1]


def flame_color(amount: float):
    """Yellow at the base of a flame, deep red at the tip."""
    if amount < 0.45:
        return lerp((255, 236, 120), (255, 150, 0), amount / 0.45)
    return lerp((255, 150, 0), (196, 18, 10), (amount - 0.45) / 0.55)


def n_cells() -> dict[tuple[int, int], tuple[int, int, int]]:
    """Map each solid cell of the N to its colour."""
    cells: dict[tuple[int, int], tuple[int, int, int]] = {}
    for y in range(TOP, BOTTOM + 1):
        for x in range(LEFT_STEM[0], LEFT_STEM[1] + 1):
            cells[(x, y)] = body_color(x)
        for x in range(RIGHT_STEM[0], RIGHT_STEM[1] + 1):
            cells[(x, y)] = body_color(x)
        # Thick diagonal from the top-left to the bottom-right.
        center = LEFT_STEM[0] + (y - TOP) * (RIGHT_STEM[1] - LEFT_STEM[0]) / (BOTTOM - TOP)
        for x in range(round(center) - 2, round(center) + 3):
            if 0 <= x < GRID:
                cells[(x, y)] = body_color(x)
    return cells


def build_grid() -> list[list[tuple[int, int, int, int]]]:
    grid = [[(0, 0, 0, 0)] * GRID for _ in range(GRID)]

    cells = n_cells()
    for (x, y), color in cells.items():
        # Give the bottom edge a hotter, more molten tint.
        if y >= BOTTOM - 3:
            color = lerp(color, (255, 196, 0), 0.30)
        grid[y][x] = (*color, 255)

    # Flames grow upward from the topmost cell of every column of the N.
    for index, x in enumerate(range(LEFT_STEM[0], RIGHT_STEM[1] + 1)):
        top = min((y for (cx, y) in cells if cx == x), default=None)
        if top is None:
            continue
        height = FLAME_HEIGHTS[index % len(FLAME_HEIGHTS)]
        for step in range(1, height + 1):
            y = top - step
            if 0 <= y < GRID:
                grid[y][x] = (*flame_color(step / (height + 0.5)), 255)

    # A few embers drifting off the fire.
    for index, (x, y) in enumerate(SPARKS):
        if 0 <= x < GRID and 0 <= y < GRID:
            color = flame_color(0.25 + (index % 4) * 0.18)
            grid[y][x] = (*color, 255)

    return grid


def scale_nearest(grid, size: int):
    """Resample the 32x32 grid with nearest-neighbour (keeps pixels crisp)."""
    result = []
    for y in range(size):
        source_y = y * GRID // size
        row = []
        for x in range(size):
            row.append(grid[source_y][x * GRID // size])
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
    ASSETS.mkdir(parents=True, exist_ok=True)
    grid = build_grid()

    large = scale_nearest(grid, 256)
    (ASSETS / "nayla.png").write_bytes(png_bytes(large))

    entries: list[tuple[int, bytes]] = []
    for size in (16, 24, 32, 48, 64, 128):
        entries.append((size, bmp_bytes(scale_nearest(grid, size))))
    entries.append((256, png_bytes(large)))
    (ASSETS / "nayla.ico").write_bytes(ico_bytes(entries))

    print(f"wrote {ASSETS / 'nayla.png'}")
    print(f"wrote {ASSETS / 'nayla.ico'}")


if __name__ == "__main__":
    main()
