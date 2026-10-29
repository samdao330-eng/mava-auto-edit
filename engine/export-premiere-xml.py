"""Write the edit in edl.json as a Final Cut Pro 7 XML (xmeml v4) that Premiere Pro
imports with File > Import, organised like the user's own projects:
  SOURCE/ASSET, VIDEO, AUDIO, SOUND   master clips (graphics, footage, VO, music)
  SEQUENCE/0. INTRO, 1. <place> …    one sequence per section: V1 footage with cross dissolves
                                     and a fade from / to black at its edges, A1 VO sentence slices,
                                     A2-A4 left empty for the editor's SFX
  SEQUENCE/FINAL                     the section sequences nested back to back (V1 + A1),
                                     V2 intro title / lower thirds / quiz / subscribe / ending,
                                     V3 logo, A2 background music, A3 overlay sound (Subscribe)

Usage: python export-premiere-xml.py <edl.json> <out.xml>
"""
import json, os, re, subprocess, sys, unicodedata, urllib.parse
from xml.sax.saxutils import escape

edl = json.load(open(sys.argv[1]))
out = sys.argv[2]
FPS = 30000 / 1001
W, H = 3840, 2160
RATE = "<rate><timebase>30</timebase><ntsc>TRUE</ntsc></rate>"

_probe = {}


def probe(path):
    """Duration (s) and whether the file has video / audio streams."""
    if path not in _probe:
        j = json.loads(subprocess.run(["ffprobe", "-v", "error", "-show_entries",
                                       "format=duration:stream=codec_type,channels,width,height", "-of", "json",
                                       path], capture_output=True, text=True).stdout)
        types = {s["codec_type"] for s in j.get("streams", [])}
        v = next((s for s in j.get("streams", []) if s["codec_type"] == "video" and s.get("width")), None)
        _size[path] = (v["width"], v["height"]) if v else (W, H)
        _channels[path] = max([s.get("channels", 0) for s in j.get("streams", []) if s["codec_type"] == "audio"] or [0])
        _probe[path] = (float(j["format"].get("duration") or 0), "video" in types, "audio" in types)
    return _probe[path]


_channels, _size = {}, {}


def size(path):
    """Frame size of a video file (the sequence size for audio-only files)."""
    probe(path)
    return _size[path]


def channels(path):
    probe(path)
    return _channels[path]


def fr(seconds):
    return int(round(float(seconds) * FPS))


# ---------------------------------------------------------------- master clips in SOURCE bins
files, masters, bins = {}, {}, {"ASSET": [], "VIDEO": [], "AUDIO": [], "SOUND": []}


def file_xml(path, fid, still):
    dur, has_v, has_a = probe(path)
    n = 86400 * 30 if still else max(1, fr(dur))           # stills: effectively unlimited
    media = ""
    if has_v or still:
        w, h = size(path)
        media += (f"<video><samplecharacteristics>{RATE}<width>{w}</width><height>{h}</height>"
                  f"</samplecharacteristics></video>")
    if has_a and not still:
        n_ch = channels(path)
        media += ("<audio><samplecharacteristics><depth>16</depth><samplerate>48000</samplerate>"
                  f"</samplecharacteristics><channelcount>{n_ch}</channelcount>"
                  + ("<layout>stereo</layout><audiochannel><sourcechannel>1</sourcechannel><channellabel>left"
                     "</channellabel></audiochannel><audiochannel><sourcechannel>2</sourcechannel>"
                     "<channellabel>right</channellabel></audiochannel>" if n_ch == 2 else "")
                  + "</audio>")
    # Premiere's FCP7 importer only takes %20: a path encoded any further (a comma, "&", brackets, or the
    # combining accent macOS writes in file names) makes it refuse the whole file, silently. So the path
    # goes in composed and with only the space escaped (user-set: found 2026-10-23).
    # quote() would escape every non-ASCII byte ("Yasuní" -> "Yasun%C3%AD"), so those letters are kept as they are
    url = "file://localhost" + "".join(c if ord(c) > 127 else urllib.parse.quote(c, safe="/,()&'!$+=@~[]^`{}|;?#")
                                       for c in unicodedata.normalize("NFC", path))
    return (f'<file id="{fid}"><name>{escape(os.path.basename(path))}</name>'
            f"<pathurl>{escape(url)}</pathurl>{RATE}<duration>{n}</duration>"
            f"<timecode>{RATE}<string>00:00:00:00</string><frame>0</frame><displayformat>NDF</displayformat>"
            f"</timecode><media>{media}</media></file>")


def master(path, bin_name, still=False):
    """Register a source file as a master clip in a SOURCE bin (once); returns its ids."""
    if path not in files:
        k = len(files) + 1
        fid, mid = f"file-{k}", f"masterclip-{k}"
        files[path], masters[path] = fid, mid
        dur, has_v, _ = probe(path)
        n = 86400 * 30 if still else max(1, fr(dur))
        kind = "video" if has_v or still else "audio"
        name = escape(os.path.basename(path))
        # Describe the file exactly as Premiere would import it (video and / or one stereo audio
        # clip), so Premiere reuses a master clip the editor already imported instead of adding a copy.
        media, defined = "", False
        if kind == "video":
            media += (f'<video><track><clipitem id="{mid}-item"><masterclipid>{mid}</masterclipid>'
                      f"<name>{name}</name>{file_xml(path, fid, still)}</clipitem></track></video>")
            defined = True
        if probe(path)[2] and not still:                # stereo audio: channel 1 and 2 as one pair
            items = []
            for c in (1, 2):
                body = f'<file id="{fid}"/>' if defined else file_xml(path, fid, still)
                defined = True
                items.append(f'<track><clipitem id="{mid}-item{c}"><masterclipid>{mid}</masterclipid>'
                             f"<name>{name}</name>{body}<sourcetrack><mediatype>audio</mediatype>"
                             f"<trackindex>{min(c, max(1, channels(path)))}</trackindex></sourcetrack>"
                             f"</clipitem></track>")
            media += "<audio>" + "".join(items) + "</audio>"
        bins[bin_name].append(
            f'<clip id="{mid}" explodedTracks="true"><masterclipid>{mid}</masterclipid><ismasterclip>TRUE</ismasterclip>'
            f"<name>{name}</name><duration>{n}</duration>{RATE}<in>-1</in><out>-1</out>"
            f"<media>{media}</media></clip>")
    return files[path], masters[path]


ids = [0]


def fill_motion(path):
    """Basic Motion scale that makes footage smaller than the 4K frame (Full HD, 2.7K, vertical …) fill it,
    centre-cropped like render-final (user-set 2026-10-29). Premiere places such a clip at 100 %, a small
    picture in black, so it has to be scaled up in the XML."""
    w, h = size(path)
    sc = max(W / w, H / h) * 100
    if sc < 100.01:                                     # 4K and larger (4096 x 2304 …) stay at 100 % as before
        return ""
    return ("<filter><effect><name>Basic Motion</name><effectid>basic</effectid><effectcategory>motion"
            "</effectcategory><effecttype>motion</effecttype><mediatype>video</mediatype>"
            "<parameter authoringApp=\"PremierePro\"><parameterid>scale</parameterid><name>Scale</name>"
            f"<valuemin>0</valuemin><valuemax>1000</valuemax><value>{sc:.2f}</value></parameter>"
            "</effect></filter>")


def clipitem(name, path, start, end, src_in, kind="video", still=False, gain=None, ch=1, cid=None, links="",
             fill=False):
    """One clip on a track. start/end are sequence frames, src_in a source frame.
    Audio: ch is the source channel this half of a stereo pair plays (mono files play channel 1 on both).
    fill: scale footage smaller than 4K up to fill the frame (V1 footage)."""
    if cid is None:
        ids[0] += 1
        cid = f"clipitem-{ids[0]}"
    src_out = src_in + (end - start)
    dur = 86400 * 30 if still else max(src_out, fr(probe(path)[0]))
    extra = fill_motion(path) if fill and kind == "video" else ""
    if kind == "audio":
        extra += (f"<sourcetrack><mediatype>audio</mediatype><trackindex>{min(ch, max(1, channels(path)))}"
                  f"</trackindex></sourcetrack>{links}")
        if gain is not None:
            lin = 10 ** (gain / 20)
            extra += ("<filter><effect><name>Audio Levels</name><effectid>audiolevels</effectid>"
                      "<effectcategory>audiolevels</effectcategory><effecttype>audiolevels</effecttype>"
                      "<mediatype>audio</mediatype><parameter><parameterid>level</parameterid>"
                      "<name>Level</name><valuemin>0</valuemin><valuemax>3.98109</valuemax>"
                      f"<value>{lin:.5f}</value></parameter></effect></filter>")
    return (f'<clipitem id="{cid}"><masterclipid>{masters[path]}</masterclipid>'
            f"<name>{escape(name)}</name><enabled>TRUE</enabled>"
            f"<duration>{dur}</duration>{RATE}<start>{start}</start><end>{end}</end>"
            f'<in>{src_in}</in><out>{src_out}</out><file id="{files[path]}"/>{extra}</clipitem>')


def nest(name, seq_id, start, end, kind="video", ch=1, cid=None, links=""):
    """A section sequence used as a clip inside FINAL (audio: one half of its stereo output)."""
    if cid is None:
        ids[0] += 1
        cid = f"clipitem-{ids[0]}"
    extra = (f"<sourcetrack><mediatype>audio</mediatype><trackindex>{ch}</trackindex></sourcetrack>{links}"
             if kind == "audio" else "")
    return (f'<clipitem id="{cid}"><name>{escape(name)}</name><enabled>TRUE</enabled>'
            f"<duration>{end - start}</duration>{RATE}<start>{start}</start><end>{end}</end>"
            f'<in>0</in><out>{end - start}</out><sequence id="{seq_id}"/>{extra}</clipitem>')


def dissolve(cut, length, align="center"):
    """Cross Dissolve at a cut (sequence frames): centred, or end-black / start-black
    for a fade to / from black that sits wholly on one clip."""
    a = {"center": cut - length // 2, "end-black": cut - length, "start-black": cut}[align]
    return (f"<transitionitem>{RATE}<start>{a}</start><end>{a + length}</end>"
            f"<alignment>{align}</alignment><cutPointTicks>0</cutPointTicks>"
            "<effect><name>Cross Dissolve</name><effectid>Cross Dissolve</effectid>"
            "<effectcategory>Dissolve</effectcategory><effecttype>transition</effecttype>"
            "<mediatype>video</mediatype><wipecode>0</wipecode><wipeaccuracy>100</wipeaccuracy>"
            "<startratio>0</startratio><endratio>1</endratio><reverse>FALSE</reverse></effect>"
            "</transitionitem>")


def track(items, attrs=""):
    return f"<track{attrs}>{''.join(items)}<enabled>TRUE</enabled><locked>FALSE</locked></track>"


def link(cid, track_no, clip_no):
    return (f"<link><linkclipref>{cid}</linkclipref><mediatype>audio</mediatype><trackindex>{track_no}</trackindex>"
            f"<clipindex>{clip_no}</clipindex><groupindex>1</groupindex></link>")


def stereo_tracks(entries, first_no):
    """A Premiere stereo track: two exploded xmeml tracks (left / right) whose clips are linked
    in pairs, so each file sits on ONE stereo track instead of being split over two mono ones.
    entries: functions (ch, cid, links) -> clipitem xml."""
    left, right = [], []
    for k, make in enumerate(entries, start=1):
        ids[0] += 2
        l_id, r_id = f"clipitem-{ids[0] - 1}", f"clipitem-{ids[0]}"
        links = link(l_id, first_no, k) + link(r_id, first_no + 1, k)
        left.append(make(1, l_id, links))
        right.append(make(2, r_id, links))
    attrs = ' currentExplodedTrackIndex="{}" totalExplodedTrackCount="2" premiereTrackType="Stereo"'
    return track(left, attrs.format(0)) + track(right, attrs.format(1))


def sequence(seq_id, name, length, vtracks, atracks):
    """atracks: one list of clip makers per stereo audio track."""
    return (f'<sequence id="{seq_id}"><name>{escape(name)}</name><duration>{length}</duration>{RATE}'
            f"<timecode>{RATE}<string>00:00:00:00</string><frame>0</frame><displayformat>NDF</displayformat></timecode>"
            f"<media><video><format><samplecharacteristics>{RATE}<width>{W}</width><height>{H}</height>"
            f"<pixelaspectratio>square</pixelaspectratio><fielddominance>none</fielddominance>"
            f"</samplecharacteristics></format>{''.join(track(t) for t in vtracks)}</video>"
            f"<audio><numOutputChannels>2</numOutputChannels><format><samplecharacteristics><depth>16</depth>"
            f"<samplerate>48000</samplerate></samplecharacteristics></format><outputs><group><index>1</index>"
            f"<numchannels>2</numchannels><downmix>0</downmix><channel><index>1</index></channel>"
            f"<channel><index>2</index></channel></group></outputs>"
            f"{''.join(stereo_tracks(t, 2 * k + 1) for k, t in enumerate(atracks))}</audio>"
            f"</media></sequence>")


shots = edl["shots"]
# the timeline runs to the end of the last shot or of the ending card, whichever is later
# (a last clip too short for its line must not cut the ending off)
total = max([shots[-1]["f1"]] + [round((o["start"] + o["dur"]) * FPS) for o in edl["overlays"]])
D, PD = edl["dissolve"], edl.get("part_dissolve", edl["dissolve"])
DIP = edl.get("dip", 25)
part_cuts = set(edl.get("dissolve_at", []))

for s in shots:
    master(s["path"], "VIDEO", still=s.get("still", False))
for v in edl["vo"]:
    master(v["path"], "AUDIO")
for m in edl["music"]:
    master(m["path"], "SOUND")
for x in edl.get("sfx", []):
    master(x["path"], "SOUND")
for o in edl["overlays"]:
    master(o["path"], "ASSET", still=o.get("still", False))
    if o.get("audio"):
        master(o["audio"], "ASSET")
if edl.get("logo"):                                     # a channel without a corner logo has none
    master(edl["logo"], "ASSET", still=True)

# ---------------------------------------------------------------- one sequence per section
# Sections split where the edit dips to black. Each runs from its first shot to the next
# section's first shot; it fades up from black at the start and down to black at the end.
starts = [0] + [i for i, s in enumerate(shots) if i and s.get("dip")]
max_no = max([int(m.group(1)) for s in shots for m in [re.match(r"(\d+)\.", s.get("section", ""))] if m] or [0])


def section_name(k, sec, kind=""):
    if re.match(r"\d+\.", sec):
        return sec
    if kind == "quiz":                                  # its heading is the whole question text
        n = sum(1 for i in starts[:k + 1] if shots[i].get("kind") == "quiz")
        return "QUIZ" if n == 1 and sum(1 for i in starts if shots[i].get("kind") == "quiz") == 1 else f"QUIZ {n}"
    if kind in ("intro", "outro") and "\n" in sec:   # heading is the section's pasted text: use its kind
        sec = kind.upper()
    return f"0. {sec}" if k == 0 else (f"{max_no + 1}. {sec}" if k == len(starts) - 1 else sec)


def lane_split(spans):
    """Spread (start, end, payload) over as few tracks as needed: xmeml rejects two clips overlapping on one
    track (Premiere refuses the whole file), e.g. a Subscribe that runs into the next section's lower third.
    The first lane is the usual track; the others go right above it."""
    out = []
    for item in sorted(spans, key=lambda x: x[0]):
        lane = next((ln for ln in out if ln[-1][1] <= item[0]), None)
        (lane.append(item) if lane else out.append([item]))
    return out or [[]]


def lanes(spans):
    """lane_split(), keeping only the payloads."""
    return [[o for _, _, o in ln] for ln in lane_split(spans)]


sections, sec_xml = [], []
vo = sorted(edl["vo"], key=lambda v: v["start"])
for k, a in enumerate(starts):
    b = starts[k + 1] if k + 1 < len(starts) else len(shots)
    S0 = shots[a]["f0"]
    S1 = shots[b]["f0"] if b < len(shots) else total
    v1 = []
    for i in range(a, b):
        s = shots[i]
        last = i == b - 1
        f1 = S1 if last and not s.get("gap_after") else s["f1"]   # last shot runs to the section end
        if i == a:
            v1.append(dissolve(0, DIP, "start-black"))
        elif not shots[i - 1].get("gap_after"):
            v1.append(dissolve(s["f0"] - S0, PD if i in part_cuts else D))
        v1.append(clipitem(s["file"], s["path"], s["f0"] - S0, f1 - S0, s["in_f"], still=s.get("still", False),
                           fill=True))
        if last:
            v1.append(dissolve(f1 - S0, DIP, "end-black"))
    a1 = [lambda ch, cid, links, v=v, S0=S0: clipitem(
              os.path.basename(v["path"]), v["path"], fr(v["start"]) - S0, fr(v["start"]) + fr(v["dur"]) - S0,
              fr(v.get("src_in", 0)), "audio", ch=ch, cid=cid, links=links)
          for v in vo if S0 <= fr(v["start"]) < S1]
    name = section_name(k, shots[a].get("section", f"Section {k + 1}"), shots[a].get("kind", ""))
    sid = f"sequence-{k + 1}"
    sections.append((name, sid, S0, S1))
    # A2 up: the editor's own SFX when there are any (make-language.py), else left empty for them
    # (start, end) in sequence frames, cut at the section's end: a clip running past the end of its
    # sequence makes Premiere refuse the whole file
    sfx = [(fr(x["start"]) - S0, min(fr(x["start"] + x["dur"]), S1) - S0, x)
           for x in edl.get("sfx", []) if S0 <= fr(x["start"]) < S1]
    sfx = [t for t in sfx if t[1] > t[0]]
    sfx_tracks = [[lambda ch, cid, links, b=b, e=e, x=x: clipitem(
                       x.get("name") or os.path.basename(x["path"]), x["path"], b, e,
                       fr(x.get("src_in", 0)), "audio", ch=ch, cid=cid, links=links) for b, e, x in ln]
                  for ln in lane_split(sfx)]
    sec_xml.append(sequence(sid, name, S1 - S0, [v1],
                            [a1] + (sfx_tracks + [[], [], []])[:max(3, len(sfx_tracks))]))

# ---------------------------------------------------------------- FINAL
fv1 = [nest(n, sid, S0, S1) for n, sid, S0, S1 in sections]
fa1 = [lambda ch, cid, links, n=n, sid=sid, S0=S0, S1=S1: nest(n, sid, S0, S1, "audio", ch, cid, links)
       for n, sid, S0, S1 in sections]
ov_spans = [(fr(o["start"]), fr(o["start"] + o["dur"]), o) for o in edl["overlays"]]
fv2 = [[clipitem(o["name"], o["path"], fr(o["start"]), fr(o["start"] + o["dur"]), 0, still=o.get("still", False))
        for o in ln]
       for ln in lanes(ov_spans)]
fv3 = [dissolve(0, DIP, "start-black"), clipitem("Logo", edl["logo"], 0, total, 0, still=True),
       dissolve(total, DIP, "end-black")] if edl.get("logo") else None
# end = frame of (start + length), so back-to-back songs meet exactly instead of overlapping by a frame
fa2 = [lambda ch, cid, links, m=m: clipitem(
           os.path.basename(m["path"]), m["path"], fr(m["start"]), fr(m["start"] + m["dur"]), 0, "audio",
           gain=edl.get("music_db", -17), ch=ch, cid=cid, links=links) for m in edl["music"]]
# A3: sound that belongs to an overlay (the Subscribe pop), under its picture
fa3 = [[lambda ch, cid, links, o=o: clipitem(o["name"], o["audio"], fr(o["start"]), fr(o["start"] + o["dur"]), 0,
                                             "audio", ch=ch, cid=cid, links=links) for o in ln]
       for ln in lanes([sp for sp in ov_spans if sp[2].get("audio")])]
final = sequence(f"sequence-{len(sections) + 1}", "FINAL", total, [fv1] + fv2 + ([fv3] if fv3 else []), [fa1, fa2] + fa3)


def bin_xml(name, children):
    return f"<bin><name>{escape(name)}</name><children>{''.join(children)}</children></bin>"


source = bin_xml("SOURCE", [bin_xml(n, c) for n, c in bins.items()])
seqbin = bin_xml("SEQUENCE", sec_xml + [final])
xml = (f'<?xml version="1.0" encoding="UTF-8"?>\n<!DOCTYPE xmeml>\n<xmeml version="4"><project>'
       f"<name>{escape(edl.get('name', 'Episode'))}</name><children>{source}{seqbin}</children></project></xmeml>\n")
open(out, "w").write(xml)
print("premiere xml:", out, f"({len(sections)} section sequences + FINAL, {len(shots)} shots, "
      f"{sum(len(ln) for ln in fv2)} overlays, {len(edl['vo'])} VO, {len(fa2)} music)")
