# Platform Support & Cloud Limitations

## Platform Support Matrix

| Environment | Supported? | Why |
|------------|-----------|-----|
| **macOS local** | YES | Native iTerm2 + Python API |
| **macOS CI** (GitHub Actions macOS runners) | PARTIAL | Has WindowServer, but iTerm2 must be installed + configured |
| **macOS cloud hosts** (MacStadium, AWS EC2 Mac, Hetzner) | YES | Full macOS with GUI — install iTerm2, enable API |
| **Linux containers** (Claude Code Web, Codex Web, Codespaces) | NO | iTerm2 is macOS-only |
| **Linux CI** (GitHub Actions ubuntu, etc.) | NO | No macOS, no WindowServer |
| **Remote macOS via SSH** | NO | No WindowServer access over SSH |
| **macOS VNC/remote desktop** | YES | WindowServer available through remote display |

## Why Linux/Cloud Is Not Supported

iTerm2 requires three macOS-only components:

1. **WindowServer** — macOS display server that manages windows, compositing, and Quartz graphics
2. **AppKit** — macOS application framework that iTerm2 is built on
3. **Unix domain socket** — at `~/Library/Application Support/iTerm2/private/socket` (macOS-specific path)

There is no way to run iTerm2 on Linux, even with compatibility layers. Wine/Darling do not support the required macOS frameworks.

## macOS Cloud Hosts (Viable Alternative)

If you need iTerm2 automation in a cloud/CI context, use a macOS cloud host:

### AWS EC2 Mac Instances

```bash
# After provisioning a mac1.metal or mac2.metal instance:
brew install --cask iterm2

# Enable Python API (requires GUI — use VNC or Apple Remote Desktop)
# Preferences > General > Magic > Enable Python API

# Install uv
curl -LsSf https://astral.sh/uv/install.sh | sh

# Run automation scripts
uv run your_test.py
```

### MacStadium / Hetzner Mac Mini

Similar setup — provision a Mac Mini in the cloud, install iTerm2, enable the API.

### GitHub Actions macOS Runners

```yaml
# .github/workflows/visual-test.yml
jobs:
  visual-test:
    runs-on: macos-14  # or macos-15
    steps:
      - uses: actions/checkout@v4
      - name: Install iTerm2
        run: brew install --cask iterm2
      - name: Enable Python API
        run: |
          # Write plist to enable Python API
          defaults write com.googlecode.iterm2 EnableAPIServer -bool true
      - name: Install uv
        run: curl -LsSf https://astral.sh/uv/install.sh | sh
      - name: Start iTerm2
        run: open -a iTerm
      - name: Wait for iTerm2
        run: sleep 3
      - name: Run visual tests
        run: uv run .claude/automations/visual_test.py
```

**Note:** GitHub Actions macOS runners do have a display (Quartz/WindowServer), so `screencapture` works. However, the environment is headless in the sense that no physical monitor is attached — windows render to an offscreen buffer. `screencapture -l` still captures correctly from this buffer.

## Terminal Automation Alternatives for Linux

If you need terminal automation in pure Linux environments, these are alternatives to iTerm2 (not covered by this skill):

| Tool | Approach | Screen Reading | Screenshots |
|------|----------|---------------|-------------|
| **tmux + libtmux** | Multiplexer with Python API | `pane.capture_pane()` | Text only (no pixels) |
| **GNU Screen** | Multiplexer with `-X` commands | `screen -X hardcopy` | Text only |
| **pexpect** | Process spawning + expect | Inline output capture | No |
| **pyte** | In-memory terminal emulator | Full ANSI parsing | No (but can render to text) |

None of these provide pixel-level screenshots like iTerm2 + Quartz. For visual regression testing on Linux, consider rendering terminal text to images using Rich Console SVG export or similar tools.

## Known iTerm2 Limitations

### Multiple Instances

macOS allows running multiple iTerm2 instances via `open -n /Applications/iTerm.app`, and iTerm2 supports this with an undocumented `-suite` flag. However:

- **Python API socket is singular** — only one instance owns the socket at `~/Library/Application Support/iTerm2/private/socket`
- The last instance to start overwrites the socket (calls `unlink()` before `bind()`)
- The Python client has no mechanism to select which instance to connect to
- **Recommendation:** Use one instance with multiple windows

### API Version Compatibility

The iTerm2 Python library must match the iTerm2 app version. If you update iTerm2 but not the library (or vice versa), connections may fail silently. Always use the latest `iterm2` pip package with the latest iTerm2 app.

### WebSocket Stability

Long-lived WebSocket connections can drop with code 1006 after extended operation (hours). Use `retry=True` in `run_until_complete()` or implement reconnection logic for long-running daemons.
