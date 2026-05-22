---
description: Register the launchd job that refreshes the AWS-credits segment every 5 minutes
---

# /dootdashaa:install-aws

Installs a `launchd` agent that runs `dootdashaa-refresh` at 300-second
intervals to keep the AWS-credits cache fresh. This is **optional** — the
statusline itself works fine without it; the AWS segment is opt-in via
`DOOTDASHAA_AWS_REPO=owner/repo` and reads a pre-rendered ANSI fragment
from `$TMPDIR/dootdashaa/aws.line`.

## Prerequisites

The user must set two things:

1. `DOOTDASHAA_AWS_REPO=owner/repo` in their shell rc, so the hot path
   knows when to render the segment.
2. `DOOTDASHAA_AWS_CMD="…"` pointing at a script/binary that prints the
   pre-coloured one-line ANSI fragment for the segment (e.g. an internal
   AWS-credits CLI with a `--line` flag). Without this, the refresher
   exits early and the segment stays empty.

## Instructions

1. Build the launchd plist contents:

   ```bash
   plist="$HOME/Library/LaunchAgents/com.indrasvat.dootdashaa.plist"
   bin="$HOME/.claude/bin/dootdashaa-refresh"

   cat > "$plist" <<EOF
   <?xml version="1.0" encoding="UTF-8"?>
   <!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
   <plist version="1.0">
   <dict>
     <key>Label</key><string>com.indrasvat.dootdashaa</string>
     <key>ProgramArguments</key>
     <array>
       <string>$bin</string>
     </array>
     <key>StartInterval</key><integer>300</integer>
     <key>RunAtLoad</key><true/>
     <key>EnvironmentVariables</key>
     <dict>
       <key>PATH</key><string>/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin</string>
     </dict>
   </dict>
   </plist>
   EOF
   ```

2. Load it:

   ```bash
   launchctl unload "$plist" 2>/dev/null
   launchctl load -w "$plist"
   ```

3. Confirm it is registered:

   ```bash
   launchctl list | grep com.indrasvat.dootdashaa
   ```

4. Tell the user the agent will tick every 300s; remind them to set
   `DOOTDASHAA_AWS_CMD` if they have not already. Removal is
   `launchctl unload "$plist" && rm "$plist"`.
