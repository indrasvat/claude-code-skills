# Capture

`$S` is this skill's directory (see SKILL.md). Every path below is made with
`mktemp -d` or chosen by you; nothing is fixed.

## Contents

- Both builds
- Terminal capture with shux
- Video: driver plus observer
- Trimming and cutting video
- Web, native, phones
- Frame hygiene

## Both builds

- **Base:** the published release installed to its own prefix (the project's
  installer with a `--dir`/`--prefix` into a `mktemp -d`), or the base SHA
  built in a throwaway `git worktree add "$(mktemp -d)" <base-sha>`. Name it by
  version or short SHA.
- **Branch:** the build from the final commit, copied out of the build
  directory (rebuilds and test runs replace binaries in place; never `cp` over
  a binary that is running).
- **Isolation:** every run gets its own runtime dir
  (`XDG_RUNTIME_DIR=$(mktemp -d)`; keep it short, sockets have a path limit),
  so neither build touches the user's daemon or the other build's state.
- **When shux is itself the product:** record with a stable shux
  (`SHUX_BIN=/path/to/stable/shux`) in its own runtime dir, apart from both
  builds under test.

## Terminal capture with shux

These calls are all the capture needs; for more, the shux skill if installed,
else `shux --help` and `shux <verb> --help`.

```bash
W=$(mktemp -d); export XDG_RUNTIME_DIR="$W/rt"         # private daemon
shux session create ev -d --cwd "$W" -- bash -l         # real shell, real prompt
P=$(shux --format json pane list -s ev | jq -r '.[0].id')
shux pane set-size -s ev --cols 140 --rows 26           # size to the content
shux pane run -s ev -p "$P" --timeout 60s -c './app --flag'   # with shell integration
shux pane snapshot -s ev -p "$P" -o "$W/still.png"      # one pane
shux window snapshot -s ev -o "$W/frame.png"            # whole window, borders and all
shux pane capture -s ev -p "$P" >"$W/still.txt"         # text: rows/cols to mark, leaks to grep
shux session kill ev && shux daemon stop                # leave nothing running
```

- Without shell integration, type the line and submit with C-j
  (`send-keys --text '…'` then `--data Cg==`); C-j submits in bash, zsh and
  ble.sh alike, where Enter (`DQ==`) can leave ble.sh in `-- MULTILINE --`.
- One line per step (`bash "$W/step.sh"`), never a multi-line paste.
- Wait on the pane's own signal (`pane run`, `wait-command`, `wait-settled`),
  or on fresh text the command *prints* that its typed line cannot contain
  (`printf 'DONE-%s\n' "$id"`). Never `sleep` and hope.
- Read the capture's text before snapshotting: no `Loading…`, no tofu, no
  wrapped line hiding the point (widen the pane instead).

## Video: driver plus observer

For timing and lifecycle, record one window with two panes:

```bash
W=$(mktemp -d); export XDG_RUNTIME_DIR="$W/rt"            # the recorder's own daemon
shux session create demo -d --cwd "$W" -- bash -l          # driver (top)
shux pane split -s demo -d horizontal -- bash "$S/scripts/observe.sh" -u "$W/stop" -- \
  "daemon::ps -o pid=,stat= -p \$(cat $W/app/app.pid) || echo none" \
  'workers::ps -axo pid=,command= | grep -E "[s]leep 5[0-9]{4}$" || echo none'
bash "$S/scripts/record.sh" -s demo -c 170x36 -o "$W/demo.mp4" -u "$W/stop" -t 180 -f 4 -x 1
```

- `-d horizontal` stacks the panes (observer below); `-d vertical` puts it right.
- The driver touches `$W/stop` when its last step is done; observer and
  recorder stop on it. `-t` caps the recording regardless.
- `-x 1` (real time) when the clock is the evidence; `-x 1.5` otherwise.
  `record.sh` encodes at the measured capture rate, so the speed is true.
- Start recording only once the driver has drawn its first heading, so the
  poster never shows the prompt.
- Driver scripts print a heading per scenario and pause about a second
  between scenarios, so the viewer reads the caption before it moves.
- Probes use a unique needle per run (`sleep 5xxxx`), never a shared name that
  matches other processes, and never the observer's own argv (the `[s]` trick).
- **Probes are read-only.** A probe must never change what it observes: a CLI
  that auto-starts a daemon restarts the very daemon the driver just stopped.
  Query `ps`, a pidfile, or the socket with a short timeout, and report a
  timeout as "not answering", never "gone". `observe.sh` cuts off any probe
  after `-T` seconds (default 2) and shows "(probe timed out after 2s)".
- **Size the observer for its worst case**: one line per probe, rows for all
  of them. An overflowing list scrolls the clock off, in the frame that matters.
- Record base and branch with the same driver, then
  `uv run "$S/scripts/evidence_video.py" stack base.mp4 branch.mp4 -o both.mp4
  --labels "before · v1.2.0" "after · this PR"`.

## Trimming and cutting video

Every encode needs the phone-safe flags; `evidence_video.py` and `record.sh`
already use them. By hand:

```bash
ENC="-r 15 -c:v libx264 -profile:v high -level:v 4.2 -preset slow -crf 18 -pix_fmt yuv420p -movflags +faststart"
ffmpeg -ss 0.3 -i in.mp4 -vf fps=15 $ENC trimmed.mp4          # drop a leading prompt frame
ffmpeg -i in.mp4 -filter_complex "[0]trim=0:12,setpts=PTS-STARTPTS[p1];\
[0]trim=20:35,setpts=PTS-STARTPTS[p2];[p1][p2]concat=n=2,fps=15[out]" -map "[out]" $ENC cut.mp4
```

- Give every pad a unique name per chain: a reused name silently wires streams
  crosswise (the "before" label lands on "after" frames).
- Many ffmpeg builds have no `drawtext`. Captions and labels are drawn as
  images (`evidence_video.py mark`, `stack --labels`), never with `drawtext`.
- `-level:v 4.2` fits frames up to 8704 macroblocks (about 2.2 MP); above, 5.1.
- Then `bash "$S/scripts/check_video.sh" out.mp4` must print PASS.

## Web, native, phones

- **Web:** `agent-browser` screenshots (device scale ≥ 2) and its recording
  for flows. Logged-in sites: a signed-in browser bridge such as
  `browsing-as-you`, never typed credentials.
- **Native on macOS:** `screencapture -l <windowid>` for stills,
  `screencapture -v` or ffmpeg `-f avfoundation` for video.
- **Native on Linux:** run the app under `Xvfb :99 -screen 0 1600x1000x24`,
  then `ffmpeg -f x11grab -framerate 15 -video_size 1600x1000 -i :99` for
  video and `import -window root` (ImageMagick) for stills.
- **Phones:** iOS Simulator `xcrun simctl io booted screenshot|recordVideo`;
  Android `adb exec-out screencap -p` and `adb shell screenrecord`. Both record
  variable frame rates: re-encode with `fps=30` and the flags above.

## Frame hygiene

- Save each frame's text (`shux pane capture`) beside it and pass those files
  to `check_evidence.sh`; it greps them for home paths and the host name.
- Never edit a script while it is running.
