"""Render the Chaseland text graphics (Premiere text layers in the channel's projects) as 4K ProRes 4444
.mov with alpha. Measured from "260822 Chaseland - Australia" FINAL:

  lower  place / section name in white Be Vietnam Pro Regular caps, bottom left: glyphs from x=95,
         caps 1950-2069 ("SYDNEY HARBOUR" = 1480 px); fades in over 0.8 s and out over the last 25 frames.
         7.2 s.
  title  country name in white Futura Medium caps, centred (caps 921-1303, "AUSTRALIA" = 2640 px):
         comes in out of a blur 0.8-1.8 s, blurs and fades away 4.2-6.9 s. 7.04 s.

Usage: python render-caption.py lower|title "<text>" <seconds> <out.mov>
"""
import os, subprocess, sys
from PIL import Image, ImageDraw, ImageFilter, ImageFont

mode, text, seconds, out = sys.argv[1], sys.argv[2].upper(), float(sys.argv[3]), sys.argv[4]
W, H, FPS = 3840, 2160, 30000 / 1001
HERE = os.path.dirname(os.path.abspath(__file__))
FUTURA = "/System/Library/Fonts/Supplemental/Futura.ttc"        # macOS system font, index 0 = Medium


def layer(fnt, x, base, ref, anchor):
    """Text on a full-frame layer with the template's letter spacing, worked out from a measured sample."""
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    track = (ref[1] - d.textlength(ref[0], font=fnt)) / (len(ref[0]) - 1)
    total = d.textlength(text, font=fnt) + track * (len(text) - 1)
    left = d.textbbox((0, 0), text[0], font=fnt, anchor="ls")[0]
    cx = (x - total / 2 if anchor == "centre" else x - left)
    for ch in text:
        d.text((cx, base), ch, font=fnt, fill=(255, 255, 255, 255), anchor="ls")
        cx += d.textlength(ch, font=fnt) + track
    return im


def faded(im, a):
    o = im.copy()
    o.putalpha(im.getchannel("A").point(lambda v: int(v * max(0.0, min(1.0, a)))))
    return o


def smooth(t):
    t = max(0.0, min(1.0, t))
    return t * t * (3 - 2 * t)


if mode == "lower":
    base_im = layer(ImageFont.truetype(os.path.join(HERE, "fonts", "BeVietnamPro-Regular.ttf"), 159), 86, 2068,
                    ("SYDNEY HARBOUR", 1499), "left")
else:
    base_im = layer(ImageFont.truetype(FUTURA, 470, index=0), W / 2, 1297, ("AUSTRALIA", 2640), "centre")
box = base_im.getchannel("A").getbbox()
pad = 120
crop = (max(0, box[0] - pad), max(0, box[1] - pad), min(W, box[2] + pad), min(H, box[3] + pad))
small = base_im.crop(crop)

n = int(round(seconds * FPS))
enc = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgba", "-s", f"{W}x{H}",
                        "-r", "30000/1001", "-i", "-", "-c:v", "prores_ks", "-profile:v", "4444",
                        "-pix_fmt", "yuva444p10le", "-alpha_bits", "16", out], stdin=subprocess.PIPE)
for i in range(n):
    t, left = i / FPS, (n - 1 - i) / FPS
    if mode == "lower":
        a, blur = min(smooth(t / 0.8), smooth(left / (25 / FPS))), 0
    else:                                               # out of a blur in, back into one out
        p_in, p_out = smooth((t - 0.8) / 1.0), smooth((left - 0.15) / 2.7)
        a, blur = min(p_in, p_out), 40 * (1 - min(p_in, p_out))
    fr = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    if a > 0:
        lay = small.filter(ImageFilter.GaussianBlur(blur)) if blur > 0.5 else small
        fr.paste(faded(lay, a), crop[:2])
    enc.stdin.write(fr.tobytes())
enc.stdin.close()
enc.wait()
print(f"{mode}:", out, n, "frames")
