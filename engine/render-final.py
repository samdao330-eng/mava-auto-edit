"""Render the finished episode as a 4K MP4 straight from edl.json (no NLE needed):
same shots, dissolves, fade-through-black between sections, logo, lower thirds,
opening title, subscribe, ending, VO and music as the Resolve / Premiere timelines.

Long episodes are rendered section by section (each section is one ffmpeg run), then
the sections are joined without re-encoding and the audio mix is added.

Usage: python render-final.py <edl.json> <out.mp4> [--bitrate 60M] [--from N] [--keep-parts]
  --from N       resume: reuse already-rendered section files before section N
  --keep-parts   keep the per-section files in .autoedit/_render (removed after a successful run)
"""
import json, os, shutil, subprocess, sys

args = sys.argv[1:]
edl_path, out = args[0], args[1]
BITRATE = args[args.index("--bitrate") + 1] if "--bitrate" in args else "60M"
START_AT = int(args[args.index("--from") + 1]) if "--from" in args else 0
edl = json.load(open(edl_path))
W, H, R = 3840, 2160, "30000/1001"
F = 30000 / 1001
D, PD, DIP = edl["dissolve"], edl.get("part_dissolve", edl["dissolve"]), edl.get("dip", 25)
part_cuts = set(edl.get("dissolve_at", []))
shots = edl["shots"]
tmp = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(edl_path))), "_render")   # .autoedit/_render
os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
os.makedirs(tmp, exist_ok=True)

# sections = runs of shots between fade-through-black boundaries
bounds = [0] + [i for i, s in enumerate(shots) if s.get("dip")] + [len(shots)]
sections = [(bounds[k], bounds[k + 1]) for k in range(len(bounds) - 1)]
total_f = shots[-1]["f1"]
overlays = ([dict(path=edl["logo"], start=0.0, dur=total_f / F, still=True)] if edl.get("logo") else []) + \
           [dict(path=o["path"], start=float(o["start"]), dur=float(o["dur"]), still=o.get("still", False))
            for o in edl["overlays"]]


def overlap(i):
    return PD if i in part_cuts else D


def render_section(k, a, b):
    """Shots a..b-1 as one 4K file covering timeline frames [f_start, f_end)."""
    f_start = shots[a]["f0"]
    f_end = shots[b]["f0"] if b < len(shots) else total_f
    seg = os.path.join(tmp, f"section-{k:03d}.mov")
    cmd = ["ffmpeg", "-v", "error", "-y", "-hwaccel", "videotoolbox"]
    fc, labels = [], []
    for j, i in enumerate(range(a, b)):
        s = shots[i]
        pre = overlap(i) // 2 if j else 0
        # the last shot before a section break runs on through the black gap, like in Premiere;
        # a clip that ran out (gap_after) is followed by black up to the next shot
        end_f = shots[i + 1]["f0"] if i + 1 < b else f_end
        post = overlap(i + 1) - overlap(i + 1) // 2 if i + 1 < b else 0
        n = end_f - s["f0"] + pre + post
        real = s["f1"] - s["f0"] + pre if s.get("gap_after") else n
        black = f",tpad=stop_mode=add:stop={n - real}:color=black" if n > real else ""
        cmd += ["-ss", f"{(s['in_f'] - pre) / F:.4f}", "-t", f"{real / F + 1:.3f}", "-i", s["path"]]
        fc.append(f"[{j}:v]fps={R},scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},"
                  f"setsar=1,format=yuv420p,tpad=stop_mode=clone:stop={real},trim=end_frame={real}{black},"   # hold the last frame if a clip runs short
                  f"settb=AVTB,setpts=PTS-STARTPTS[s{j}]")
    prev = "s0"
    for j, i in enumerate(range(a + 1, b), start=1):
        off = (shots[i]["f0"] - overlap(i) // 2 - f_start) / F
        fc.append(f"[{prev}][s{j}]xfade=transition=fade:duration={overlap(i) / F:.5f}:offset={off:.5f}[x{j}]")
        prev = f"x{j}"
    # fade up from black over DIP frames at a section start, fade to black over the last DIP
    # frames before the next section (Premiere: end-black + start-black, one each side of the cut)
    v = f"[{prev}]"
    chain = []
    if k:
        chain.append(f"fade=t=in:st=0:d={DIP / F:.4f}")
    if b < len(shots):
        chain.append(f"fade=t=out:st={(f_end - DIP - f_start) / F:.4f}:d={DIP / F:.4f}")
    fc.append(f"{v}{','.join(chain) if chain else 'null'}[base]")
    base, n_in = "base", b - a
    # overlays that touch this section, shifted to section time
    for o in overlays:
        o0, o1 = o["start"] * F, (o["start"] + o["dur"]) * F
        if o1 <= f_start + 1 or o0 >= f_end - 1:          # ignore overlays that only touch the edge
            continue
        shift = (o0 - f_start) / F
        if o.get("still"):
            # a still runs for its own length (a held lower third), the logo for the whole section
            cmd += ["-loop", "1", "-framerate", R, "-t", f"{o['dur'] - max(0.0, -shift):.4f}", "-i", o["path"]]
            src_ss = 0
        else:
            src_ss = max(0.0, -shift)
            cmd += ["-ss", f"{src_ss:.4f}", "-i", o["path"]]
        lab = f"o{n_in}"
        fc.append(f"[{n_in}:v]format=yuva420p,settb=AVTB,setpts=PTS-STARTPTS+{max(0.0, shift):.4f}/TB[{lab}]")
        fc.append(f"[{base}][{lab}]overlay=0:0:eof_action=pass:shortest={1 if o.get('still') else 0}[b{n_in}]")
        base, n_in = f"b{n_in}", n_in + 1
    fc.append(f"[{base}]format=yuv420p[out]")             # encoder needs plain 4:2:0 after alpha overlays
    script = os.path.join(tmp, f"section-{k:03d}.txt")
    open(script, "w").write(";\n".join(fc))
    cmd += ["-/filter_complex", script, "-map", "[out]", "-frames:v", str(f_end - f_start),
            "-c:v", "hevc_videotoolbox", "-b:v", BITRATE, "-tag:v", "hvc1", "-r", R, seg]
    subprocess.run(cmd, check=True)
    return seg


segs = []
for k, (a, b) in enumerate(sections):
    seg = os.path.join(tmp, f"section-{k:03d}.mov")
    if k < START_AT and os.path.exists(seg):
        segs.append(seg)
        continue
    print(f"section {k + 1}/{len(sections)}: shots {a}-{b - 1}", flush=True)
    segs.append(render_section(k, a, b))

# audio: every VO slice and music cue at its timeline position
inputs, fc = [], []
for c in edl["vo"]:
    inputs.append((c["path"], float(c.get("src_in", 0)), float(c["dur"]), float(c["start"]), 0, False))
for c in edl["music"]:
    inputs.append((c["path"], 0.0, float(c["dur"]), float(c["start"]), edl.get("music_db", -17), True))
cmd = ["ffmpeg", "-v", "error", "-y"]
for k, (p, src_in, du, st, db, fade) in enumerate(inputs):
    cmd += ["-ss", f"{src_in:.4f}", "-t", f"{du:.4f}", "-i", p]
    fx = f"afade=t=in:d=0.5,afade=t=out:st={max(0, du - 2):.3f}:d=2," if fade else ""
    ms = int(round(st * 1000))
    fc.append(f"[{k}:a]{fx}volume={db}dB,aresample=48000,aformat=channel_layouts=stereo,adelay={ms}|{ms}[a{k}]")
fc.append("".join(f"[a{k}]" for k in range(len(inputs))) + f"amix=inputs={len(inputs)}:normalize=0[a]")
script = os.path.join(tmp, "audio.txt")
open(script, "w").write(";\n".join(fc))
mix = os.path.join(tmp, "mix.wav")
subprocess.run(cmd + ["-/filter_complex", script, "-map", "[a]", "-t", f"{total_f / F:.3f}", mix], check=True)

# join sections and add the mix
lst = os.path.join(tmp, "sections.txt")
open(lst, "w").write("".join(f"file '{s}'\n" for s in segs))
subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", lst, "-i", mix,
                "-map", "0:v", "-map", "1:a", "-c:v", "copy", "-c:a", "aac", "-b:a", "320k",
                "-movflags", "+faststart", out], check=True)
if "--keep-parts" not in args:
    shutil.rmtree(tmp)                                  # section files are only needed to resume
print("final:", out)
