"""Render the Earthcue quiz card as a 4K ProRes 4444 .mov with alpha:
"Quiz Time!", the question, a countdown bar that fills blue, four white answer
boxes (2x2) and animated dots. Layout matches the channel's quiz template.

Usage: python render-quiz.py "<question>\nA. ..\nB. ..\nC. ..\nD. .." <seconds> <out.mov> [scale,cx,cy[,answer]]
  scale,cx,cy: the channel shows the same card smaller, scaled about the point (cx, cy);
  answer: answers in bold, this many times larger (channel.json "quiz_fit"; Tripinsight 0.619,1920,1135,1.19).
"""
import os, re, subprocess, sys
from PIL import Image, ImageDraw, ImageFont

text, seconds, out = sys.argv[1], float(sys.argv[2]), sys.argv[3]
fit = [float(v) for v in sys.argv[4].split(",")] if len(sys.argv) > 4 else None
lines = [l.strip() for l in text.split("\n") if l.strip()]
question = lines[0]
answers = [re.sub(r"^[A-D][.)]\s*", "", l) for l in lines[1:5]]

W, H, FPS = 3840, 2160, 30000 / 1001
S = W / 1083                        # template was measured on a 1083px-wide frame
def font_path(name):
    """Fonts ship with the toolkit (fonts/); fall back to the user's installed fonts."""
    here = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fonts", name)
    return here if os.path.exists(here) else os.path.expanduser(f"~/Library/Fonts/{name}")


FONT = font_path("Montserrat-Bold.ttf")
SEMI = font_path("Montserrat-SemiBold.ttf")
BLUE, WHITE, DARK = (30, 144, 230, 255), (255, 255, 255, 255), (55, 55, 55, 255)


def px(v):
    return int(round(v * S))


def shadow_text(d, xy, s, font, anchor):
    d.text((xy[0] + px(1), xy[1] + px(1)), s, font=font, fill=(0, 0, 0, 90), anchor=anchor)
    d.text(xy, s, font=font, fill=WHITE, anchor=anchor)


# static layer: title, question, bar track, answer boxes
base = Image.new("RGBA", (W, H), (0, 0, 0, 0))
d = ImageDraw.Draw(base)
shadow_text(d, (W // 2, px(158)), "Quiz Time!", ImageFont.truetype(FONT, px(19)), "mm")
qf = ImageFont.truetype(FONT, px(33))
while d.textlength(question, font=qf) > px(900):      # long questions shrink to fit
    qf = ImageFont.truetype(FONT, qf.size - 4)
shadow_text(d, (W // 2, px(201)), question, qf, "mm")
bar_x0, bar_x1, bar_y, bar_h = px(183), px(895), px(247), px(4)
d.rectangle((bar_x0, bar_y - bar_h // 2, bar_x1, bar_y + bar_h // 2), fill=WHITE)
# a 4th quiz_fit value: the channel's answers are bold and this much larger
ANS_FONT = FONT if fit and len(fit) > 3 else SEMI
af = ImageFont.truetype(ANS_FONT, px(25 * (fit[3] if fit and len(fit) > 3 else 1)))
boxes = [(208, 272), (552, 272), (208, 337), (552, 337)]
for (bx, by), a in zip(boxes, answers):
    x0, y0, x1, y1 = px(bx), px(by), px(bx + 320), px(by + 48)
    d.rectangle((x0, y0, x1, y1), fill=WHITE)
    f = af
    while d.textlength(a, font=f) > (x1 - x0) * 0.9:
        f = ImageFont.truetype(ANS_FONT, f.size - 4)
    d.text(((x0 + x1) // 2, (y0 + y1) // 2), a, font=f, fill=DARK, anchor="mm")

def fitted(im):
    """Scale the whole card about (cx, cy) as the channel's sequence does."""
    if not fit:
        return im
    s, cx, cy = fit[:3]
    small = im.resize((int(W * s), int(H * s)), Image.LANCZOS)
    canvas = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    canvas.paste(small, (int(round(cx - cx * s)), int(round(cy - cy * s))))
    return canvas


n = int(round(seconds * FPS))
fade = int(0.3 * FPS)
enc =subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgba", "-s", f"{W}x{H}",
                        "-r", "30000/1001", "-i", "-", "-c:v", "prores_ks", "-profile:v", "4444",
                        "-pix_fmt", "yuva444p10le", "-alpha_bits", "16", out], stdin=subprocess.PIPE)
for i in range(n):
    fr = base.copy()
    d = ImageDraw.Draw(fr)
    # countdown bar fills left -> right over the whole hold
    fill_x = bar_x0 + int((bar_x1 - bar_x0) * min(1, i / max(1, n - fade)))
    d.rectangle((bar_x0, bar_y - bar_h // 2, fill_x, bar_y + bar_h // 2), fill=BLUE)
    # five dots, one lighting up every 0.4s
    lit = int(i / (0.4 * FPS)) % 6
    for k in range(5):
        cx, cy, r = W // 2 + px((k - 2) * 11), px(420), px(2.6)
        d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=WHITE if k < lit else (255, 255, 255, 110))
    # fade in / out
    a = min(1, i / fade, (n - 1 - i) / fade) if fade else 1
    if a < 1:
        alpha = fr.getchannel("A").point(lambda v: int(v * a))
        fr.putalpha(alpha)
    enc.stdin.write(fitted(fr).tobytes())
enc.stdin.close()
enc.wait()
fitted(base).save(out.rsplit(".", 1)[0] + "-still.png")
print("quiz:", out, n, "frames")
