"""Generate one narration clip per line with edge-tts, then measure durations."""
import asyncio
import json
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from narration import SCENES, VOICE, RATE, PITCH, LINE_GAP, SCENE_TAIL  # noqa: E402

import edge_tts  # noqa: E402

BASE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(BASE, "narration")


def duration(path):
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", path],
        capture_output=True, text=True, check=True,
    )
    return float(out.stdout.strip())


async def synth(text, path):
    for attempt in range(4):
        try:
            comm = edge_tts.Communicate(text, VOICE, rate=RATE, pitch=PITCH)
            await comm.save(path)
            if os.path.getsize(path) > 2000:
                return
        except Exception as exc:  # noqa: BLE001
            print(f"  retry {attempt + 1}: {exc}", flush=True)
        await asyncio.sleep(1.5 + attempt)
    raise RuntimeError(f"TTS failed for: {text[:50]}")


async def main():
    manifest = []
    for scene in SCENES:
        lines = []
        for i, line in enumerate(scene["lines"]):
            path = os.path.join(OUT, f"{scene['id']}_{i:02d}.mp3")
            if not (os.path.exists(path) and os.path.getsize(path) > 2000):
                await synth(line["say"], path)
            d = duration(path)
            lines.append({"file": path, "dur": d, "cap": line["cap"], "say": line["say"]})
            print(f"{scene['id']}_{i:02d}  {d:5.2f}s  {line['say'][:60]}", flush=True)
        scene_dur = sum(l["dur"] + LINE_GAP for l in lines) + SCENE_TAIL
        manifest.append({
            "id": scene["id"],
            "kind": scene["kind"],
            "card": scene.get("card"),
            "chapter": scene.get("chapter"),
            "lines": lines,
            "dur": round(scene_dur, 3),
        })
        print(f"--> {scene['id']} total {scene_dur:.2f}s\n", flush=True)

    total = sum(s["dur"] for s in manifest)
    print(f"TOTAL: {total:.1f}s  ({int(total // 60)}m {int(total % 60)}s)")
    with open(os.path.join(BASE, "manifest.json"), "w") as fh:
        json.dump({"total": total, "scenes": manifest, "line_gap": LINE_GAP, "scene_tail": SCENE_TAIL}, fh, indent=2)


asyncio.run(main())
