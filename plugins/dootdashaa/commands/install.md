---
description: Wire dootdashaa as your Claude Code statusLine (one-time, idempotent)
---

# /dootdashaa:install

Idempotently edits `~/.claude/settings.json` so Claude Code uses `dootdashaa`
as its statusLine. If a different statusLine is already configured it is
preserved as `statusLine.previous` so `/dootdashaa:uninstall` can restore it.

## Instructions

1. Confirm the symlink exists. Run:
   ```bash
   test -x "${CLAUDE_CONFIG_DIR:-$HOME/.claude}/bin/dootdashaa" || \
     "${CLAUDE_PLUGIN_ROOT}/bin/dootdashaa-helper" ensure-symlinks
   ```

2. Read `~/.claude/settings.json` (or `{}` if missing).

3. If `.statusLine` is absent OR `.statusLine.command` equals
   `~/.claude/bin/dootdashaa`, write the dootdashaa entry. Otherwise back
   up the existing `.statusLine` to `.statusLine.previous` first, then
   write ours.

4. Write atomically via a temp file. The final JSON object must contain:

   ```json
   {
     "statusLine": {
       "type": "command",
       "command": "~/.claude/bin/dootdashaa",
       "padding": 0
     }
   }
   ```

5. Use `jq` to perform the merge — never hand-edit the file. Example:
   ```bash
   set -e
   cfg="${CLAUDE_CONFIG_DIR:-$HOME/.claude}/settings.json"
   tmp="$cfg.tmp.$$"
   [ -f "$cfg" ] || echo '{}' > "$cfg"
   jq '
     (.statusLine // null) as $cur |
     if ($cur == null) or ($cur.command == "~/.claude/bin/dootdashaa") then
       .statusLine = {type:"command", command:"~/.claude/bin/dootdashaa", padding:0}
     else
       .statusLine_previous = $cur |
       .statusLine = {type:"command", command:"~/.claude/bin/dootdashaa", padding:0}
     end
   ' "$cfg" > "$tmp" && mv -f "$tmp" "$cfg"
   ```

6. Tell the user the statusLine takes effect on the next `claude` session.
   Print a short success line so they can confirm.

## Optional environment variables (mention to the user)

| Var | Effect |
| --- | --- |
| `DOOTDASHAA_AWS_REPO=owner/repo` | Enables the AWS-credits segment when the active repo matches. Reads pre-rendered line from `$TMPDIR/dootdashaa/aws.line`. |
| `DOOTDASHAA_GAUGE_PCT=always` | Show the precise context percentage at all levels (not just ≥75%). |
| `NO_COLOR=1` | Disable ANSI colour entirely. |
