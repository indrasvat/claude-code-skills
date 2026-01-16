---
description: Generate a comprehensive PRD with interactive discovery questions
---

# PRD Generator

Generate a comprehensive Product Requirements Document through collaborative discovery.

## Instructions

1. **Use the prd-generator skill** to conduct interactive discovery
2. **Be a thought partner, not an interrogator** - help users who have vague ideas
3. Ask 8-12 adaptive questions covering:
   - Problem space (pain points, users, success criteria)
   - Technical context (stack, existing code, requirements)
   - Scope & constraints (MVP boundaries, non-functional requirements)
   - Verification (testing strategy, acceptance criteria)
4. **When users are unsure**: Offer concrete suggestions, propose sensible defaults, break big questions into smaller ones
5. Generate `docs/PRD.md` using the template at `${CLAUDE_PLUGIN_ROOT}/skills/prd-generator/templates/PRD-TEMPLATE.md`
6. Generate `docs/PROGRESS.md` using the template at `${CLAUDE_PLUGIN_ROOT}/skills/prd-generator/templates/PROGRESS-TEMPLATE.md`

## Key Principles

- **Guide, don't interrogate** - "I don't know" should lead to helpful suggestions
- **Offer options** - when users are stuck, provide 2-3 concrete choices
- **Suggest sensible defaults** - based on similar projects and best practices
- **All tasks must have checkboxes** for tracking
- **Break into 2-4 phases** with clear verification criteria
- **Files are the source of truth** - no hallucinating requirements

Begin the collaborative discovery now. Start with an open-ended question like "Tell me about what you're trying to build" or "What sparked this idea?"
