"""Read the SFX an editor added in Premiere out of their finished project (.prproj).

The project is built by importing the engine's EN xml, so it keeps that layout: one sequence per
section (named after the section), A1 the VO sentence slices, A2-A4 left free for the editor's SFX,
A5+ the music. Only the section sequences are read, and only the clips that are neither VO nor music:
those are the SFX to carry into the ES / PT edit (make-language.py).

A .prproj is a gzipped XML of Premiere's own objects: every object carries an ObjectID / ObjectUID and
refers to the others by ObjectRef / ObjectURef. A clip is reached as
  Sequence -> TrackGroups -> (audio) TrackGroup -> Track -> AudioClipTrack
           -> ClipItems/TrackItems -> AudioClipTrackItem -> {Start, End} + SubClip -> {Name, Clip -> InPoint}
Times are in ticks; Start is left out when it is 0.

Media paths in the file point at the editor's own machine, so files are found by name under the
episode folder instead.

Usage (check what would be carried over):  python read-prproj.py "<project.prproj>" ["<episode>"]
"""
import gzip, os, re, sys, unicodedata, xml.etree.ElementTree as ET

TICKS = 254016000000                                     # Premiere ticks per second
AUDIO_MEDIA_TYPE = "80b8e3d5-6dca-4195-aefb-cb5f407ab009"
SOUND_EXT = (".mp3", ".wav", ".aif", ".aiff", ".m4a", ".mov", ".mp4")


def _load(path):
    with gzip.open(path, "rb") as f:
        return ET.parse(f).getroot()


def _index(root):
    byid = {el.get("ObjectID"): el for el in root if el.get("ObjectID")}
    byuid = {el.get("ObjectUID"): el for el in root if el.get("ObjectUID")}
    return byid, byuid


def _audio_clips(seq, byid, byuid):
    """Every audio clip of one sequence: (track index, start s, end s, source in s, file name)."""
    out = []
    for group in seq.find("TrackGroups") or []:
        if group.findtext("First") != AUDIO_MEDIA_TYPE:
            continue
        tg = byid.get(group.find("Second").get("ObjectRef"))
        for t in (tg.findall("TrackGroup/Tracks/Track") if tg is not None else []):
            track = byuid.get(t.get("ObjectURef"))
            if track is None:
                continue
            for item in track.findall("ClipTrack/ClipItems/TrackItems/TrackItem"):
                clip = byid.get(item.get("ObjectRef"))
                if clip is None or clip.find(".//End") is None:
                    continue
                sub = clip.find("ClipTrackItem/SubClip")
                sub = byid.get(sub.get("ObjectRef")) if sub is not None else None
                if sub is None:
                    continue
                src = sub.find("Clip")
                src = byid.get(src.get("ObjectRef")) if src is not None else None
                out.append(dict(
                    track=int(t.get("Index")),
                    tag=clip.findtext(".//ESP.Tag") or "",
                    start=int(clip.findtext(".//Start") or 0) / TICKS,   # left out when 0
                    end=int(clip.findtext(".//End")) / TICKS,
                    src_in=int((src.findtext(".//InPoint") if src is not None else None) or 0) / TICKS,
                    name=sub.findtext("Name") or "",
                ))
    return out


def _sound_files(root_dir):
    """Every sound file under the episode, by folded name: the paths in the project are the editor's."""
    found = {}
    for dirpath, dirnames, filenames in os.walk(root_dir):
        dirnames[:] = [d for d in dirnames if not d.startswith((".", "Adobe "))]
        for f in filenames:
            if f.lower().endswith(SOUND_EXT) and not f.startswith("._"):
                found.setdefault(_fold(f), os.path.join(dirpath, f))
                found.setdefault(_fold(os.path.splitext(f)[0]), os.path.join(dirpath, f))
    return found


def section_sfx(prproj, episode_root, sections, skip=(), also=()):
    """{section name: [clip, ...]} — the SFX the editor added, per section sequence.

    sections: the names to read (the edit's own sections); skip: file names that are VO or music;
    also: further folders to look the media up in (the channel template, the music library).
    Clip times are relative to the start of the section. Clips whose file is nowhere to be found are
    dropped and reported (the xml must not point at media that is not there).
    """
    root = _load(prproj)
    byid, byuid = _index(root)
    wanted = {_key(s): s for s in sections}
    skip = {_fold(re.sub(r"\s*\(\d+\)$", "", os.path.splitext(os.path.basename(s))[0])) for s in skip}
    files, missing, out = _sound_files(episode_root), set(), {}
    for d in also:
        for k, v in _sound_files(d).items():
            files.setdefault(k, v)
    for seq in [el for el in root if el.tag == "Sequence" and el.get("ObjectUID")]:
        name = wanted.get(_key(seq.findtext("Name") or ""))
        if name is None:
            continue
        for c in _audio_clips(seq, byid, byuid):
            stem = os.path.splitext(c["name"])[0]
            if _fold(re.sub(r"\s*\(\d+\)$", "", stem)) in skip or c["tag"] == "music":
                continue                                 # the VO and the music are laid out by the engine
            path = files.get(_fold(c["name"])) or files.get(_fold(stem))
            if not path:
                missing.add(c["name"])
                continue
            out.setdefault(name, []).append(
                dict(name=c["name"], path=path, track=c["track"],
                     start=c["start"], dur=c["end"] - c["start"], src_in=c["src_in"]))
    return out, sorted(missing)


def _fold(s):
    """Lowercase, single-spaced, without accents: macOS writes "Jardín" in a file name decomposed,
    Premiere stores it composed, and the two must still be the same name."""
    s = "".join(c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", s).strip().lower()


def _key(s):
    """Match a project sequence to a section: the engine numbers them ("INTRO" -> "0. INTRO")."""
    return _fold(re.sub(r"^\d+\.\s*", "", s.splitlines()[0] if s else ""))


if __name__ == "__main__":
    proj = sys.argv[1]
    ep = sys.argv[2] if len(sys.argv) > 2 else os.path.dirname(os.path.abspath(proj))
    root = _load(proj)
    byid, byuid = _index(root)
    for seq in [el for el in root if el.tag == "Sequence" and el.get("ObjectUID")]:
        clips = _audio_clips(seq, byid, byuid)
        if clips:
            print(f"== {seq.findtext('Name')}")
            for c in sorted(clips, key=lambda c: (c["track"], c["start"])):
                print(f"   A{c['track'] + 1} {c['start']:8.2f}-{c['end']:8.2f} in={c['src_in']:7.2f}  {c['name']}")
