"""Build an Earthcue episode edit from a prepared work folder and write it as
  - <out_dir>/<name>.xml             Premiere Pro (File > Import)  [out_dir = the episode folder]
  - <out_dir>/<name>.fcpxml          DaVinci Resolve, only when channel.json has "export_resolve": true
  - <out_dir>/MEDIA/                 background music only (copied from the library)
  - <out_dir>/.autoedit/             generated graphics (logo overlay, lower thirds, titles) + work data
  Channel assets (subscribe, ending) are used straight from the template folder.
  - <work>/edl.json                  the same edit as data (used by render-preview.py)

Usage: python build-timeline.py <work_dir>
  work_dir is made by prepare-episode.py: episode.json, script.json, vo/index.tsv,
  vo/NN.csv (whisper word timestamps) and vo/NN.wav (16 kHz copies of the VO).

House style (learned from the Sierra Nevada episode and the editor's own fixes):
  V1 footage (one shot per script line), V2 lower thirds / quiz / subscribe / ending,
  V3 corner logo, A1 VO cut per sentence with a 5 s pause after each, A2 music.
"""
import csv, difflib, json, os, re, shutil, subprocess, sys, urllib.parse
from fractions import Fraction
from xml.sax.saxutils import escape

WORK = sys.argv[1]
HERE = os.path.dirname(os.path.abspath(__file__))
EP = json.load(open(os.path.join(WORK, "episode.json")))
# channel look (logo, lower third, ending, subscribe, opening title): channels/<slug>/channel.json
sys.path.insert(0, HERE)
import channel
CH = channel.load(WORK)
ROOT = EP["root"]
NAME = EP["name"]
VIDEO = f"{ROOT}/VIDEO"
AUDIO = EP["audio_dir"]
TEMPLATE = EP["template"]
OUT_DIR = EP["out_dir"]
MEDIA = f"{OUT_DIR}/MEDIA"                  # background music copied from the library
GEN = f"{OUT_DIR}/.autoedit"                # graphics made for this episode (hidden in Finder)
LOGO = f"{GEN}/logo-overlay-3840.png"
MUSIC_LIB = EP["music_lib"]                 # shared library, used after the episode's own music
PLAN = [(sec["prefix"], sec["vo"]) for sec in EP["sections"]]
KIND = {sec["prefix"]: sec["kind"] for sec in EP["sections"]}

FPS = Fraction(30000, 1001)
DISSOLVE = 25                 # frames between shots, matches reference (0.83s)
DIP = 25                      # frames of fade-to-black, and again of fade-from-black, where a section ends
PART_DISSOLVE = 30            # frames where one VO part ends and the next begins (1.0s in reference)
HANDLE = Fraction(1, 2)       # seconds kept free at both ends of every source clip
SENTENCE_PAUSE = 5.0          # music-only pause after every spoken sentence
MIN_PAUSE = 3.0               # shortened down to this when the footage would run out before the next shot
CUT_LEAD = 0.25               # cut this much before the line is spoken
MUSIC_DB = -17
LOWER_THIRD_DUR = CH.get("lower_third_seconds", 4.0)   # seconds a location name stays on screen


def frames(t):
    return int(round(Fraction(t) * FPS))


def ts(n_frames):
    """Timeline frames -> FCPXML rational time."""
    return f"{n_frames * 1001}/30000s" if n_frames else "0s"


_probe_cache, _dir_cache = {}, {}


def probe(path):
    if path not in _probe_cache:
        _probe_cache[path] = _probe(path)
    return _probe_cache[path]


def _probe(path):
    out =subprocess.run(["ffprobe", "-v", "error", "-show_entries",
                          "format=duration:stream=codec_type,width,height,r_frame_rate",
                          "-of", "json", path], capture_output=True, text=True).stdout
    j = json.loads(out)
    v = next((s for s in j.get("streams", []) if s["codec_type"] == "video"), None)
    return dict(dur=float(j["format"].get("duration", 0) or 0),
                w=v and v.get("width"), h=v and v.get("height"),
                rate=v and v.get("r_frame_rate"),
                audio=any(s["codec_type"] == "audio" for s in j.get("streams", [])))


STILL_EXT = (".jpg", ".jpeg", ".png", ".tif", ".tiff", ".webp")


def still_4k(path):
    """A photo used as footage: a 3840x2160 copy that fills the frame (centre crop), made once."""
    out = os.path.join(GEN, "stills", os.path.splitext(os.path.basename(path))[0] + ".png")
    if not os.path.exists(out):
        os.makedirs(os.path.dirname(out), exist_ok=True)
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", path, "-vf",
                        "scale=3840:2160:force_original_aspect_ratio=increase,crop=3840:2160",
                        "-frames:v", "1", out], check=True)
    return out


def find_file(folder, stem):
    if folder not in _dir_cache:
        _dir_cache[folder] = sorted(os.listdir(folder))
    for f in _dir_cache[folder]:
        if not f.startswith("._") and (f.startswith(stem + ".") or f.startswith(stem)):
            return os.path.join(folder, f)
    if stem.startswith("-"):                            # line without Number: "-<ID>" names "<n>-<ID>.*"
        for f in _dir_cache[folder]:
            if not f.startswith("._") and stem + "." in f:
                return os.path.join(folder, f)
    raise FileNotFoundError(f"{stem} in {folder}")


def rs(x):
    """Fraction seconds -> FCPXML rational time."""
    x = Fraction(x)
    return f"{x.numerator}/{x.denominator}s" if x else "0s"


_tc_cache = {}


def timecode(path):
    """Start timecode embedded in a media file, in seconds (0 if none). Resolve places
    media at its own timecode, so FCPXML source times must be offset by it."""
    if path in _tc_cache:
        return _tc_cache[path]
    j = json.loads(subprocess.run(["ffprobe", "-v", "error", "-show_entries",
                                   "stream=codec_type,r_frame_rate:stream_tags=timecode:format_tags=timecode",
                                   "-of", "json", path], capture_output=True, text=True).stdout)
    v = next((st for st in j.get("streams", []) if st.get("codec_type") == "video"), {})
    tc = (v.get("tags", {}).get("timecode") or j.get("format", {}).get("tags", {}).get("timecode")
          or next((st.get("tags", {}).get("timecode") for st in j.get("streams", [])
                   if st.get("tags", {}).get("timecode")), None))
    val = Fraction(0)
    if tc and v.get("r_frame_rate", "0/0") != "0/0":
        rate = Fraction(v["r_frame_rate"])
        base = round(rate)
        h, m, sec, fr = map(int, re.split(r"[:;.]", tc))
        n = (h * 3600 + m * 60 + sec) * base + fr
        if ";" in tc or "." in tc:                       # drop-frame: undo the skipped numbers
            drop = round(base / 15)                      # 2 for 29.97, 4 for 59.94
            mins = h * 60 + m
            n -= drop * (mins - mins // 10)
        val = n / rate
    _tc_cache[path] = val
    return val


def norm(w):
    return re.sub(r"[^a-z0-9]", "", w.lower())


# ---------------------------------------------------------------- inputs
rows = json.load(open(os.path.join(WORK, "script.json")))
vo_files = {}
for line in open(os.path.join(WORK, "vo", "index.tsv")):
    n, name = line.rstrip("\n").split("\t")
    vo_files[int(n)] = name


def whisper_words(n):
    """(word, start, end) in seconds within VO file n."""
    with open(os.path.join(WORK, "vo", f"{n:02d}.csv")) as fh:
        for r in csv.DictReader(fh):
            w = norm(r["text"])
            if w:
                yield w, int(r["start"]) / 1000.0, int(r["end"]) / 1000.0


_wav_cache = {}


def quiet_point(n, t0, t1):
    """Centre (s) of the quietest 80 ms in VO file n between t0 and t1, so slices are cut
    in silence rather than mid-word. Whisper word ends are loose, so callers search from
    just after the last word starts to just after the next word starts."""
    import wave, array
    if n not in _wav_cache:
        with wave.open(os.path.join(WORK, "vo", f"{n:02d}.wav")) as w:
            _wav_cache[n] = (w.getframerate(), array.array("h", w.readframes(w.getnframes())))
    sr, pcm = _wav_cache[n]
    if t1 - t0 < 0.16:
        mid = (t0 + t1) / 2; t0, t1 = mid - 0.08, mid + 0.08
    step, win = sr // 100, sr * 8 // 100
    best, best_t = None, (t0 + t1) / 2
    for k in range(int(t0 * sr), max(int(t0 * sr) + 1, int(t1 * sr) - win), step):
        e = sum(abs(x) for x in pcm[k:k + win])
        if best is None or e < best:
            best, best_t = e, (k + win / 2) / sr
    return best_t


# ---------------------------------------------------------------- timing
def sentence_pause(shot, vo_end):
    """Pause after a sentence: SENTENCE_PAUSE, cut back (not below MIN_PAUSE) when the shot
    under the end of the sentence has too little footage to reach the next shot plus its
    dissolve. Room = clip minus 0.5 s head (incoming dissolve) and 0.5 s tail (outgoing)."""
    path = find_file(VIDEO, shot["line"]["file"])
    clip = 1e9 if path.lower().endswith(STILL_EXT) else float(probe(path)["dur"])   # a photo never runs out
    room = clip - 1.05 - (vo_end - CUT_LEAD - shot["start"])
    return min(SENTENCE_PAUSE, max(MIN_PAUSE, room))



# Every script sentence gets its own slice of VO followed by SENTENCE_PAUSE seconds of
# music + picture. Slices are cut in the silence between sentences.
shots, vo_clips, titles, warnings = [], [], [], []
sfx_clips = []                                          # SFX are not part of the house style
t = CH.get("intro_lead", 0.0)        # Chaseland: the intro VO starts after the opening title
for sec_i, (prefix, parts) in enumerate(PLAN):
    lines = [r for r in rows if (r["sec"] or "").startswith(prefix)]
    words, part_dur, part_path = [], {}, {}
    for k, n in enumerate(parts):
        part_path[k] = os.path.join(AUDIO, vo_files[n])
        part_dur[k] = probe(part_path[k])["dur"]
        words += [(w, k, s0, s1) for w, s0, s1 in whisper_words(n)]
    # align script tokens to whisper tokens
    toks, owner = [], []
    for li, r in enumerate(lines):
        for w in str(r["en"]).split():
            if norm(w):
                toks.append(norm(w)); owner.append(li)
    sm = difflib.SequenceMatcher(None, toks, [w[0] for w in words], autojunk=False)
    hit = {}
    for a_, b_, size in sm.get_matching_blocks():
        for k in range(size):
            hit[a_ + k] = words[b_ + k]
    first, last = {}, {}
    for ti, li in enumerate(owner):
        if ti in hit:
            first.setdefault(li, hit[ti])
            last[li] = hit[ti]
    spoken = [li for li in range(len(lines)) if li in first]
    for li in range(len(lines)):
        if li not in first and not lines[li].get("extra"):
            warnings.append(f"line {lines[li]['n']} ({lines[li]['file']}) is not in the VO: its footage shares the "
                            f"previous line's time")
    # footage-only lines (no text) and lines the VO does not say (Chaseland's on-screen "hit that subscribe
    # button" cue) follow the spoken line before them (the first one at the section start)
    extras_after, owner_li = {}, None
    for li in range(len(lines)):
        if li in first:
            owner_li = li
        else:
            extras_after.setdefault(owner_li if owner_li is not None else (spoken or [None])[0], []).append(li)
    # group lines into spoken sentences: a pause only follows a line that ends a sentence
    def ends_sentence(li):
        return re.search(r"[.?!\u2026][\"\u201d\u2019')]*\s*$", str(lines[li]["en"])) is not None
    groups, cur = [], []
    for j, li in enumerate(spoken):
        if cur and first[li][1] != first[cur[-1]][1]:      # a new VO file always starts a group
            groups.append(cur); cur = []
        cur.append(li)
        if ends_sentence(li):
            groups.append(cur); cur = []
    if cur:
        groups.append(cur)
    # slice boundaries: quietest point in the gap between one sentence and the next
    bounds = []
    for g_i, g in enumerate(groups):
        part = first[g[0]][1]
        prev = groups[g_i - 1] if g_i else None
        nxt = groups[g_i + 1] if g_i + 1 < len(groups) else None
        s0 = (quiet_point(parts[part], last[prev[-1]][2] + 0.2, first[g[0]][2] + 0.3)
              if prev and first[prev[-1]][1] == part and last[prev[-1]][1] == part else 0.0)
        s1 = (quiet_point(parts[part], last[g[-1]][2] + 0.2, first[nxt[0]][2] + 0.3)
              if nxt and first[nxt[0]][1] == part and last[g[-1]][1] == part else part_dur[part])
        bounds.append((g, part, s0, s1))
    sec_start = t
    for g_i, (g, part, s0, s1) in enumerate(bounds):
        dur = s1 - s0
        vo_clips.append(dict(path=part_path[part], start=t, dur=dur, src_in=s0))
        for j, li in enumerate(g):
            if sec_i == 0 and g_i == 0 and j == 0:
                cut = 0.0
            elif j == 0:
                cut = t - CUT_LEAD
            else:                                           # later lines of the sentence: cut on their first word
                cut = t + (first[li][2] - s0) - CUT_LEAD
            part_start = j == 0 and (g_i == 0 or bounds[g_i - 1][1] != part)
            shots.append(dict(start=cut, line=lines[li], section=prefix, part_start=part_start))
            for ex in extras_after.get(li, []):             # timed once the next cut is known
                shots.append(dict(start=None, line=lines[ex], section=prefix, part_start=False))
        last_group = sec_i == len(PLAN) - 1 and g_i == len(bounds) - 1
        timed = next(s for s in reversed(shots) if s["start"] is not None)
        t += dur + (0 if last_group else sentence_pause(timed, t + dur))
    if KIND[prefix] == "quiz":
        q = next((r["en"] for r in lines if re.search(r"\nA[.)]", str(r["en"]))), lines[min(1, len(lines) - 1)]["en"])
        titles.append(dict(start=sec_start + 2.0, end=t - 0.5, text=q))
end_of_vo = t
if EP.get("title_vo"):                  # the region name said over the opening title (Chaseland "Australia.mp3")
    tv = os.path.join(AUDIO, EP["title_vo"])
    vo_clips.insert(0, dict(path=tv, start=CH.get("intro_title_start", 0.5) + CH.get("title_vo_at", 2.34),
                            dur=probe(tv)["dur"], src_in=0.0))
ending = os.path.join(TEMPLATE, CH["ending_file"])
ending_dur = probe(ending)["dur"]
timeline_end = end_of_vo + ending_dur
# a spoken line and the footage-only lines after it share its time on screen evenly
for i, s in enumerate(shots):
    if s["start"] is not None and i + 1 < len(shots) and shots[i + 1]["start"] is None:
        j = next((k for k in range(i + 1, len(shots)) if shots[k]["start"] is not None), len(shots))
        nxt = shots[j]["start"] if j < len(shots) else end_of_vo
        for k in range(i + 1, j):
            shots[k]["start"] = s["start"] + (nxt - s["start"]) * (k - i) / (j - i)

# a quiz stays inside the location before it: same section sequence, no fade to black between them
# (user-set 2026-10-21). "part" keeps the script section each shot came from.
quiz_parent, prev = {}, None
for prefix, _ in PLAN:
    if KIND[prefix] == "quiz" and prev:
        quiz_parent[prefix] = prev
    elif KIND[prefix] != "quiz":
        prev = prefix
for s in shots:
    s["part"] = s["section"]
    s["section"] = quiz_parent.get(s["section"], s["section"])

# ---------------------------------------------------------------- shots -> source ranges
for i, s in enumerate(shots):
    s["end"] = shots[i + 1]["start"] if i + 1 < len(shots) else timeline_end
    s["path"] = find_file(VIDEO, s["line"]["file"])
    if s["path"].lower().endswith(STILL_EXT):
        s["path"], s["still"] = still_4k(s["path"]), True
    s["probe"] = probe(s["path"])
# drop shots too short to read (<1.2s): previous shot absorbs the time
shots = [s for s in shots if s["end"] - s["start"] >= 1.2 or s is shots[0]]
for i, s in enumerate(shots):
    s["end"] = shots[i + 1]["start"] if i + 1 < len(shots) else timeline_end
# snap to frames
for s in shots:
    s["f0"], s["f1"] = frames(s["start"]), frames(s["end"])
for i in range(1, len(shots)):
    shots[i]["f0"] = shots[i - 1]["f1"]
# Footage always stays on its own script line. A clip too short for its line plays in full
# from the start of the line and the rest of the line is left empty on V1 (gap_after), for
# the editor to fill by hand; the next shot still starts exactly on its own line.
for i, s in enumerate(shots):
    if s.get("still"):                                  # a photo holds for the whole line
        s["in"], s["in_f"] = Fraction(0), 0
        continue
    need = Fraction(s["f1"] - s["f0"], 1) / FPS + Fraction(PART_DISSOLVE, 1) / FPS
    avail = Fraction(s["probe"]["dur"]).limit_denominator(100000) - 2 * HANDLE
    if need <= avail:
        s["in"] = HANDLE + (avail - need) / 2           # centre the used range in the clip
        s["in_f"] = frames(s["in"])
        continue
    # short clip: drop the handles, keep just enough head for the incoming dissolve
    clip_f = int(Fraction(s["probe"]["dur"]).limit_denominator(100000) * FPS) - 1
    s["in_f"] = PART_DISSOLVE // 2
    s["in"] = Fraction(s["in_f"], 1) / FPS
    if s["in_f"] + (s["f1"] - s["f0"]) <= clip_f:
        continue                                        # fits once the handles are used (a dissolve tail
                                                        # past the clip end is held by Premiere)
    s["f1"] = s["f0"] + clip_f - s["in_f"]              # never longer than its line: f1 only moves earlier
    s["gap_after"] = True
    end_f = shots[i + 1]["f0"] if i + 1 < len(shots) else s["f1"]
    m, sec = divmod(s["f1"] / FPS, 60)
    warnings.append(f"{s['line']['file']}: clip {float(s['probe']['dur']):.1f}s too short, "
                    f"V1 empty {float((end_f - s['f1']) / FPS):.1f}s from {int(m)}:{float(sec):04.1f}")

# where one section ends and the next begins: the outgoing shot fades to black and the
# incoming one fades up from black. In FCPXML that is a DIP-frame gap taken from the end
# of the outgoing shot, with a dissolve into and out of the gap.
gaps = []
for i in range(1, len(shots)):
    if shots[i]["section"] != shots[i - 1]["section"]:
        shots[i]["dip"] = True
        if not shots[i - 1].get("gap_after"):           # a short clip already ends before the gap
            shots[i - 1]["f1"] -= DIP
        gaps.append(dict(gap=True, f0=shots[i - 1]["f1"], f1=shots[i]["f0"]))
    elif shots[i - 1].get("gap_after"):
        gaps.append(dict(gap=True, f0=shots[i - 1]["f1"], f1=shots[i]["f0"]))

# ---------------------------------------------------------------- music + sfx
def music_playlist():
    """Episode tracks first, then the shared library (top level + Epidemic Sound/Music),
    de-duplicated by title and shuffled with a fixed seed so rebuilds are stable."""
    import random
    own = list(EP.get("music", []))
    lib = []
    for d in (MUSIC_LIB, os.path.join(MUSIC_LIB, "Epidemic Sound", "Music")):
        if os.path.isdir(d):
            lib += [os.path.join(d, f) for f in sorted(os.listdir(d))
                    if f.lower().endswith((".mp3", ".wav")) and not f.startswith("._")]
    title = lambda p: re.sub(r"^ES_(\d+_)?", "", os.path.splitext(os.path.basename(p))[0]).lower()
    seen, out = set(), []
    random.Random(ROOT).shuffle(lib)
    for p in own + lib:
        if title(p) not in seen:
            seen.add(title(p)); out.append(p)
    return out


music_files = music_playlist()
music, mt, mi = [], 0.0, 0
while mt < timeline_end - 1:
    p = music_files[mi % len(music_files)]
    d = probe(p)["dur"]
    left = timeline_end - mt
    if left - 30 < d < left:
        # this song would leave a short tail: use a later song long enough to finish the video
        p = next((q for q in music_files[mi + 1:] if probe(q)["dur"] >= left), p)
        d = probe(p)["dur"]
    use = min(d, left)
    music.append(dict(path=p, start=mt, dur=use, lane=-2))
    if use < d:                                         # this track reaches the end
        break
    mt += use                                           # songs back to back on A2
    mi += 1

# ---------------------------------------------------------------- FCPXML
assets, asset_ids = [], {}


def collect(path):
    """Copy library music into the episode's MEDIA folder under a plain ASCII name.
    Everything else (episode files, channel template assets every machine has,
    generated graphics) is used where it is."""
    if path.startswith(ROOT + "/") or not path.startswith(MUSIC_LIB + "/"):
        return path
    os.makedirs(MEDIA, exist_ok=True)
    stem, ext = os.path.splitext(os.path.basename(path))
    dst = os.path.join(MEDIA, re.sub(r"[^A-Za-z0-9._-]+", "_", stem).strip("_") + ext.lower())
    if not os.path.exists(dst) or os.path.getsize(dst) != os.path.getsize(path):
        shutil.copy2(path, dst)
    return dst


def asset(path, kind):
    path = collect(path)
    if path in asset_ids:
        return asset_ids[path]
    aid = f"a{len(asset_ids) + 1}"
    asset_ids[path] = aid
    pr = probe(path) if kind != "still" else dict(dur=0, audio=False)
    dur = "0s" if kind == "still" else f"{int(pr['dur'] * 1000)}/1000s"
    has_v = "1" if kind in ("video", "still", "overlay", "overlay_v") else "0"
    has_a = "1" if kind in ("audio", "overlay") and pr["audio"] or kind == "audio" else "0"
    fmt = ' format="r1"' if kind in ("video", "overlay", "overlay_v") else ""
    url = "file://" + urllib.parse.quote(path)
    extra = ' audioSources="1" audioChannels="2" audioRate="48000"' if has_a == "1" else ""
    assets.append(f'<asset id="{aid}" name="{escape(os.path.basename(path))}" start="{rs(timecode(path))}" '
                  f'duration="{dur}" hasVideo="{has_v}" hasAudio="{has_a}"{fmt}{extra}>'
                  f'<media-rep kind="original-media" src="{escape(url)}"/></asset>')
    return aid


def parent_for(tl_frame):
    for s in shots + gaps:
        if s["f0"] <= tl_frame < s["f1"]:
            return s
    return shots[-1]


connected = {id(s): [] for s in shots + gaps}


def connect(tl_start_s, xml_fn):
    f = frames(tl_start_s)
    p = parent_for(f)
    if p.get("gap"):                                    # gaps have their own clock starting at 0
        connected[id(p)].append(xml_fn(ts(f - p["f0"])))
        return
    local = p["in_f"] + (f - p["f0"])                   # offset in parent's source time
    connected[id(p)].append(xml_fn(rs(timecode(p["path"]) + Fraction(local * 1001, 30000))))


def vol(db):
    return f'<adjust-volume amount="{db}dB"/>'


for c in vo_clips:
    aid = asset(c["path"], "audio")
    connect(c["start"], lambda off, aid=aid, c=c: f'<asset-clip ref="{aid}" lane="-1" offset="{off}" '
            f'name="VO" start="{rs(timecode(c["path"]) + Fraction(c["src_in"]).limit_denominator(48000))}" duration="{ts(frames(c["dur"]))}" role="dialogue"/>')
for c in music:
    aid = asset(c["path"], "audio")
    connect(c["start"], lambda off, aid=aid, c=c: f'<asset-clip ref="{aid}" lane="{c["lane"]}" offset="{off}" '
            f'name="Music" start="0s" duration="{ts(frames(c["dur"]))}" role="music">{vol(MUSIC_DB)}</asset-clip>')
if not os.path.exists(LOGO):
    # full-frame 4K overlay with the corner logo where the channel places it (measured on the reference)
    os.makedirs(GEN, exist_ok=True)
    subprocess.run([sys.executable, "-I", os.path.join(HERE, "make-logo-overlay.py"),
                    os.path.join(TEMPLATE, CH["logo_file"]), LOGO] + [str(v) for v in CH["logo_box"]], check=True)
logo_id = asset(LOGO, "still")
connect(0, lambda off: f'<video ref="{logo_id}" lane="2" offset="{off}" name="Logo" start="0s" '
        f'duration="{ts(shots[-1]["f1"])}"/>')          # logo stays to the very end
# the ending's own sound (channel.json "ending_sound") goes on FINAL A3 under it
overlays = [dict(name="ENDING", path=ending, audio=ending if CH.get("ending_sound") and probe(ending)["audio"] else None,
                 start=end_of_vo, dur=ending_dur)]
end_id = asset(ending, "overlay_v")
connect(end_of_vo, lambda off: f'<video ref="{end_id}" lane="1" offset="{off}" name="ENDING" '
        f'start="0s" duration="{ts(frames(ending_dur))}"/>')


def placed_copy(src, motion, out):
    """An overlay placed like the channel's template sequence: motion = scale %, centre x / y as
    fractions of the frame. Baked into a full-frame alpha copy (with its sound) so every NLE
    shows it the same way."""
    if not os.path.exists(out):
        sc, cx, cy = motion
        os.makedirs(GEN, exist_ok=True)
        w, h = int(3840 * sc / 100) // 2 * 2, int(2160 * sc / 100) // 2 * 2
        x, y = int(3840 * cx - w / 2), int(2160 * cy - h / 2)
        # pad cannot place a frame partly outside the canvas: crop the overhang (transparent) first
        cl, ct = max(0, -x), max(0, -y)
        cw, ch = min(w, 3840 - x) - cl, min(h, 2160 - y) - ct
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", src, "-map", "0:v", "-map", "0:a?",
                        "-vf", f"scale={w}:{h},format=argb,crop={cw}:{ch}:{cl}:{ct},"
                               f"pad=3840:2160:{max(x, 0)}:{max(y, 0)}:color=black@0",
                        "-c:v", "qtrle", "-c:a", "copy", out], check=True)
    return out


# subscribe: the alpha version (an rgb24 copy without alpha would black out the frame), with its sound
sub_v = os.path.join(TEMPLATE, CH["subscribe_file"])
if CH.get("subscribe_motion"):
    sub_v = placed_copy(sub_v, CH["subscribe_motion"], os.path.join(GEN, "subscribe.mov"))
sub_dur = probe(sub_v)["dur"]
# its sound (on FINAL A3) comes from the subscribe file itself, or from the separate file the
# channel's template sequence uses for it (subscribe_audio_file)
sub_src = os.path.join(TEMPLATE, CH["subscribe_audio_file"]) if CH.get("subscribe_audio_file") else sub_v
sub_a = sub_src if CH.get("subscribe_sound") and subprocess.run(
    ["ffprobe", "-v", "error", "-select_streams", "a", "-show_entries", "stream=index", "-of", "csv=p=0", sub_src],
    capture_output=True, text=True).stdout.strip() else None
# one Subscribe, as the VO calls on viewers: the first script line mentioning "subscribe", else the
# first line asking them to comment (not the quiz's "Comment your answer"; Tripinsight's
# "comment number 9 …" — where the editor puts it in the ES / PT edits), else the sentence nearest
# the middle of the video
asks = ([s for s in shots if re.search(r"subscrib", str(s["line"]["en"]), re.I)]
        or [s for s in shots if KIND[s["part"]] != "quiz" and re.search(r"\bcomment", str(s["line"]["en"]), re.I)])
mid = shots[-1]["f1"] / 2
for _ in [0]:
    if asks:
        st = asks[0]["f0"] / float(FPS) + CUT_LEAD          # when the line starts being spoken
    else:
        first = min((s for s in shots if KIND[s["part"]] == "location" and not s.get("part_start")),
                    key=lambda s: abs(s["f0"] - mid))
        st = first["f0"] / float(FPS) + 1.0
    vid = asset(sub_v, "overlay_v")
    overlays.append(dict(name="Subscribe", path=sub_v, audio=sub_a, start=st, dur=sub_dur))
    connect(st, lambda off, vid=vid: (
        f'<video ref="{vid}" lane="1" offset="{off}" name="Subscribe" start="0s" '
        f'duration="{ts(frames(sub_dur))}"/>'))
# call-to-action card (Tripinsight: the QR code), shown "lead" seconds before the line that
# mentions it is spoken (never before its section starts), placed like the template sequence
cta = CH.get("cta")
cta_asks = [s for s in shots if cta and re.search(re.escape(cta["match"]), str(s["line"]["en"]), re.I)]
if cta_asks:
    cta_v = os.path.join(TEMPLATE, cta["file"])
    if cta.get("motion"):
        cta_v = placed_copy(cta_v, cta["motion"], os.path.join(GEN, "cta.mov"))
    sec_f0 = next(s for s in shots if s["section"] == cta_asks[0]["section"])["f0"]
    st = max(sec_f0 / float(FPS), cta_asks[0]["f0"] / float(FPS) + CUT_LEAD - cta.get("lead", 0))
    cta_dur = probe(cta_v)["dur"]
    cid_ = asset(cta_v, "overlay_v")
    overlays.append(dict(name="CTA", path=cta_v, audio=cta_v if probe(cta_v)["audio"] else None,
                         start=st, dur=cta_dur))
    connect(st, lambda off, cid_=cid_: (f'<video ref="{cid_}" lane="1" offset="{off}" name="CTA" start="0s" '
                                         f'duration="{ts(frames(cta_dur))}"/>'))
# location-name lower third (the script's section heading, minus its number) on V2; Chaseland also
# names its story sections (History, Cuisine …): channel.json "lower_third_kinds"
for prefix, _ in PLAN:
    if KIND[prefix] not in CH.get("lower_third_kinds", ["location"]):
        continue
    name = re.sub(r"^\d+\.\s*", "", prefix)
    first = next(s for s in shots if s["section"] == prefix)
    os.makedirs(GEN, exist_ok=True)
    lt = os.path.join(GEN, "lower-third-" + re.sub(r"[^A-Za-z0-9]+", "-", name).strip("-").lower() + ".mov")
    if not os.path.exists(lt):
        if CH.get("lower_third_style") == "pin":           # Docs Untold: pin + place + region
            cmd = ["render-lower-third-pin.py", name, EP.get("region", ""), f"{LOWER_THIRD_DUR}", lt]
        elif CH.get("lower_third_style") == "bracket":     # Tripinsight: number in brackets + place + region
            cmd = ["render-lower-third-bracket.py", re.match(r"\d+", prefix).group(0), name,
                   EP.get("region", ""), f"{LOWER_THIRD_DUR}", lt]
        elif CH.get("lower_third_style") == "caption":     # Chaseland: plain Be Vietnam Pro caps, fades
            cmd = ["render-caption.py", "lower", name, f"{LOWER_THIRD_DUR}", lt]
        else:                                               # Earthcue: plain Jost caps
            cmd = ["render-lower-third.py", name, f"{LOWER_THIRD_DUR}", lt]
        subprocess.run([sys.executable, "-I", os.path.join(HERE, cmd[0])] + cmd[1:], check=True)
    st = first["f0"] / float(FPS)                      # appears as the section begins
    lid = asset(lt, "overlay_v")
    overlays.append(dict(name="Lower third", path=lt, audio=None, start=st, dur=LOWER_THIRD_DUR))
    connect(st, lambda off, lid=lid: (
        f'<video ref="{lid}" lane="1" offset="{off}" name="Lower third" start="0s" '
        f'duration="{ts(frames(LOWER_THIRD_DUR))}"/>'))
# opening title (episode region in large serif caps) for channels that use one
if CH.get("intro_title") and EP.get("region"):
    os.makedirs(GEN, exist_ok=True)
    it = os.path.join(GEN, "intro-title.mov")
    it_start, it_dur = CH.get("intro_title_start", 0.5), CH.get("intro_title_seconds", 6.0)
    if not os.path.exists(it):
        cmd = (["render-caption.py", "title", EP["region"]] if CH.get("intro_title_style") == "blur"   # Chaseland
               else ["render-intro-title.py", EP["region"]])                                            # Docs Untold
        subprocess.run([sys.executable, "-I", os.path.join(HERE, cmd[0])] + cmd[1:] + [f"{it_dur}", it], check=True)
    iid = asset(it, "overlay_v")
    overlays.append(dict(name="Intro title", path=it, audio=None, start=it_start, dur=it_dur))
    connect(it_start, lambda off: (f'<video ref="{iid}" lane="1" offset="{off}" name="Intro title" start="0s" '
                                   f'duration="{ts(frames(it_dur))}"/>'))
# quiz card: animated 4K ProRes 4444 overlay rendered by render-quiz.py
for k, ti in enumerate(titles):
    os.makedirs(GEN, exist_ok=True)
    qmov = os.path.join(GEN, f"quiz-{k + 1}.mov")
    qdur = ti["end"] - ti["start"]
    fit = [",".join(str(v) for v in CH["quiz_fit"])] if CH.get("quiz_fit") else []
    subprocess.run([sys.executable, "-I", os.path.join(os.path.dirname(os.path.abspath(__file__)), "render-quiz.py"),
                    ti["text"], f"{qdur:.4f}", qmov] + fit, check=True)
    qid = asset(qmov, "overlay_v")
    overlays.append(dict(name="Quiz", path=qmov, audio=None, start=ti["start"], dur=qdur))
    connect(ti["start"], lambda off, qid=qid, qdur=qdur: (
        f'<video ref="{qid}" lane="1" offset="{off}" name="Quiz" start="0s" duration="{ts(frames(qdur))}"/>'))

# every cut dissolves; the cut nearest the start of each VO part gets the longer one
dissolve_at = {i for i, s in enumerate(shots) if i and s.get("part_start")}
def transition(at, dlen):
    return (f'<transition name="Cross Dissolve" offset="{ts(at - dlen // 2)}" duration="{ts(dlen)}">'
            f'<filter-video ref="fx1" name="Cross Dissolve"/></transition>')


spine = []
for i, s in enumerate(shots):
    aid = asset(s["path"], "video")
    dur = s["f1"] - s["f0"]
    if i and s.get("dip"):
        g = next(g for g in gaps if g["f1"] == s["f0"])
        spine.append(transition(g["f0"], DIP))         # fade out into black
        spine.append(f'<gap name="Gap" offset="{ts(g["f0"])}" start="0s" duration="{ts(g["f1"] - g["f0"])}">'
                     f'{"".join(connected[id(g)])}</gap>')
        spine.append(transition(s["f0"], DIP))         # fade up from black
    elif i and shots[i - 1].get("gap_after"):          # empty V1 where the footage ran out
        g = next(g for g in gaps if g["f1"] == s["f0"])
        spine.append(f'<gap name="Gap" offset="{ts(g["f0"])}" start="0s" duration="{ts(g["f1"] - g["f0"])}">'
                     f'{"".join(connected[id(g)])}</gap>')
    elif i:
        spine.append(transition(s["f0"], PART_DISSOLVE if i in dissolve_at else DISSOLVE))
    inner = "".join(connected[id(s)])
    spine.append(f'<asset-clip ref="{aid}" offset="{ts(s["f0"])}" name="{escape(s["line"]["file"])}" '
                 f'start="{rs(timecode(s["path"]) + Fraction(s["in_f"] * 1001, 30000))}" duration="{ts(dur)}" audioRole="dialogue" tcFormat="NDF">'
                 f'<adjust-volume amount="-96dB"/>{inner}</asset-clip>')

total = max(shots[-1]["f1"], frames(timeline_end))     # a short last clip must not cut the ending off
xml = f'''<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE fcpxml>
<fcpxml version="1.10">
<resources>
<format id="r1" name="FFVideoFormat2160p2997" frameDuration="1001/30000s" width="3840" height="2160"/>
<effect id="fx1" name="Cross Dissolve" uid="FxPlug:4731E73A-8DAC-4113-9A30-AE85B1761265"/>
{chr(10).join(assets)}
</resources>
<library><event name="{escape(NAME)}"><project name="{escape(NAME)}">
<sequence format="r1" duration="{ts(total)}" tcStart="0s" tcFormat="NDF" audioLayout="stereo" audioRate="48k">
<spine>
{chr(10).join(spine)}
</spine></sequence></project></event></library></fcpxml>
'''
if CH.get("export_resolve"):
    open(os.path.join(OUT_DIR, f"{NAME}.fcpxml"), "w").write(xml)
# the Premiere XML / final render read edl.json: point music at its copy in MEDIA
for c in music:
    c["path"] = collect(c["path"])
for o in overlays:
    o["path"] = collect(o["path"])
json.dump(dict(total_s=total / float(FPS), shots=[dict(file=s["line"]["file"], start=s["f0"] / float(FPS),
          dur=(s["f1"] - s["f0"]) / float(FPS), text=s["line"]["en"], path=s["path"],
          f0=s["f0"], f1=s["f1"], in_f=s["in_f"], dip=bool(s.get("dip")), still=bool(s.get("still")),
          gap_after=bool(s.get("gap_after")), section=s["section"], part=s["part"], kind=KIND[s["section"]]) for s in shots], dissolve=DISSOLVE,
          dip=DIP,
          dissolve_at=sorted(dissolve_at), part_dissolve=PART_DISSOLVE, overlays=overlays,
          vo=vo_clips, music=music, sfx=sfx_clips, titles=titles, warnings=warnings,
          logo=LOGO, music_db=MUSIC_DB, name=NAME),
          open(os.path.join(WORK, "edl.json"), "w"), indent=1, default=str)
# same edit as a Final Cut Pro 7 XML that Premiere Pro imports (File > Import)
subprocess.run([sys.executable, "-I", os.path.join(os.path.dirname(os.path.abspath(__file__)), "export-premiere-xml.py"),
                os.path.join(WORK, "edl.json"), os.path.join(OUT_DIR, f"{NAME}.xml")], check=True)
d = [(s["f1"] - s["f0"]) / float(FPS) for s in shots]
print(f"total {total / float(FPS) / 60:.2f} min, shots {len(shots)}, median {sorted(d)[len(d) // 2]:.1f}s, "
      f"min {min(d):.1f}s, max {max(d):.1f}s, sfx {len(sfx_clips)}, music {len(music)}")
print("\n".join(warnings) or "no footage-length warnings")
