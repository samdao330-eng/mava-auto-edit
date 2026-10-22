"""Render the Tripinsight location lower third as a 4K ProRes 4444 .mov with alpha:
the location number inside a white bracket with a coral offset bracket, the place name in
white Montserrat Bold caps and the region in small Montserrat italic caps underneath.
Measured from "260414 Tripinsight - Colombia" (LOWER_THIRDS_4K_20 MOGRT at 40 %):
white lines 209-327 x 1871-1988 (+ bottom to 481), coral 234-677 x 1863-1980,
number centred on x=268 (caps 1904-1962), place from x=361 (caps 1869-1916, "FILANDIA" = 352 px),
region from x=361 (caps 1939-1959, "COLOMBIA" = 165 px), 5.97 s on screen.
Lines grow out from their centres, the name wipes in left to right, then the number and
the region; everything fades out over the last 25 frames (the reference's cross dissolve).

Usage: python render-lower-third-bracket.py <number> "<Place>" "<Region>" <seconds> <out.mov>
"""
import os, subprocess, sys
from PIL import Image, ImageDraw, ImageFont

number, place, region = sys.argv[1], sys.argv[2].upper(), sys.argv[3].upper()
seconds, out = float(sys.argv[4]), sys.argv[5]
W, H, FPS = 3840, 2160, 30000 / 1001
HERE = os.path.dirname(os.path.abspath(__file__))
font = lambda name, size: ImageFont.truetype(os.path.join(HERE, "fonts", name), size)
WHITE, CORAL = (255, 255, 255, 255), (246, 103, 80, 255)
BOX = (150, 1800, 1650, 2040)                          # everything is drawn inside this crop
X_TEXT, PLACE_BASE, REGION_BASE, NUM_X, NUM_BASE = 361, 1916, 1959, 268, 1962

# lines as (x0, y0, x1, y1, colour, grows "h" or "v")
LINES = [(209, 1871, 327, 1873, WHITE, "h"), (209, 1871, 211, 1911, WHITE, "v"),
         (325, 1871, 327, 1988, WHITE, "v"), (325, 1986, 481, 1988, WHITE, "h"),
         (234, 1863, 335, 1865, CORAL, "h"), (333, 1863, 335, 1980, CORAL, "v"),
         (333, 1978, 677, 1980, CORAL, "h")]


def text_layer(text, fnt, x_left, base, shear=0.0):
    """Text whose glyphs start exactly at x_left, sitting on base; optional italic shear."""
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    left = d.textbbox((0, 0), text, font=fnt, anchor="ls")[0]
    d.text((x_left - left, base), text, font=fnt, fill=WHITE, anchor="ls")
    if shear:                                            # Montserrat has no italic here: slant it
        im = im.transform(im.size, Image.AFFINE, (1, shear, -shear * base, 0, 1, 0), Image.BICUBIC)
    return im.crop(BOX)


place_im = text_layer(place, font("Montserrat-Bold.ttf", 69), X_TEXT, PLACE_BASE)
region_im = text_layer(region, font("Montserrat-Medium.ttf", 28), X_TEXT, REGION_BASE, shear=0.21)
num_im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
ImageDraw.Draw(num_im).text((NUM_X, NUM_BASE), number, font=font("Montserrat-ExtraBold.ttf", 77),
                            fill=WHITE, anchor="ms")
num_im = num_im.crop(BOX)


def ease(t):
    t = min(1.0, max(0.0, t))
    return 1 - (1 - t) ** 3


def faded(im, a):
    if a >= 1:
        return im
    out = im.copy()
    out.putalpha(im.getchannel("A").point(lambda v: int(v * a)))
    return out


n = int(round(seconds * FPS))
fade_out = 25
bw, bh = BOX[2] - BOX[0], BOX[3] - BOX[1]
enc = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgba", "-s", f"{W}x{H}",
                        "-r", "30000/1001", "-i", "-", "-c:v", "prores_ks", "-profile:v", "4444",
                        "-pix_fmt", "yuva444p10le", "-alpha_bits", "16", out], stdin=subprocess.PIPE)
for i in range(n):
    t = i / FPS
    crop = Image.new("RGBA", (bw, bh), (0, 0, 0, 0))
    d = ImageDraw.Draw(crop)
    p = ease((t - 0.1) / 0.6)                           # lines grow from their centres
    for x0, y0, x1, y1, col, axis in LINES:
        if p <= 0:
            break
        if axis == "h":
            c, half = (x0 + x1) / 2, (x1 - x0) / 2 * p
            x0, x1 = c - half, c + half
        else:
            c, half = (y0 + y1) / 2, (y1 - y0) / 2 * p
            y0, y1 = c - half, c + half
        d.rectangle((x0 - BOX[0], y0 - BOX[1], x1 - BOX[0], y1 - BOX[1]), fill=col)
    # place name: soft-edged wipe from left to right
    pw = ease((t - 0.45) / 0.5)
    if pw > 0:
        edge = X_TEXT - BOX[0] + int(pw * (bw - (X_TEXT - BOX[0])))
        mask = Image.new("L", (bw, bh), 0)
        md = ImageDraw.Draw(mask)
        md.rectangle((0, 0, max(0, edge - 120), bh), fill=255)
        for k in range(120):                            # 120 px feather at the wipe edge
            md.line((edge - 120 + k, 0, edge - 120 + k, bh), fill=255 - int(255 * k / 120))
        lay = place_im.copy()
        lay.putalpha(Image.composite(place_im.getchannel("A"), Image.new("L", (bw, bh), 0), mask))
        crop.alpha_composite(lay)
    pn = ease((t - 0.85) / 0.35)                        # number: fades in, rising slightly
    if pn > 0:
        crop.alpha_composite(faded(num_im, pn), (0, int((1 - pn) * 18)))
    pr = ease((t - 1.5) / 0.4)                          # region: fades in, rising slightly
    if pr > 0:
        crop.alpha_composite(faded(region_im, pr), (0, int((1 - pr) * 12)))
    a = min(1.0, (n - 1 - i) / fade_out)
    fr = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    fr.paste(faded(crop, a), BOX[:2])
    enc.stdin.write(fr.tobytes())
enc.stdin.close()
enc.wait()
print("lower third:", out, n, "frames")
