---
description: Generate a comprehensive PRD with interactive discovery questions
---

# PRD Generator

Generate a comprehensive Product Requirements Document through interactive discovery.

## Instructions

1. **Use the prd-generator skill** to conduct interactive discovery
2. Ask 8-12 adaptive questions covering:
   - Problem space (pain points, users, success criteria)
   - Technical context (stack, existing code, requirements)
   - Scope & constraints (MVP boundaries, non-functional requirements)
   - Verification (testing strategy, acceptance criteria)
3. Continue asking follow-up questions until you have enough detail for each PRD section
4. Generate `docs/PRD.md` using the template at `${CLAUDE_PLUGIN_ROOT}/skills/prd-generator/templates/PRD-TEMPLATE.md`
5. Generate `docs/PROGRESS.md` using the template at `${CLAUDE_PLUGIN_ROOT}/skills/prd-generator/templates/PROGRESS-TEMPLATE.md`

## Key Principles

- **Don't accept vague answers** - ask clarifying follow-ups
- **Minimum 8 questions** before generating PRD
- **All tasks must have checkboxes** for tracking
- **Break into 2-4 phases** with clear verification criteria
- **Files are the source of truth** - no hallucinating requirements

Begin the interactive discovery now.
