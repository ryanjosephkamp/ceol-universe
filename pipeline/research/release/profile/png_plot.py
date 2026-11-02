"""Bar charts written as PNG files with the standard library and numpy
(PACKAGE_UR1.md reading R11).

The earlier profile drew its plots with matplotlib, which no committed file
of this repository imports; the committed profile draws them here instead,
with a 5-by-9 bitmap font scaled by 2, so the release adds no dependency.
A chart is an RGB pixel array; `pixels_sha256` hashes the pixels, which is
what the profile records and AT-UR1-9 compares, because a PNG's compressed
bytes depend on the zlib build while its pixels do not.

The font covers the characters the profile's labels use: the digits, the
Latin letters in both cases, the grammar's accented letters and ligatures,
and a few marks. A character outside it raises, so a label is never drawn
with a missing glyph.
"""

from __future__ import annotations

import hashlib
import math
import struct
import zlib

import numpy as np

# ---------------------------------------------------------------------------
# The font: 5 columns by 9 rows (rows 0 to 6 above and on the baseline, rows
# 7 and 8 the descender); '#' is ink. Lowercase letters keep rows 0 and 1
# free, where the accents are drawn.
# ---------------------------------------------------------------------------

_G = {
    " ": (".....",) * 7,
    "0": (".###.", "#...#", "#..##", "#.#.#", "##..#", "#...#", ".###."),
    "1": ("..#..", ".##..", "..#..", "..#..", "..#..", "..#..", ".###."),
    "2": (".###.", "#...#", "....#", "...#.", "..#..", ".#...", "#####"),
    "3": ("#####", "...#.", "..#..", "...#.", "....#", "#...#", ".###."),
    "4": ("...#.", "..##.", ".#.#.", "#..#.", "#####", "...#.", "...#."),
    "5": ("#####", "#....", "####.", "....#", "....#", "#...#", ".###."),
    "6": ("..##.", ".#...", "#....", "####.", "#...#", "#...#", ".###."),
    "7": ("#####", "....#", "...#.", "..#..", ".#...", ".#...", ".#..."),
    "8": (".###.", "#...#", "#...#", ".###.", "#...#", "#...#", ".###."),
    "9": (".###.", "#...#", "#...#", ".####", "....#", "...#.", ".##.."),
    "a": (".....", ".....", ".###.", "....#", ".####", "#...#", ".####"),
    "b": ("#....", "#....", "####.", "#...#", "#...#", "#...#", "####."),
    "c": (".....", ".....", ".###.", "#....", "#....", "#...#", ".###."),
    "d": ("....#", "....#", ".####", "#...#", "#...#", "#...#", ".####"),
    "e": (".....", ".....", ".###.", "#...#", "#####", "#....", ".###."),
    "f": ("..##.", ".#..#", ".#...", "###..", ".#...", ".#...", ".#..."),
    "g": (".....", ".....", ".####", "#...#", "#...#", ".####", "....#",
          "#...#", ".###."),
    "h": ("#....", "#....", "#.##.", "##..#", "#...#", "#...#", "#...#"),
    "i": ("..#..", ".....", ".##..", "..#..", "..#..", "..#..", ".###."),
    "ı": (".....", ".....", ".##..", "..#..", "..#..", "..#..", ".###."),
    "j": ("...#.", ".....", "..##.", "...#.", "...#.", "...#.", "...#.",
          "#..#.", ".##.."),
    "k": ("#....", "#....", "#..#.", "#.#..", "##...", "#.#..", "#..#."),
    "l": (".##..", "..#..", "..#..", "..#..", "..#..", "..#..", ".###."),
    "m": (".....", ".....", "##.#.", "#.#.#", "#.#.#", "#...#", "#...#"),
    "n": (".....", ".....", "#.##.", "##..#", "#...#", "#...#", "#...#"),
    "o": (".....", ".....", ".###.", "#...#", "#...#", "#...#", ".###."),
    "p": (".....", ".....", "####.", "#...#", "#...#", "#...#", "####.",
          "#....", "#...."),
    "q": (".....", ".....", ".####", "#...#", "#...#", "#...#", ".####",
          "....#", "....#"),
    "r": (".....", ".....", "#.##.", "##..#", "#....", "#....", "#...."),
    "s": (".....", ".....", ".####", "#....", ".###.", "....#", "####."),
    "t": (".#...", ".#...", "###..", ".#...", ".#...", ".#..#", "..##."),
    "u": (".....", ".....", "#...#", "#...#", "#...#", "#..##", ".##.#"),
    "v": (".....", ".....", "#...#", "#...#", "#...#", ".#.#.", "..#.."),
    "w": (".....", ".....", "#...#", "#...#", "#.#.#", "#.#.#", ".#.#."),
    "x": (".....", ".....", "#...#", ".#.#.", "..#..", ".#.#.", "#...#"),
    "y": (".....", ".....", "#...#", "#...#", "#...#", ".####", "....#",
          "#...#", ".###."),
    "z": (".....", ".....", "#####", "...#.", "..#..", ".#...", "#####"),
    "æ": (".....", ".....", "##.#.", "..#.#", ".####", "#.#..", ".#.##"),
    "œ": (".....", ".....", ".#.#.", "#.#.#", "#.###", "#.#..", ".#.##"),
    "A": (".###.", "#...#", "#...#", "#####", "#...#", "#...#", "#...#"),
    "B": ("####.", "#...#", "#...#", "####.", "#...#", "#...#", "####."),
    "C": (".###.", "#...#", "#....", "#....", "#....", "#...#", ".###."),
    "D": ("###..", "#..#.", "#...#", "#...#", "#...#", "#..#.", "###.."),
    "E": ("#####", "#....", "#....", "####.", "#....", "#....", "#####"),
    "F": ("#####", "#....", "#....", "####.", "#....", "#....", "#...."),
    "G": (".###.", "#...#", "#....", "#.###", "#...#", "#...#", ".####"),
    "H": ("#...#", "#...#", "#...#", "#####", "#...#", "#...#", "#...#"),
    "I": (".###.", "..#..", "..#..", "..#..", "..#..", "..#..", ".###."),
    "J": ("..###", "...#.", "...#.", "...#.", "...#.", "#..#.", ".##.."),
    "K": ("#...#", "#..#.", "#.#..", "##...", "#.#..", "#..#.", "#...#"),
    "L": ("#....", "#....", "#....", "#....", "#....", "#....", "#####"),
    "M": ("#...#", "##.##", "#.#.#", "#.#.#", "#...#", "#...#", "#...#"),
    "N": ("#...#", "#...#", "##..#", "#.#.#", "#..##", "#...#", "#...#"),
    "O": (".###.", "#...#", "#...#", "#...#", "#...#", "#...#", ".###."),
    "P": ("####.", "#...#", "#...#", "####.", "#....", "#....", "#...."),
    "Q": (".###.", "#...#", "#...#", "#...#", "#.#.#", "#..#.", ".##.#"),
    "R": ("####.", "#...#", "#...#", "####.", "#.#..", "#..#.", "#...#"),
    "S": (".####", "#....", "#....", ".###.", "....#", "....#", "####."),
    "T": ("#####", "..#..", "..#..", "..#..", "..#..", "..#..", "..#.."),
    "U": ("#...#", "#...#", "#...#", "#...#", "#...#", "#...#", ".###."),
    "V": ("#...#", "#...#", "#...#", "#...#", "#...#", ".#.#.", "..#.."),
    "W": ("#...#", "#...#", "#...#", "#.#.#", "#.#.#", "#.#.#", ".#.#."),
    "X": ("#...#", "#...#", ".#.#.", "..#..", ".#.#.", "#...#", "#...#"),
    "Y": ("#...#", "#...#", ".#.#.", "..#..", "..#..", "..#..", "..#.."),
    "Z": ("#####", "....#", "...#.", "..#..", ".#...", "#....", "#####"),
    "-": (".....", ".....", ".....", "#####", ".....", ".....", "....."),
    "_": (".....",) * 7 + ("#####",),
    ".": (".....", ".....", ".....", ".....", ".....", ".##..", ".##.."),
    ",": (".....", ".....", ".....", ".....", ".....", ".##..", ".##..",
          ".#..."),
    ":": (".....", ".##..", ".##..", ".....", ".....", ".##..", ".##.."),
    ";": (".....", ".##..", ".##..", ".....", ".....", ".##..", ".##..",
          ".#..."),
    "'": ("..#..", "..#..", ".#...", ".....", ".....", ".....", "....."),
    "(": ("...#.", "..#..", ".#...", ".#...", ".#...", "..#..", "...#."),
    ")": (".#...", "..#..", "...#.", "...#.", "...#.", "..#..", ".#..."),
    "/": (".....", "....#", "...#.", "..#..", ".#...", "#....", "....."),
    "+": (".....", "..#..", "..#..", "#####", "..#..", "..#..", "....."),
    "=": (".....", ".....", "#####", ".....", "#####", ".....", "....."),
    "<": ("...#.", "..#..", ".#...", "#....", ".#...", "..#..", "...#."),
    ">": (".#...", "..#..", "...#.", "....#", "...#.", "..#..", ".#..."),
    "%": ("##...", "##..#", "...#.", "..#..", ".#...", "#..##", "...##"),
    "@": (".###.", "#...#", "#.###", "#.#.#", "#.###", "#....", ".###."),
}

_ACCENT_ROWS = {
    "acute": ("...#.", "..#.."),
    "grave": (".#...", "..#.."),
    "circumflex": ("..#..", ".#.#."),
    "diaeresis": (".....", ".#.#."),
    "tilde": (".##.#", "#.##."),
}

#: The grammar's accented letters (C-001), each a base and an accent.
_ACCENTED = {
    "á": ("a", "acute"), "à": ("a", "grave"), "â": ("a", "circumflex"),
    "ä": ("a", "diaeresis"), "é": ("e", "acute"), "è": ("e", "grave"),
    "ê": ("e", "circumflex"), "ë": ("e", "diaeresis"), "í": ("ı", "acute"),
    "î": ("ı", "circumflex"), "ï": ("ı", "diaeresis"), "ñ": ("n", "tilde"),
    "ó": ("o", "acute"), "ô": ("o", "circumflex"), "ö": ("o", "diaeresis"),
    "ú": ("u", "acute"), "û": ("u", "circumflex"), "ü": ("u", "diaeresis"),
}

GLYPH_W, GLYPH_H, ADVANCE = 5, 9, 6


def _bitmap(rows) -> np.ndarray:
    rows = tuple(rows) + (".....",) * (GLYPH_H - len(rows))
    return np.array([[ch == "#" for ch in r] for r in rows], dtype=bool)


def _build_font() -> dict[str, np.ndarray]:
    font = {ch: _bitmap(rows) for ch, rows in _G.items()}
    for ch, (base, accent) in _ACCENTED.items():
        glyph = font[base].copy()
        glyph[0:2] = _bitmap(_ACCENT_ROWS[accent])[0:2]
        font[ch] = glyph
    cedilla = font["c"].copy()
    cedilla[7:9] = _bitmap((".....",) * 7 + ("..#..", ".##.."))[7:9]
    font["ç"] = cedilla
    return font


FONT = _build_font()


def text_mask(text: str, scale: int = 2) -> np.ndarray:
    """The ink of `text` as a boolean array, `scale` pixels per font dot."""
    missing = sorted({ch for ch in text if ch not in FONT})
    if missing:
        raise ValueError(f"no glyph for {missing!r}")
    width = max(1, len(text) * ADVANCE - 1)
    mask = np.zeros((GLYPH_H, width), dtype=bool)
    for i, ch in enumerate(text):
        mask[:, i * ADVANCE:i * ADVANCE + GLYPH_W] |= FONT[ch]
    return np.kron(mask, np.ones((scale, scale), dtype=bool))


# ---------------------------------------------------------------------------
# The canvas and the PNG encoding
# ---------------------------------------------------------------------------

def _rgb(hex_color: str) -> tuple[int, int, int]:
    h = hex_color.lstrip("#")
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


INK, MUTED, RULE = _rgb("#20272E"), _rgb("#5B6670"), _rgb("#E2E5E3")
ACCENT, SECOND = _rgb("#0B6E68"), _rgb("#9AA4AC")


class Canvas:
    def __init__(self, width: int, height: int):
        self.pixels = np.full((height, width, 3), 255, dtype=np.uint8)

    @property
    def height(self) -> int:
        return self.pixels.shape[0]

    @property
    def width(self) -> int:
        return self.pixels.shape[1]

    def rect(self, x0: int, y0: int, x1: int, y1: int, color) -> None:
        x0, x1 = sorted((max(0, x0), min(self.width, x1)))
        y0, y1 = sorted((max(0, y0), min(self.height, y1)))
        if x1 > x0 and y1 > y0:
            self.pixels[y0:y1, x0:x1] = color

    def blit(self, mask: np.ndarray, x: int, y: int, color) -> None:
        h, w = mask.shape
        region = self.pixels[y:y + h, x:x + w]
        region[mask[:region.shape[0], :region.shape[1]]] = color

    def text(self, s: str, x: int, y: int, color=INK, *, rotate=False,
             anchor="left") -> None:
        mask = text_mask(s)
        if rotate:
            mask = np.rot90(mask)
        h, w = mask.shape
        if anchor == "right":
            x -= w
        elif anchor == "center":
            x -= w // 2
        self.blit(mask, x, y, color)

    def png(self) -> bytes:
        raw = b"".join(b"\x00" + row.tobytes() for row in self.pixels)

        def chunk(kind: bytes, data: bytes) -> bytes:
            return (struct.pack(">I", len(data)) + kind + data
                    + struct.pack(">I", zlib.crc32(kind + data)))

        header = struct.pack(">IIBBBBB", self.width, self.height, 8, 2, 0,
                             0, 0)
        return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", header)
                + chunk(b"IDAT", zlib.compress(raw, 9))
                + chunk(b"IEND", b""))

    def pixels_sha256(self) -> str:
        return hashlib.sha256(self.pixels.tobytes()).hexdigest()


def decode_pixels(png: bytes) -> np.ndarray:
    """The RGB pixels of a PNG this module wrote (filter type 0 only)."""
    if png[:8] != b"\x89PNG\r\n\x1a\n":
        raise ValueError("not a PNG")
    pos, idat, width, height = 8, b"", 0, 0
    while pos < len(png):
        (length,) = struct.unpack(">I", png[pos:pos + 4])
        kind = png[pos + 4:pos + 8]
        data = png[pos + 8:pos + 8 + length]
        if kind == b"IHDR":
            width, height = struct.unpack(">II", data[:8])
        elif kind == b"IDAT":
            idat += data
        pos += 12 + length
    raw = np.frombuffer(zlib.decompress(idat), dtype=np.uint8)
    rows = raw.reshape(height, 1 + width * 3)
    if (rows[:, 0] != 0).any():
        raise ValueError("a row uses a PNG filter this module never writes")
    return rows[:, 1:].reshape(height, width, 3).copy()


# ---------------------------------------------------------------------------
# The chart
# ---------------------------------------------------------------------------

def _compact(value: float) -> str:
    for unit, size in (("M", 10**6), ("k", 10**3)):
        if value >= size:
            v = value / size
            return f"{v:g}{unit}"
    return f"{value:g}"


def _ticks_log(top: float) -> list[float]:
    n = max(1, math.ceil(math.log10(max(top, 1))))
    return [10.0 ** k for k in range(0, n + 1)]


def _ticks_linear(top: float) -> list[float]:
    if top <= 0:
        return [0.0]
    step = 10 ** math.floor(math.log10(top))
    for m in (1, 2, 5, 10):
        if top / (step * m) <= 6:
            step *= m
            break
    return [step * k for k in range(0, int(top // step) + 2)]


def bar_chart(labels: list[str], series: list[tuple[str, list[float], tuple]],
              title: str, xlabel: str, ylabel: str = "rows", *,
              log_y: bool = True, rotate_labels: bool | None = None,
              label_every: int = 1) -> Canvas:
    """Bars per label; with several series the later ones are drawn over
    the earlier ones (an overlay, as the earlier profile drew length by EOL)."""
    n = len(labels)
    if rotate_labels is None:
        rotate_labels = max((len(s) for s in labels), default=1) > 3
    label_px = (max((len(s) for s in labels), default=1) * ADVANCE * 2
                if rotate_labels else GLYPH_H * 2)
    left, right = 96, 24
    legend = len(series) > 1
    top_pad = 96 if legend else 72
    bottom = label_px + 64
    slot = max(8, min(48, (960 - left - right) // max(n, 1)))
    legend_px = sum(20 + len(name) * ADVANCE * 2 + 24
                    for name, _v, _c in series) if legend else 0
    width = max(left + right + slot * n, 32 + len(title) * ADVANCE * 2,
                left + legend_px + 16, 480)
    plot_h = 300
    height = top_pad + plot_h + bottom
    cv = Canvas(width, height)
    cv.text(title, 16, 16, INK)
    scale = "log scale" if log_y else "linear scale"
    cv.text(f"{ylabel}, {scale}", left, 44, MUTED)
    if legend:
        x = left
        for name, _v, color in series:
            cv.rect(x, 70, x + 14, 84, color)
            cv.text(name, x + 20, 68, INK)
            x += 20 + len(name) * ADVANCE * 2 + 24
    top_value = max((max(v) if v else 0) for _n, v, _c in series)
    base_y = top_pad + plot_h

    if log_y:
        ticks = _ticks_log(top_value)
        hi = math.log10(ticks[-1])

        def ypix(v: float) -> int:
            if v < 1 or hi <= 0:
                return base_y
            return base_y - int(round(math.log10(v) / hi * plot_h))
    else:
        ticks = _ticks_linear(top_value)
        span = ticks[-1] if ticks[-1] > 0 else 1.0

        def ypix(v: float) -> int:
            return base_y - int(round(v / span * plot_h))

    for t in ticks:
        y = ypix(t)
        cv.rect(left, y, left + slot * n, y + 1, RULE)
        cv.text(_compact(t), left - 8, y - GLYPH_H, MUTED, anchor="right")
    for _name, values, color in series:
        for i, v in enumerate(values):
            if v <= 0 or (log_y and v < 1):
                continue
            x0 = left + i * slot + 1
            cv.rect(x0, ypix(v), x0 + slot - 2, base_y, color)
    cv.rect(left, base_y, left + slot * n, base_y + 2, INK)
    for i, lab in enumerate(labels):
        if i % label_every:
            continue
        cx = left + i * slot + slot // 2
        if rotate_labels:
            mask = np.rot90(text_mask(lab))
            cv.blit(mask, cx - mask.shape[1] // 2, base_y + 8, INK)
        else:
            cv.text(lab, cx, base_y + 8, INK, anchor="center")
    cv.text(xlabel, left, height - 28, MUTED)
    return cv
