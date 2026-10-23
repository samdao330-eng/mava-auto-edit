"""Check a Premiere XML before the editor imports it. Premiere refuses the whole file (or loses media)
when one of these is wrong, so every build is checked:

  - the file parses (xmeml)
  - every <pathurl> exists on this machine
  - no two clips overlap on one track (xmeml rejects that)
  - no clip runs past the end of a nested (section) sequence: Premiere then refuses the whole file.
    FINAL may overrun — the edits built before 2026-10-23 do and import fine — so only the nested ones
    are checked (found 2026-10-23: an SFX past its section's end stopped Premiere importing at all)
  - clip ids are unique
  - there is a FINAL sequence and no separate QUIZ sequence (quiz stays in its location's sequence)

Usage: python check-xml.py <file.xml> ...   exit 1 when a file fails
"""
import os, re, sys, urllib.parse
import xml.etree.ElementTree as ET


def check(path):
    errors = []
    try:
        root = ET.parse(path).getroot()
    except ET.ParseError as e:
        return [f"XML hỏng: {e}"]
    missing = sorted({urllib.parse.unquote(urllib.parse.urlparse(u.text).path)
                      for u in root.iter("pathurl") if u.text} - {None})
    missing = [m for m in missing if not os.path.exists(m)]
    errors += [f"thiếu file: {m}" for m in missing[:10]] + ([f"… và {len(missing) - 10} file nữa"] if len(missing) > 10 else [])
    odd = sorted({m for u in root.iter("pathurl") for m in re.findall(r"%(?!20)[0-9A-Fa-f]{2}", u.text or "")})
    if odd:
        errors.append(f"đường dẫn mã hoá quá mức (Premiere chỉ nhận %20): {', '.join(odd)}")
    ids = [c.get("id") for c in root.iter("clipitem") if c.get("id")]
    if len(ids) != len(set(ids)):
        errors.append(f"trùng id clip: {len(ids) - len(set(ids))}")
    names = [s.findtext("name") or "" for s in root.iter("sequence")]
    if "FINAL" not in names:
        errors.append("không có sequence FINAL")
    errors += [f"có sequence quiz riêng: {n}" for n in names if "QUIZ" in n.upper()]
    for seq in root.iter("sequence"):
        media = seq.find("media")
        for kind in ("video", "audio"):
            m = media.find(kind) if media is not None else None
            for ti, tr in enumerate(m.findall("track") if m is not None else [], 1):
                items = sorted((int(c.findtext("start")), int(c.findtext("end")), c.findtext("name") or "")
                               for c in tr.findall("clipitem")
                               if c.findtext("start") and int(c.findtext("start")) >= 0)
                for a, b in zip(items, items[1:]):
                    if b[0] < a[1]:
                        errors.append(f"chồng clip {seq.findtext('name')} {kind[0].upper()}{ti}: "
                                      f"{a[2]} ({a[0]}-{a[1]}) / {b[2]} (từ {b[0]})")
                dur = seq.findtext("duration")
                for a in items if dur and (seq.findtext("name") or "") != "FINAL" else []:
                    if a[1] > int(dur):
                        errors.append(f"clip vượt quá sequence {seq.findtext('name')} "
                                      f"{kind[0].upper()}{ti}: {a[2]} hết ở {a[1]}, sequence dài {dur}")
    return errors


bad = 0
for x in sys.argv[1:]:
    errs = check(x)
    bad += bool(errs)
    print(("LỖI  " if errs else "OK   ") + x)
    for e in errs:
        print("     " + e)
sys.exit(1 if bad else 0)
