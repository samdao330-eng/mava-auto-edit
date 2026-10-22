"""Make the full-frame 4K corner-logo overlay from a channel's logo PNG: the logo's
opaque area is cropped, scaled to <width> px wide, placed with its top-left at (x, y)
and multiplied by <opacity>. Positions are measured from each channel's published episodes
(see channel.json "logo_box").

Usage: python make-logo-overlay.py <logo.png> <out.png> <x> <y> <width> [opacity]
"""
import sys
from PIL import Image

src, out = sys.argv[1], sys.argv[2]
x, y, w = (int(v) for v in sys.argv[3:6])
opacity = float(sys.argv[6]) if len(sys.argv) > 6 else 1.0
im = Image.open(src).convert("RGBA")
box = im.getchannel("A").point(lambda v: 255 if v > 128 else 0).getbbox()
im = im.crop(box)
im = im.resize((w, round(im.height * w / im.width)), Image.LANCZOS)
if opacity < 1:
    im.putalpha(im.getchannel("A").point(lambda v: int(v * opacity)))
frame = Image.new("RGBA", (3840, 2160), (0, 0, 0, 0))
frame.paste(im, (x, y), im)
frame.save(out)
print("logo overlay:", out)
