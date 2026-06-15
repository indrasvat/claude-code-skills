#!/usr/bin/env node
// Validate every skills/<name>/SKILL.md frontmatter by *parsing* it with the
// same YAML engine the `skills` CLI (https://skills.sh) uses — js-yaml — instead
// of grep-matching field names. A plain (unquoted) scalar containing ": "
// (colon-space) is invalid YAML and makes the skill silently un-discoverable;
// grep can't see that, a real parse can. Rules mirror the Agent Skills spec:
//   - name: required, ^[a-z0-9-]+$, <= 64 chars, must match the directory name
//   - description: required, non-empty, <= 1024 chars
import { readFileSync, readdirSync, existsSync, statSync } from 'node:fs';
import { join } from 'node:path';
import yaml from 'js-yaml';

const SKILLS_DIR = 'skills';
const NAME_RE = /^[a-z0-9-]+$/;
const MAX_NAME = 64;
const MAX_DESC = 1024;

let totalErrors = 0;

const dirs = readdirSync(SKILLS_DIR)
  .filter((d) => statSync(join(SKILLS_DIR, d)).isDirectory())
  .sort();

for (const skill of dirs) {
  const file = join(SKILLS_DIR, skill, 'SKILL.md');
  const problems = [];
  const fail = (msg) => problems.push(msg);

  if (!existsSync(file)) {
    console.error(`❌ ${skill}: missing SKILL.md`);
    totalErrors++;
    continue;
  }

  const raw = readFileSync(file, 'utf8');
  const m = raw.match(/^---\r?\n([\s\S]*?)\r?\n---/);
  if (!m) {
    console.error(`❌ ${skill}: missing or malformed YAML frontmatter (--- fences)`);
    totalErrors++;
    continue;
  }

  let fm;
  try {
    // JSON_SCHEMA = pure data (strings/numbers/bools/null/seq/map) only. It can't
    // construct arbitrary objects, so it's safe against !!js/!!python-style tags,
    // and it still throws on the syntax fault we care about (a plain scalar with
    // ": ") because that's a parser-level error raised before schema resolution.
    fm = yaml.load(m[1], { schema: yaml.JSON_SCHEMA });
  } catch (e) {
    const reason = String(e.message).split('\n')[0];
    console.error(`❌ ${skill}: frontmatter is not valid YAML — ${reason}`);
    console.error(`     (a plain description containing ": " must use a folded block scalar "description: >" or be quoted)`);
    totalErrors++;
    continue;
  }

  if (fm === null || typeof fm !== 'object' || Array.isArray(fm)) {
    console.error(`❌ ${skill}: frontmatter did not parse to a key/value mapping`);
    totalErrors++;
    continue;
  }

  const name = fm.name;
  if (name === undefined || name === null || name === '') {
    fail("missing 'name'");
  } else {
    const n = String(name);
    if (!NAME_RE.test(n)) fail(`name '${n}' must match ${NAME_RE} (lowercase, digits, hyphens)`);
    if (n.length > MAX_NAME) fail(`name is ${n.length} chars (max ${MAX_NAME})`);
    if (n !== skill) fail(`name '${n}' must match directory name '${skill}'`);
  }

  const description = fm.description;
  if (description === undefined || description === null) {
    fail("missing 'description'");
  } else {
    const d = String(description).trim();
    if (d.length === 0) fail('description is empty');
    if (d.length > MAX_DESC) fail(`description is ${d.length} chars (max ${MAX_DESC})`);
  }

  if (problems.length) {
    for (const p of problems) console.error(`❌ ${skill}: ${p}`);
    totalErrors += problems.length;
  } else {
    console.log(`✓ ${skill}`);
  }
}

if (totalErrors) {
  console.error(`\n${totalErrors} problem(s) found across ${dirs.length} skills.`);
  process.exit(1);
}
console.log(`\nAll ${dirs.length} skills have valid, parseable frontmatter.`);
