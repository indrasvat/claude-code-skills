---
name: pr-evidence
description: >
  Captures before/after evidence for a pull request and posts it as one PR
  comment. Picks stills, clocked video or numbers from the nature of the change,
  records the real product on the base and the branch (shux for terminals,
  agent-browser for web), marks what changed, gates every video for phone
  playback and attaches files without committing them. Use before opening or
  marking ready any non-trivial PR, before claiming a fix is done, and when
  asked to "capture evidence", "post evidence", "prove the fix", "before/after",
  "add screenshots to the PR", "record a demo video", "evidence comment",
  "highlight what changed", "annotate the video" or "zoomed screenshot". Most
  broken rule: a timing, lifecycle or interaction change needs video with an
  independent observer (a clock, ps, the list), never a still of a script's own
  verdict.
license: MIT
compatibility: macOS or Linux, any agent. Needs bash, ffmpeg (libx264), perl, jq, uv; shux for terminals, agent-browser for web, gh for posting. Run scripts/doctor.sh.
allowed-tools: Bash, Read, Write, Grep, Glob
argument-hint: "[pr-number]"
---

# PR evidence

Evidence lets a reviewer see in seconds, without trusting the author, that the
change does what the PR says.

`S` is this skill's directory, the folder holding this SKILL.md (Claude Code:
`${CLAUDE_SKILL_DIR}`). Start with `bash "$S/scripts/doctor.sh"`: it checks
every route, prints the install command for anything missing, and ends with
`doctor: core=… terminal=… web=… publish=… skill=<dir>`.

## 1. Choose the medium from the nature of the change

| The change is about | Evidence |
|---|---|
| What a screen shows (layout, colour, glyphs, wording) | Before/after **stills**, zoomed on the change, marked |
| **Time**: a hang, timeout, latency | **Video** with an on-screen clock |
| **Lifecycle**: something lingers, leaks, dies, restarts | **Video** with an observer pane (`ps`, the list, the socket) |
| **Interaction**: keys, focus, a multi-step flow | **Video** with a caption per step |
| **Races**: fails one run in N | One video, **plus** the count over N runs |
| A measured quantity (speed, size) | The **numbers** before and after, with the method |
| A library or API | A minimal caller script run on both builds, outputs side by side |
| Nothing visible (CI, docs, pure refactor) | One line: "visual proof: exempt, non-visual: <reason>" |

A leak, hang or wrong output is never "internals"; several natures get several
media. Worked examples and traps: `references/choosing-the-medium.md`.

## 2. Rules

1. **Same run, both builds.** Same script, input and size on the base (the
   published release or base SHA) and the branch; name both on every frame.
2. **The system's own state, not the harness's verdict.** "✓ fixed" printed by
   your script is a claim. Show the process list, the screen, the clock.
3. **Real and colourful.** Real binary and data, colour on, a neutral cwd
   (`mktemp -d`), content loaded first: no `Loading…` frames.
4. **Glanceable.** One point per image or clip, marked, zoomed, framed to its
   content. Clips show cause, event, consequence: usually 15–60 s at 1.5×.
5. **Final code only.** Capture after the last review fix; re-capture on change.
6. **Never committed, never private:** no local paths, hosts, tokens, third parties.
7. **Plays on a phone:** H.264 High 4.2 (5.1 over ~2.2 MP), yuv420p, constant
   rate, faststart, a first frame showing the subject. `check_video.sh` decides.
8. **Repo protocol wins** (CLAUDE.md, AGENTS.md, CONTRIBUTING) where it differs.

## 3. Workflow

1. **Plan.** Name the nature; list each frame or clip, what it must show, and
   every cell of any matrix the repo defines.
2. **Build both sides** at their own paths or ports, outside build dirs: base
   in a throwaway `git worktree` (or the release), branch from its final commit,
   each run with its own `XDG_RUNTIME_DIR` (`mktemp -d`).
3. **Capture the real product.** Terminals: drive both builds in shux panes;
   stills with `shux pane snapshot`, video with `scripts/record.sh` over a
   window holding the driver and, for time or lifecycle, `scripts/observe.sh`.
   Web: `agent-browser`. Native: the OS recorder. Recipes: `references/capture.md`.
4. **Compose and mark** with `uv run "$S/scripts/evidence_img.py" zoom|pair|mark`
   (stills) and `evidence_video.py stack|mark` (base over branch; marks over a
   time range). Red = base wrong, green = branch fixed, amber = shared; thin
   rounded outlines, numbered badges, words in the legend, never over a glyph.
   Layouts and placement by terminal cell: `references/marking.md`.
5. **Look before posting.** Open every PNG at full size; for each video read
   its poster and `evidence_video.py sheet` (agents cannot watch video). Fill
   `assets/evidence-comment.md`, then `bash "$S/scripts/check_evidence.sh"
   evidence.md [capture.txt …]` must print PASS. Show the user the key frame.
6. **Publish one comment** right after the PR opens (no draft PR just to
   hold evidence): `gh pr comment N --body-file evidence.md --attach a.png
   --attach demo.mp4` rewrites `![…](./a.png)` to the uploaded asset. No
   `--attach`, or re-recording: `references/publishing.md`.

## Scripts (in `$S/scripts/`; read the last line each prints)

| Script | Does |
|---|---|
| `doctor.sh` | Preflight: routes available, install commands, the skill dir |
| `record.sh` | Records a shux window or pane to mp4 at a true speed; gates it |
| `observe.sh` | Live clock plus read-only probes, the independent observer |
| `evidence_img.py` | `zoom`, `pair`, `mark` (by pixel or terminal cell) on stills |
| `evidence_video.py` | `stack`, `mark`, `sheet` for videos; gates what it writes |
| `check_video.sh` | Phone-playback gate plus the poster frame |
| `check_evidence.sh` | Comment gate: artifacts exist, play, are untracked, leak nothing |
