# /// script
# requires-python = ">=3.11"
# dependencies = ["pillow"]
# ///
"""Evidence images: zoomed crops, before/after pairs, and marks.

  uv run evidence_img.py zoom IN.png -o OUT.png --box X,Y,W,H [--scale 2]
  uv run evidence_img.py pair BEFORE.png AFTER.png -o OUT.png
        --labels "before · v1.2.0" "after · this PR" [--side-by-side]
  uv run evidence_img.py mark IN.png -o OUT.png [--scale 2] [--cell 9x19]
        [--crop COL,ROW,NCOLS,NROWS] --box X,Y,W,H,COLOR,LABEL [--box ...]
        [--title "legend title"]

Boxes are pixels in the input image, or with --cell WxH terminal cells
(COL,ROW,NCOLS,NROWS, 0-based, read off `shux pane capture`; shux's raster cell
is 9x19). Prefer cells: a guessed pixel box lands on the wrong row.
--crop (cells, needs --cell) zooms to a region before marking; boxes keep the
frame's own cell coordinates. COLOR is a name (bad, good, same) or
#RRGGBB; pick the colours the screen already uses. Badges go only on blank
space; labels go in a legend bar above the image.
"""

import argparse
import os
import pathlib
import shutil
import subprocess
import sys

from PIL import Image, ImageDraw, ImageFont, ImageStat

NAMED = {"bad": "#E2564B", "good": "#4FD37A", "same": "#E0A33E"}
BAR_BG, BAR_FG = (24, 24, 30), (225, 225, 232)
# Font files by name, best first. Found via $EVIDENCE_FONT, then the OS's own
# font folders, then fontconfig; no path is assumed to exist.
FONT_NAMES = [
    "JetBrainsMonoNerdFont-Regular.ttf",
    "JetBrainsMono-Regular.ttf",
    "Menlo.ttc",
    "DejaVuSansMono.ttf",
]
FONT_DIRS = {"darwin": ["~/Library/Fonts", "/Library/Fonts", "/System/Library/Fonts"]}


def font_path() -> str:
    if os.environ.get("EVIDENCE_FONT"):
        return os.environ["EVIDENCE_FONT"]
    for d in FONT_DIRS.get(sys.platform, []):
        for name in FONT_NAMES:
            hits = sorted(pathlib.Path(d).expanduser().rglob(name))
            if hits:
                return str(hits[0])
    if shutil.which("fc-match"):  # Linux, and macOS with fontconfig installed
        # fc-match always answers with its closest font, so check the family.
        for query, family in (
            ("JetBrains Mono", "JetBrains"),
            ("DejaVu Sans Mono", "DejaVu"),
            ("monospace", ""),
        ):
            out = subprocess.run(
                ["fc-match", "-f", "%{family}|%{file}", query], capture_output=True, text=True
            ).stdout.strip()
            fam, _, found = out.partition("|")
            if found and family in fam and pathlib.Path(found).exists():
                return found
    sys.exit(
        "evidence_img: no monospace font found; set EVIDENCE_FONT=<a .ttf> or install "
        "one (macOS: brew install --cask font-jetbrains-mono; "
        "Linux: apt-get install fontconfig fonts-dejavu-core)"
    )


def font(size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(font_path(), size)


def cells(spec: str) -> tuple[int, int]:
    """--cell WxH, e.g. 9x19 (shux's raster cell)."""
    w, h = (int(n) for n in spec.lower().split("x"))
    return w, h


LABELS_HELP = "name both builds, e.g. 'before · v1.2.0' 'after · this PR'"


def above(top: Image.Image, body: Image.Image) -> Image.Image:
    """TOP (a label or legend bar) stacked over BODY."""
    out = Image.new("RGB", (max(top.width, body.width), top.height + body.height), BAR_BG)
    out.paste(top, (0, 0))
    out.paste(body, (0, top.height))
    return out


def colour(spec: str) -> tuple[int, int, int]:
    h = NAMED.get(spec, spec).lstrip("#")
    if len(h) != 6:
        sys.exit(f"evidence_img: bad colour {spec!r}")
    return tuple(int(h[i : i + 2], 16) for i in (0, 2, 4))


def bar(width: int, items: list[tuple[str, tuple[int, int, int] | None]], size: int) -> Image.Image:
    """A legend bar: (text, colour) pairs; a colour draws a dot before the text."""
    f = font(size)
    h = int(size * 2.2)
    img = Image.new("RGB", (width, h), BAR_BG)
    d = ImageDraw.Draw(img)
    x = size
    for text, c in items:
        if c is not None:
            r = size // 2
            d.ellipse((x, h // 2 - r, x + 2 * r, h // 2 + r), fill=c)
            x += 2 * r + size // 2
        d.text((x, h // 2), text, font=f, fill=c or BAR_FG, anchor="lm")
        x += int(d.textlength(text, font=f)) + size * 2
    return img


def cmd_zoom(a: argparse.Namespace) -> None:
    img = Image.open(a.input).convert("RGB")
    x, y, w, h = (int(v) for v in a.box.split(","))
    if x < 0 or y < 0 or x + w > img.width or y + h > img.height:
        sys.exit(f"evidence_img: box {a.box} is outside {img.width}x{img.height}")
    crop = img.crop((x, y, x + w, y + h))
    crop.resize((w * a.scale, h * a.scale), Image.NEAREST).save(a.output)


def cmd_pair(a: argparse.Namespace) -> None:
    before = Image.open(a.before).convert("RGB")
    after = Image.open(a.after).convert("RGB")
    labels = a.labels
    size = max(14, before.width // 60)
    tops = [
        bar(before.width, [(labels[0], colour("bad"))], size),
        bar(after.width, [(labels[1], colour("good"))], size),
    ]
    halves = [above(top, body) for top, body in zip(tops, (before, after))]
    gap = size
    if a.side_by_side:
        out = Image.new(
            "RGB", (sum(h.width for h in halves) + gap, max(h.height for h in halves)), BAR_BG
        )
        out.paste(halves[0], (0, 0))
        out.paste(halves[1], (halves[0].width + gap, 0))
    else:
        out = Image.new(
            "RGB", (max(h.width for h in halves), sum(h.height for h in halves) + gap), BAR_BG
        )
        out.paste(halves[0], (0, 0))
        out.paste(halves[1], (0, halves[0].height + gap))
    out.save(a.output)


def blank(img: Image.Image, box: tuple[int, int, int, int]) -> bool:
    """Whether a region holds no content: inside the image and near-uniform."""
    x0, y0, x1, y1 = box
    if x0 < 0 or y0 < 0 or x1 > img.width or y1 > img.height:
        return False
    return max(ImageStat.Stat(img.crop(box)).stddev) < 6


def draw_marks(
    img: Image.Image,
    boxes: list[str],
    cell: tuple[int, int],
    scale: int,
    origin: tuple[int, int],
    title: str | None,
) -> tuple[Image.Image, Image.Image]:
    """Marks for IMG (already cropped and scaled): (RGBA overlay, legend bar).

    Boxes are X,Y,W,H,COLOR,LABEL in pixels, or in cells when CELL is given;
    ORIGIN is the crop's top-left cell. Badges go only where IMG is blank.
    """
    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(overlay)
    # Marks scale with the text they sit on: the cell height, else the width.
    size = cell[1] * scale if cell != (1, 1) else max(14, img.width // 60)
    f = font(int(size * 0.6))
    legend: list[tuple[str, tuple[int, int, int] | None]] = []
    if title:
        legend.append((title, None))
    for n, spec in enumerate(boxes, start=1):
        parts = spec.split(",", 5)
        if len(parts) != 6:
            sys.exit(f"evidence_img: --box wants X,Y,W,H,COLOR,LABEL, got {spec!r}")
        cw, ch = cell
        col, row, ncols, nrows = (int(v) for v in parts[:4])
        col, row = col - origin[0], row - origin[1]
        x, y, w, h = (v * k * scale for v, k in zip((col, row, ncols, nrows), (cw, ch, cw, ch)))
        c = colour(parts[4])
        pad = max(3, size // 4)
        rect = (x - pad, y - pad, x + w + pad, y + h + pad)
        d.rounded_rectangle(
            rect, radius=size // 2, fill=(*c, 34), outline=(*c, 255), width=max(2, size // 8)
        )
        r = int(size * 0.42)
        mid = (rect[1] + rect[3]) // 2
        spots = [
            (rect[2] + pad + r, mid),
            (rect[0] - pad - r, mid),
            (rect[0] + r, rect[1] - pad - r),
        ]
        spot = next(
            (
                (sx, sy)
                for sx, sy in spots
                if blank(img, (sx - r - 1, sy - r - 1, sx + r + 1, sy + r + 1))
            ),
            None,
        )
        if spot is None:
            # Never cover content: the box's colour still ties it to the legend.
            print(f"evidence_img: no blank spot for badge {n}; drawn without it", file=sys.stderr)
        else:
            cx, cy = spot
            d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=(*c, 255))
            d.text((cx, cy), str(n), font=f, fill=BAR_BG, anchor="mm")
        legend.append((f"{n} {parts[5]}", c))
    return overlay, bar(img.width, legend, size)


def cmd_mark(a: argparse.Namespace) -> None:
    img = Image.open(a.input).convert("RGB")
    origin = (0, 0)
    if a.crop:
        if a.cell == (1, 1):
            sys.exit("evidence_img: --crop is in cells; give --cell too")
        cw, ch = a.cell
        c0, r0, nc, nr = (int(v) for v in a.crop.split(","))
        box = (c0 * cw, r0 * ch, (c0 + nc) * cw, (r0 + nr) * ch)
        if box[2] > img.width or box[3] > img.height:
            sys.exit(f"evidence_img: crop {a.crop} is outside the frame")
        img = img.crop(box)
        origin = (c0, r0)
    if a.scale > 1:
        img = img.resize((img.width * a.scale, img.height * a.scale), Image.NEAREST)
    overlay, top = draw_marks(img, a.box, a.cell, a.scale, origin, a.title)
    marked = Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB")
    above(top, marked).save(a.output)


def main() -> None:
    p = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    sub = p.add_subparsers(dest="cmd", required=True)
    z = sub.add_parser("zoom")
    z.add_argument("input")
    z.add_argument("-o", "--output", required=True)
    z.add_argument("--box", required=True)
    z.add_argument("--scale", type=int, default=2)
    pr = sub.add_parser("pair")
    pr.add_argument("before")
    pr.add_argument("after")
    pr.add_argument("-o", "--output", required=True)
    pr.add_argument("--labels", nargs=2, required=True, help=LABELS_HELP)
    pr.add_argument("--side-by-side", action="store_true")
    m = sub.add_parser("mark")
    m.add_argument("input")
    m.add_argument("-o", "--output", required=True)
    m.add_argument("--box", action="append", required=True)
    m.add_argument("--title")
    m.add_argument("--scale", type=int, default=1)
    m.add_argument("--crop", help="COL,ROW,NCOLS,NROWS in cells (needs --cell)")
    m.add_argument("--cell", default="1x1", type=cells)
    a = p.parse_args()
    {"zoom": cmd_zoom, "pair": cmd_pair, "mark": cmd_mark}[a.cmd](a)
    print(f"evidence_img: wrote {a.output}")


if __name__ == "__main__":
    main()
