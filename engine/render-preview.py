"""Render a 720p preview of edl.json that matches the Resolve timeline: same source
ranges, 25-frame cross dissolves, corner logo, Subscribe lower thirds, quiz card,
ENDING, and the VO / music / SFX mix.

Usage: python render-preview.py <edl.json> <logo.png> <out.mp4>
Needs Pillow for the quiz card (run with the venv python).
"""
import json, os, subprocess, sys, tempfile
from concurrent.futures import ThreadPoolExecutor
from PIL import Image, ImageDraw, ImageFont

edl = json.load(open(sys.argv[1]))
logo, out = sys.argv[2], sys.argv[3]
tmp = tempfile.mkdtemp(prefix="preview-")
W, H, FPS = 1280, 720, "30000/1001"
F = 30000 / 1001
D = edl["dissolve"]
shots = edl["shots"]
last = len(shots) - 1
DIS = set(edl.get("dissolve_at", []))
PD = edl.get("part_dissolve", D)


def overlap(i):
    """Dissolve length in frames between shot i-1 and shot i (longer at VO part changes)."""
    return PD if i in DIS else D


# 1) one 720p segment per shot, padded with half of each joining overlap
def render_seg(i, s):
    pre = overlap(i) // 2 if i else 0
    post = overlap(i + 1) - overlap(i + 1) // 2 if i < last else 0
    seg = os.path.join(tmp, f"{i:04d}.mp4")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-hwaccel", "videotoolbox",
                    "-ss", f"{(s['in_f'] - pre) / F:.4f}", "-i", s["path"],
                    "-frames:v", str(s["f1"] - s["f0"] + pre + post), "-an",
                    "-vf", f"scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},fps={FPS},format=yuv420p",
                    "-c:v", "h264_videotoolbox", "-b:v", "8M", seg], check=True)
    return seg


with ThreadPoolExecutor(6) as ex:                     # segments are independent; render in parallel
    segs = list(ex.map(lambda a: render_seg(*a), enumerate(shots)))

cards = []                                            # quiz is now a .mov in edl["overlays"]

# 3) one ffmpeg graph: xfade chain -> logo -> overlays -> audio mix
cmd = ["ffmpeg", "-v", "error", "-y"]
for p in segs:
    cmd += ["-i", p]
n = len(segs)
cmd += ["-loop", "1", "-framerate", FPS, "-i", logo]
idx_logo = n
ov = edl["overlays"]
for o in ov:
    cmd += ["-i", o["path"]]
for p, _, du in cards:
    cmd += ["-loop", "1", "-framerate", FPS, "-t", f"{du:.3f}", "-i", p]
# audio clips: (input index, start, dur, gain dB, fade). Each separate file gets its own input.
audio_inputs, audio = [], []


def add_audio(path, st, du, db, fade=True):
    audio_inputs.append(path)
    audio.append((n + 1 + len(ov) + len(cards) + len(audio_inputs) - 1, st, du, db, fade))


for c in edl["vo"]:
    add_audio(c["path"], float(c["start"]), float(c["dur"]), 0)
for c in edl["music"]:
    add_audio(c["path"], float(c["start"]), float(c["dur"]), -17)
for c in edl["sfx"]:
    add_audio(c["path"], float(c["start"]), float(c["dur"]), -24)
for k, o in enumerate(ov):                           # Subscribe whoosh, ENDING music
    if o["audio"] is None:
        continue
    if o["audio"] == o["path"]:
        audio.append((n + 1 + k, float(o["start"]), float(o["dur"]), 0, False))
    else:
        add_audio(o["audio"], float(o["start"]), float(o["dur"]), 0, fade=False)
for p in audio_inputs:
    cmd += ["-i", p]

fc = [f"[{i}:v]settb=AVTB,setpts=PTS-STARTPTS[s{i}]" for i in range(n)]
prev = "s0"
for i in range(1, n):
    off = (shots[i]["f0"] - overlap(i) // 2) / F
    fc.append(f"[{prev}][s{i}]xfade=transition=fade:duration={overlap(i) / F:.5f}:offset={off:.5f}[x{i}]")
    prev = f"x{i}"
fc.append(f"[{idx_logo}:v]scale={W}:{H}[lg]")
fc.append(f"[{prev}][lg]overlay=0:0:shortest=1[b0]")
base = "b0"
layers = [(n + 1 + k, float(o["start"])) for k, o in enumerate(ov)]
layers += [(n + 1 + len(ov) + k, st) for k, (_, st, _) in enumerate(cards)]
for k, (inp, st) in enumerate(layers):
    fc.append(f"[{inp}:v]scale={W}:{H},format=yuva420p,setpts=PTS-STARTPTS+{st:.4f}/TB[o{k}]")
    fc.append(f"[{base}][o{k}]overlay=0:0:eof_action=pass[b{k + 1}]")
    base = f"b{k + 1}"
labels = []
for k, (inp, st, du, db, fade) in enumerate(audio):
    ms = int(st * 1000)
    fx = f"afade=t=in:d=0.3,afade=t=out:st={max(0, du - 1):.3f}:d=1," if fade else ""
    fc.append(f"[{inp}:a]atrim=0:{du:.3f},{fx}volume={db}dB,aresample=48000,"
              f"aformat=channel_layouts=stereo,adelay={ms}|{ms}[a{k}]")
    labels.append(f"[a{k}]")
fc.append("".join(labels) + f"amix=inputs={len(labels)}:normalize=0[a]")
script = os.path.join(tmp, "graph.txt")
open(script, "w").write(";\n".join(fc))
cmd += ["-/filter_complex", script, "-map", f"[{base}]", "-map", "[a]",
        "-c:v", "h264_videotoolbox", "-b:v", "8M", "-c:a", "aac", "-b:a", "192k",
        "-t", f"{edl['total_s']:.3f}", out]
subprocess.run(cmd, check=True)
print("preview:", out)
