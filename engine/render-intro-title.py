"""Render the opening title (the episode's region, e.g. PATAGONIA) as a 4K ProRes 4444
.mov with alpha: large white serif caps centred a little above the middle. The letters
start widely spaced and faint, close up to normal spacing while fading in, hold, then
fade out. Matches the Docs Untold opening (Bavaria episode).

Usage: python render-intro-title.py "<Title>" <seconds> <out.mov> [font file]
"""
import os, subprocess, sys
from PIL import Image, ImageDraw, ImageFont

text, seconds, out = sys.argv[1].upper(), float(sys.argv[2]), sys.argv[3]
HERE = os.path.dirname(os.path.abspath(__file__))
FONT = sys.argv[4] if len(sys.argv) > 4 else os.path.join(HERE, "fonts", "BunyanPro-Medium.otf")
W, H, FPS = 3840, 2160, 30000 / 1001
CY = int(H * 0.47)                       # vertical centre of the caps
TARGET_W = 2150                          # "BAVARIA" spans ~56% of the frame in the reference

d = ImageDraw.Draw(Image.new("RGBA", (1, 1)))
size = 100
while d.textlength(text, font=ImageFont.truetype(FONT, size + 4)) <= TARGET_W:
    size += 4
font = ImageFont.truetype(FONT, size)
widths = [d.textlength(c, font=font) for c in text]

n = int(round(seconds * FPS))
f = lambda s: int(round(s * FPS))
enc = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgba", "-s", f"{W}x{H}",
                        "-r", "30000/1001", "-i", "-", "-c:v", "prores_ks", "-profile:v", "4444",
                        "-pix_fmt", "yuva444p10le", "-alpha_bits", "16", out], stdin=subprocess.PIPE)
for i in range(n):
    t_in = min(1, i / f(2.0))
    ease = 1 - (1 - t_in) ** 3
    track = (1 - ease) * size * 0.45                    # extra space between letters
    alpha = min(1, i / f(1.5), (n - 1 - i) / f(1.0))
    total = sum(widths) + track * (len(text) - 1)
    x = (W - total) / 2
    fr = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    dr = ImageDraw.Draw(fr)
    for c, w in zip(text, widths):
        dr.text((x, CY), c, font=font, fill=(255, 255, 255, int(255 * alpha)), anchor="lm")
        x += w + track
    enc.stdin.write(fr.tobytes())
enc.stdin.close()
enc.wait()
print("intro title:", out, n, "frames")
