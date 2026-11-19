# /// script
# requires-python = ">=3.11"
# dependencies = ["pillow"]
# ///
"""Evidence videos: base-over-branch stacks, marks over a stretch of time, and
frame sheets to read a video without playing it.

  uv run evidence_video.py stack BASE.mp4 BRANCH.mp4 -o OUT.mp4
        --labels "before · v1.2.0" "after · this PR"
  uv run evidence_video.py mark IN.mp4 -o OUT.mp4 --box X,Y,W,H,COLOR,LABEL [--box ...]
        [--cell 9x19] [--from SECONDS] [--to SECONDS] [--title TEXT]
  uv run evidence_video.py sheet IN.mp4 -o SHEET.png [--frames 9] [--cols 3]

stack: the shorter clip holds its last frame so both run to the end; labels
are drawn bars (red base, green branch), so no ffmpeg drawtext is needed.
mark: the same marks as evidence_img.py (thin rounded outlines, numbered
badges, legend bar above the frame), shown between --from and --to.
sheet: evenly spaced frames, each stamped with its time; the first is the
poster. Read it, and the poster, before posting: agents cannot watch video.

stack and mark encode with the phone-safe flags and run check_video.sh on the
result; their exit code is the gate's.
"""

import argparse
import pathlib
import subprocess
import sys
import tempfile

from PIL import Image

from evidence_img import BAR_BG, LABELS_HELP, above, bar, cells, colour, draw_marks

HERE = pathlib.Path(__file__).resolve().parent
BG = "0x{:02x}{:02x}{:02x}".format(*BAR_BG)


def run(cmd: list[str]) -> str:
    p = subprocess.run(cmd, capture_output=True, text=True)
    if p.returncode != 0:
        sys.exit(f"evidence_video: {cmd[0]} failed ({p.returncode}):\n{p.stderr.strip()}")
    return p.stdout


def probe(path: str) -> dict[str, float]:
    out = run(
        [
            "ffprobe",
            "-v",
            "error",
            "-select_streams",
            "v:0",
            "-show_entries",
            "stream=width,height,r_frame_rate,duration:format=duration",
            "-of",
            "default=nw=1",
            path,
        ]
    )
    # The video stream's own duration: a longer audio track stretches the file's.
    kv: dict[str, str] = {}
    for line in out.splitlines():
        k, _, val = line.partition("=")
        if val and val != "N/A":
            kv.setdefault(k, val)
    num, den = kv["r_frame_rate"].split("/")
    return {
        "w": int(kv["width"]),
        "h": int(kv["height"]),
        "fps": int(num) / int(den),
        "dur": float(kv["duration"]),
    }


def encode_args(w: int, h: int, fps: int) -> list[str]:
    # Level 4.2 fits up to 8704 macroblocks (about 2.2 MP); 5.1 above. Never 6.x.
    level = "4.2" if ((w + 15) // 16) * ((h + 15) // 16) <= 8704 else "5.1"
    return [
        "-r",
        str(fps),
        "-c:v",
        "libx264",
        "-profile:v",
        "high",
        "-level:v",
        level,
        "-preset",
        "slow",
        "-crf",
        "18",
        "-pix_fmt",
        "yuv420p",
        "-movflags",
        "+faststart",
    ]


def gate(path: str) -> None:
    sys.exit(subprocess.run(["bash", str(HERE / "check_video.sh"), path]).returncode)


def cmd_stack(a: argparse.Namespace) -> None:
    clips = [probe(a.base), probe(a.branch)]
    fps = 15  # a constant rate both clips are normalised to; phones need one
    longest = max(c["dur"] for c in clips)
    width = max(c["w"] for c in clips)
    width += width % 2  # even, so yuv420p padding cannot round it down
    size = max(14, max(c["w"] for c in clips) // 50)
    with tempfile.TemporaryDirectory() as tmp:
        inputs, chains, bar_h = [], [], 0
        for i, (path, clip, label, tone) in enumerate(
            zip((a.base, a.branch), clips, a.labels, ("bad", "good"))
        ):
            png = pathlib.Path(tmp) / f"label{i}.png"
            label_bar = bar(width, [(label, colour(tone))], size)
            label_bar.save(png)
            bar_h = max(bar_h, label_bar.height)
            inputs += ["-i", path, "-loop", "1", "-framerate", str(fps), "-i", str(png)]
            v, lab = 2 * i, 2 * i + 1
            hold = longest - clip["dur"]
            # Pad names carry the clip index: a reused name wires streams crosswise.
            chains.append(
                # setpts before fps: after it, ffmpeg 7.1's tpad holds nothing.
                f"[{v}:v]setpts=PTS-STARTPTS,fps={fps},"
                f"tpad=stop_mode=clone:stop_duration={hold:.3f},"
                f"format=yuv420p,pad={width}:ih:0:0:color={BG}[c{i}v];"
                f"[{lab}:v]fps={fps}[c{i}l];[c{i}l][c{i}v]vstack=shortest=1[c{i}]"
            )
        graph = ";".join(chains) + (
            f";[c0][c1]vstack=shortest=1,pad=ceil(iw/2)*2:ceil(ih/2)*2:color={BG}[out]"
        )
        h = sum(c["h"] for c in clips) + 2 * bar_h
        run(
            [
                "ffmpeg",
                "-v",
                "error",
                "-y",
                *inputs,
                "-filter_complex",
                graph,
                "-map",
                "[out]",
                "-t",
                f"{longest:.3f}",
                *encode_args(width, h, fps),
                a.output,
            ]
        )
    gate(a.output)


def cmd_mark(a: argparse.Namespace) -> None:
    clip = probe(a.input)
    fps = max(1, round(clip["fps"]))
    start, end = a.start, a.end if a.end is not None else clip["dur"]
    if not 0 <= start < end <= clip["dur"] + 0.5:
        print(
            f"evidence_video: need 0 <= --from < --to <= {clip['dur']:.1f}s, "
            f"got --from {start} --to {end}",
            file=sys.stderr,
        )
        sys.exit(2)
    with tempfile.TemporaryDirectory() as tmp:
        frame = pathlib.Path(tmp) / "frame.png"
        run(
            [
                "ffmpeg",
                "-v",
                "error",
                "-y",
                "-ss",
                f"{start:.3f}",
                "-i",
                a.input,
                "-frames:v",
                "1",
                str(frame),
            ]
        )
        img = Image.open(frame).convert("RGB")
        overlay, legend = draw_marks(img, a.box, a.cell, 1, (0, 0), a.title)
        marks_png, legend_png = pathlib.Path(tmp) / "marks.png", pathlib.Path(tmp) / "legend.png"
        overlay.save(marks_png)
        legend.save(legend_png)
        graph = (
            f"[0:v]setpts=PTS-STARTPTS,fps={fps}[mv];"
            f"[1:v]fps={fps}[mo];[2:v]fps={fps}[ml];"
            f"[mv][mo]overlay=0:0:enable='between(t,{start},{end})'[mm];"
            f"[ml][mm]vstack=shortest=1,pad=ceil(iw/2)*2:ceil(ih/2)*2:color={BG}[out]"
        )
        run(
            [
                "ffmpeg",
                "-v",
                "error",
                "-y",
                "-i",
                a.input,
                "-loop",
                "1",
                "-framerate",
                str(fps),
                "-i",
                str(marks_png),
                "-loop",
                "1",
                "-framerate",
                str(fps),
                "-i",
                str(legend_png),
                "-filter_complex",
                graph,
                "-map",
                "[out]",
                "-t",
                f"{clip['dur']:.3f}",
                *encode_args(clip["w"], clip["h"] + legend.height, fps),
                a.output,
            ]
        )
    gate(a.output)


def cmd_sheet(a: argparse.Namespace) -> None:
    clip = probe(a.input)
    n = max(1, a.frames)
    # The first tile is t=0 (the poster); the last sits just before the end.
    # Clamp to the last whole frame: a later seek yields no image (exit 0).
    last = max(0.0, clip["dur"] - 1.5 / clip["fps"])
    times = [0.0] + [min(last, clip["dur"] * k / n) for k in range(1, n)]
    tile_w = min(640, clip["w"])
    tiles = []
    with tempfile.TemporaryDirectory() as tmp:
        for i, t in enumerate(times):
            png = pathlib.Path(tmp) / f"{i}.png"
            run(
                [
                    "ffmpeg",
                    "-v",
                    "error",
                    "-y",
                    "-ss",
                    f"{t:.3f}",
                    "-i",
                    a.input,
                    "-frames:v",
                    "1",
                    "-vf",
                    f"scale={tile_w}:-2",
                    str(png),
                ]
            )
            if not png.exists():
                sys.exit(f"evidence_video: no frame at {t:.2f}s in {a.input}")
            body = Image.open(png).convert("RGB")
            label = bar(tile_w, [(f"t={t:.1f}s" + ("  poster" if i == 0 else ""), None)], 14)
            tiles.append(above(label, body))
    cols = min(a.cols, len(tiles))
    rows = -(-len(tiles) // cols)
    th = max(t.height for t in tiles)
    gap = 6
    sheet = Image.new(
        "RGB", (cols * tile_w + (cols - 1) * gap, rows * th + (rows - 1) * gap), BAR_BG
    )
    for i, tile in enumerate(tiles):
        sheet.paste(tile, ((i % cols) * (tile_w + gap), (i // cols) * (th + gap)))
    sheet.save(a.output)
    print(f"evidence_video: wrote {a.output} ({len(tiles)} frames over {clip['dur']:.1f}s)")


def main() -> None:
    p = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    sub = p.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("stack")
    s.add_argument("base")
    s.add_argument("branch")
    s.add_argument("-o", "--output", required=True)
    s.add_argument("--labels", nargs=2, required=True, help=LABELS_HELP)
    m = sub.add_parser("mark")
    m.add_argument("input")
    m.add_argument("-o", "--output", required=True)
    m.add_argument("--box", action="append", required=True)
    m.add_argument("--title")
    m.add_argument("--from", dest="start", type=float, default=0.0)
    m.add_argument("--to", dest="end", type=float)
    m.add_argument("--cell", default="1x1", type=cells)
    sh = sub.add_parser("sheet")
    sh.add_argument("input")
    sh.add_argument("-o", "--output", required=True)
    sh.add_argument("--frames", type=int, default=9)
    sh.add_argument("--cols", type=int, default=3)
    a = p.parse_args()
    {"stack": cmd_stack, "mark": cmd_mark, "sheet": cmd_sheet}[a.cmd](a)


if __name__ == "__main__":
    main()
