#!/usr/bin/env bash
#
# Claude Code Skills - Bootstrap Installer
#
# One-command installation from GitHub:
#   bash <(curl -fsSL https://raw.githubusercontent.com/indrasvat/claude-code-skills/main/bootstrap.sh)
#
# Custom installation location:
#   INSTALL_DIR=~/my-skills bash <(curl -fsSL ...)
#
# Install from a specific branch:
#   BRANCH=develop bash <(curl -fsSL ...)
#
# Custom repository URL (auto-detects SSH vs HTTPS by default):
#   REPO_URL=https://github.com/yourname/your-fork.git bash <(curl -fsSL ...)
#   REPO_URL=git@github.com:yourname/your-fork.git bash <(curl -fsSL ...)
#
# Combined example:
#   INSTALL_DIR=~/my-skills BRANCH=develop bash <(curl -fsSL ...)
#
# For private repositories:
#   - SSH is automatically used if you have GitHub SSH keys configured
#   - Otherwise, HTTPS will prompt for credentials (use GitHub token as password)
#
# This script:
#   1. Clones the repository to ~/.config/claude-code-skills (or custom location)
#   2. Installs all skills to ~/.claude/skills/
#   3. Adds cc-skills to PATH automatically
#

set -eo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
INSTALL_DIR="${INSTALL_DIR:-${HOME}/.config/claude-code-skills}"
BRANCH="${BRANCH:-main}"

# Auto-detect best repository URL (SSH if available, HTTPS fallback)
if [ -z "${REPO_URL}" ]; then
    # Test SSH access to GitHub
    if ssh -T git@github.com -o StrictHostKeyChecking=accept-new -o ConnectTimeout=5 2>&1 | grep -q "successfully authenticated"; then
        REPO_URL="git@github.com:indrasvat/claude-code-skills.git"
    else
        REPO_URL="https://github.com/indrasvat/claude-code-skills.git"
    fi
fi

# Logging functions
log_info() {
    echo -e "${BLUE}ℹ${NC} $*"
}

log_success() {
    echo -e "${GREEN}✓${NC} $*"
}

log_warning() {
    echo -e "${YELLOW}⚠${NC} $*"
}

log_error() {
    echo -e "${RED}✗${NC} $*" >&2
}

# Main installation
echo ""
echo "════════════════════════════════════════════════════════"
echo "  🚀 Claude Code Skills - Bootstrap Installer"
echo "════════════════════════════════════════════════════════"
echo ""

# Show authentication method
if [[ "${REPO_URL}" == git@* ]]; then
    log_info "Repository: ${REPO_URL} (SSH)"
else
    log_info "Repository: ${REPO_URL} (HTTPS)"
fi

log_info "Install to: ${INSTALL_DIR}"
log_info "Branch: ${BRANCH}"
echo ""

# Check prerequisites
if ! command -v git &> /dev/null; then
    log_error "git is required but not installed"
    echo ""
    echo "Install git:"
    echo "  macOS: brew install git"
    echo "  Ubuntu/Debian: sudo apt install git"
    exit 1
fi

# Clone or update repository
if [ -d "${INSTALL_DIR}" ]; then
    log_info "Repository already exists, updating..."
    cd "${INSTALL_DIR}"

    # Check if it's actually a git repository
    if git -C "${INSTALL_DIR}" rev-parse --git-dir > /dev/null 2>&1; then
        git pull origin "${BRANCH}"
        log_success "Repository updated"
    else
        log_error "${INSTALL_DIR} exists but is not a git repository"
        log_info "Please remove or rename this directory and try again"
        exit 1
    fi
else
    log_info "Cloning repository..."

    # Create parent directory if needed
    mkdir -p "$(dirname "${INSTALL_DIR}")"

    if git clone --branch "${BRANCH}" "${REPO_URL}" "${INSTALL_DIR}"; then
        log_success "Repository cloned"
    else
        log_error "Failed to clone repository"
        exit 1
    fi
fi

echo ""
log_success "Repository ready at: ${INSTALL_DIR}"
echo ""

# Make cc-skills executable
chmod +x "${INSTALL_DIR}/bin/cc-skills"

# Run installation
log_info "Installing skills..."
cd "${INSTALL_DIR}"
if ./bin/cc-skills install; then
    echo ""
    log_success "Skills installed successfully!"
else
    log_error "Skill installation failed"
    exit 1
fi

echo ""

# Add to PATH
SHELL_RC=""
if [ -n "${ZSH_VERSION}" ]; then
    SHELL_RC="${HOME}/.zshrc"
elif [ -n "${BASH_VERSION}" ]; then
    if [ -f "${HOME}/.bashrc" ]; then
        SHELL_RC="${HOME}/.bashrc"
    elif [ -f "${HOME}/.bash_profile" ]; then
        SHELL_RC="${HOME}/.bash_profile"
    fi
fi

if [ -n "${SHELL_RC}" ]; then
    # Check if already in PATH
    if grep -q "claude-code-skills/bin" "${SHELL_RC}" 2>/dev/null; then
        log_info "Already in PATH (${SHELL_RC})"
    else
        log_info "Adding to PATH..."
        {
            echo ""
            echo "# Claude Code Skills CLI"
            echo "export PATH=\"\${PATH}:${INSTALL_DIR}/bin\""
        } >> "${SHELL_RC}"

        log_success "Added to PATH in ${SHELL_RC}"
        echo ""
        log_info "To use immediately, run:"
        echo "  source ${SHELL_RC}"
        echo ""
        log_info "Or open a new terminal window"
    fi
else
    log_warning "Could not detect shell configuration file"
    log_info "Add to PATH manually:"
    echo "  export PATH=\"\${PATH}:${INSTALL_DIR}/bin\""
fi

# Final success message
echo ""
echo "════════════════════════════════════════════════════════"
echo "  ✅ Installation Complete!"
echo "════════════════════════════════════════════════════════"
echo ""
log_success "Skills are now active in Claude Code!"
echo ""
echo "📚 Useful commands:"
echo ""
echo "  # Check installation status"
echo "  ${INSTALL_DIR}/bin/cc-skills status"
echo ""
echo "  # Or if you sourced your shell rc:"
echo "  cc-skills status"
echo ""
echo "  # Update skills in the future"
echo "  cc-skills update"
echo ""
echo "  # See all available commands"
echo "  cc-skills help"
echo ""
echo "  # View example scripts"
echo "  ls ${INSTALL_DIR}/skills/iterm2-driver/examples/"
echo ""
echo "  # Run an example"
echo "  cd ${INSTALL_DIR}/skills/iterm2-driver/examples"
echo "  uv run 01-basic-tab.py"
echo ""
echo "📖 Documentation: ${INSTALL_DIR}/README.md"
echo ""
