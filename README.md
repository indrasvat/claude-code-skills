# Claude Code Skills

A collection of personal Claude Code skills for automating terminal tasks, driving TUIs, and enhancing AI-assisted development workflows.

## 🎯 Overview

This repository contains production-ready skills for [Claude Code](https://claude.ai/code), designed to extend Claude's capabilities with specialized domain knowledge and automation patterns.

### Current Skills

#### 🖥️ **iterm2-driver**
Drive iTerm2 programmatically using Python scripts to automate terminal tasks, run tests, or manage sessions.

**Capabilities:**
- Create and orchestrate complex terminal layouts
- Drive interactive TUIs (vim, nano, htop, etc.)
- Automate REPL interactions (Python, Node, etc.)
- Monitor screen output in real-time
- Manage sessions and environment variables
- Visual status indicators with badges

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

## Installation

### Via Claude Code Plugin (Recommended)

In Claude Code, run:

```
/plugin install https://github.com/indrasvat/claude-code-skills
```

This installs all skills as a plugin. Skills are automatically available based on context.

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
│   └── plugin.json             # Plugin manifest (required)
├── skills/                      # All skills (at plugin root)
│   ├── iterm2-driver/
│   │   ├── SKILL.md            # Main skill file
│   │   └── examples/           # Runnable examples
│   ├── cf-edge/
│   │   └── SKILL.md
│   └── coderabbit/
│       └── SKILL.md
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
