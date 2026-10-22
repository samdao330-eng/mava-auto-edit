"""Render the Tripinsight ES / PT location lower thirds as 4K ProRes 4444 .mov with alpha.
Measured from "260414 Tripinsight - Colombia" FINAL ES / FINAL PT (the "LOWER THIRD ES" MOGRT at 100 %,
"PT LOWER THIRD" at 60 %):

  box   (ES): orange box (240,109,0) 216-393 x 1864-1991 with the 2-digit number in white Montserrat
        ExtraBold (caps 1894-1963); spacing of the texts from the template's own "09 LOCATION" sample
        (user-set 2026-10-22): place in white Montserrat Bold from x=421 (caps 1888-1926, "LOCATION" = 292 px),
        orange line 421-830 x 1934-1937, region in Montserrat Bold 7 px under the line (caps 1944-1965,
        "COLOMBIA" = 187 px). The box grows from its centre, the line from the left, the texts wipe in; at the end
        everything collapses back. 6.97 s.
  frame (PT): measured on the template's own render "PT LOWER THIRD_Rendered.mov" (user-set 2026-10-22):
        green outlines (33,196,111), 5 px: number square 134-354 and frame 378-1324, both 1816-2037; green bar
        (4,163,93) 404-1298 x 1920-2008 with the place in white Montserrat Bold centred (caps 1946-1978);
        region in light grey (234) Montserrat Medium centred above (caps 1858-1889, "TÊN BÀI" = 181 px);
        2-digit number in pale green (152,225,177) Montserrat SemiBold 103 centred in the square
        ("20" = 129 x 76 px, 1890-1965). 6.31 s.

Usage: python render-lower-third-lang.py box|frame <number> "<Place>" "<Region>" <seconds> <out.mov>
"""
import os, subprocess, sys
from PIL import Image, ImageDraw, ImageFont

style, number, place, region = sys.argv[1], sys.argv[2], sys.argv[3].upper(), sys.argv[4].upper()
seconds, out = float(sys.argv[5]), sys.argv[6]
W, H, FPS = 3840, 2160, 30000 / 1001
HERE = os.path.dirname(os.path.abspath(__file__))
WHITE = (255, 255, 255, 255)
BOX = (100, 1780, 1500, 2080)                           # everything is drawn inside this crop
BW, BH = BOX[2] - BOX[0], BOX[3] - BOX[1]
CAP = 0.736                                             # Montserrat cap height / font size


def font(name, cap_px):
    return ImageFont.truetype(os.path.join(HERE, "fonts", name), int(round(cap_px / CAP)))


def text_layer(text, fnt, x, base, ref=None, fill=WHITE, anchor="left"):
    """Text on a crop-sized layer. ref = (sample text, its measured width): the template's letter
    spacing, worked out from that sample and used for any text."""
    im = Image.new("RGBA", (BW, BH), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    plain = d.textlength(text, font=fnt)
    track = (ref[1] - d.textlength(ref[0], font=fnt)) / (len(ref[0]) - 1) if ref else 0
    total = plain + track * (len(text) - 1)
    cx = x - BOX[0] - (total / 2 if anchor == "centre" else 0)
    for ch in text:
        d.text((cx, base - BOX[1]), ch, font=fnt, fill=fill, anchor="ls")
        cx += d.textlength(ch, font=fnt) + track
    return im


def ease(t):
    t = min(1.0, max(0.0, t))
    return 1 - (1 - t) ** 3


def faded(im, a):
    if a >= 1:
        return im
    o = im.copy()
    o.putalpha(im.getchannel("A").point(lambda v: int(v * max(0.0, a))))
    return o


def wiped(im, x0, x1, p, from_right=False):
    """Show the part of `im` between x0 and x1 (frame coords) revealed by progress p."""
    if p <= 0:
        return None
    if p >= 1:
        return im
    mask = Image.new("L", (BW, BH), 0)
    a, b = x0 - BOX[0], x1 - BOX[0]
    edge = a + (b - a) * p
    ImageDraw.Draw(mask).rectangle(((b - (edge - a)) if from_right else 0, 0, BW if from_right else edge, BH), fill=255)
    o = im.copy()
    o.putalpha(Image.composite(im.getchannel("A"), Image.new("L", (BW, BH), 0), mask))
    return o


def rect(d, x0, y0, x1, y1, fill):
    d.rectangle((x0 - BOX[0], y0 - BOX[1], x1 - BOX[0], y1 - BOX[1]), fill=fill)


n = int(round(seconds * FPS))
T = seconds
if style == "box":
    ORANGE, LINE = (240, 109, 0, 255), (245, 130, 20, 255)
    num_im = text_layer(number.zfill(2), font("Montserrat-ExtraBold.ttf", 69), 304.5, 1963, anchor="centre")
    place_im = text_layer(place, font("Montserrat-Bold.ttf", 38), 421, 1926, ref=("LOCATION", 292))
    region_im = text_layer(region, font("Montserrat-Bold.ttf", 21), 421, 1965, ref=("COLOMBIA", 187))

    def frame(t):
        c = Image.new("RGBA", (BW, BH), (0, 0, 0, 0))
        out_t = T - t                                   # time left, for the exit
        s = min(ease((t - 0.3) / 0.5), ease((out_t - 0.5) / 0.5))
        s = 0.2 + 0.8 * s if min(t - 0.2, out_t - 0.4) > 0 else 0
        if s > 0:                                       # box (with its number) scales about its centre
            cx, cy, hw, hh = 304.5, 1927.5, 88.5 * s, 63.5 * s
            layer = Image.new("RGBA", (BW, BH), (0, 0, 0, 0))
            rect(ImageDraw.Draw(layer), cx - hw, cy - hh, cx + hw, cy + hh, ORANGE)
            num = num_im.resize((max(1, int(BW * s)), max(1, int(BH * s))), Image.LANCZOS)
            layer.alpha_composite(num, (int(cx - BOX[0] - (cx - BOX[0]) * s), int(cy - BOX[1] - (cy - BOX[1]) * s)))
            c.alpha_composite(layer)
        pl = min(ease((t - 0.3) / 0.7), ease((out_t - 0.45) / 0.5))
        if pl > 0:                                      # line grows from the left
            rect(ImageDraw.Draw(c), 421, 1934, 421 + 409 * pl, 1937, LINE)
        exit_txt = ease((out_t - 1.0) / 0.4)
        for im, x0, x1, start in ((place_im, 421, 1400, 0.6), (region_im, 421, 1000, 0.8)):
            w = wiped(im, x0, x1, min(ease((t - start) / 0.5), exit_txt))
            if w:
                c.alpha_composite(w)
        return c
else:
    # Timings / positions read frame by frame off the template's own render (PT LOWER THIRD_Rendered.mov,
    # 6.31 s): the outlines draw out from a point on their bottom edge, the region appears word by word,
    # the bar wipes in from the right with the name sliding into place inside it, and the number rolls in
    # like a counter. The exit runs on the template's clock counted back from the end.
    LINE, BAR, NUM, GREY = (33, 196, 111, 255), (4, 163, 93, 255), (152, 225, 177, 255), (234, 234, 234, 255)
    TPL_T = 6.3063
    place_im = text_layer(place, font("Montserrat-Bold.ttf", 32), 851.5, 1978, ref=("CIUDAD PERDIDA", 445),
                          anchor="centre")
    reg_font = font("Montserrat-Medium.ttf", 30)
    num_im = text_layer(number.zfill(2), ImageFont.truetype(os.path.join(HERE, "fonts", "Montserrat-SemiBold.ttf"), 103),
                        244, 1965, fill=NUM, anchor="centre")

    def word_layers(text, fnt, cx, base, ref):
        """One layer per word of a centred, letter-spaced line (the template shows them one by one)."""
        d = ImageDraw.Draw(Image.new("RGBA", (1, 1)))
        track = (ref[1] - d.textlength(ref[0], font=fnt)) / (len(ref[0]) - 1)
        total = d.textlength(text, font=fnt) + track * (len(text) - 1)
        x, layers, cur = cx - BOX[0] - total / 2, [], None
        for ch in text:
            if ch == " " or cur is None:
                cur = Image.new("RGBA", (BW, BH), (0, 0, 0, 0)); layers.append(cur)
            ImageDraw.Draw(cur).text((x, base - BOX[1]), ch, font=fnt, fill=GREY, anchor="ls")
            x += d.textlength(ch, font=fnt) + track
        return layers

    region_words = word_layers(region, reg_font, 851.5, 1889, ("TÊN BÀI", 181))

    def table(points, t):
        """Linear interpolation in a (time, value) table measured on the template."""
        if t <= points[0][0]:
            return points[0][1]
        for (t0, v0), (t1, v1) in zip(points, points[1:]):
            if t <= t1:
                return v0 + (v1 - v0) * (t - t0) / (t1 - t0)
        return points[-1][1]

    BAR_IN = [(0.385, 1298), (0.435, 1292), (0.535, 1256), (0.635, 1184), (0.735, 1052), (0.8, 944), (0.87, 840),
              (0.935, 752), (1.0, 678), (1.07, 618), (1.135, 572), (1.2, 532), (1.27, 502), (1.335, 476), (1.4, 456),
              (1.47, 440), (1.535, 428), (1.635, 416), (1.735, 407), (1.835, 404)]
    BAR_OUT = [(4.6, 404), (4.7, 410), (4.8, 419), (4.9, 434), (5.0, 458), (5.1, 488), (5.2, 533), (5.3, 596),
               (5.4, 680), (5.5, 794), (5.6, 944), (5.7, 1100), (5.8, 1214), (5.9, 1274), (6.0, 1298)]
    NAME_IN = [(0.9, -200), (0.935, -187), (1.0, -153), (1.07, -123), (1.135, -97), (1.2, -77), (1.27, -59),
               (1.335, -47), (1.4, -35), (1.47, -27), (1.6, -12), (1.8, -3), (2.0, 0)]
    # outlines: a stroke runs round the frame from a point on its bottom edge (right, up, left, down), a
    # second one follows 0.35 s behind, and the head wraps on until the loop is closed (trim paths in the
    # template). Head / tail as shares of the perimeter; the exit plays the same backwards.
    HEAD = [(0.05, 0), (0.1, .01), (0.2, .065), (0.3, .183), (0.4, .386), (0.5, .64), (0.6, .86), (0.7, 1.03),
            (0.8, 1.15), (0.9, 1.27)]
    TAIL = [(0.1, 0), (0.2, .017), (0.3, .051), (0.4, .11), (0.5, .185), (0.6, .25)]

    def segments(t):
        """Drawn spans of the outline (shares of the perimeter from the start point) at entry time t."""
        if t <= 0.05:
            return []
        if t >= 0.9:
            return [(0, 1)]
        spans = [(table(TAIL, t), table(HEAD, t))]
        if t > 0.4:
            spans.append((table(TAIL, t - 0.35), table(HEAD, t - 0.35)))
        return spans

    def outline(d, x0, y0, x1, y1, xs, spans):
        """Rectangle outline (5 px): draw the given spans, measured from (xs, bottom edge) going right."""
        w, h = x1 - x0, y1 - y0
        per = 2 * (w + h)
        sides = [((x0, y0), (x1, y0)), ((x1, y0), (x1, y1)), ((x1, y1), (x0, y1)), ((x0, y1), (x0, y0))]

        def draw(a, b):                                  # perimeter span a..b (clockwise from top-left)
            pos = 0
            for (ax, ay), (bx, by) in sides:
                ln = abs(bx - ax) + abs(by - ay)
                lo, hi = max(a, pos), min(b, pos + ln)
                if lo < hi:
                    f0, f1 = (lo - pos) / ln, (hi - pos) / ln
                    px0, py0 = ax + (bx - ax) * f0, ay + (by - ay) * f0
                    px1, py1 = ax + (bx - ax) * f1, ay + (by - ay) * f1
                    rect(d, min(px0, px1) - 2, min(py0, py1) - 2, max(px0, px1) + 2, max(py0, py1) + 2, LINE)
                pos += ln

        s0 = w + h + (x1 - xs)                           # the start point, clockwise from the top-left corner
        for u0, u1 in spans:
            if u1 - u0 >= 1:
                draw(0, per)
                continue
            a, b = (s0 - u1 * per) % per, (s0 - u0 * per) % per   # going right along the bottom = backwards
            if a <= b:
                draw(a, b)
            else:
                draw(a, per); draw(0, b)

    D, P = 807, 230                                      # number roll: distance and spacing of the copies
    num_mask = Image.new("L", (BW, BH), 0)
    ImageDraw.Draw(num_mask).rectangle((139 - BOX[0], 1821 - BOX[1], 349 - BOX[0], 2032 - BOX[1]), fill=255)

    def frame(t):
        c = Image.new("RGBA", (BW, BH), (0, 0, 0, 0))
        d = ImageDraw.Draw(c)
        te = t - (T - TPL_T)                             # the template's clock, for the exit
        tf = min(t, TPL_T + 0.1 - te)                    # the frame: entry clock, or the exit run backwards
        outline(d, 378, 1816, 1324, 2037, 578, segments(tf))
        tq = min((t - 0.55) * 1.4 + 0.05, (TPL_T + 0.05 - te - 0.55) * 1.4 + 0.05)   # square: later and quicker
        outline(d, 134, 1816, 354, 2037, 222, segments(tq))
        left = max(table(BAR_IN, t), table(BAR_OUT, te))
        if t >= 0.35 and left < 1298:                    # bar from its left edge to 1298, name inside it
            bar = Image.new("RGBA", (BW, BH), (0, 0, 0, 0))
            rect(ImageDraw.Draw(bar), left, 1920, 1298, 2008, BAR)
            if t >= 0.9:
                bar.alpha_composite(place_im, (int(round(table(NAME_IN, t))), 0))
            clip = Image.new("L", (BW, BH), 0)
            ImageDraw.Draw(clip).rectangle((left - BOX[0], 0, 1298 - BOX[0], BH), fill=255)
            bar.putalpha(Image.composite(bar.getchannel("A"), Image.new("L", (BW, BH), 0), clip))
            c.alpha_composite(bar)
        k = len(region_words)
        for i, wl in enumerate(region_words):            # words appear one by one, leave last-first
            a = min((t - (0.25 + 0.3 * i)) / 0.12, ((4.2 + 0.4 * (k - 1 - i)) - te) / 0.12) if k > 1 else \
                min((t - 0.25) / 0.12, (4.2 - te) / 0.12)
            if a > 0:
                c.alpha_composite(faded(wl, min(1.0, a)))
        if 1.2 <= t and te <= 5.2:                       # number rolls in (eases to a stop), rolls out
            o = D * (1 - min(1, (t - 1.2) / 1.3)) ** 3 if te < 4.0 else D * min(1, (te - 4.0) / 1.2) ** 3
            strip = Image.new("RGBA", (BW, BH), (0, 0, 0, 0))
            for j in range(3):
                strip.alpha_composite(num_im, (int(round(o - j * P)), 0)) if -BW < o - j * P < BW else None
            strip.putalpha(Image.composite(strip.getchannel("A"), Image.new("L", (BW, BH), 0), num_mask))
            c.alpha_composite(strip)
        return c

enc = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgba", "-s", f"{W}x{H}",
                        "-r", "30000/1001", "-i", "-", "-c:v", "prores_ks", "-profile:v", "4444",
                        "-pix_fmt", "yuva444p10le", "-alpha_bits", "16", out], stdin=subprocess.PIPE)
for i in range(n):
    fr = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    fr.paste(frame(i / FPS), BOX[:2])
    enc.stdin.write(fr.tobytes())
enc.stdin.close()
enc.wait()
print("lower third:", out, n, "frames")
