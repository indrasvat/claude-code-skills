# Troubleshooting

Common issues and solutions for Claude Code skills installation and usage.

## Installation Issues

### Skills Not Being Detected

**Symptoms**: Claude doesn't use your skills even though they're installed.

**Solutions**:

1. **Verify installation**:
   ```bash
   cc-skills status
   ```
   Should show skills with "✓ symlinked to repository"

2. **Check symlinks**:
   ```bash
   ls -la ~/.claude/skills/
   ```
   Should show symlinks (indicated by `@` and `->`)

3. **Restart Claude Code**:
   Skills are loaded at startup. Restart Claude Code to pick up new skills.

4. **Verify SKILL.md exists**:
   ```bash
   cat ~/.claude/skills/iterm2-driver/SKILL.md | head -10
   ```
   Should show YAML frontmatter

5. **Check frontmatter format**:
   ```bash
   head -5 ~/.claude/skills/iterm2-driver/SKILL.md
   ```
   Should be:
   ```yaml
   ---
   name: skill-name
   description: Description here
   ---
   ```

### Symlink Creation Failed

**Symptoms**: `cc-skills install` shows errors about symlink creation.

**Solutions**:

1. **Check permissions**:
   ```bash
   ls -la ~/.claude/
   ```
   You should own the `.claude` directory

2. **Fix permissions**:
   ```bash
   chmod 755 ~/.claude
   chmod 755 ~/.claude/skills
   ```

3. **Remove conflicting directory**:
   ```bash
   # Backup first
   cc-skills backup

   # Remove directory
   rm -rf ~/.claude/skills/skill-name

   # Reinstall
   cc-skills install
   ```

### Directory Exists (Not Symlink)

**Symptoms**: Status shows "⚠ directory (not symlink)"

**Solutions**:

The CLI handles this automatically:

```bash
cc-skills install
```

If you want to do it manually:

```bash
# Backup
cc-skills backup

# Remove directory
rm -rf ~/.claude/skills/iterm2-driver

# Reinstall
cc-skills install
```

## CLI Tool Issues

### Command Not Found

**Symptoms**: `cc-skills: command not found`

**Solutions**:

1. **Use full path**:
   ```bash
   ~/.config/claude-code-skills/bin/cc-skills status
   ```

2. **Check if installed via bootstrap**:
   ```bash
   ls -la ~/.config/claude-code-skills/bin/cc-skills
   ```

3. **Source your shell rc file**:
   ```bash
   source ~/.zshrc  # or ~/.bashrc
   ```

4. **Add to PATH manually** (if bootstrap didn't):
   ```bash
   # Add to ~/.zshrc or ~/.bashrc
   export PATH="${PATH}:~/.config/claude-code-skills/bin"

   # Reload shell
   source ~/.zshrc
   ```

5. **Reinstall via bootstrap**:
   ```bash
   bash <(curl -fsSL https://raw.githubusercontent.com/indrasvat/claude-code-skills/main/bootstrap.sh)
   ```

### Permission Denied

**Symptoms**: `Permission denied` when running cc-skills

**Solutions**:

```bash
chmod +x bin/cc-skills
```

### Git Pull Fails During Update

**Symptoms**: `cc-skills update` fails at git pull

**Solutions**:

1. **Check git status**:
   ```bash
   cd claude-code-skills
   git status
   ```

2. **Commit or stash changes**:
   ```bash
   git stash
   git pull
   git stash pop
   ```

3. **Or update manually**:
   ```bash
   cd claude-code-skills
   git pull
   cc-skills install
   ```

## Skill Usage Issues

### Skill Not Triggering

**Symptoms**: Claude doesn't seem to use your skill even when relevant.

**Solutions**:

1. **Check description relevance**:
   The `description` field must include keywords the user might mention.

   ❌ "A helpful tool"
   ✅ "Drive iTerm2 programmatically using Python scripts to automate terminal tasks"

2. **Be more explicit**:
   Try asking Claude directly:
   - "Use the iterm2-driver skill to create a layout"
   - "Can you create an iTerm2 layout with 4 panes?"

3. **Verify skill is loaded**:
   ```bash
   cc-skills status
   ```

4. **Check skill content**:
   ```bash
   cat ~/.claude/skills/iterm2-driver/SKILL.md | head -20
   ```

### Skill Examples Don't Work

**Symptoms**: Running example scripts fails.

**Solutions**:

1. **Check uv is installed**:
   ```bash
   uv --version
   ```

   If not installed:
   ```bash
   curl -LsSf https://astral.sh/uv/install.sh | sh
   ```

2. **Run with uv**:
   ```bash
   uv run script_name.py
   ```
   NOT `python script_name.py`

3. **Check Python version**:
   ```bash
   python3 --version
   ```
   Should be 3.13+

4. **Check script has metadata**:
   ```bash
   head -10 script_name.py
   ```
   Should show:
   ```python
   # /// script
   # requires-python = ">=3.13"
   # dependencies = [...]
   # ///
   ```

## macOS-Specific Issues

### iTerm2 Not Found

**Symptoms**: iterm2-driver skill fails with "iTerm2 not found"

**Solutions**:

1. **Install iTerm2**:
   ```bash
   brew install --cask iterm2
   ```

2. **Verify iTerm2 is running**:
   The skill requires iTerm2 to be running

3. **Enable Python API**:
   - Open iTerm2
   - Preferences → General → Magic
   - Enable "Python API"

### Python API Permission Denied

**Symptoms**: "Permission denied" when running iterm2 scripts

**Solutions**:

1. **Enable Python API** in iTerm2:
   - Preferences → General → Magic
   - Check "Enable Python API"

2. **Grant accessibility permissions**:
   - System Preferences → Privacy & Security → Accessibility
   - Add iTerm2 if not present

## Backup and Restore Issues

### Restore Shows No Backups

**Symptoms**: `cc-skills restore` shows no backups

**Solutions**:

1. **Check backup directory**:
   ```bash
   ls -la ~/.claude/skills-backup/
   ```

2. **Create backup manually**:
   ```bash
   cp -r ~/.claude/skills/skill-name ~/.claude/skills-backup/skill-name-$(date +%Y%m%d-%H%M%S)
   ```

### Too Many Backups

**Symptoms**: Backup directory is getting large

**Solutions**:

```bash
# List backups by date
ls -lt ~/.claude/skills-backup/

# Remove old backups (keep last 5)
cd ~/.claude/skills-backup
ls -t | tail -n +6 | xargs rm -rf
```

## Repository Issues

### Repository Out of Sync

**Symptoms**: Local changes conflict with remote

**Solutions**:

1. **Check status**:
   ```bash
   cd claude-code-skills
   git status
   ```

2. **Stash and pull**:
   ```bash
   git stash
   git pull
   git stash pop
   ```

3. **Reset to remote** (loses local changes):
   ```bash
   git fetch origin
   git reset --hard origin/main
   ```

### Accidental Changes

**Symptoms**: Modified files in repository by mistake

**Solutions**:

```bash
# Discard changes to specific file
git checkout -- file_path

# Discard all changes
git reset --hard

# Then reinstall
cc-skills install
```

## Multi-Machine Issues

### Different Versions on Different Machines

**Symptoms**: Skills work differently on different machines

**Solutions**:

1. **Sync repository**:
   ```bash
   # Machine 1
   cd claude-code-skills
   git pull

   # Machine 2
   cd claude-code-skills
   git pull
   ```

2. **Reinstall on both**:
   ```bash
   cc-skills update
   ```

3. **Check versions**:
   ```bash
   cd claude-code-skills
   git log -1
   ```

### Installation Paths Differ

**Symptoms**: Skills installed in different locations

**Solutions**:

Standardize using environment variables:

```bash
# Add to ~/.zshrc or ~/.bashrc
export CLAUDE_SKILLS_DIR="${HOME}/.claude/skills"
export CLAUDE_BACKUP_DIR="${HOME}/.claude/skills-backup"
```

Then reinstall:

```bash
cc-skills install
```

## Debugging

### Enable Verbose Output

Add debugging to CLI commands:

```bash
bash -x ./bin/cc-skills status
```

### Check Claude Code Logs

Claude Code may log skill loading issues:

```bash
# Location varies, check Claude Code documentation
tail -f ~/.claude/logs/*.log
```

### Validate YAML Frontmatter

```python
# /// script
# requires-python = ">=3.12"
# dependencies = ["pyyaml"]
# ///

import yaml

with open('skills/iterm2-driver/SKILL.md') as f:
    content = f.read()
    # Extract frontmatter
    if content.startswith('---'):
        end = content.find('---', 3)
        frontmatter = content[3:end]
        try:
            data = yaml.safe_load(frontmatter)
            print("Valid YAML:")
            print(data)
        except yaml.YAMLError as e:
            print("Invalid YAML:")
            print(e)
```

### Test Skill Manually

```python
# Read the skill file
with open('~/.claude/skills/iterm2-driver/SKILL.md') as f:
    content = f.read()
    print(f"Skill size: {len(content)} characters")
    print(f"Lines: {len(content.splitlines())}")

# Check frontmatter
lines = content.splitlines()
print(f"First 10 lines:")
print('\n'.join(lines[:10]))
```

## Getting Help

### Check Documentation

- [README](../README.md)
- [Skill Authoring Guide](skill-authoring.md)
- [Best Practices](best-practices.md)

### Official Resources

- [Claude Code Documentation](https://docs.anthropic.com/en/docs/build-with-claude/claude-code)
- [Agent Skills Spec](https://docs.anthropic.com/en/docs/build-with-claude/agent-skills)
- [Anthropic's Official Skills](https://github.com/anthropics/skills)

### Report Issues

If you find a bug:

1. Check existing issues on GitHub
2. Create a new issue with:
   - What you tried
   - What you expected
   - What actually happened
   - Output of `cc-skills status`
   - Relevant log files

### Common Diagnostic Commands

```bash
# System info
uname -a
python3 --version
uv --version

# Installation status
cc-skills status
ls -la ~/.claude/skills/

# Skill content
head -20 ~/.claude/skills/iterm2-driver/SKILL.md

# Git status
cd claude-code-skills && git status && git log -1

# Test CLI
./bin/cc-skills help
```

---

Still stuck? Open an issue on GitHub with the output of these diagnostic commands.
