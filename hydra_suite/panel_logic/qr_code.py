# =============================================================================
# HYDRA-UMC SUITE - panel_logic/qr_code.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
#
# A small QR Code encoder (ISO/IEC 18004) for the one thing this program has to show as a code: the otpauth address that
# an authenticator app scans to learn the secret of the second step. Byte mode, error correction level M, versions 1 to 10
# (up to 213 bytes); it picks the smallest version that holds the text and the best of the eight masks. A text that does not
# fit is refused (the screen then shows the key to type by hand, which always works). The same encoder lives in
# HYDRA-UMC-STUDIO (src/lib/qrCode.ts) and both draw the same symbol for the same text.
# =============================================================================
from __future__ import annotations

# Per version (index 0 = version 1), level M: (error correction codewords per block, ((blocks, data codewords), ...)).
_BLOCKS_M = [
    (10, ((1, 16),)),
    (16, ((1, 28),)),
    (26, ((1, 44),)),
    (18, ((2, 32),)),
    (24, ((2, 43),)),
    (16, ((4, 27),)),
    (18, ((4, 31),)),
    (22, ((2, 38), (2, 39))),
    (22, ((3, 36), (2, 37))),
    (26, ((4, 43), (1, 44))),
]
_ALIGNMENT = [(), (6, 18), (6, 22), (6, 26), (6, 30), (6, 34), (6, 22, 38), (6, 24, 42), (6, 26, 46), (6, 28, 50)]

QR_MAX_BYTES = 213


def _data_codewords(version: int) -> int:
    return sum(count * size for count, size in _BLOCKS_M[version - 1][1])


_EXP = [0] * 512
_LOG = [0] * 256
_x = 1
for _i in range(255):
    _EXP[_i] = _x
    _LOG[_x] = _i
    _x <<= 1
    if _x & 0x100:
        _x ^= 0x11D
for _i in range(255, 512):
    _EXP[_i] = _EXP[_i - 255]


def _generator(degree: int) -> list[int]:
    poly = [1]
    for i in range(degree):
        nxt = [0] * (len(poly) + 1)
        for j, coef in enumerate(poly):
            nxt[j] ^= coef
            nxt[j + 1] ^= 0 if coef == 0 else _EXP[_LOG[coef] + i]
        poly = nxt
    return poly


def _remainder(data: list[int], degree: int) -> list[int]:
    gen = _generator(degree)
    out = [0] * degree
    for byte in data:
        factor = byte ^ out[0]
        out = out[1:] + [0]
        if factor:
            for i in range(degree):
                out[i] ^= _EXP[_LOG[gen[i + 1]] + _LOG[factor]]
    return out


def _bits_of(payload: bytes, version: int) -> list[int]:
    bits: list[int] = []

    def push(value: int, length: int) -> None:
        for i in range(length - 1, -1, -1):
            bits.append((value >> i) & 1)

    push(0b0100, 4)
    push(len(payload), 8 if version <= 9 else 16)
    for byte in payload:
        push(byte, 8)
    capacity = _data_codewords(version) * 8
    push(0, min(4, capacity - len(bits)))
    while len(bits) % 8:
        bits.append(0)
    pad = 0xEC
    while len(bits) < capacity:
        push(pad, 8)
        pad = 0x11 if pad == 0xEC else 0xEC
    return bits


def _interleave(data: list[int], version: int) -> list[int]:
    ec_len, groups = _BLOCKS_M[version - 1]
    blocks: list[list[int]] = []
    offset = 0
    for count, size in groups:
        for _ in range(count):
            blocks.append(data[offset:offset + size])
            offset += size
    ec_blocks = [_remainder(block, ec_len) for block in blocks]
    out: list[int] = []
    for i in range(max(len(block) for block in blocks)):
        for block in blocks:
            if i < len(block):
                out.append(block[i])
    for i in range(ec_len):
        for block in ec_blocks:
            out.append(block[i])
    return out


def _bch(value: int, poly: int, poly_bits: int) -> int:
    rem = value << (poly_bits - 1)
    top = poly_bits - 1
    for i in range(31, top - 1, -1):
        if (rem >> i) & 1:
            rem ^= poly << (i - top)
    return rem


def _format_bits(mask: int) -> int:
    data = mask  # level M = 00
    return ((data << 10) | _bch(data, 0x537, 11)) ^ 0x5412


def _version_bits(version: int) -> int:
    return (version << 12) | _bch(version, 0x1F25, 13)


class _Grid:
    def __init__(self, version: int) -> None:
        self.size = 17 + 4 * version
        self.cells = [[0] * self.size for _ in range(self.size)]
        self.reserved = [[False] * self.size for _ in range(self.size)]

    def put(self, row: int, col: int, dark: bool) -> None:
        self.cells[row][col] = 1 if dark else 0
        self.reserved[row][col] = True


def _finder(grid: _Grid, row: int, col: int) -> None:
    for r in range(-1, 8):
        for c in range(-1, 8):
            rr, cc = row + r, col + c
            if rr < 0 or cc < 0 or rr >= grid.size or cc >= grid.size:
                continue
            ring = max(abs(r - 3), abs(c - 3))
            grid.put(rr, cc, ring not in (2, 4))


def _reserve_function_areas(grid: _Grid, version: int) -> None:
    size = grid.size
    _finder(grid, 0, 0)
    _finder(grid, 0, size - 7)
    _finder(grid, size - 7, 0)
    for r in _ALIGNMENT[version - 1]:
        for c in _ALIGNMENT[version - 1]:
            if (r == 6 and c == 6) or (r == 6 and c == size - 7) or (r == size - 7 and c == 6):
                continue
            for dr in range(-2, 3):
                for dc in range(-2, 3):
                    grid.put(r + dr, c + dc, max(abs(dr), abs(dc)) != 1)
    for i in range(8, size - 8):
        grid.put(6, i, i % 2 == 0)
        grid.put(i, 6, i % 2 == 0)
    for i in range(9):
        grid.reserved[8][i] = True
        grid.reserved[i][8] = True
    for i in range(8):
        grid.reserved[8][size - 1 - i] = True
        grid.reserved[size - 1 - i][8] = True
    grid.put(size - 8, 8, True)  # the always-dark module
    if version >= 7:
        for i in range(6):
            for j in range(3):
                grid.reserved[i][size - 11 + j] = True
                grid.reserved[size - 11 + j][i] = True


def _place_data(grid: _Grid, bits: list[int]) -> None:
    index = 0
    upward = True
    col = grid.size - 1
    while col > 0:
        if col == 6:
            col = 5
        for step in range(grid.size):
            row = grid.size - 1 - step if upward else step
            for k in range(2):
                c = col - k
                if grid.reserved[row][c]:
                    continue
                grid.cells[row][c] = bits[index] if index < len(bits) else 0
                index += 1
        upward = not upward
        col -= 2


_MASKS = [
    lambda r, c: (r + c) % 2 == 0,
    lambda r, c: r % 2 == 0,
    lambda r, c: c % 3 == 0,
    lambda r, c: (r + c) % 3 == 0,
    lambda r, c: (r // 2 + c // 3) % 2 == 0,
    lambda r, c: (r * c) % 2 + (r * c) % 3 == 0,
    lambda r, c: ((r * c) % 2 + (r * c) % 3) % 2 == 0,
    lambda r, c: ((r + c) % 2 + (r * c) % 3) % 2 == 0,
]


def _with_mask(grid: _Grid, mask: int, version: int) -> list[list[int]]:
    size = grid.size
    cells = [row[:] for row in grid.cells]
    test = _MASKS[mask]
    for r in range(size):
        for c in range(size):
            if not grid.reserved[r][c] and test(r, c):
                cells[r][c] ^= 1
    fmt = _format_bits(mask)
    for i in range(15):
        bit = (fmt >> i) & 1
        if i < 6:
            cells[i][8] = bit
        elif i < 8:
            cells[i + 1][8] = bit
        elif i == 8:
            cells[8][7] = bit
        else:
            cells[8][14 - i] = bit
        if i < 8:
            cells[8][size - 1 - i] = bit
        else:
            cells[size - 15 + i][8] = bit
    if version >= 7:
        info = _version_bits(version)
        for i in range(18):
            bit = (info >> i) & 1
            a = i // 3
            b = size - 11 + (i % 3)
            cells[a][b] = bit
            cells[b][a] = bit
    return cells


def _penalty(cells: list[list[int]]) -> int:
    size = len(cells)
    score = 0
    w = [1, 0, 1, 1, 1, 0, 1, 0, 0, 0, 0]
    v = [0, 0, 0, 0, 1, 0, 1, 1, 1, 0, 1]
    for transpose in (False, True):
        lines = [list(col) for col in zip(*cells)] if transpose else cells
        for line in lines:
            run = 1
            for b in range(1, size):
                if line[b] == line[b - 1]:
                    run += 1
                    if run == 5:
                        score += 3
                    elif run > 5:
                        score += 1
                else:
                    run = 1
            for b in range(size - 10):
                window = line[b:b + 11]
                if window == w:
                    score += 40
                if window == v:
                    score += 40
    for r in range(size - 1):
        for c in range(size - 1):
            value = cells[r][c]
            if value == cells[r][c + 1] == cells[r + 1][c] == cells[r + 1][c + 1]:
                score += 3
    dark = sum(sum(row) for row in cells)
    score += int(abs(dark * 100 / (size * size) - 50) // 5) * 10
    return score


def encode_qr(text: str) -> list[list[int]] | None:
    """The module matrix (1 = dark) of the QR Code for `text`, or None when it needs more than 213 bytes."""
    payload = text.encode("utf-8")
    version = 0
    for v in range(1, 11):
        header = 12 if v <= 9 else 20
        if header + len(payload) * 8 <= _data_codewords(v) * 8:
            version = v
            break
    if not version:
        return None
    bits_data = _bits_of(payload, version)
    codewords = [int("".join(map(str, bits_data[i:i + 8])), 2) for i in range(0, len(bits_data), 8)]
    stream = _interleave(codewords, version)
    bits = [(byte >> i) & 1 for byte in stream for i in range(7, -1, -1)]
    grid = _Grid(version)
    _reserve_function_areas(grid, version)
    _place_data(grid, bits)
    best = None
    best_score = None
    for mask in range(8):
        candidate = _with_mask(grid, mask, version)
        score = _penalty(candidate)
        if best_score is None or score < best_score:
            best, best_score = candidate, score
    return best


def qr_svg_path(matrix: list[list[int]], quiet: int = 4) -> tuple[str, int]:
    """The matrix as the path of an SVG (one square per dark module, with the quiet zone) and the side of the drawing."""
    parts = []
    for r, row in enumerate(matrix):
        for c, value in enumerate(row):
            if value:
                parts.append(f"M{c + quiet} {r + quiet}h1v1h-1z")
    return "".join(parts), len(matrix) + quiet * 2
