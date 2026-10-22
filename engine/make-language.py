"""Make another language's edit (ES, PT) from the finished EN edit of the same episode: the EN
timeline is copied, its sections are put in that language's order (the numbers in the script's ES / PT
headings), the VO is replaced by the language's own files and every shot / graphic is re-timed to it.

  - VO: each section's language files are cut at their longest pauses into as many slices as the EN
    section has sentence slices, and laid out with the EN pauses after them. Slice i of the language
    takes the place of EN slice i: the shots under it are stretched / squeezed to its length.
    (When the language has more files than EN has slices, the whole section is stretched evenly.)
  - Graphics: the language's logo, lower third (its own number and name), subscribe and ending
    (channel.json "languages"); quiz re-rendered with the language's question; QR card kept.
  - Music: the EN songs in the same order, re-laid to the new length.

Footage is not re-matched to the translated text: it keeps the EN line order and timing ratio.
Build the EN edit first (autoedit edit).

Usage: python make-language.py "<episode folder>" ES|PT [--en-work DIR] [--out DIR]
Output: <episode>/<LANG>/<name>.xml (+ MEDIA/, .autoedit/), name = folder name with " <LANG> - ".
"""
import glob, json, os, re, shutil, subprocess, sys, unicodedata
from fractions import Fraction

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import channel
root, LANG = os.path.abspath(sys.argv[1].rstrip("/")), sys.argv[2].upper()
CH = channel.load(root)
opt = lambda name: sys.argv[sys.argv.index(name) + 1] if name in sys.argv else None   # --en-work / --out (tests)
LC = CH["languages"][LANG]
TEMPLATE = CH["template"]
# the EN edit lives in <episode>/EN (Tripinsight) or in the episode folder itself (Earthcue)
EN_WORK = opt("--en-work") or next((d for d in (os.path.join(root, "EN", ".autoedit", "_work"),
                                                os.path.join(root, ".autoedit", "_work"))
                                    if os.path.exists(os.path.join(d, "edl.json"))), None)
if not EN_WORK:
    sys.exit('Chưa có bản EN: chạy  autoedit edit "<tập>"  trước')
OUT_DIR = opt("--out") or os.path.join(root, LANG)
GEN = os.path.join(OUT_DIR, ".autoedit")
WORK = os.path.join(GEN, "_work")
MEDIA = os.path.join(OUT_DIR, "MEDIA")
base = os.path.basename(root)
NAME = base.replace(" - ", f" {LANG} - ", 1) if " - " in base else f"{base} {LANG}"
REGION = base.split(" - ")[-1] if " - " in base else ""
FPS = Fraction(30000, 1001)
DISSOLVE, DIP, PART_DISSOLVE, CUT_LEAD = 25, 25, 30, 0.25
HANDLE = Fraction(1, 2)
os.makedirs(WORK, exist_ok=True)

ep = json.load(open(os.path.join(EN_WORK, "episode.json")))
edl = json.load(open(os.path.join(EN_WORK, "edl.json")))
script = json.load(open(os.path.join(EN_WORK, "script.json")))
warnings = []


def frames(t):
    return int(round(Fraction(t).limit_denominator(1000000) * FPS))


_probe = {}


def probe(path):
    if path not in _probe:
        j = json.loads(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration:stream=codec_type",
                                       "-of", "json", path], capture_output=True, text=True).stdout)
        _probe[path] = dict(dur=float(j["format"].get("duration", 0) or 0),
                            audio=any(s["codec_type"] == "audio" for s in j.get("streams", [])))
    return _probe[path]


# ---------------------------------------------------------------- the language's headings and quiz text
import openpyxl

book = next(b for b in sorted(glob.glob(os.path.join(root, "**", "*.xlsx"), recursive=True))
            if not os.path.basename(b).startswith("._"))
ws = openpyxl.load_workbook(book, data_only=True)["Content"]
rows = list(ws.iter_rows(values_only=True))
col = {str(c or "").strip(): i for i, c in enumerate(rows[0])}
c_en, c_lang = col.get("English", 2), col[LC.get("column", LANG)]
lang_of = {}                                             # EN text (stripped) -> the language's text
for r in rows[1:]:
    if r[c_en] and r[c_lang]:
        lang_of.setdefault(str(r[c_en]).strip(), str(r[c_lang]).strip())

sections = []                                            # EN order, with the language's heading
for s in ep["sections"]:
    head = lang_of.get(s["prefix"].strip(), s["prefix"])
    m = re.match(r"(\d+)\.\s*(.*)", head)
    sections.append(dict(en=s["prefix"], kind=s["kind"], head=head,
                         num=int(m.group(1)) if m and s["kind"] == "location" else None,
                         name=m.group(2).strip() if m else head))
# the language's order: intro, then locations by their number (a quiz / story stays after the
# location it follows in EN), outro last
groups, cur = [], None
for s in sections:
    if s["kind"] == "location" or cur is None or s["kind"] in ("intro", "outro"):
        cur = [s]; groups.append(cur)
    else:
        cur.append(s)
rank = lambda g: (0, 0) if g[0]["kind"] == "intro" else (2, 0) if g[0]["kind"] == "outro" else (1, g[0]["num"] or 0)
order = [s for g in sorted(groups, key=rank) for s in g]
for g in groups:                                         # a quiz shares its location's section sequence
    for s in g:
        s["group"] = g[0]["head"]

# ---------------------------------------------------------------- the language's VO files
audio_dir = next(d for d in (os.path.join(root, LANG, f"AUDIO {LANG}"), os.path.join(root, LANG, "AUDIO")) if os.path.isdir(d))
files = sorted(f for f in os.listdir(audio_dir) if not f.startswith("._") and f.lower().endswith((".mp3", ".wav")))
fixed = [f for f in files if "(" in f]                  # "… 2 pt (sửa câu cuối).mp3" replaces "… 2 pt.mp3"
for f in fixed:
    orig = re.sub(r"\s*\([^)]*\)", "", f)
    if orig in files:
        files.remove(orig)
        warnings.append(f"VO: dùng '{f}' thay cho '{orig}'")
fold = lambda s: unicodedata.normalize("NFC", s).lower()


def part_no(f):
    stem = os.path.splitext(f)[0]
    m = (re.search(r"\b(?:en|es|pt)\s*(\d+)\b", stem, re.I) or re.search(r"(\d+)\s*(?:en|es|pt)?\s*(?:\([^)]*\))?\s*$", stem, re.I)
         or re.match(r"[A-Za-z]+\s*(\d+)\b", stem))
    return int(m.group(1)) if m else 0


def vo_for(s):
    if s["kind"] == "location":
        fs = [f for f in files if re.match(rf"{s['num']}\.(?!\d)", f) and "quiz" not in fold(f)]
    elif s["kind"] == "quiz":                            # PT names it "1. quiz …"
        fs = [f for f in files if "quiz" in fold(f)]
    else:
        fs = [f for f in files if fold(f).startswith(s["kind"])]
    return sorted(fs, key=part_no)


def silences(path):
    """(start, end) of every pause >= 0.3 s in a VO file."""
    err = subprocess.run(["ffmpeg", "-v", "info", "-i", path, "-af", "silencedetect=noise=-35dB:d=0.3", "-f", "null", "-"],
                         capture_output=True, text=True).stderr
    st = [float(x) for x in re.findall(r"silence_start: ([\d.]+)", err)]
    en = [float(x) for x in re.findall(r"silence_end: ([\d.]+)", err)]
    return list(zip(st, en))


# ---------------------------------------------------------------- EN sections on the EN timeline
en_shots = edl["shots"]
first_f0 = {}
for s in en_shots:
    first_f0.setdefault(s.get("part", s["section"]), s["f0"])
en_end_of_vo = next(o["start"] for o in edl["overlays"] if o["name"] == "ENDING")
for k, s in enumerate(sections):
    s["b"] = first_f0[s["en"]] / float(FPS)
    s["e"] = first_f0[sections[k + 1]["en"]] / float(FPS) if k + 1 < len(sections) else en_end_of_vo
    s["en_vo"] = sorted((v for v in edl["vo"] if s["b"] <= v["start"] < s["e"]), key=lambda v: v["start"])

# ---------------------------------------------------------------- lay out the language's sections
vo_clips, t = [], 0.0
for s in order:
    fs = vo_for(s)
    if not fs:
        sys.exit(f"no {LANG} VO for: {s['head'].splitlines()[0]}")
    n_en = len(s["en_vo"])
    paths = [os.path.join(audio_dir, f) for f in fs]
    k_slices = max(n_en, len(paths))
    # cut points: the longest pauses inside the files (not within 1 s of a file's ends)
    cands = []
    for pi, p in enumerate(paths):
        d = probe(p)["dur"]
        cands += [(e - a, pi, (a + e) / 2) for a, e in silences(p) if a > 1.0 and e < d - 1.0]
    cuts = sorted(cands, reverse=True)[:k_slices - len(paths)]
    slices = []
    for pi, p in enumerate(paths):
        pts = [0.0] + sorted(c[2] for c in cuts if c[1] == pi) + [probe(p)["dur"]]
        slices += [(p, a, b - a) for a, b in zip(pts, pts[1:])]
    en = s["en_vo"]
    en_pauses = [en[i + 1]["start"] - (en[i]["start"] + en[i]["dur"]) for i in range(n_en - 1)]
    last_pause = s["e"] - (en[-1]["start"] + en[-1]["dur"])
    pre = en[0]["start"] - s["b"]
    s["lb"] = t
    tt = t + pre
    for j, (p, a, d) in enumerate(slices):
        pause = (en_pauses[j] if len(slices) == n_en and j < n_en - 1 else
                 last_pause if j == len(slices) - 1 else sum(en_pauses) / len(en_pauses) if en_pauses else 5.0)
        vo_clips.append(dict(path=p, start=tt, dur=d, src_in=a, new_file=a == 0 and (j > 0 or s["kind"] == "quiz")))
        if j == 0:
            s["l_first"] = tt
        s.setdefault("l_slices", []).append((tt, d))
        tt += d + pause
    s["le"] = t = tt
    # EN time -> language time for this section (piecewise when the slices pair up, else one stretch)
    seg = [(s["b"], en[0]["start"], s["lb"], s["l_first"])]
    if len(slices) == n_en:
        ls = s["l_slices"]
        for i in range(n_en):
            a0, a1 = en[i]["start"], en[i]["start"] + en[i]["dur"]
            nxt = en[i + 1]["start"] if i + 1 < n_en else s["e"]
            b0, b1 = ls[i][0], ls[i][0] + ls[i][1]
            seg += [(a0, a1, b0, b1), (a1, nxt, b1, ls[i + 1][0] if i + 1 < n_en else s["le"])]
    else:
        seg.append((en[0]["start"], s["e"], s["l_first"], s["le"]))
    s["seg"] = seg
end_of_vo = vo_clips[-1]["start"] + vo_clips[-1]["dur"]
order[-1]["le"] = end_of_vo                              # the ending starts right after the last word


def warp(t_en):
    """EN timeline time -> language timeline time."""
    s = next((s for s in sections if s["b"] <= t_en < s["e"]), sections[-1])
    for a0, a1, b0, b1 in s["seg"]:
        if a0 <= t_en <= a1 or (a0, a1, b0, b1) == s["seg"][-1]:
            return b0 + (t_en - a0) * ((b1 - b0) / (a1 - a0) if a1 > a0 else 1)
    return s["lb"]


# ---------------------------------------------------------------- shots in the language's order
ending = os.path.join(TEMPLATE, LC["ending_file"])


def placed_copy(src, motion, out):
    """An overlay placed like the template sequence (scale %, centre x / y as fractions of the frame),
    baked into a full-frame alpha copy with its sound."""
    if not os.path.exists(out):
        sc, cx, cy = motion
        w, h = int(3840 * sc / 100) // 2 * 2, int(2160 * sc / 100) // 2 * 2
        x, y = int(3840 * cx - w / 2), int(2160 * cy - h / 2)
        cl, ct = max(0, -x), max(0, -y)
        cw, chh = min(w, 3840 - x) - cl, min(h, 2160 - y) - ct
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", src, "-map", "0:v", "-map", "0:a?",
                        "-vf", f"scale={w}:{h},format=argb,crop={cw}:{chh}:{cl}:{ct},"
                               f"pad=3840:2160:{max(x, 0)}:{max(y, 0)}:color=black@0",
                        "-c:v", "qtrle", "-c:a", "copy", out], check=True)
    return out


if LC.get("ending_motion"):
    ending = placed_copy(ending, LC["ending_motion"], os.path.join(GEN, "ending.mov"))
ending_dur = probe(ending)["dur"]
timeline_end = end_of_vo + ending_dur
new_file_starts = sorted(v["start"] for v in vo_clips if v["new_file"])
shots = []
for s in order:
    for x in (x for x in en_shots if x.get("part", x["section"]) == s["en"]):
        start = s["lb"] if x["f0"] / float(FPS) <= s["b"] + 1e-6 else warp(x["f0"] / float(FPS))
        shots.append(dict(x, start=start, section=s["group"], part=s["head"], kind=s["kind"], part_start=False, dip=False,
                          gap_after=False))
for t0 in new_file_starts:                              # the longer dissolve where a new VO file begins
    c = min(shots, key=lambda x: abs(x["start"] - (t0 - CUT_LEAD)))
    c["part_start"] = True
for i, x in enumerate(shots):
    x["end"] = shots[i + 1]["start"] if i + 1 < len(shots) else timeline_end
shots = [x for x in shots if x["end"] - x["start"] >= 1.2 or x is shots[0]]
for i, x in enumerate(shots):
    x["end"] = shots[i + 1]["start"] if i + 1 < len(shots) else timeline_end
    x["f0"] = shots[i - 1]["f1"] if i else frames(x["start"])
    x["f1"] = frames(x["end"])
# footage in-points: same rules as build-timeline.py (centred, handles; short clips leave V1 empty)
for i, x in enumerate(shots):
    if x.get("still"):
        x["in_f"] = 0
        continue
    dur = Fraction(probe(x["path"])["dur"]).limit_denominator(100000)
    need = Fraction(x["f1"] - x["f0"], 1) / FPS + Fraction(PART_DISSOLVE, 1) / FPS
    avail = dur - 2 * HANDLE
    if need <= avail:
        x["in_f"] = frames(HANDLE + (avail - need) / 2)
        continue
    clip_f = int(dur * FPS) - 1
    x["in_f"] = PART_DISSOLVE // 2
    if x["in_f"] + (x["f1"] - x["f0"]) <= clip_f:
        continue
    x["f1"] = x["f0"] + clip_f - x["in_f"]
    x["gap_after"] = True
    end_f = shots[i + 1]["f0"] if i + 1 < len(shots) else x["f1"]
    m, sec = divmod(x["f1"] / float(FPS), 60)
    warnings.append(f"{x['file']}: clip {float(dur):.1f}s too short, V1 empty "
                    f"{(end_f - x['f1']) / float(FPS):.1f}s from {int(m)}:{sec:04.1f}")
for i in range(1, len(shots)):
    if shots[i]["section"] != shots[i - 1]["section"]:
        shots[i]["dip"] = True
        if not shots[i - 1]["gap_after"]:
            shots[i - 1]["f1"] -= DIP

# ---------------------------------------------------------------- graphics
os.makedirs(GEN, exist_ok=True)
overlays = [dict(name="ENDING", path=ending,                 # its sound only where the channel uses it
                 audio=ending if LC.get("ending_sound", CH.get("ending_sound")) and probe(ending)["audio"] else None,
                 start=end_of_vo, dur=ending_dur)]
en_ov = {o["name"]: o for o in edl["overlays"]}
if LC.get("subscribe_file") and "Subscribe" in en_ov:
    sub = os.path.join(TEMPLATE, LC["subscribe_file"])
    # its sound: the file's own, or the separate file the channel's template uses (Earthcue "YSB THIRD 4K sfx")
    snd = LC.get("subscribe_audio_file", CH.get("subscribe_audio_file"))
    snd = os.path.join(TEMPLATE, snd) if snd else (sub if probe(sub)["audio"] else None)
    overlays.append(dict(name="Subscribe", path=sub, audio=snd if CH.get("subscribe_sound", True) else None,
                         start=warp(en_ov["Subscribe"]["start"]), dur=probe(sub)["dur"]))
elif "Subscribe" in en_ov and not LC.get("subscribe_manual"):   # the editor adds it by hand for some languages
    warnings.append(f"Subscribe: chưa có file Subscribe {LANG} dùng được (channel.json languages.{LANG}.subscribe_file)")
if "CTA" in en_ov:
    o = en_ov["CTA"]
    cta = os.path.join(GEN, os.path.basename(o["path"]))  # the language folder keeps its own copy
    if not os.path.exists(cta):
        shutil.copy2(o["path"], cta)
    overlays.append(dict(o, path=cta, audio=cta if o.get("audio") else None, start=warp(o["start"])))
if "Quiz" in en_ov:
    o = en_ov["Quiz"]
    q_en = next(r["en"] for r in script if re.search(r"\nA[.)]", r["en"]))
    q = lang_of.get(q_en.strip(), q_en)
    st, en_t = warp(o["start"]), warp(o["start"] + o["dur"])
    qmov = os.path.join(GEN, "quiz-1.mov")
    fit = [",".join(str(v) for v in CH["quiz_fit"])] if CH.get("quiz_fit") else []
    subprocess.run([sys.executable, "-I", os.path.join(HERE, "render-quiz.py"), q, f"{en_t - st:.4f}", qmov] + fit,
                   check=True)
    overlays.append(dict(name="Quiz", path=qmov, audio=None, start=st, dur=en_t - st))
lt_dur = LC["lower_third_seconds"]
for s in order:
    if s["kind"] != "location":
        continue
    lt = os.path.join(GEN, "lower-third-" + re.sub(r"[^A-Za-z0-9]+", "-", unicodedata.normalize("NFKD", s["name"])
                                                    .encode("ascii", "ignore").decode()).strip("-").lower() + ".mov")
    if not os.path.exists(lt):
        style = LC["lower_third"]
        cmd = (["render-lower-third-lang.py", style, str(s["num"]), s["name"], REGION] if style in ("box", "frame")
               else ["render-lower-third.py", s["name"]] if style == "plain"               # Earthcue: plain Jost caps
               else ["render-caption.py", "lower", s["name"]] if style == "caption"        # Chaseland
               else ["render-lower-third-bracket.py", str(s["num"]), s["name"], REGION])   # Tripinsight EN look
        subprocess.run([sys.executable, "-I", os.path.join(HERE, cmd[0])] + cmd[1:] + [f"{lt_dur}", lt], check=True)
    first = next(x for x in shots if x["section"] == s["head"])
    overlays.append(dict(name="Lower third", path=lt, audio=None, start=first["f0"] / float(FPS), dur=lt_dur))
logo = os.path.join(GEN, "logo-overlay-3840.png")
if not os.path.exists(logo):
    subprocess.run([sys.executable, "-I", os.path.join(HERE, "make-logo-overlay.py"),
                    os.path.join(TEMPLATE, LC["logo_file"]), logo] + [str(v) for v in LC.get("logo_box", CH["logo_box"])], check=True)

# ---------------------------------------------------------------- music: the EN songs, re-laid
lib = sorted(os.path.join(ep["music_lib"], f) for f in os.listdir(ep["music_lib"])
             if f.lower().endswith((".mp3", ".wav")) and not f.startswith("._"))
songs = list(dict.fromkeys(m["path"] for m in sorted(edl["music"], key=lambda m: m["start"])))
songs += [p for p in lib if os.path.basename(p) not in {os.path.basename(q) for q in songs}]
music, mt = [], 0.0
for p in songs:
    if mt >= timeline_end - 1:
        break
    if p.startswith(os.path.join(root, "EN", "MEDIA") + "/") or p.startswith(ep["music_lib"] + "/"):
        os.makedirs(MEDIA, exist_ok=True)                # each language folder keeps its own copies
        dst = os.path.join(MEDIA, re.sub(r"[^A-Za-z0-9._-]+", "_", os.path.basename(p)))
        if not os.path.exists(dst):
            shutil.copy2(p, dst)
        p = dst
    use = min(probe(p)["dur"], timeline_end - mt)
    music.append(dict(path=p, start=mt, dur=use, lane=-2))
    mt += use

# ---------------------------------------------------------------- write edl.json + Premiere XML
for v in vo_clips:
    v.pop("new_file", None)
dissolve_at = [i for i, x in enumerate(shots) if i and x["part_start"]]
total = max(shots[-1]["f1"], frames(timeline_end))      # a short last clip must not cut the ending off
json.dump(dict(total_s=total / float(FPS),
               shots=[dict(file=x["file"], start=x["f0"] / float(FPS), dur=(x["f1"] - x["f0"]) / float(FPS),
                           text=x.get("text", ""), path=x["path"], f0=x["f0"], f1=x["f1"], in_f=x["in_f"],
                           dip=x["dip"], still=bool(x.get("still")), gap_after=x["gap_after"],
                           section=x["section"], kind=x["kind"]) for x in shots],
               dissolve=DISSOLVE, dip=DIP, dissolve_at=dissolve_at, part_dissolve=PART_DISSOLVE, overlays=overlays,
               vo=vo_clips, music=music, sfx=[], titles=[], warnings=warnings, logo=logo,
               music_db=edl.get("music_db", -17), name=NAME),
          open(os.path.join(WORK, "edl.json"), "w"), ensure_ascii=False, indent=0)
out_xml = os.path.join(OUT_DIR, NAME + ".xml")
subprocess.run([sys.executable, "-I", os.path.join(HERE, "export-premiere-xml.py"), os.path.join(WORK, "edl.json"),
                out_xml], check=True)
m, sec = divmod(total / float(FPS), 60)
print(f"{LANG}: {int(m)}:{sec:05.2f}, {len(shots)} shots, {len(vo_clips)} VO slices, {len(music)} music")
print("order:", ", ".join(s["head"].splitlines()[0][:30] for s in order))
for w in warnings:
    print(w)
print("\nDone ->", out_xml)
