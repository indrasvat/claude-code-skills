# Choosing the medium

## The question to ask

"What would a skeptical reviewer need to *see* to believe this, without
taking my word for it?" Then capture exactly that. If the honest answer is
"a moment in time", "a process that should be gone", or "a sequence of
steps", a still cannot carry it.

## Worked examples

### A timeout that fires too early (timing)

*Defect:* a CLI gave a busy daemon 5 s, then called it wedged.

- **Worthless:** a still of the demo's own output: "✗ failed after 5.1s /
  ✓ answered after 8.0s". These are numbers the script printed about itself.
  The reader sees no clock, no daemon, no waiting.
- **Right:** a video, two panes. The driver runs the old CLI, then the new one,
  against a daemon stopped for 8 s. The observer shows a running clock and
  the daemon's real `ps` state (`T` while stopped, `S` once continued). The
  reader watches the old CLI give up at +5 s while the daemon is still `T`,
  and the new one return the moment it turns `S`. Play at real time, or say
  the speed in the caption, so the clock reads true.

### Processes left behind (lifecycle)

*Defect:* a kill whose client hangs up leaves the session's programs running.

- **Worthless:** "4 orphaned / 0 orphaned" printed by the script.
- **Right:** the observer pane shows the session list and `ps` for the
  programs, live, using a unique needle per run. Before: the session vanishes
  from the list while its programs stay in `ps`. After: both go together.
  Give the count over the N attempts as a caption, since one hang-up may not
  hit the window.

### A rendering bug (static)

*Defect:* a status-bar badge overlaps the clock at 60 columns.

- **Right:** before/after stills at the failing size, zoomed 2× on the
  status bar, each change marked. Add the other cells the repo's protocol
  requires (sizes, themes, config states), named by cell.

### An interaction bug

*Defect:* Alt+Left is swallowed when there is no pane to move to.

- **Right:** a short video with keycaps (or a caption per key). The probe
  echoes what it received. Before: nothing arrives. After: the shell's
  word-motion happens.

### A flake or race

- **Right:** one video of a failing and a passing run if it can be forced,
  plus the rate: "red in 4/20 runs at 800 CPU hogs before, 0/20 after", with
  the command. A single green clip of a flaky thing proves nothing.

### Performance

- **Right:** the measured numbers, before and after, with the method (tool,
  load, runs, percentiles) and where it was measured. Add a frame only if the
  slowness is visible (a stutter: video; a spinner that lingers: video).

## Traps that produced worthless evidence

| Trap | Instead |
|---|---|
| Choosing a still because a still is easy | Choose by the table in SKILL.md first |
| Reading "dynamic" as "UI motion" only | Timing, lifecycle and concurrency are dynamic too |
| A repo rule exempting "non-visual" changes, applied to a behaviour change | Behaviour a user notices is visual: CLI output, waiting, a lingering process |
| The demo script's verdict lines as the proof | An independent observer: `ps`, the screen, a clock, the file |
| An after with no before | Both builds, same script |
| A frame captured before the app drew (`Loading…`, empty list) | Wait for content, then capture |
| Matching a done-marker left on screen from the previous run | A fresh marker per run, never printed in a way the shell echo can match |
| Monochrome capture of a colourful tool | Colour on; check the frame |
| Thumbnails or stretched images | Native size or 2× nearest-neighbour; zoom on the change |
| A 2-minute video of a 3-second event | Cut to cause, event, consequence |
