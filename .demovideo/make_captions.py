"""Render the burned-in caption plates, so the demo reads perfectly on mute.

One transparent 1920x1080 PNG per narration line (chapter eyebrow + caption),
plus one "chapter only" plate per scene for the pauses between lines.
"""
import json
import os
import textwrap

from PIL import Image, ImageDraw, ImageFont

BASE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(BASE, "cards", "caps")

W, H = 1920, 1080
FIG_SEMI = "/usr/share/fonts/truetype/figtree/Figtree-SemiBold.ttf"
FIG_BOLD = "/usr/share/fonts/truetype/figtree/Figtree-Bold.ttf"
MONO = "/usr/share/fonts/truetype/robotomono/RobotoMono-Medium.ttf"

CAP_SIZE = 37
EYE_SIZE = 17
BAR_MAX = 1560
PAD_X, PAD_Y = 40, 26
LINE_H = 50
BOTTOM = 54
RADIUS = 20

BAR_FILL = (13, 25, 35, 234)
BAR_EDGE = (255, 255, 255, 34)
CAP_INK = (244, 249, 250, 255)
EYE_INK = (110, 208, 215, 255)
SHADOW = (10, 22, 32, 92)

cap_font = ImageFont.truetype(FIG_SEMI, CAP_SIZE)
eye_font = ImageFont.truetype(MONO, EYE_SIZE)


def text_w(draw, s, font):
    return draw.textlength(s, font=font)


def wrap_lines(draw, text, font, max_w):
    out = []
    for para in text.split("\n"):
        words, cur = para.split(), ""
        for word in words:
            probe = (cur + " " + word).strip()
            if text_w(draw, probe, font) <= max_w or not cur:
                cur = probe
            else:
                out.append(cur)
                cur = word
        out.append(cur)
    return [l for l in out if l != ""] or [""]


def draw_tracked(draw, xy, s, font, fill, tracking):
    x, y = xy
    for ch in s:
        draw.text((x, y), ch, font=font, fill=fill)
        x += draw.textlength(ch, font=font) + tracking
    return x - tracking - xy[0]


def tracked_w(draw, s, font, tracking):
    return sum(draw.textlength(c, font=font) for c in s) + tracking * (len(s) - 1)


def plate(caption, chapter):
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)

    lines = wrap_lines(d, caption, cap_font, BAR_MAX - 2 * PAD_X) if caption else []
    eyebrow = (chapter or "").upper()
    tracking = 3.0

    body_w = max([text_w(d, l, cap_font) for l in lines] or [0])
    if eyebrow:
        body_w = max(body_w, tracked_w(d, eyebrow, eye_font, tracking))
    bar_w = min(BAR_MAX, int(body_w) + 2 * PAD_X)
    bar_h = 2 * PAD_Y + (len(lines) * LINE_H if lines else 0) + (30 if eyebrow else 0)
    if lines:
        bar_h -= LINE_H - CAP_SIZE - 8

    x0 = (W - bar_w) // 2
    y1 = H - BOTTOM
    y0 = y1 - bar_h

    d.rounded_rectangle([x0 + 3, y0 + 7, x0 + bar_w + 3, y1 + 7], RADIUS, fill=SHADOW)
    d.rounded_rectangle([x0, y0, x0 + bar_w, y1], RADIUS, fill=BAR_FILL,
                        outline=BAR_EDGE, width=1)

    y = y0 + PAD_Y
    if eyebrow:
        ew = tracked_w(d, eyebrow, eye_font, tracking)
        draw_tracked(d, ((W - ew) / 2, y), eyebrow, eye_font, EYE_INK, tracking)
        y += 30
    for line in lines:
        lw = text_w(d, line, cap_font)
        d.text(((W - lw) / 2, y), line, font=cap_font, fill=CAP_INK)
        y += LINE_H
    return img


def main():
    os.makedirs(OUT, exist_ok=True)
    manifest = json.load(open(os.path.join(BASE, "manifest.json")))
    Image.new("RGBA", (W, H), (0, 0, 0, 0)).save(os.path.join(OUT, "blank.png"))
    made = 0
    for scene in manifest["scenes"]:
        chapter = scene.get("chapter")
        if chapter:
            plate("", chapter).save(os.path.join(OUT, f"{scene['id']}_pill.png"))
        else:
            Image.new("RGBA", (W, H), (0, 0, 0, 0)).save(
                os.path.join(OUT, f"{scene['id']}_pill.png"))
        for i, line in enumerate(scene["lines"]):
            plate(line["cap"], chapter).save(os.path.join(OUT, f"{scene['id']}_{i:02d}.png"))
            made += 1
    print(f"rendered {made} caption plates + {len(manifest['scenes'])} pill plates")


if __name__ == "__main__":
    main()
