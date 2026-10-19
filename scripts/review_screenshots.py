"""Screenshots of the running review app for UI evidence (AGENTS.md: show, don't claim).

  uv run --group screenshots python scripts/review_screenshots.py [--base http://127.0.0.1:8765]
      [--credentials ~/.config/publicfunds/admin_credentials] [--flag FLAG_ID]

Signs in with the credentials file (the password is read, never printed), takes read-only screenshots, signs out.
It records no decisions. Uses the system Chrome (/usr/bin/google-chrome) if present.
"""
from __future__ import annotations

import argparse
import shutil
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]


def creds(path: Path) -> tuple[str, str]:
    kv = dict(ln.split("=", 1) for ln in path.read_text().splitlines() if "=" in ln and not ln.startswith("#"))
    return kv["username"], kv["password"]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="http://127.0.0.1:8765")
    ap.add_argument("--credentials", default=str(Path.home() / ".config/publicfunds/admin_credentials"))
    ap.add_argument("--flag", help="flag id for the detail screenshot (default: the D3 flag)")
    ap.add_argument("--out", default=str(ROOT / "dist"))
    a = ap.parse_args()
    user, pw = creds(Path(a.credentials).expanduser())
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    chrome = shutil.which("google-chrome") or shutil.which("chromium")
    shots = []
    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path=chrome, headless=True) if chrome else p.chromium.launch()
        ctx = browser.new_context(viewport={"width": 1366, "height": 900}, device_scale_factor=1)
        page = ctx.new_page()
        page.goto(f"{a.base}/login")
        page.fill("input[name=username]", user)
        page.fill("input[name=password]", pw)
        page.click("button[type=submit]")
        page.wait_for_url("**/flags")

        def snap(path, name, full=False):
            page.goto(a.base + path)
            page.wait_for_load_state("networkidle")
            page.screenshot(path=str(out / name), full_page=full)
            shots.append(str(out / name))

        snap("/flags", "screenshot_review_queue.png")
        flag = a.flag
        if not flag:
            page.goto(f"{a.base}/flags?detector=D3_restricted_supplier_awarded")
            flag = page.locator("table.queue tbody a[href^='/flags/']").first.get_attribute("href").split("/")[-1]
        snap(f"/flags/{flag}", "screenshot_review_flag_detail.png", full=True)
        snap("/coverage?data_type=core", "screenshot_review_coverage.png")
        snap("/coverage?data_type=uifw&province=KZN", "screenshot_review_coverage_kzn_uifw.png", full=True)
        mob = browser.new_context(viewport={"width": 390, "height": 844}, device_scale_factor=2, is_mobile=True,
                                  has_touch=True, storage_state=ctx.storage_state())
        mpage = mob.new_page()
        mpage.goto(f"{a.base}/flags?named=yes")
        mpage.wait_for_load_state("networkidle")
        mpage.screenshot(path=str(out / "screenshot_review_mobile_queue.png"))
        shots.append(str(out / "screenshot_review_mobile_queue.png"))
        csrf = page.locator("form[action='/logout'] input[name=csrf_token]").first.get_attribute("value")
        page.request.post(f"{a.base}/logout", form={"csrf_token": csrf})
        browser.close()
    print("\n".join(shots))


if __name__ == "__main__":
    main()
