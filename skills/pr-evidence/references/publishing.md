# Publishing

## The evidence comment

One comment, posted as soon as the PR is open, filled in from
`$S/assets/evidence-comment.md`. Lead with the strongest artifact (the video
for dynamic changes, the marked zoom for static ones); numbers go in the
table, beside the frames that show them.

No transcript, no test lists, no "CI green": the PR body and checks carry those.

## Route, in order

Run `doctor.sh`; its `publish=` field picks the route.

1. **`publish=attach`:** gh has `--attach` and is logged in.
   `gh pr comment N --body-file evidence.md --attach ./demo.mp4 --attach ./a.png`.
   Each `![…](./a.png)` is rewritten to the uploaded asset, a video becomes a
   player, and unreferenced files are appended. The PR body itself:
   `gh pr edit N --attach …`.
2. **`publish=manual`, signed-in browser available:** a bridge such as the
   `browsing-as-you` skill's `cdp.py --json gh-attach --repo O/R --pr N -f a.png`
   returns asset URLs without clicking anything. Put them in the body, then
   `gh api repos/O/R/issues/N/comments -F body=@evidence.md`.
3. **Neither** (a cloud or headless box with no browser): upgrade gh
   (`doctor.sh` prints the command) and log in with `GH_TOKEN`. If that is not
   possible, stop and ask the user where the files should go. A page only the
   author can open (a private agent artifact, a local server) is not evidence.

Never drop the video because the route changed, and never fall back to
committing the files.

## Before posting: the gate and the cold read

1. `bash "$S/scripts/check_evidence.sh" evidence.md [frame texts …]` prints PASS:
   every artifact exists, every video passes the phone gate, nothing is
   tracked by git, and no home path or host name appears in the text.
2. After posting, open the comment as a reader would, in a signed-in browser
   (uploaded assets 404 to anonymous `curl`): every image loads at full size,
   every video plays. A desktop player proves nothing for phones; the gate on
   the exact uploaded file does. If the user can, ask them to open it on a phone.
3. Each artifact shows its point with no other context: the change's nature,
   not the script's verdict.
4. Marks pass the check in `marking.md`.

## Rules

- Never commit evidence: no PNG or MP4 in the repo, no links to ignored
  paths, no `raw.githubusercontent` links to committed binaries. A committed
  image is justified only as a test baseline something diffs against.
- Replace, do not stack: when evidence is re-recorded, edit the comment
  (`gh api -X PATCH repos/O/R/issues/comments/ID -F body=@evidence.md` after
  uploading the new files), so the PR shows one current set.
- The same comment shape works on an issue that needs proof of a defect.
