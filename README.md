# Claude Code Skills

A marketplace of personal [Claude Code](https://claude.ai/code) plugins: 15 skills for AI-assisted dev workflows, plus `dootdashaa`, a glanceable statusline.

## 🎯 Overview

This repository is a Claude Code marketplace exposing two independently-installable plugins:

| Plugin | Install command | What it adds |
|---|---|---|
| **indrasvat-skills** | `/plugin install indrasvat-skills@indrasvat-skills` | 15 skills (CI gating, exec plans, PR shipping, K8s diffing, PRD generation, iTerm2 automation, browsing-as-you, …) |
| **dootdashaa** | `/plugin install dootdashaa@indrasvat-skills` | Single-line, Nerd-Font-icon statusline. `~9ms` p50 render budget. |

Both share one `/plugin marketplace add` step (see [Installation](#installation)). Each can be installed, updated, and uninstalled on its own.

### dootdashaa — statusline

Glanceable, single-line. One carrier per signal (icon, text, or colour — never two). Zero emoji. Pre-computed git cache keeps the hot path under the 300ms Claude Code debounce. See [`plugins/dootdashaa/README.md`](plugins/dootdashaa/README.md) for env-var options and the install / uninstall command list; design report is at [`plugins/dootdashaa/docs/DESIGN.html`](plugins/dootdashaa/docs/DESIGN.html).

### Skills (15 total)

#### Universal Dev Workflow (5 new)

| Skill | Command | Description |
|-------|---------|-------------|
| **ci-gate** | `/ci-gate` | Run all CI checks locally before pushing (Go, JS/TS, Rust, Python). `--fix` to auto-fix. |
| **exec-plan** | `/exec-plan` | Create self-contained execution plans any agent can follow end-to-end. |
| **ship-pr** | `/ship-pr` | Create PRs with a standards compliance review gate. Blocks on CLAUDE.md violations. |
| **deslop** | `/deslop` | Clean AI-generated slop — dead comments, unused code, redundant logic. |
| **triage-pr** | `/triage-pr` | Fetch, categorize, and address PR review comments by priority (BLOCKER > QUESTION > SUGGESTION > NITPICK). |

#### Go / Kubernetes (5 new)

| Skill | Command | Description |
|-------|---------|-------------|
| **k8s-diff** | `/k8s-diff` | Diff Helm/Kustomize/raw YAML against live cluster, flag risky changes. |
| **migration-guard** | `/migration-guard` | Analyze DB migrations for lock risk, backward compat, rollback safety. |
| **api-compat** | `/api-compat` | Detect breaking changes in protobuf, OpenAPI, GraphQL, or Go exported APIs. |
| **rollout-check** | `/rollout-check` | Verify K8s deployment health — pods, events, HPA, logs. |
| **crd-impact** | `/crd-impact` | Find all controllers, webhooks, RBAC, and manifests affected by a CRD change. |

#### Original Skills (4)

#### 📋 **prd-generator**
Generate comprehensive Product Requirements Documents with interactive discovery, progress tracking, and True Ralph Loop support for autonomous implementation.

**Capabilities:**
- Interactive discovery with 12+ adaptive questions
- Generates `docs/PRD.md` with checkboxes and phased tasks
- Creates `docs/PROGRESS.md` for context recovery across sessions
- **True Ralph Loop**: Fresh Claude sessions for each iteration (no context rot)
- Supports both external script and tmux modes for autonomous implementation
- Smart context recovery after crashes or compaction

**Key Insight:** Unlike Anthropic's Ralph plugin (same-session Stop hook), True Ralph spawns fresh Claude sessions, preventing context pollution.

**Slash Commands:**
- `/prd` - Generate a new PRD with interactive discovery
- `/prd-status` - Check implementation progress
- `/prd-ralph` - Start True Ralph Loop (autonomous implementation)
- `/prd-resume` - Recover context after crash/new session

[View Templates →](skills/prd-generator/templates/)

#### 🖥️ **iterm2-driver**
Drive iTerm2 programmatically using Python scripts to automate terminal tasks, run visual tests, or manage sessions. Includes parallel agent support for concurrent testing.

**Capabilities:**
- Create and orchestrate complex terminal layouts (splits, tabs, windows)
- Drive interactive TUIs (vim, nano, htop, BubbleTea, etc.)
- Run multiple agents concurrently with independent windows and screenshots
- Automate REPL interactions (Python, Node, etc.)
- Monitor screen output in real-time with ScreenStreamer
- Connection diagnostics for troubleshooting silent failures
- Visual regression testing for CLI/TUI applications (L4 testing)

**Platform:** macOS only (see [cloud limitations](skills/iterm2-driver/references/cloud-and-limitations.md))

[View Examples →](skills/iterm2-driver/examples/)

#### ☁️ **cf-edge**
Deploy web apps, APIs, static sites, and edge functions to Cloudflare's free tier using wrangler and cloudflared CLIs.

**Capabilities:**
- Host static sites and SPAs on Pages (unlimited bandwidth)
- Create serverless APIs with Workers (100K req/day)
- SQL databases with D1 (5GB storage, 5M reads/day)
- Key-value storage with KV and object storage with R2
- Expose localhost via Cloudflare Tunnels
- AI inference with Workers AI (10K neurons/day)
- All deployments stay within $0 free tier limits

#### 🤖 **coderabbit**
Local AI code reviews via CodeRabbit CLI. Use sparingly—rate-limited to 1 review/hour.

**Capabilities:**
- AI-powered code reviews for security-sensitive changes
- Detection of concurrency issues and race conditions
- Memory leak and resource cleanup analysis
- Complex business logic validation
- Background execution with monitoring
- Prioritized findings (critical > major > minor)

#### Browser Automation (1 new)

#### 🌐 **browsing-as-you**
One persistent, already-authenticated Chrome that every agent and sub-agent attaches to over the DevTools Protocol — no per-task browser launches, no re-login, and no repeated macOS "Allow" prompts. The window launches in the background (`open -g`) and never steals focus.

**Capabilities:**
- `chrome-agent.sh` control plane: idempotent/concurrent-safe `start`, plus `status`/`health`/`doctor`/`recover` with stable exit codes (0 ok · 3 down · 4 wedged)
- `cdp.py` driver: open background tabs, navigate, eval JS, screenshot, browser contexts — all safe for parallel agents via owned `targetId`s and `--strict`
- **Trusted input** (`click`/`type`/`key` via the CDP Input domain) that drives react-select/combobox/checkbox widgets which ignore synthetic events — and refuses CAPTCHA/Turnstile targets (human-only step)
- **`probe`**: DOM-based auth check (`login-wall \| likely-authed \| unknown`) so a cookie-only `seed` that silently lands on a sign-in screen (Cloudflare and other localStorage/SSO SPAs) is caught, instead of trusting an unreliable URL heuristic
- **`seed`**: import your existing Chrome logins by decrypting a profile's cookies (macOS keychain → PBKDF2 → AES-128-CBC) and injecting them over CDP — act as you on sites you're already signed into, no re-login
- One-time `login` flow for DBSC (Google/YouTube) and localStorage-token apps that cookies alone can't carry — durable across restarts and reboots
- `--front` to foreground visibility-gated SPAs (e.g. the Cloudflare dashboard), and `autostart on|off|status`: a self-pathing launchd LaunchAgent for hands-free start at login
- Dedicated profile (your everyday Chrome is never touched); real keychain by default so logins persist, with `CHROME_AGENT_MOCK_KEYCHAIN=1` for a prompt-free seed-only mode

**Platform:** macOS (Linux supported except `seed`, which needs `login`). Needs `uv`; chrome-devtools-mcp integration needs Node 22+.

## Installation

### Via Claude Code Plugin (Recommended)

Inside a `claude` session, register the marketplace once and install whichever plugins you want:

```
/plugin marketplace add indrasvat/claude-code-skills    # once per machine

# 15 skills (CI gating, exec plans, PR shipping, K8s diffing, PRD generation, browsing-as-you, ...)
/plugin install indrasvat-skills@indrasvat-skills

# Statusline
/plugin install dootdashaa@indrasvat-skills
/dootdashaa:install                                     # wires ~/.claude/settings.json statusLine
```

The first command adds the repository as a plugin marketplace. Each `/plugin install` line picks one of the two plugins exposed by that marketplace. `/dootdashaa:install` is the one-time idempotent step that edits `~/.claude/settings.json` to point at the statusline binary; it backs up any existing `statusLine` entry so `/dootdashaa:uninstall` can restore it.

Skills from `indrasvat-skills` are available based on context. The dootdashaa statusline appears on the next session restart.

### For Development

Test the plugin locally without installing:

```bash
claude --plugin-dir /path/to/claude-code-skills
```

### Via Bootstrap Script (Alternative)

For traditional symlink-based installation to `~/.claude/skills/`:

```bash
bash <(curl -fsSL https://raw.githubusercontent.com/indrasvat/claude-code-skills/main/bootstrap.sh)
```

<details>
<summary>Bootstrap options and details</summary>

This will:
- Clone the repository to `~/.config/claude-code-skills`
- Install all skills to `~/.claude/skills/`
- Add `cc-skills` to your PATH automatically
- Set up automatic updates via git

**Custom options:**

```bash
# Custom installation location
INSTALL_DIR=~/my-skills bash <(curl -fsSL https://raw.githubusercontent.com/indrasvat/claude-code-skills/main/bootstrap.sh)

# Install from a specific branch
BRANCH=develop bash <(curl -fsSL https://raw.githubusercontent.com/indrasvat/claude-code-skills/main/bootstrap.sh)

# Install from your fork
REPO_URL=https://github.com/yourname/your-fork.git bash <(curl -fsSL https://raw.githubusercontent.com/indrasvat/claude-code-skills/main/bootstrap.sh)
```

**Private repositories:** The bootstrap script automatically detects if you have SSH keys configured and uses SSH for authentication.

**Security note:** Review the bootstrap script before running:
```bash
curl -fsSL https://raw.githubusercontent.com/indrasvat/claude-code-skills/main/bootstrap.sh | less
```

</details>

### Updating

**Plugin users:** Plugins update automatically when you reinstall or update Claude Code plugins.

**Bootstrap users:**
```bash
cc-skills update  # Pulls latest changes and reinstalls
```

## 📋 How It Works

### Plugin Installation (Recommended)

When installed as a plugin via `/plugin install`, Claude Code:
1. Clones the repository to its plugin directory
2. Automatically discovers all skills in the `skills/` folder
3. Makes skills available based on context (model-invoked)

Skills are loaded on-demand when relevant to your request.

### Discovery by Claude Code

Claude Code discovers skills from multiple sources:
1. **Plugin skills**: Installed via `/plugin install` (recommended)
2. **Personal skills**: `~/.claude/skills/`
3. **Project skills**: `.claude/skills/`

<details>
<summary>CLI Tool: cc-skills (for bootstrap users)</summary>

A CLI to manage symlink-based installation.

### Commands

```bash
cc-skills install      # Install skills from repository
cc-skills update       # Update skills (git pull + reinstall)
cc-skills uninstall    # Remove symlinks (keeps backups)
cc-skills restore      # Restore from backup
cc-skills status       # Show installation status
cc-skills list         # List available skills
cc-skills backup       # Create backup of current skills
cc-skills help         # Show help message
```

### Features

- Automatic backups before destructive operations
- Graceful handling of symlinks and conflicts
- Clear status reporting with colored output

### Adding to PATH

```bash
# Add to ~/.zshrc or ~/.bashrc
export PATH="${PATH}:/path/to/claude-code-skills/bin"
```

</details>

## 📦 Repository Structure

```
claude-code-skills/
├── .claude-plugin/
│   ├── plugin.json             # 'indrasvat-skills' plugin manifest
│   └── marketplace.json        # marketplace exposing both plugins
├── commands/                    # Slash commands for 'indrasvat-skills'
│   ├── prd.md                  # /prd - Generate PRD
│   ├── prd-status.md           # /prd-status - Check progress
│   ├── prd-ralph.md            # /prd-ralph - Start True Ralph Loop
│   └── prd-resume.md           # /prd-resume - Recover context
├── plugins/
│   └── dootdashaa/              # Statusline plugin (independent install)
│       ├── .claude-plugin/plugin.json
│       ├── bin/{dootdashaa,dootdashaa-refresh,dootdashaa-helper}
│       ├── hooks/hooks.json     # SessionStart → ensure-symlinks
│       ├── commands/            # /dootdashaa:{install,uninstall,install-aws}
│       └── README.md
├── skills/                      # All skills (model-invoked)
│   ├── ci-gate/SKILL.md        # Local CI checks
│   ├── exec-plan/              # Execution planning
│   │   ├── SKILL.md
│   │   └── references/template.md
│   ├── ship-pr/                # PR creation with standards gate
│   │   ├── SKILL.md
│   │   └── references/templates.md
│   ├── deslop/SKILL.md         # AI slop cleanup
│   ├── triage-pr/SKILL.md      # PR review triage
│   ├── k8s-diff/SKILL.md       # K8s manifest diffing
│   ├── migration-guard/SKILL.md # DB migration safety
│   ├── api-compat/SKILL.md     # API breaking change detection
│   ├── rollout-check/SKILL.md  # K8s deployment health
│   ├── crd-impact/SKILL.md     # CRD change impact analysis
│   ├── prd-generator/          # PRD generation
│   │   ├── SKILL.md
│   │   ├── scripts/
│   │   └── templates/
│   ├── iterm2-driver/          # iTerm2 automation
│   │   ├── SKILL.md
│   │   └── examples/
│   ├── cf-edge/SKILL.md        # Cloudflare deployment
│   ├── coderabbit/SKILL.md     # AI code reviews
│   └── browsing-as-you/          # Shared authenticated Chrome over CDP
│       ├── SKILL.md
│       ├── scripts/{chrome-agent.sh,cdp.py}
│       └── reference/{integration.md,launchd.md}
├── README.md
├── LICENSE                      # MIT License
├── bin/
│   └── cc-skills               # CLI tool (for bootstrap users)
├── bootstrap.sh                 # One-line installer (alternative)
├── docs/                        # Documentation
│   ├── skill-authoring.md
│   ├── best-practices.md
│   └── troubleshooting.md
└── .github/
    └── workflows/
        └── lint.yml             # CI validation
```

## 🎓 Using Skills

Once installed, skills are automatically invoked by Claude when relevant. You don't need to explicitly call them.

### Example Workflow

```
You: "Create a 4-pane development layout in iTerm2 with server, worker, database, and logs"

Claude: [Uses iterm2-driver skill to generate and execute the appropriate script]
```

### Running Examples Manually

All skills include standalone example scripts you can run directly:

```bash
cd skills/iterm2-driver/examples
uv run 01-basic-tab.py
uv run 02-dev-layout.py
```

These serve as:
- 📖 Learning resources
- 🔧 Testing templates
- 📋 Copy-paste starting points

## ✍️ Creating New Skills

See [docs/skill-authoring.md](docs/skill-authoring.md) for a comprehensive guide to creating skills.

### Quick Guide

1. **Create skill directory**:
   ```bash
   mkdir -p skills/my-new-skill
   ```

2. **Create `SKILL.md` with frontmatter**:
   ```yaml
   ---
   name: my-new-skill
   description: What it does and when to use it.
   ---

   # Skill content here...
   ```

3. **Test in Claude Code**:
   ```bash
   claude --plugin-dir /path/to/claude-code-skills
   ```

### Best Practices

- Keep `SKILL.md` under 500 lines for optimal performance
- Use progressive disclosure (separate files for examples, reference)
- Include concrete examples demonstrating key patterns
- Use inline dependency management for scripts (uv metadata)
- Follow the [Claude Code skill specification](https://docs.anthropic.com/en/docs/build-with-claude/agent-skills)

## 🔧 Troubleshooting

### Skills Not Showing Up

1. **Check plugin is installed**: Run `/plugin list` in Claude Code
2. **Restart Claude Code** after installing

### Plugin Issues

Try reinstalling the plugin:
```
/plugin uninstall indrasvat-skills
/plugin install https://github.com/indrasvat/claude-code-skills
```

<details>
<summary>Bootstrap installation troubleshooting</summary>

### Skills Not Showing Up (Bootstrap)

1. **Check installation**:
   ```bash
   cc-skills status
   ```

2. **Verify symlinks**:
   ```bash
   ls -la ~/.claude/skills/
   ```

### Symlink Issues

```bash
cc-skills backup
rm -rf ~/.claude/skills/iterm2-driver
cc-skills install
```

### Permission Errors

```bash
chmod +x bin/cc-skills
ls -la ~/.claude/skills/
```

</details>

See [docs/troubleshooting.md](docs/troubleshooting.md) for more solutions.

## 🌍 Multi-Machine Setup

Install the plugin on each machine:

```
/plugin install https://github.com/indrasvat/claude-code-skills
```

Skills stay in sync across machines through the plugin system.

## 🤝 Contributing

This is a personal skills collection, but you're welcome to:
- Fork and create your own collection
- Open issues for bugs or suggestions
- Submit PRs for improvements to existing skills

## 📄 License

MIT License - see [LICENSE](LICENSE) for details.

## 🔗 Resources

- [Claude Code Plugins](https://code.claude.com/docs/en/plugins)
- [Claude Code Skills](https://code.claude.com/docs/en/skills)
- [Anthropic's Official Skills](https://github.com/anthropics/skills)

## 🙏 Acknowledgments

Built using the Claude Code Agent Skills framework by Anthropic.

---

**Made with ❤️ for AI-enhanced development workflows**
