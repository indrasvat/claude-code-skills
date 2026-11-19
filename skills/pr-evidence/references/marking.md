# Marking and layout

## The mark

The goal: found in under a second, and still part of the picture. A faint
mark is missed; a loud one looks pasted on and hides what it points at.

- **Colours the screen already uses.** Red for what the base gets wrong,
  green for what the branch shows, amber for what both share. `evidence_img.py`
  names them `bad`, `good`, `same`; pass the subject's own theme hex when it
  has one. Never a colour foreign to the frame.
- **Thin, rounded, full strength,** with a faint tint inside (alpha about
  34/255). Never a filled box, a drop shadow, or an arrow drawn across text.
- **Breathing room:** padding around the matched text; the outline never
  touches a glyph.
- **One point, one mark.** Rows that say one thing share one box.
- **At most three or four marks per frame.** More means the frame is doing too
  much: split it.

## Badges and legend

- A small numbered badge in the mark's colour sits in blank space beside the
  mark (right, then left, then above). `evidence_img.py` tests the spot is
  blank and leaves the badge out, with a warning, rather than cover content.
- Words never go inside the frame. The legend bar above it carries each
  number and a short plain label: "4 programs orphaned", not
  "handler dropped before teardown".

## Placing marks

Mark by terminal cell, read off the pane's text:

```bash
shux pane capture -s S -p P | grep -n 'orphaned'      # grep -n is 1-based: row = n-1
uv run "$S/scripts/evidence_img.py" mark frame.png -o marked.png \
  --scale 2 --cell 9x19 --title "PR #123" \
  --box 51,12,34,1,bad,"4 programs orphaned" --box 51,13,34,1,good,"none orphaned"
```

`--box COL,ROW,NCOLS,NROWS,COLOUR,LABEL`. shux's raster cell is 9×19 px;
verify by dividing the image width by the pane's columns. Guessing pixel
coordinates off a displayed image lands marks on the wrong row.

## Zoom

Zoom to the change: `evidence_img.py zoom frame.png -o z.png --box X,Y,W,H --scale 2`.
To zoom **and** mark in one step, give `mark` a cell crop; boxes stay in the
frame's own cell coordinates:
`evidence_img.py mark frame.png -o z.png --cell 9x19 --crop 0,10,90,6 --scale 2 --box …`.
Nearest-neighbour only, so glyphs stay crisp. A partial screen is fine when
it makes the point; keep enough context (the row's label, the panel's title)
that the reader knows where they are.

## Marks on video

Mark a stretch of a clip the same way, by pixel (or `--cell` on a raw shux
recording), shown only while it matters:

```bash
uv run "$S/scripts/evidence_video.py" mark both.mp4 -o marked.mp4 \
  --from 4.5 --to 9 --title "PR #123" \
  --box 40,310,300,80,bad,"workers left running" --box 40,720,300,80,good,"workers stopped"
```

The legend bar sits above the frame for the whole clip; boxes and badges
appear between `--from` and `--to`. Read the coordinates off a frame from
`evidence_video.py sheet` or `ffmpeg -ss T -i in.mp4 -frames:v 1 f.png`. For
marks at several times, run `mark` once per stretch on the previous output.

## Before/after layouts

| Layout | Use for |
|---|---|
| **Paired stills** (`evidence_img.py pair`), stacked or side by side, each with a labelled bar (base in red, branch in green) | Static rendering changes |
| **One video, base on top, branch below** (`evidence_video.py stack`), same inputs and timeline | Motion, interaction, timing |
| **Split frame:** left half base, right half branch, in one image | A single row or region compared |
| **Table** of behaviour / base / branch beside the images | Saying in words what to look at |

## Captions

One line per image or clip, saying what to look at and naming both builds:
"v0.56.1 (top) gives up at +5 s while the daemon is still stopped; this PR
(bottom) answers when it resumes at +8 s". Change video captions only at
timeline steps.

## Check a marked frame

1. Every mark is found without searching; its colour and number match the legend.
2. No mark or badge covers a glyph.
3. Red only on the base, green only on the branch.
4. Each label is a plain statement a reviewer would agree with by looking.
5. The caption matches the frame.
