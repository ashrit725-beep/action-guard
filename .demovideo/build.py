"""Assemble the final demo video.

For every scene: cut the recording down to the paced take, scale it to 1080p
(the phone take is composited onto a branded stage), and burn in the caption
plate for whichever narration line is being spoken. Then concatenate, lay the
narration underneath and encode an MP4 + WebM + poster.
"""
import json
import math
import os
import shutil
import subprocess

BASE = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(BASE, "raw")
CARDS = os.path.join(BASE, "cards")
CAPS = os.path.join(CARDS, "caps")
SCENES_DIR = os.path.join(BASE, "scenes")
OUT = os.path.join(BASE, "out")
WORK = os.path.join(BASE, "work")

FPS = 30
W, H = 1920, 1080
EXTRA_CAP = 3.0          # never hold more than this much extra tail per scene
PHONE = (379, 820, 1210, 44)

MANIFEST = json.load(open(os.path.join(BASE, "manifest.json")))
CLIPS = json.load(open(os.path.join(BASE, "clips.json")))
GAP = MANIFEST["line_gap"]


def run(args, label=""):
    proc = subprocess.run(args, capture_output=True, text=True)
    if proc.returncode != 0:
        print(f"FFMPEG FAILED {label}\n{' '.join(args[:14])}...\n{proc.stderr[-2600:]}")
        raise SystemExit(1)


def probe(path):
    return float(subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", path],
        capture_output=True, text=True).stdout.strip())


def line_starts(scene):
    out, t = [], 0.0
    for line in scene["lines"]:
        out.append(t)
        t += line["dur"] + GAP
    return out


def seg_length(scene):
    clip = CLIPS.get(scene["id"])
    need = scene["dur"]
    if scene["kind"] == "card" or not clip:
        return need
    cuts = sum(b - a for a, b in clip["cuts"])
    usable = clip["raw"] - clip["lead_in"] - cuts
    return round(min(max(need, usable), need + EXTRA_CAP), 3)


def caption_overlays(scene, seg_len, first_input=1):
    """Filter chain that keeps exactly one caption plate on screen at all times."""
    starts = line_starts(scene)
    chain, prev = [], "[base]"
    for i, start in enumerate(starts):
        end = starts[i + 1] if i + 1 < len(starts) else seg_len + 0.05
        tag = f"[c{i}]"
        chain.append(
            f"{prev}[{first_input + i}:v]overlay=0:0:eof_action=pass:"
            f"enable='between(t,{start:.3f},{end:.3f})'{tag}"
        )
        prev = tag
    return chain, prev


def build_scene(scene):
    sid = scene["id"]
    seg_len = seg_length(scene)
    frames = int(round(seg_len * FPS))
    dst = os.path.join(SCENES_DIR, f"{sid}.mp4")
    plates = [os.path.join(CAPS, f"{sid}_{i:02d}.png") for i in range(len(scene["lines"]))]

    if scene["kind"] == "card":
        card = os.path.join(CARDS, f"{scene['card']}.png")
        args = ["ffmpeg", "-v", "error", "-y", "-loop", "1", "-framerate", str(FPS), "-i", card]
        for p in plates:
            args += ["-loop", "1", "-framerate", str(FPS), "-i", p]
        chain, last = caption_overlays(scene, seg_len)
        graph = (
            f"[0:v]scale={W}:{H},zoompan=z='min(1+0.00055*on,1.055)':d={frames}"
            f":x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s={W}x{H}:fps={FPS},"
            f"format=yuv420p[base];" + ";".join(chain)
        )
        args += ["-filter_complex", graph, "-map", last,
                 "-frames:v", str(frames), "-r", str(FPS),
                 "-c:v", "libx264", "-preset", "medium", "-crf", "16",
                 "-pix_fmt", "yuv420p", dst]
        run(args, sid)
        print(f"  {sid:16s} card   {seg_len:6.2f}s")
        return dst, seg_len

    clip = CLIPS[sid]
    src = os.path.join(RAW, f"{sid}.webm")
    start = max(0.0, min(clip["lead_in"], clip["raw"] - clip["need"]))

    # Drop the dead stretches the recorder marked, then hold the take we want.
    keeps, cursor = [], 0.0
    for a, b in clip["cuts"]:
        keeps.append((cursor, a))
        cursor = b
    keeps.append((cursor, None))

    pieces = []
    for i, (a, b) in enumerate(keeps):
        piece = os.path.join(WORK, f"{sid}_p{i}.mp4")
        args = ["ffmpeg", "-v", "error", "-y", "-ss", f"{start + a:.3f}"]
        if b is not None:
            args += ["-t", f"{b - a:.3f}"]
        args += ["-i", src, "-an", "-vsync", "cfr", "-r", str(FPS),
                 "-c:v", "libx264", "-preset", "veryfast", "-crf", "14",
                 "-pix_fmt", "yuv420p", piece]
        run(args, f"{sid} piece {i}")
        pieces.append(piece)

    if len(pieces) > 1:
        joined = os.path.join(WORK, f"{sid}_joined.mp4")
        listing = os.path.join(WORK, f"{sid}.txt")
        with open(listing, "w") as fh:
            for piece in pieces:
                fh.write(f"file '{piece}'\n")
        run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", listing,
             "-c", "copy", joined], f"{sid} join")
    else:
        joined = pieces[0]

    args = ["ffmpeg", "-v", "error", "-y", "-i", joined]
    if sid == "s08_phone":
        args += ["-loop", "1", "-framerate", str(FPS), "-i", os.path.join(CARDS, "phone_stage.png")]
        base_inputs = 2
    else:
        base_inputs = 1
    for p in plates:
        args += ["-loop", "1", "-framerate", str(FPS), "-i", p]

    chain, last = caption_overlays(scene, seg_len, first_input=base_inputs)
    if sid == "s08_phone":
        pw, ph, px, py = PHONE
        pre = (
            f"[0:v]scale={pw}:{ph}:flags=lanczos,tpad=stop_mode=clone:stop_duration=4[ph];"
            f"[1:v]scale={W}:{H}[stage];"
            f"[stage][ph]overlay={px}:{py}:eof_action=pass,format=yuv420p[base];"
        )
    else:
        pre = (
            f"[0:v]scale={W}:{H}:flags=lanczos,tpad=stop_mode=clone:stop_duration=4,"
            f"format=yuv420p[base];"
        )
    args += ["-filter_complex", pre + ";".join(chain), "-map", last,
             "-frames:v", str(frames), "-r", str(FPS),
             "-c:v", "libx264", "-preset", "medium", "-crf", "16",
             "-pix_fmt", "yuv420p", dst]
    run(args, sid)
    print(f"  {sid:16s} scene  {seg_len:6.2f}s  (cut {start:.2f}s lead-in"
          f"{', ' + str(len(clip['cuts'])) + ' edit' if clip['cuts'] else ''})")
    return dst, seg_len


def build_audio(lengths):
    """One continuous narration bed: each line at its beat, silence in between."""
    parts = []
    for scene in MANIFEST["scenes"]:
        starts = line_starts(scene)
        used = 0.0
        for i, line in enumerate(scene["lines"]):
            wav = os.path.join(WORK, f"a_{scene['id']}_{i}.wav")
            run(["ffmpeg", "-v", "error", "-y", "-i", line["file"],
                 "-ac", "2", "-ar", "48000", "-c:a", "pcm_s16le", wav], "tts->wav")
            parts.append(wav)
            used += probe(wav)
            if i + 1 < len(starts):
                pad = starts[i + 1] - starts[i] - probe(wav)
                if pad > 0.005:
                    parts.append(silence(pad, f"{scene['id']}_{i}"))
                    used += pad
        tail = lengths[scene["id"]] - used
        if tail > 0.005:
            parts.append(silence(tail, f"{scene['id']}_tail"))

    listing = os.path.join(WORK, "audio.txt")
    with open(listing, "w") as fh:
        for part in parts:
            fh.write(f"file '{part}'\n")
    raw = os.path.join(WORK, "narration_raw.wav")
    run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", listing,
         "-c", "copy", raw], "audio concat")

    final = os.path.join(WORK, "narration.wav")
    run(["ffmpeg", "-v", "error", "-y", "-i", raw,
         "-af", "highpass=f=70,acompressor=threshold=-19dB:ratio=2.6:attack=8:release=210,"
                "loudnorm=I=-16:TP=-1.5:LRA=9",
         "-ar", "48000", "-ac", "2", final], "audio master")
    return final


def silence(seconds, tag):
    path = os.path.join(WORK, f"sil_{tag}_{seconds:.3f}.wav")
    if not os.path.exists(path):
        run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi",
             "-i", "anullsrc=r=48000:cl=stereo", "-t", f"{seconds:.3f}",
             "-c:a", "pcm_s16le", path], "silence")
    return path


def main():
    for d in (SCENES_DIR, OUT, WORK):
        shutil.rmtree(d, ignore_errors=True)
        os.makedirs(d, exist_ok=True)

    print("scenes:")
    segments, lengths = [], {}
    for scene in MANIFEST["scenes"]:
        path, length = build_scene(scene)
        segments.append(path)
        lengths[scene["id"]] = length

    total = sum(lengths.values())
    print(f"video total {total:.2f}s ({int(total // 60)}m {total % 60:04.1f}s)")

    print("audio...")
    audio = build_audio(lengths)
    print(f"  narration {probe(audio):.2f}s")

    listing = os.path.join(WORK, "scenes.txt")
    with open(listing, "w") as fh:
        for seg in segments:
            fh.write(f"file '{seg}'\n")
    silent = os.path.join(WORK, "silent.mp4")
    run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", listing,
         "-c", "copy", silent], "concat scenes")

    fade_out = max(0.0, total - 0.9)
    mp4 = os.path.join(OUT, "vexen-demo.mp4")
    run(["ffmpeg", "-v", "error", "-y", "-i", silent, "-i", audio,
         "-filter_complex",
         f"[0:v]fade=t=in:st=0:d=0.5,fade=t=out:st={fade_out:.2f}:d=0.9[v];"
         f"[1:a]afade=t=in:st=0:d=0.35,afade=t=out:st={fade_out:.2f}:d=0.9[a]",
         "-map", "[v]", "-map", "[a]",
         "-c:v", "libx264", "-preset", "slow", "-crf", "21", "-profile:v", "high",
         "-level", "4.0", "-pix_fmt", "yuv420p", "-movflags", "+faststart",
         "-c:a", "aac", "-b:a", "128k", "-ar", "48000", "-shortest", mp4], "mp4")
    print(f"  mp4  {os.path.getsize(mp4) / 1e6:.1f} MB  {probe(mp4):.2f}s")

    poster = os.path.join(OUT, "vexen-demo-poster.png")
    run(["ffmpeg", "-v", "error", "-y", "-ss", "2.4", "-i", mp4, "-frames:v", "1",
         "-vf", "scale=1920:1080", poster], "poster")

    webm = os.path.join(OUT, "vexen-demo.webm")
    run(["ffmpeg", "-v", "error", "-y", "-i", mp4,
         "-c:v", "libvpx-vp9", "-crf", "34", "-b:v", "0", "-row-mt", "1",
         "-deadline", "good", "-cpu-used", "4", "-tile-columns", "2", "-threads", "8",
         "-pix_fmt", "yuv420p", "-c:a", "libopus", "-b:a", "96k", webm], "webm")
    print(f"  webm {os.path.getsize(webm) / 1e6:.1f} MB")
    print("BUILD COMPLETE")


if __name__ == "__main__":
    main()
