# dootdashaa

Glanceable Claude Code statusline.

- One line, no duplicate signals — each fact has exactly one carrier
  (icon, text, or colour; never two).
- Zero emoji. Nerd Font PUA glyphs + plain geometric Unicode only.
- Single `jq` call + 5-second git mtime cache; debounce-friendly.
- Optional per-repo AWS-credits segment, opt-in via env var.

## Install

```text
> /plugin marketplace add indrasvat/claude-code-skills    # once per machine
> /plugin install dootdashaa@indrasvat-skills             # pulls plugin, runs SessionStart hook
> /dootdashaa:install                                     # wires ~/.claude/settings.json statusLine
```

Restart your `claude` session — the new statusline appears immediately.

## What it shows

```
Opus  kartaa main•↑3   222    45/s  $0.42  5h31%·2h14
└┬─┘  └──┬─┘ └─┬─┘ └┬─┘ └┬─┘ └─┬┘ └──┬─┘ └────┬────┘
 │       │     │    │    │     │    │        │
 │       │     │    │    │     │    │        └─ 5h rate-limit window + reset countdown
 │       │     │    │    │     │    └─ session cost (hidden when $0)
 │       │     │    │    │     └─ token rate (output/s, smoothed over 5 samples)
 │       │     │    │    └─ context-window battery icon (precise % only ≥75%)
 │       │     │    └─ PR number, colour = state (approved/changes_req/pending/draft)
 │       │     └─ branch name, dirty marker, ahead/behind
 │       └─ repo name (bold)
 └─ model + effort suffix (·hi, ·xh, ·mx, ·lo); medium is hidden
```

Hide-steady-state is the rule: $0 cost, clean+synced git, medium effort,
7-day usage <20%, and the AWS segment are all invisible unless they deviate.

## Optional environment variables

| Variable | Effect |
| --- | --- |
| `DOOTDASHAA_AWS_REPO=owner/repo` | Append the AWS-credits segment when the active repo matches. Reads `$TMPDIR/dootdashaa/aws.line`. |
| `DOOTDASHAA_AWS_CMD="…"` | Command the refresher runs to regenerate that line (any script that prints a pre-coloured ANSI fragment). |
| `DOOTDASHAA_GAUGE_PCT=always` | Always show the context %, not only ≥75%. |
| `NO_COLOR=1` | Disable ANSI colour entirely. |

## Optional AWS-segment refresher

After `/dootdashaa:install`, you can register a `launchd` job that ticks
every 300 seconds to update the AWS-credits cache:

```text
> /dootdashaa:install-aws
```

This is only useful if you set both `DOOTDASHAA_AWS_REPO` and
`DOOTDASHAA_AWS_CMD` — without them, the refresher exits early.

## Uninstall

```text
> /dootdashaa:uninstall                # remove statusLine entry, restore any prior one
> /plugin uninstall dootdashaa         # remove the plugin itself
```

## Requirements

- macOS (Apple Silicon or Intel)
- `bash` 3.2+ (the macOS default works)
- `jq` 1.6+ (`brew install jq`)
- A Nerd-Font-patched terminal font for the icon glyphs (JetBrainsMono NF,
  Symbols Only NF, or any other patched font)

If iTerm2's *Use Non-ASCII Font* is checked and the secondary font is not
a Nerd Font, all icons render as tofu. Either uncheck it or set the
secondary font to a NF.

## Design

Source-of-truth design report (architecture, perf budget, bulletproof
matrix, glyph alphabet) is checked in at
[`docs/DESIGN.html`](docs/DESIGN.html). Open it locally in a browser for
the full mockups, conditional-display rules, and verification spike
walkthrough.
