"""Which channel an episode belongs to, and that channel's assets (channels/<slug>/channel.json).

The channel is, in order:
  1. AUTOEDIT_CHANNEL (slug), set by the autoedit command or by hand (tests on copies outside /Volumes/SAM/0-*)
  2. "channel" in <work>/episode.json, when the path given is an episode's .autoedit/_work
  3. the first channel whose "match" (e.g. "/0-EARTHCUE/") is in the path (or in episode.json "root")

load() also sets AUTOEDIT_CHANNEL so every script it starts uses the same channel.
"""
import json, os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CHANNELS = os.path.join(ROOT, "channels")


def slugs():
    return sorted(s for s in os.listdir(CHANNELS) if os.path.isfile(os.path.join(CHANNELS, s, "channel.json")))


def config(slug):
    return json.load(open(os.path.join(CHANNELS, slug, "channel.json")))


def detect(path):
    """Channel slug for an episode folder or work folder, or None."""
    slug = os.environ.get("AUTOEDIT_CHANNEL")
    if slug:
        return slug
    ep = os.path.join(path, "episode.json")
    ep = json.load(open(ep)) if os.path.isfile(ep) else {}
    if ep.get("channel"):
        return ep["channel"]
    p = (os.path.abspath(path) + "/" + ep.get("root", "") + "/").upper()
    return next((s for s in slugs() if any(m.upper() in p for m in config(s).get("match", []))), None)


def load(path):
    slug = detect(path)
    if slug not in slugs():
        sys.exit(f"Không biết {path} thuộc kênh nào (kênh có: {', '.join(slugs())}). "
                 "Đặt AUTOEDIT_CHANNEL=<kênh> hoặc thêm \"match\" vào channels/<kênh>/channel.json.")
    os.environ["AUTOEDIT_CHANNEL"] = slug
    return dict(config(slug), slug=slug)


if __name__ == "__main__":          # python channel.py <episode folder>  ->  prints the slug
    print(detect(sys.argv[1]) or "")
