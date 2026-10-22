"""Render the Docs Untold location lower third as a 4K ProRes 4444 .mov with alpha:
white map pin, place name in white Bebas Neue, region underneath in bronze.
Measured from the Bavaria episode: pin 152-288 x 1824-2002, title from x=326 with
"EAGLE'S NEST" 667 px wide (caps 1824-1940), region "BAVARIA" 225 px wide (1968-2030), ~8 s on screen. Title and
region slide up out of a mask, the pin pops in, and it all leaves in reverse.

Usage: python render-lower-third-pin.py "<Place>" "<Region>" <seconds> <out.mov>
"""
import os, subprocess, sys
from PIL import Image, ImageDraw, ImageFont

place, region, seconds, out = sys.argv[1].upper(), sys.argv[2].upper(), float(sys.argv[3]), sys.argv[4]
W, H, FPS = 3840, 2160, 30000 / 1001
HERE = os.path.dirname(os.path.abspath(__file__))
FONT = os.path.join(HERE, "fonts", "BebasNeue-Regular.ttf")
WHITE, BRONZE = (255, 255, 255, 255), (173, 124, 61, 255)
X_TEXT, TITLE_BASE, SUB_BASE = 320, 1940, 2030


def fitted(text, width):
    d = ImageDraw.Draw(Image.new("RGBA", (1, 1)))
    size = 40
    while d.textlength(text, font=ImageFont.truetype(FONT, size + 1)) <= width:
        size += 1
    return ImageFont.truetype(FONT, size)


title_font = fitted("EAGLE'S NEST", 667)       # same size for every place name
sub_font = fitted("BAVARIA", 225)


def layer(draw_fn):
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw_fn(ImageDraw.Draw(im))
    return im


def pin(d):
    # teardrop pin with a round hole, 136 x 178 px, top-left at (152, 1824)
    cx, cy, r = 220, 1892, 68
    d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=WHITE)
    d.polygon([(cx - 60, cy + 32), (cx + 60, cy + 32), (cx, 2002)], fill=WHITE)
    d.ellipse((cx - 28, cy - 28, cx + 28, cy + 28), fill=(0, 0, 0, 0))


title = layer(lambda d: d.text((X_TEXT, TITLE_BASE), place, font=title_font, fill=WHITE, anchor="ls"))
sub = layer(lambda d: d.text((X_TEXT, SUB_BASE), region, font=sub_font, fill=BRONZE, anchor="ls"))
pin_im = layer(pin)

n = int(round(seconds * FPS))
f = lambda s: int(round(s * FPS))


def progress(i, start, length):
    """0 -> 1 with ease-out between frame start and start+length."""
    t = min(1, max(0, (i - start) / max(1, length)))
    return 1 - (1 - t) ** 3


def masked_slide(src, base, p, height):
    """Text rises out of a mask whose lower edge is its baseline (+ descender room)."""
    if p <= 0:
        return None
    off = int((1 - p) * height)
    moved = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    moved.paste(src, (0, off), src)
    clip = Image.new("L", (W, H), 0)
    ImageDraw.Draw(clip).rectangle((0, 0, W, base + 12), fill=255)
    moved.putalpha(Image.composite(moved.getchannel("A"), Image.new("L", (W, H), 0), clip))
    return moved


enc = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgba", "-s", f"{W}x{H}",
                        "-r", "30000/1001", "-i", "-", "-c:v", "prores_ks", "-profile:v", "4444",
                        "-pix_fmt", "yuva444p10le", "-alpha_bits", "16", out], stdin=subprocess.PIPE)
for i in range(n):
    j = n - 1 - i                                       # frames left, for the exit
    p_title = min(progress(i, 0, f(0.35)), progress(j, f(0.25), f(0.35)))
    p_sub = min(progress(i, f(0.15), f(0.35)), progress(j, f(0.1), f(0.35)))
    p_pin = min(progress(i, f(0.3), f(0.25)), progress(j, 0, f(0.25)))
    fr = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    for lay in (masked_slide(title, TITLE_BASE, p_title, 150), masked_slide(sub, SUB_BASE, p_sub, 90)):
        if lay:
            fr.alpha_composite(lay)
    if p_pin > 0:                                       # pin pops in: scale about its tip
        s = 0.6 + 0.4 * p_pin
        box = pin_im.crop((150, 1820, 292, 2006))
        small = box.resize((max(1, int(box.width * s)), max(1, int(box.height * s))), Image.LANCZOS)
        a = small.getchannel("A").point(lambda v: int(v * p_pin))
        small.putalpha(a)
        fr.alpha_composite(small, (int(221 - small.width / 2), 2006 - small.height))
    enc.stdin.write(fr.tobytes())
enc.stdin.close()
enc.wait()
print("lower third:", out, n, "frames")
