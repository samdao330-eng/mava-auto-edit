"""Render the World Unpaved lower third (a Premiere graphic in the channel's projects: text + shape + the
Impact Text Animator) as ONE clip that covers a whole section, built from three cached pieces:

  <prefix>-in.mov    0-3.6 s: a red bar grows from its middle, the name flies in letter by letter from the
                     right (motion-blurred), then everything shrinks to 70.9 % towards the bottom left
  <prefix>-hold.png  the small state, held over the rest of the section
  <prefix>-out.mov   the last 0.9 s: letters fly out right to left, then the bar slides away
joined into <out.mov> of exactly <frames> frames (QuickTime Animation with alpha: the held part costs almost
nothing, a whole section is a few seconds to encode and tens of MB). One clip per section on V2, not three
(user-set 2026-10-29).

Measured from "261015 World Unpaved - Amazon" FINAL (section "1. Gocta Waterfall"):
  large  bar x 130-142, y 1848-2023, rgb(213, 39, 39); white Be Vietnam Pro Regular caps, ink from x=201,
         caps 1888-1984 ("GOCTA WATERFALL" = 1249 px)
  small  the same scaled by 0.709 around (-117.5, 2233): bar 58-66 / 1960-2084, text from x=109, caps 1989-2057
  times  bar 0.29-0.66 s, letters 0.39-1.46 s, shrink 3.05-3.5 s; out: letters end-0.81 to end-0.28 s,
         bar end-0.28 to end-0.15 s

Usage: python render-lower-third-bar.py "<name>" <pieces prefix> <frames> <out.mov>
"""
import os, subprocess, sys
from PIL import Image, ImageDraw, ImageFont

text, prefix, total, out_mov = sys.argv[1].upper(), sys.argv[2], int(sys.argv[3]), sys.argv[4]
W, H, FPS = 3840, 2160, 30000 / 1001
HERE = os.path.dirname(os.path.abspath(__file__))
RED, WHITE = (213, 39, 39, 255), (255, 255, 255, 255)
BAR = (130, 1848, 142, 2023)                      # large state
INK_X, BASE = 194, 1984
SMALL, FIX = 0.709, (-117.5, 2233.0)              # shrink factor and the point that stays put
IN_DUR, OUT_DUR = 3.6, 0.9
OX, OY, CW, CH = 0, 1760, 3840, 400               # local canvas (large-state coordinates) holding the graphic

fnt = ImageFont.truetype(os.path.join(HERE, "fonts", "BeVietnamPro-Regular.ttf"), 130)


TRACK, SPACE = -5.9, 17       # px added after every letter / after a space (Premiere's word gap is wider)
# fitted on "GOCTA WATERFALL" and "PACAYA-SAMIRIA NATIONAL RESERVE": within ~20 px of the published
# glyph positions (Pillow here lays out without the font's kerning, Premiere with it)


def glyph_layout(s):
    """x of each character's pen position."""
    d = ImageDraw.Draw(Image.new("L", (1, 1)))
    x, pos = 0.0, []
    for ch in s:
        pos.append(x)
        x += d.textlength(ch, font=fnt) + TRACK + (SPACE if ch == " " else 0)
    left = d.textbbox((0, 0), s[0], font=fnt, anchor="ls")[0]
    return [INK_X - left + p for p in pos]


xs = glyph_layout(text)
glyphs = []                                       # (image, x, y) per visible character, local coordinates
for ch, x in zip(text, xs):
    if ch == " ":
        continue
    im = Image.new("RGBA", (260, 260), (0, 0, 0, 0))
    ImageDraw.Draw(im).text((60, 200), ch, font=fnt, fill=WHITE, anchor="ls")
    glyphs.append((im, x - 60 - OX, BASE - 200 - OY))


def smooth(t):
    t = max(0.0, min(1.0, t))
    return t * t * (3 - 2 * t)


def ease_out(t):
    t = max(0.0, min(1.0, t))
    return 1 - (1 - t) ** 3


def faded(im, a):
    o = im.copy()
    o.putalpha(im.getchannel("A").point(lambda v: int(v * a)))
    return o


def put(canvas, im, x, y, a, blur):
    """Paste a glyph at opacity a, smeared horizontally over blur px (the animator's motion blur)."""
    if a <= 0:
        return
    k = max(1, min(12, int(blur / 4)))
    for j in range(k):
        dx = blur * (j / (k - 1) - 0.5) if k > 1 else 0
        canvas.alpha_composite(faded(im, a / k if k > 1 else a), (int(round(x + dx)), int(round(y))))


def frame(letters, bar, scale):
    """letters: per glyph (opacity, dx, blur); bar: (opacity, height fraction, dx, width) in large px."""
    c = Image.new("RGBA", (CW, CH), (0, 0, 0, 0))
    ba, bh, bdx, bw = bar
    if ba > 0 and bh > 0:
        cy, h = (BAR[1] + BAR[3]) / 2 - OY, (BAR[3] - BAR[1]) * bh
        x0 = BAR[0] - OX + bdx
        ImageDraw.Draw(c).rectangle((x0, cy - h / 2, x0 + bw - 1, cy + h / 2), fill=RED[:3] + (int(255 * ba),))
    for (im, x, y), (a, dx, blur) in zip(glyphs, letters):
        put(c, im, x + dx, y, a, blur)
    out = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    if scale != 1:
        c = c.resize((max(1, round(CW * scale)), max(1, round(CH * scale))), Image.LANCZOS)
    x, y = round(FIX[0] + scale * (OX - FIX[0])), round(FIX[1] + scale * (OY - FIX[1]))
    if x < 0:                                     # the shrunk canvas starts left of the frame (empty there)
        c, x = c.crop((-x, 0, c.width, c.height)), 0
    out.alpha_composite(c, (x, y))
    return out


def at_in(t):
    n = len(glyphs)
    step = (1.46 - 0.39 - 0.2) / max(1, n - 1)
    letters = []
    for i in range(n):
        p = ease_out((t - 0.39 - i * step) / 0.2)
        letters.append((min(1.0, p * 1.4), 45 * (1 - p), 50 * (1 - p) if 0 < p < 1 else 0))
    g = ease_out((t - 0.29) / 0.37)
    bar = (1.0 if g > 0 else 0, g, 52 * (1 - g), 4 + 8 * g)
    return frame(letters, bar, 1 - (1 - SMALL) * smooth((t - 3.05) / 0.45))


def at_out(left):
    """left = seconds to the end of the section."""
    n = len(glyphs)
    step = (0.53 - 0.12) / max(1, n - 1)
    letters = []
    for i in range(n):
        p = smooth(((OUT_DUR - left) - (OUT_DUR - 0.81) - (n - 1 - i) * step) / 0.12)
        letters.append((1 - p, 60 * p, 50 * p if 0 < p < 1 else 0))
    g = smooth(((OUT_DUR - left) - (OUT_DUR - 0.28)) / 0.13)
    bar = (1 - g, 1 - 0.3 * g, 40 * g, 12 - 4 * g)
    return frame(letters, bar, SMALL)


def encode(path, frames):
    enc = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgba", "-s", f"{W}x{H}",
                            "-r", "30000/1001", "-i", "-", "-c:v", "prores_ks", "-profile:v", "4444",
                            "-pix_fmt", "yuva444p10le", "-alpha_bits", "16", path], stdin=subprocess.PIPE)
    for f in frames:
        enc.stdin.write(f.tobytes())
    enc.stdin.close()
    if enc.wait():
        sys.exit(f"ffmpeg failed: {path}")


n_in, n_out = int(round(IN_DUR * FPS)), int(round(OUT_DUR * FPS))
if not os.path.exists(prefix + "-out.mov"):            # the pieces depend only on the name: made once
    encode(prefix + "-in.mov", (at_in(i / FPS) for i in range(n_in)))
    at_in(IN_DUR).save(prefix + "-hold.png")
    encode(prefix + "-out.mov", (at_out((n_out - i) / FPS) for i in range(n_out)))

# in, the still repeated, out; a section shorter than in + out keeps the start of in and all of out
hold = total - n_in - n_out
a = min(n_in, total - n_out)
fc = (f"[0:v]format=rgba,trim=end_frame={max(1, a)},setpts=N/(30000/1001)/TB[a];"
      f"[1:v]format=rgba,loop=loop={max(0, hold - 1)}:size=1,trim=end_frame={max(1, hold)},"
      f"setpts=N/(30000/1001)/TB[b];[2:v]format=rgba,setpts=N/(30000/1001)/TB[c];"
      + ("[a][b][c]concat=n=3:v=1:a=0" if hold > 0 else "[a][c]concat=n=2:v=1:a=0"))
subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", prefix + "-in.mov", "-loop", "0", "-i", prefix + "-hold.png",
                "-i", prefix + "-out.mov", "-filter_complex", fc, "-r", "30000/1001", "-frames:v", str(total),
                "-c:v", "qtrle", "-g", "300", "-pix_fmt", "argb", out_mov], check=True)
print("lower third:", out_mov, total, "frames")
