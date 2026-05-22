---
description: Remove the dootdashaa statusLine from ~/.claude/settings.json
---

# /dootdashaa:uninstall

Reverses `/dootdashaa:install`. Removes the `statusLine` entry that points
at dootdashaa; if a `statusLine_previous` backup exists, restores it.

## Instructions

1. Read `~/.claude/settings.json`.

2. Perform the unwind atomically with `jq`:
   ```bash
   set -e
   cfg="$HOME/.claude/settings.json"
   tmp="$cfg.tmp.$$"
   jq '
     if (.statusLine.command // "") == "~/.claude/bin/dootdashaa" then
       if .statusLine_previous then
         .statusLine = .statusLine_previous | del(.statusLine_previous)
       else
         del(.statusLine)
       end
     else . end
   ' "$cfg" > "$tmp" && mv -f "$tmp" "$cfg"
   ```

3. Tell the user that the change takes effect on the next `claude` session,
   and that they can finish by running `/plugin uninstall dootdashaa` if
   they want to remove the plugin entirely. Dangling `~/.claude/bin/dootdashaa*`
   symlinks are harmless once the statusLine entry is gone.
