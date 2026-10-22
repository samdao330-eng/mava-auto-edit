"""Render a location-name lower third as a 4K ProRes 4444 .mov with alpha, matching
the channel's template (measured from the Sierra Nevada episode): white uppercase
Jost Regular, bottom-left, no bar or shadow, quick fade in/out.

Usage: python render-lower-third.py "<Location name>" <seconds> <out.mov>
"""
import os, subprocess, sys
from PIL import Image, ImageDraw, ImageFont

name, seconds, out = sys.argv[1].upper(), float(sys.argv[2]), sys.argv[3]
W, H, FPS = 3840, 2160, 30000 / 1001
_bundled = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fonts", "Jost-Regular.ttf")
FONT = _bundled if os.path.exists(_bundled) else os.path.expanduser("~/Library/Fonts/Jost-Regular.ttf")
X, BASELINE = 130, 2068               # measured on the reference frame (4K)
REF_TEXT, REF_WIDTH = "YOSEMITE NATIONAL PARK", 1632   # reference text and its rendered width
FADE = int(0.2 * FPS)

# font size chosen so the reference title renders at the reference width
d = ImageDraw.Draw(Image.new("RGBA", (1, 1)))
size = 100
while d.textlength(REF_TEXT, font=ImageFont.truetype(FONT, size + 1)) <= REF_WIDTH:
    size += 1
font = ImageFont.truetype(FONT, size)
while d.textlength(name, font=font) > W - 2 * X:       # very long names shrink to fit
    font = ImageFont.truetype(FONT, font.size - 4)

card = Image.new("RGBA", (W, H), (0, 0, 0, 0))
ImageDraw.Draw(card).text((X, BASELINE), name, font=font, fill=(255, 255, 255, 255), anchor="ls")

n = int(round(seconds * FPS))
enc = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgba", "-s", f"{W}x{H}",
                        "-r", "30000/1001", "-i", "-", "-c:v", "prores_ks", "-profile:v", "4444",
                        "-pix_fmt", "yuva444p10le", "-alpha_bits", "16", out], stdin=subprocess.PIPE)
alpha = card.getchannel("A")
for i in range(n):
    a = min(1, i / FADE, (n - 1 - i) / FADE)
    fr = card if a >= 1 else card.copy()
    if a < 1:
        fr.putalpha(alpha.point(lambda v: int(v * a)))
    enc.stdin.write(fr.tobytes())
enc.stdin.close()
enc.wait()
print("lower third:", out, n, "frames, font size", font.size)
