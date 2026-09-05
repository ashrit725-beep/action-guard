#!/usr/bin/env python3
"""Render the deck and assert no slide's content overflows its 1600x900 box."""
import asyncio
import sys
from playwright.async_api import async_playwright

CHROME = "/usr/bin/google-chrome"


async def main() -> int:
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            executable_path=CHROME,
            args=["--no-sandbox", "--disable-dev-shm-usage", "--font-render-hinting=none"],
        )
        page = await browser.new_page(viewport={"width": 1600, "height": 900})
        await page.goto("file:///app/deck/deck2.html")
        await page.wait_for_timeout(2500)

        report = await page.evaluate("""() => {
          const out = [];
          document.querySelectorAll('.slide').forEach((s, i) => {
            const box = s.getBoundingClientRect();
            let lowest = 0, culprit = '';
            // walk every leaf-ish element and find the one reaching furthest down
            s.querySelectorAll('*').forEach(el => {
              if (!el.offsetParent && getComputedStyle(el).position !== 'absolute') return;
              const r = el.getBoundingClientRect();
              if (r.height === 0) return;
              const bottom = r.bottom - box.top;
              if (bottom > lowest) {
                lowest = bottom;
                culprit = el.tagName.toLowerCase() + '.' + (el.className || '').toString().split(' ')[0];
              }
            });
            const body = s.querySelector('.body');
            out.push({
              n: i + 1,
              lowest: Math.round(lowest),
              scrollH: s.scrollHeight,
              bodyScroll: body ? body.scrollHeight : 0,
              bodyClient: body ? body.clientHeight : 0,
              culprit
            });
          });
          return out;
        }""")

        bad = []
        print(f"{'slide':>6} {'deepest px':>11} {'scrollH':>8} {'body fit':>10}   deepest element")
        print("-" * 78)
        for r in report:
            body_over = r["bodyScroll"] - r["bodyClient"]
            flag = ""
            if r["lowest"] > 900 or r["scrollH"] > 900 or body_over > 1:
                flag = "  <-- OVERFLOW"
                bad.append(r["n"])
            print(f"{r['n']:>6} {r['lowest']:>11} {r['scrollH']:>8} "
                  f"{('+' + str(body_over)) if body_over > 0 else 'ok':>10}   "
                  f"{r['culprit']}{flag}")

        # per-slide PNGs for visual QA
        for i, el in enumerate(await page.query_selector_all(".slide"), start=1):
            await el.screenshot(path=f"/app/deck/qa2/s{i:02d}.png")

        await browser.close()

        print("-" * 78)
        if bad:
            print(f"OVERFLOWING SLIDES: {bad}")
            return 1
        print("all slides fit within 1600x900")
        return 0


sys.exit(asyncio.run(main()))
