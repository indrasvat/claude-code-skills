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

#### 🤖 **coderabbit**
Local AI code reviews via CodeRabbit CLI. Use sparingly—rate-limited to 1 review/hour.

**Capabilities:**
- AI-powered code reviews for security-sensitive changes
- Detection of concurrency issues and race conditions
- Memory leak and resource cleanup analysis
- Complex business logic validation
- Background execution with monitoring
- Prioritized findings (critical > major > minor)

## 🚀 Quick Start

### One-Command Installation (Recommended)

Install skills with a single command:

```bash
bash <(curl -fsSL https://raw.githubusercontent.com/indrasvat/claude-code-skills/main/bootstrap.sh)
```

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

# Combine options
INSTALL_DIR=~/my-skills BRANCH=develop bash <(curl -fsSL https://raw.githubusercontent.com/indrasvat/claude-code-skills/main/bootstrap.sh)
```

**Private repositories:** The bootstrap script automatically detects if you have SSH keys configured and uses SSH for authentication. Otherwise, it falls back to HTTPS (which will prompt for credentials).

**Security note:** Review the bootstrap script before running:
```bash
curl -fsSL https://raw.githubusercontent.com/indrasvat/claude-code-skills/main/bootstrap.sh | less
```

### Manual Installation (Alternative)

If you prefer to clone the repository yourself:

```bash
git clone https://github.com/indrasvat/claude-code-skills.git
cd claude-code-skills
./bin/cc-skills install
```

### Updating

After installation via bootstrap:

```bash
cc-skills update  # Pulls latest changes and reinstalls
```

Or manually:

```bash
cd ~/.config/claude-code-skills  # or wherever you installed
git pull
./bin/cc-skills install
```

The CLI tool handles everything automatically - backups, symlinks, and verification.

## 🛠️ CLI Tool: `cc-skills`

A bulletproof, forgiving CLI to manage your skills installation.

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

- ✅ **Automatic backups** before any destructive operation
- ✅ **Graceful handling** of symlinks, directories, and conflicts
- ✅ **Clear status reporting** with colored output
- ✅ **Safe by default** - never deletes without confirmation
- ✅ **Works anywhere** - just point to the repo

### Adding to PATH (Optional)

For convenience, add the `bin/` directory to your PATH:

```bash
# Add to ~/.zshrc or ~/.bashrc
export PATH="${PATH}:/path/to/claude-code-skills/bin"
```

Then you can run `cc-skills` from anywhere.

## 📋 How It Works

### Symlink-Based Installation

Skills are installed as symlinks from `~/.claude/skills/` to the repository:

```
~/.claude/skills/iterm2-driver -> /path/to/claude-code-skills/skills/iterm2-driver
```

**Benefits:**
- ✅ Skills auto-update with `git pull`
- ✅ Version controlled
- ✅ Single source of truth
- ✅ Easy to manage across machines

### Discovery by Claude Code

Claude Code automatically discovers skills from:
1. **Personal skills**: `~/.claude/skills/`
2. **Project skills**: `.claude/skills/`
3. **Plugin skills**: Bundled with installed plugins

Skills are loaded on-demand when relevant to the user's request.

## 📦 Repository Structure

```
claude-code-skills/
├── README.md                    # This file
├── LICENSE                      # MIT License
├── bin/
│   └── cc-skills               # CLI management tool
├── skills/                      # All skills
│   └── iterm2-driver/
│       ├── SKILL.md            # Main skill file
│       └── examples/           # Runnable examples
│           ├── 01-basic-tab.py
│           ├── 02-dev-layout.py
│           └── ...
├── docs/                        # Documentation
│   ├── skill-authoring.md      # How to create skills
│   ├── best-practices.md       # Conventions
│   └── troubleshooting.md      # Common issues
└── .github/
    └── workflows/
        └── validate.yml         # CI validation
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

3. **Install the skill**:
   ```bash
   ./bin/cc-skills install
   ```

4. **Test in Claude Code**

### Best Practices

- Keep `SKILL.md` under 500 lines for optimal performance
- Use progressive disclosure (separate files for examples, reference)
- Include concrete examples demonstrating key patterns
- Use inline dependency management for scripts (uv metadata)
- Follow the [Claude Code skill specification](https://docs.anthropic.com/en/docs/build-with-claude/agent-skills)

## 🔧 Troubleshooting

### Skills Not Showing Up

1. **Check installation**:
   ```bash
   cc-skills status
   ```

2. **Verify symlinks**:
   ```bash
   ls -la ~/.claude/skills/
   ```

3. **Restart Claude Code**

### Symlink Issues

If you see warnings about existing directories:

```bash
# Backup current installation
cc-skills backup

# Remove old installation
rm -rf ~/.claude/skills/iterm2-driver

# Reinstall
cc-skills install
```

### Permission Errors

```bash
# Ensure script is executable
chmod +x bin/cc-skills

# Ensure you have write access
ls -la ~/.claude/skills/
```

See [docs/troubleshooting.md](docs/troubleshooting.md) for more solutions.

## 🌍 Multi-Machine Setup

### All Machines

Same one-command installation everywhere:

```bash
bash <(curl -fsSL https://raw.githubusercontent.com/indrasvat/claude-code-skills/main/bootstrap.sh)
```

Skills stay in sync across machines:
- All machines pull from same repository
- `cc-skills update` keeps everyone current
- Consistent `~/.config/claude-code-skills` location

### Manual Sync Alternative

If you prefer manual control:

```bash
# Machine 1: Make changes
cd ~/.config/claude-code-skills
git add skills/new-skill
git commit -m "feat: add new skill"
git push

# Machine 2: Update
cd ~/.config/claude-code-skills
git pull
cc-skills install
```

## 🔄 Update Workflow

```bash
cd claude-code-skills
git pull                  # Get latest changes
cc-skills update          # Reinstall (automatic backup)
```

Or use the shorthand:

```bash
cc-skills update          # Does both git pull + reinstall
```

## 🤝 Contributing

This is a personal skills collection, but you're welcome to:
- Fork and create your own collection
- Open issues for bugs or suggestions
- Submit PRs for improvements to existing skills

## 📄 License

MIT License - see [LICENSE](LICENSE) for details.

## 🔗 Resources

- [Claude Code Documentation](https://code.claude.com/docs/en/skills)
- [Agent Skills Overview](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/overview)
- [Agent Skills Best Practices](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices)
- [Anthropic's Official Skills](https://github.com/anthropics/skills)

## 🙏 Acknowledgments

Built using the Claude Code Agent Skills framework by Anthropic.

---

**Made with ❤️ for AI-enhanced development workflows**
