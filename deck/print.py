import subprocess, sys, pathlib
out = "/app/deck/Vexen-Pitch-Deck.pdf"
cmd = [
  "google-chrome","--headless=new","--no-sandbox","--disable-gpu",
  "--disable-dev-shm-usage","--hide-scrollbars","--force-color-profile=srgb",
  "--font-render-hinting=none","--run-all-compositor-stages-before-draw",
  "--virtual-time-budget=12000",
  "--no-pdf-header-footer", f"--print-to-pdf={out}",
  "file:///app/deck/deck.html",
]
r = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
print([l for l in (r.stderr or "").splitlines() if "written" in l or "ERROR:cert" in l][:3])
p = pathlib.Path(out)
print("exists:", p.exists(), "size:", f"{p.stat().st_size:,}" if p.exists() else 0)
