#!/usr/bin/env python3
"""Offline tests for the gh-attach helper logic (issue #18).

Stdlib-only and live-GitHub-free: exercises the pure helpers in gh_attach.py and
asserts the structural safety invariant — that the upload path issues NO clicks,
so destructive GitHub controls (Close/Merge/Delete/Reopen/Submit review) are
unreachable. Run: `python3 test_gh_attach.py` (also `make test-browsing`).
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import gh_attach as g  # noqa: E402

HERE = Path(__file__).parent
ASSET = "https://github.com/user-attachments/assets/8b1c2d3e-4f56-7890-abcd-ef1234567890"
ASSET2 = "https://github.com/user-attachments/assets/0011aabb-ccdd-eeff-0011-223344556677"
FILE_URL = "https://github.com/user-attachments/files/19283746/trace.log"

passed = 0
failures: list[str] = []


def check(name: str, cond: bool) -> None:
    global passed
    if cond:
        passed += 1
    else:
        failures.append(name)


def raises(fn) -> bool:
    try:
        fn()
        return False
    except g.TargetError:
        return True


# --- resolve_target -----------------------------------------------------------
t = g.resolve_target("o/r", 123, None, None)
check("issue->/issues", t["url"].endswith("/o/r/issues/123") and t["kind"] == "issues"
      and t["number"] == 123 and t["repo"] == "o/r")

t = g.resolve_target("o/r", None, 19, None)
check("pr->/pull", t["url"].endswith("/o/r/pull/19") and t["kind"] == "pull" and t["number"] == 19)

t = g.resolve_target(None, None, None, "https://github.com/o/r/pull/42#issuecomment-1")
check("url-parse", t["repo"] == "o/r" and t["kind"] == "pull" and t["number"] == 42)

t = g.resolve_target(None, None, None, "https://github.com/o/r/issues/new")
check("bare-github-url", t["repo"] is None and t["number"] is None)

check("both-issue-and-pr-rejected", raises(lambda: g.resolve_target("o/r", 1, 2, None)))
check("neither-rejected", raises(lambda: g.resolve_target("o/r", None, None, None)))
check("bad-repo-rejected", raises(lambda: g.resolve_target("not-a-repo", 1, None, None)))
check("non-github-url-rejected", raises(lambda: g.resolve_target(None, None, None, "https://evil.test/x")))
check("nothing-rejected", raises(lambda: g.resolve_target(None, None, None, None)))

# --- new_asset_urls: single, multiple, none, files-form, no trailing paren ----
check("single-image-url", g.new_asset_urls("", f"![s1]({ASSET})") == [ASSET])
check("no-trailing-paren", g.new_asset_urls("", f"![s1]({ASSET})")[0] == ASSET)  # not ASSET + ")"
check("html-img-form",
      g.new_asset_urls("", f'<img width="909" alt="s" src="{ASSET}">') == [ASSET])
check("non-image-file-url", g.new_asset_urls("", f"[trace.log]({FILE_URL})") == [FILE_URL])
check("only-new-url-after-first",
      g.new_asset_urls(f"![s1]({ASSET})", f"![s1]({ASSET})\n![s2]({ASSET2})") == [ASSET2])
check("empty-when-only-placeholder",
      g.new_asset_urls("", "![Uploading screenshot.png…]()") == [])
check("empty-when-no-change", g.new_asset_urls(f"x {ASSET}", f"x {ASSET}") == [])

# --- inserted_segment ---------------------------------------------------------
check("inserted-empty-baseline", g.inserted_segment("", f"![s1]({ASSET})") == f"![s1]({ASSET})")
check("inserted-appended",
      g.inserted_segment(f"![s1]({ASSET})\n", f"![s1]({ASSET})\n![s2]({ASSET2})") == f"![s2]({ASSET2})")

# --- comment_body / post_command ----------------------------------------------
assets = [{"path": "a.png", "url": ASSET, "markdown": f"![a]({ASSET})"},
          {"path": "b.log", "url": FILE_URL, "markdown": f"[b]({FILE_URL})"}]
body = g.comment_body(assets)
check("body-joins-both", f"![a]({ASSET})" in body and f"[b]({FILE_URL})" in body)
cmd = g.post_command("o/r", 19, body)
check("post-cmd-issues-endpoint", cmd is not None and "repos/o/r/issues/19/comments" in cmd)
check("post-cmd-quotes-body", cmd is not None and "-f body=" in cmd)
check("post-cmd-none-without-repo", g.post_command(None, 19, body) is None)
check("post-cmd-none-without-number", g.post_command("o/r", None, body) is None)

# --- SAFETY: the upload path clicks nothing (issue #18 core guarantee) ---------
js_blobs = [g.FIND_JS, g.POLL_JS, g.INPUT_JS, g.restore_js("prev value")]
check("js-never-clicks", all(".click(" not in b for b in js_blobs))
check("js-never-submits", all("submit" not in b.lower() for b in js_blobs))
check("restore-empties-to-original", '"prev value"' in g.restore_js("prev value"))

# Scope-check the cdp.py upload region: it must drive uploads via
# DOM.setFileInputFiles and must NOT use any trusted-input click primitive.
cdp_src = (HERE / "cdp.py").read_text()
start = cdp_src.index("async def _gh_attach_wait_url")
end = cdp_src.index('if __name__ == "__main__"')
region = cdp_src[start:end]
check("upload-uses-setfileinputfiles", "DOM.setFileInputFiles" in region)
check("upload-no-input-dispatch", "Input.dispatch" not in region)
check("upload-no-click-helper", "_click_point" not in region and ".click(" not in region)
check("upload-restores-composer", "restore_js" in region)
check("allow-submit-refused", "--allow-submit is intentionally unsupported" in cdp_src)

# --- report -------------------------------------------------------------------
if failures:
    print(f"FAIL ({len(failures)} of {passed + len(failures)}):")
    for f in failures:
        print(f"  ✗ {f}")
    sys.exit(1)
print(f"ok — {passed} checks passed")
