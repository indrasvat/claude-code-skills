# Ship checklist

```
Core
- [ ] description states what + when, third person, with literal trigger terms
- [ ] name is [a-z0-9-], <=64 chars, equals the directory, no reserved words
- [ ] SKILL.md < 100 lines; extra detail in one-level-deep references; TOC on refs > 100 lines
- [ ] no time-sensitive info (superseded guidance in a collapsed "old patterns" block)
- [ ] consistent terminology; concrete, not abstract, examples
- [ ] freedom matches fragility; one default + escape hatch, not a menu

Machinery (only what applies)
- [ ] scripts solve, not punt; explicit error handling; no voodoo constants
- [ ] hooks: exit 0 to inject, exit 2 / deny to block, never exit 1; re-entrancy guard
- [ ] script-talks-back / memory: output and storage shape documented as a contract
- [ ] cross-harness diffs detect-and-degrade, not hardcoded; capability notes dated
- [ ] dependencies listed; forward slashes; MCP tools fully qualified

Repo gates
- [ ] frontmatter: allowed-tools + argument-hint present; disable-model-invocation set iff mutation
- [ ] `make check` green (validate-skills parses frontmatter; shellcheck clean)
- [ ] README skills table + count updated; marketplace.json count updated

Test
- [ ] >= 3 evals; baseline captured; re-runs beat baseline
- [ ] every script linted and run; verified on the weakest target model
```
