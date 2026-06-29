# claude-code-skills — developer tasks.
# Run `make` or `make help` to see available targets.

SHELL := bash
.DEFAULT_GOAL := help
.PHONY: help validate validate-skills lint list clean check ci test-browsing

# --- Colors (disabled when not a TTY, e.g. in CI logs) ----------------------
ifneq (,$(findstring xterm,$(TERM))$(findstring color,$(TERM)))
  CYAN  := \033[36m
  BOLD  := \033[1m
  DIM   := \033[2m
  RESET := \033[0m
else
  CYAN  :=
  BOLD  :=
  DIM   :=
  RESET :=
endif

SHELLCHECK ?= shellcheck
# Match the CI shellcheck job (ludeeus/action-shellcheck severity: warning).
SHELLCHECK_SEVERITY ?= warning

help: ## Show this help
	@printf "$(BOLD)claude-code-skills$(RESET) $(DIM)— make targets$(RESET)\n\n"
	@grep -hE '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) \
		| sort \
		| awk 'BEGIN{FS=":.*?## "}{printf "  $(CYAN)%-16s$(RESET) %s\n", $$1, $$2}'
	@printf "\n"

check: lint validate test-browsing ## Run everything CI runs (lint + validate + tests)
ci: check ## Alias for `check`

validate: validate-skills ## Run all validation

test-browsing: ## Run offline tests for the browsing-as-you gh-attach helper
	@python3 skills/browsing-as-you/scripts/test_gh_attach.py

validate-skills: ## Validate every SKILL.md frontmatter (YAML parse + skills CLI cross-check)
	@bash scripts/validate-skills.sh

lint: ## Run shellcheck on every tracked shell script
	@command -v $(SHELLCHECK) >/dev/null 2>&1 || { \
		printf "$(BOLD)shellcheck not installed$(RESET) — brew install shellcheck\n" >&2; exit 1; }
	@if git rev-parse --git-dir >/dev/null 2>&1; then list=$$(git ls-files); \
	else list=$$(find . -type f -not -path './.git/*' -not -path './node_modules/*' -not -path './.local/*'); fi; \
	files=$$(for f in $$list; do head -1 "$$f" 2>/dev/null | grep -qE '^#!.*(bash|sh)' && printf '%s\n' "$$f"; done); \
	if [ -z "$$files" ]; then echo "no shell scripts found"; else \
		echo "$$files" | sed 's/^/  /'; $(SHELLCHECK) -S $(SHELLCHECK_SEVERITY) $$files && \
		printf "$(BOLD)shellcheck: clean$(RESET)\n"; fi

list: ## List all skills discovered in this repo
	@find skills -mindepth 2 -maxdepth 2 -name SKILL.md -print \
		| sed -E 's#skills/([^/]+)/SKILL.md#  \1#' | sort

clean: ## Remove transient build artifacts (node_modules, lockfile)
	@rm -rf node_modules package-lock.json
	@echo "cleaned"
