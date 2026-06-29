"""Pure helpers for the cdp.py `gh-attach` command — GitHub attachment uploads.

Split out from cdp.py on purpose: everything here is stdlib-only and side-effect
free (no websockets, no Chrome), so it is unit-testable under a plain `python3`
with no PEP-723 dependency resolution. cdp.py imports these; test_gh_attach.py
exercises them directly.

The safe two-phase flow this supports (see issue #18):
  1. authenticated CDP uploads the file(s) through GitHub's hidden file input and
     reads back the `user-attachments/...` URL(s) — it NEVER clicks a page button;
  2. the agent posts the final comment with `gh api`, using those URLs.

GitHub mints two URL shapes, so a generic (non-image) uploader must match both:
  * images        -> https://github.com/user-attachments/assets/<uuid>
  * everything else-> https://github.com/user-attachments/files/<n>/<name.ext>
"""
from __future__ import annotations

import re
import shlex

# Both attachment URL shapes GitHub inserts into the comment textarea. Kept
# deliberately broad (any file extension) — this is a generic uploader, not an
# image-only one. Stops at whitespace and the markdown/HTML delimiters that wrap
# the URL ( ) ] " ' < > so a trailing `)` from `![alt](url)` isn't captured.
_ASSET_RE = re.compile(
    r"https://github\.com/user-attachments/"
    r"(?:assets/[0-9a-fA-F-]{8,}|files/\d+/[^\s)\]\"'<>]+)"
)

_REPO_RE = re.compile(r"^[A-Za-z0-9._-]+/[A-Za-z0-9._-]+$")
_TARGET_URL_RE = re.compile(
    r"^https://github\.com/(?P<repo>[^/]+/[^/]+)/(?P<kind>pull|issues)/(?P<number>\d+)"
)


class TargetError(ValueError):
    """Raised when the issue/PR target can't be resolved from the given flags."""


def resolve_target(repo: str | None, issue: int | None, pr: int | None,
                   url: str | None) -> dict:
    """Turn (--repo/--issue/--pr) or (--url) into a target descriptor.

    Returns {url, repo, kind, number}; kind/number/repo may be None when only a
    bare (unparseable) github URL was given. Raises TargetError on bad input.
    """
    if url:
        m = _TARGET_URL_RE.match(url)
        if m:
            return {"url": url, "repo": m["repo"], "kind": m["kind"],
                    "number": int(m["number"])}
        if not url.startswith("https://github.com/"):
            raise TargetError("--url must be a https://github.com/... link")
        return {"url": url, "repo": repo, "kind": None, "number": None}
    if not repo:
        raise TargetError(
            "pass --repo OWNER/REPO with --issue N or --pr N, or --url, "
            "or -t <tab already on the issue/PR page>")
    if not _REPO_RE.match(repo):
        raise TargetError(f"--repo must look like OWNER/REPO (got {repo!r})")
    if (issue is None) == (pr is None):
        raise TargetError("pass exactly one of --issue N or --pr N")
    if issue is not None:
        return {"url": f"https://github.com/{repo}/issues/{issue}",
                "repo": repo, "kind": "issues", "number": issue}
    return {"url": f"https://github.com/{repo}/pull/{pr}",
            "repo": repo, "kind": "pull", "number": pr}


def new_asset_urls(before: str, after: str) -> list[str]:
    """Attachment URLs present in `after` but not in `before` (in order)."""
    seen = set(_ASSET_RE.findall(before or ""))
    out: list[str] = []
    for u in _ASSET_RE.findall(after or ""):
        if u not in seen and u not in out:
            out.append(u)
    return out


def inserted_segment(before: str, after: str) -> str:
    """The text GitHub inserted: `after` minus the common prefix/suffix it shares
    with `before`. With an empty baseline this is just `after`. Gives the literal
    markdown/HTML snippet (`![name](url)` or `<img ... src=url>`) GitHub wrote."""
    before, after = before or "", after or ""
    if before and before in after:
        i = after.find(before)
        return (after[:i] + after[i + len(before):]).strip()
    p = 0
    while p < len(before) and p < len(after) and before[p] == after[p]:
        p += 1
    s = 0
    while (s < len(before) - p and s < len(after) - p
           and before[-1 - s] == after[-1 - s]):
        s += 1
    return after[p:len(after) - s].strip()


def comment_body(assets: list[dict]) -> str:
    """Join the per-file markdown snippets into a ready-to-post comment body."""
    parts = [a["markdown"] or a["url"] for a in assets]
    return "\n\n".join(p for p in parts if p)


def post_command(repo: str | None, number: int | None, body: str) -> str | None:
    """The `gh api` line that safely posts `body` as a comment (PRs use the
    issues endpoint). None when repo/number are unknown (bare --url)."""
    if not repo or number is None:
        return None
    return (f"gh api repos/{repo}/issues/{number}/comments "
            f"-f body={shlex.quote(body)}")


# --- browser-side JS (runs in the GitHub page) --------------------------------
# Locate the MAIN comment composer's textarea + its hidden file input and pin
# them to a window global so later CDP calls can address the same input. Returns
# {ok:false, reason} when the composer isn't there (logged out, no comment
# permission, or a non-textarea React composer) so the command fails closed
# without touching the page. Critically: this NEVER clicks anything — destructive
# GitHub controls (Close/Merge/Delete/Reopen/Submit review) are out of reach by
# construction, because gh-attach issues no clicks at all.
FIND_JS = r"""
(() => {
  const vis = (el) => {
    if (!el) return false;
    const r = el.getBoundingClientRect();
    if (!r.width || !r.height) return false;
    const s = getComputedStyle(el);
    return s.display !== 'none' && s.visibility !== 'hidden';
  };
  // Most-specific comment-body textareas first; fall back to generic ones.
  const sels = [
    'textarea#new_comment_field',
    'file-attachment textarea',
    'textarea[name="comment[body]"]',
    'textarea.js-comment-field',
    'textarea[aria-label*="comment" i]',
    'textarea[placeholder*="comment" i]',
    'textarea[name*="comment" i]',
  ];
  let textarea = null;
  for (const sel of sels) {
    const els = [...document.querySelectorAll(sel)].filter(vis);
    if (els.length) { textarea = els[els.length - 1]; break; }
  }
  if (!textarea) return { ok: false, reason: 'no-comment-editor' };
  // The file input lives in the enclosing <file-attachment> or <form>; widen
  // only if that scope has none.
  const scope = textarea.closest('file-attachment')
             || textarea.closest('form') || document;
  let input = scope.querySelector('input[type=file]')
           || document.querySelector(
                'file-attachment input[type=file], input.file-attachment-input, '
                + 'input[type=file]');
  if (!input) return { ok: false, reason: 'no-file-input' };
  window.__ghAttach = { input, textarea };
  return { ok: true, original: textarea.value };
})()
"""

# Read the current composer value (null if the pin is gone).
POLL_JS = "(window.__ghAttach && window.__ghAttach.textarea) " \
          "? window.__ghAttach.textarea.value : null"

# Resolve the pinned file input element (for DOM.setFileInputFiles by objectId).
INPUT_JS = "window.__ghAttach && window.__ghAttach.input"


def restore_js(original: str) -> str:
    """JS that restores the composer to `original`, fires `input` so GitHub's
    draft autosave catches up, and drops the pin — leaving the page untouched."""
    lit = _js_string(original)
    return (
        "(() => {"
        "  const h = window.__ghAttach;"
        "  if (h && h.textarea) {"
        f"    h.textarea.value = {lit};"
        "    h.textarea.dispatchEvent(new Event('input', {bubbles: true}));"
        "  }"
        "  delete window.__ghAttach;"
        "  return true;"
        "})()"
    )


def _js_string(s: str) -> str:
    """A safe JS string literal for embedding in an evaluated expression."""
    import json
    return json.dumps(s)
