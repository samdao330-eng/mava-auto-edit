# Build an episode

Input: an episode folder (e.g. `/Volumes/SAM/0-DOCSUNTOLD/260922 Docs Untold - Patagonia`), optionally a list
of sections (`intro,1,quiz,2,3,outro`). No folder given: ask for it, do not guess.

1. **Channel**: `./autoedit channel "<episode>"`. Empty → the channel has no `channels/<slug>/` yet: tell
   the user and follow `new-channel.md` only if they want it. Read `channels/<slug>/NOTES.md`.
   Do not re-derive the edit style (`house-style.md` is settled).

2. **Machine**: `~/.auto-edit-venv/bin/python` missing → `./autoedit setup`.

3. **Check the episode** and report briefly: the `.xlsx` (sheet "Content"), `VIDEO`, the VO folder
   (`AUDIO`, `EN/AUDIO` or `EN/AUDIO EN`); number of script rows, sections, VO files; footage named in the
   `File name EN` column that is missing from `VIDEO`. Missing footage or a section without VO → stop, list
   it, ask the user.

4. **Build**: `./autoedit edit "<episode>" [--sections …] [--name …] [--region …]` (run in the background:
   speech recognition takes a few minutes the first time, it is cached after). Output:
   `<episode>/<name>.xml` (Tripinsight: `<episode>/EN/<name>.xml`), music in `MEDIA/`, generated graphics
   and work data in `.autoedit/`.

5. **Check**: `./autoedit check "<xml>"` must say OK. Read the build's warnings (V1 gaps, lines not in the
   VO, unused VO files) and pass the relevant ones on.

6. **No render.** Only `./autoedit final "<episode>"` (≈ real time, in the background) when the user asks
   for a video; then check `<episode>/FINAL/<name>.mp4` lasts `total_s` of `.autoedit/_work/edl.json`.

7. **Report**: XML path, duration, shots / VO lines, warnings. Append to `logchat.md`.

ES / PT versions: `language-version.md`, only when asked, after EN. An episode name with ES / PT in it
(`/edit "260414 Tripinsight ES - Colombia"`) is a language build, not a new edit: go there instead.
