"""Render the on-brand still frames for the demo: intro card, outro card and the
stage the phone recording sits on. Rendered in Chromium so they use the same
Figtree type and the same design tokens as the product itself.
"""
import os

from playwright.sync_api import sync_playwright

BASE = os.path.dirname(os.path.abspath(__file__))
CARDS = os.path.join(BASE, "cards")

SHELL = """<!doctype html>
<html><head><meta charset="utf-8">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Figtree:wght@400;500;600;700;800&family=Roboto+Mono:wght@400;500&display=swap" rel="stylesheet">
<style>
  :root{
    --bg:hsl(205 45% 98.5%); --ink:hsl(214 28% 23%); --muted:hsl(212 14% 47%);
    --brand:hsl(187 68% 37%); --brand-deep:hsl(190 58% 26%);
    --line:hsl(206 30% 91%); --grid:hsl(206 26% 92%);
    --allow:hsl(162 52% 33%); --ask:hsl(30 76% 43%); --block:hsl(352 60% 51%);
    --card:#fff;
  }
  *{box-sizing:border-box;margin:0;padding:0}
  html,body{width:1920px;height:1080px;overflow:hidden}
  body{background:var(--bg);font-family:Figtree,sans-serif;color:var(--ink);
       -webkit-font-smoothing:antialiased}
  .glow{position:absolute;inset:0 0 auto 0;height:640px;pointer-events:none;
    background:
      radial-gradient(900px 420px at 22% -12%, hsl(187 68% 37% / .13), transparent 70%),
      radial-gradient(760px 380px at 82% -18%, hsl(162 52% 33% / .10), transparent 72%);}
  .grid{position:absolute;inset:0;pointer-events:none;opacity:.5;
    background-image:linear-gradient(to right,var(--grid) 1px,transparent 1px),
                     linear-gradient(to bottom,var(--grid) 1px,transparent 1px);
    background-size:96px 96px;
    mask-image:radial-gradient(1200px 640px at 50% 34%, #000 30%, transparent 78%);
    -webkit-mask-image:radial-gradient(1200px 640px at 50% 34%, #000 30%, transparent 78%);}
  .grain{position:absolute;inset:0;pointer-events:none;opacity:.035;
    background-image:url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='140' height='140'><filter id='n'><feTurbulence type='fractalNoise' baseFrequency='.85' numOctaves='3'/></filter><rect width='140' height='140' filter='url(%23n)'/></svg>");}
  .wrap{position:relative;width:1920px;height:1080px;display:flex;flex-direction:column;
        align-items:center;justify-content:center;padding:0 140px 190px}
  .brand{display:flex;align-items:center;gap:15px;margin-bottom:44px}
  .mark{width:60px;height:60px;border-radius:17px;display:flex;align-items:center;
    justify-content:center;background:hsl(186 50% 93%);border:1px solid hsl(187 40% 82%)}
  .mark svg{width:31px;height:31px;stroke:var(--brand);fill:none;stroke-width:1.9}
  .word{font-size:41px;font-weight:800;letter-spacing:-.022em}
  .word span{color:var(--brand)}
  .kicker{font-family:"Roboto Mono",monospace;font-size:16px;font-weight:500;
    letter-spacing:.20em;text-transform:uppercase;color:var(--brand-deep);
    background:hsl(186 50% 93%);border:1px solid hsl(187 40% 84%);
    padding:8px 17px;border-radius:999px;margin-bottom:34px}
  h1{font-size:88px;line-height:1.02;font-weight:800;letter-spacing:-.032em;text-align:center;
     max-width:1420px}
  h1 em{font-style:normal;color:var(--brand)}
  .sub{margin-top:34px;font-size:31px;line-height:1.42;color:var(--muted);text-align:center;
       max-width:1080px;font-weight:400}
  .chips{margin-top:52px;display:flex;gap:16px}
  .chip{display:flex;align-items:center;gap:11px;font-size:22px;font-weight:600;
    background:var(--card);border:1px solid var(--line);border-radius:999px;padding:13px 26px;
    box-shadow:0 8px 22px hsl(209 32% 55% / .09)}
  .dot{width:11px;height:11px;border-radius:50%}
  .foot{position:absolute;left:0;right:0;bottom:214px;text-align:center;font-size:20px;
    color:var(--muted);letter-spacing:.01em}
</style></head><body>
<div class="glow"></div><div class="grid"></div><div class="grain"></div>
__BODY__
</body></html>"""

SHIELD = ('<svg viewBox="0 0 24 24" stroke-linecap="round" stroke-linejoin="round">'
          '<path d="M12 2.6 4.6 5.6v5.7c0 4.6 3.1 8.6 7.4 9.9 4.3-1.3 7.4-5.3 7.4-9.9V5.6Z"/>'
          '<path d="M9.4 12.2l1.9 1.9 3.4-3.9"/></svg>')

BRAND = f'<div class="brand"><div class="mark">{SHIELD}</div>' \
        '<div class="word">Ve<span>x</span>en</div></div>'

INTRO = SHELL.replace("__BODY__", f"""
<div class="wrap">
  {BRAND}
  <div class="kicker">Security for AI agents</div>
  <h1>The permission layer<br>for <em>AI agents</em></h1>
  <div class="sub">Every action an agent tries gets one answer, in one call —
    and Vexen genuinely stops it when the answer is no.</div>
  <div class="chips">
    <div class="chip"><span class="dot" style="background:var(--allow)"></span>Allowed</div>
    <div class="chip"><span class="dot" style="background:var(--ask)"></span>Needs your OK</div>
    <div class="chip"><span class="dot" style="background:var(--block)"></span>Blocked</div>
  </div>
</div>""")

OUTRO = SHELL.replace("__BODY__", f"""
<div class="wrap">
  {BRAND}
  <h1>Give AI power.<br><em>Keep control.</em></h1>
  <div class="sub">Free to start. Your workspace begins completely locked down —
    nothing can act for you until you say so.</div>
  <div class="chips">
    <div class="chip"><span class="dot" style="background:var(--allow)"></span>Deterministic enforcement</div>
    <div class="chip"><span class="dot" style="background:var(--brand)"></span>Two-tap phone approvals</div>
    <div class="chip"><span class="dot" style="background:var(--ask)"></span>Audit you can verify</div>
  </div>
</div>
<div class="foot">Agents already have the keys. Somebody has to hold the lock.</div>""")

# --- stage for the 390x844 phone recording -----------------------------------
PHONE_W, PHONE_H = 379, 820
PHONE_X, PHONE_Y = 1210, 44
BEZEL = 13

STAGE = SHELL.replace("__BODY__", f"""
<div style="position:relative;width:1920px;height:1080px">
  <div style="position:absolute;left:170px;top:212px;width:830px">
    <div class="kicker" style="display:inline-block;margin-bottom:30px">Approve by phone</div>
    <div style="font-size:64px;font-weight:800;letter-spacing:-.03em;line-height:1.06">
      One tap in your inbox.<br>One tap to confirm.</div>
    <div style="margin-top:38px;display:flex;flex-direction:column;gap:19px;font-size:26px;
                color:var(--muted);font-weight:500">
      <div style="display:flex;gap:15px;align-items:flex-start">
        <span style="color:var(--brand);font-weight:800">&#8212;</span>No login. No app to install.</div>
      <div style="display:flex;gap:15px;align-items:flex-start">
        <span style="color:var(--brand);font-weight:800">&#8212;</span>Opening the link decides nothing at all.</div>
      <div style="display:flex;gap:15px;align-items:flex-start">
        <span style="color:var(--brand);font-weight:800">&#8212;</span>Signed per recipient &#183; expires in 24 hours.</div>
      <div style="display:flex;gap:15px;align-items:flex-start">
        <span style="color:var(--brand);font-weight:800">&#8212;</span>Good for one attempt, then it is spent.</div>
    </div>
  </div>
  <div style="position:absolute;left:{PHONE_X - BEZEL}px;top:{PHONE_Y - BEZEL}px;
              width:{PHONE_W + 2 * BEZEL}px;height:{PHONE_H + 2 * BEZEL}px;
              background:hsl(214 26% 19%);border-radius:44px;
              box-shadow:0 40px 90px hsl(209 32% 45% / .28), 0 4px 10px hsl(209 32% 45% / .18)"></div>
</div>""")


def main():
    os.makedirs(CARDS, exist_ok=True)
    with sync_playwright() as p:
        b = p.chromium.launch(args=["--no-sandbox", "--disable-dev-shm-usage",
                                    "--force-color-profile=srgb", "--hide-scrollbars"])
        ctx = b.new_context(viewport={"width": 1920, "height": 1080}, device_scale_factor=1)
        page = ctx.new_page()
        for name, html in [("intro", INTRO), ("outro", OUTRO), ("phone_stage", STAGE)]:
            page.set_content(html)
            page.wait_for_timeout(1600)
            page.screenshot(path=os.path.join(CARDS, f"{name}.png"))
            print("rendered", name)
        ctx.close()
        b.close()
    with open(os.path.join(CARDS, "phone_geometry.txt"), "w") as fh:
        fh.write(f"{PHONE_W} {PHONE_H} {PHONE_X} {PHONE_Y}\n")


if __name__ == "__main__":
    main()
