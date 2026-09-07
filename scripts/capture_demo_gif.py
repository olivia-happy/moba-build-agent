"""Capture a focused walkthrough of the H5 demo phone preview and make a GIF.

Drives the live GitHub Pages demo with the system Chrome, screenshots only the
phone preview (where scene/hero changes are visible), then assembles a GIF.

Output: docs/screenshots/demo-walkthrough.gif
"""
from __future__ import annotations

from pathlib import Path

from playwright.sync_api import sync_playwright

DEMO_URL = "https://olivia-happy.github.io/moba-build-agent/"
OUT = Path(__file__).resolve().parents[1] / "docs" / "screenshots"
FRAME_DIR = OUT / "demo-frames"
FRAME_DIR.mkdir(parents=True, exist_ok=True)

VIEW = {"width": 900, "height": 1900}


def phone_clip(page) -> dict:
    box = page.locator(".phone-stage").first.bounding_box()
    return {"x": box["x"] - 20, "y": box["y"] - 20, "width": box["width"] + 40, "height": box["height"] + 40}


def shot(page, name: str) -> None:
    clip = phone_clip(page)
    page.screenshot(path=str(FRAME_DIR / f"{name}.png"), clip=clip)
    print(f"  captured {name}.png")


def main() -> None:
    with sync_playwright() as p:
        browser = p.chromium.launch(channel="chrome", headless=True)
        page = browser.new_page(viewport=VIEW)
        page.goto(DEMO_URL, wait_until="networkidle", timeout=30000)
        page.wait_for_timeout(3000)
        shot(page, "1-magic-burst")

        tabs = page.locator(".scenario-tabs button")
        tabs.nth(1).click()
        page.wait_for_timeout(2600)
        shot(page, "2-assassin-dive")

        tabs.nth(2).click()
        page.wait_for_timeout(2600)
        shot(page, "3-sustain-control")

        own = page.locator(".own-selector button")
        if own.count() > 1:
            own.nth(1).click()
            page.wait_for_timeout(2400)
            shot(page, "4-hero-switch")

        browser.close()


if __name__ == "__main__":
    main()
