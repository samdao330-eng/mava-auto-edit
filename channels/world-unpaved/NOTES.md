# World Unpaved

Assets and options: `channel.json` here. Shared style: `skills/house-style.md`.

## World Unpaved specifics (measured from "261015 World Unpaved - Amazon" project + FINAL, 2026-10-29)

- Episode: `<episode>/{xlsx, video, EN/AUDIO, EN/PROJECT, EN/FINAL}`; footage in `video/` (lower case).
  The VO comes zipped from Drive and unzips into `EN/AUDIO/<episode name>/`: the engine reads only
  `EN/AUDIO` itself, so copy the mp3s up one level (`cp -n`). `<episode>/<Region>.mp3` ("Amazon.mp3") is not
  used in the published edit.
- The first script lines (1-15 in Amazon) have footage and no text: a 30 s opening on music before the intro VO
  (published: 15 shots of 1.4-2.6 s, VO at 30.7 s) -> `cold_open_shot: 2.0` gives each 2 s, VO after them.
- A heading with no lines under it ("PLACES" between WILDLIFE and the first location) is only a divider in
  the script: skipped (`prepare-episode.py`).
- Amazon: script line 9 wants `9-539873277`, `video/` has `9-1434129624.mov` instead (the editor took the
  file from another drive) — to be settled by the user before a real build.
- Story sections ("THE AMAZON BASIN", "WILDLIFE") take the VO named after them ("WILDLIFE EN 1.mp3"); the
  intro VO is "INTRODUCTION EN <REGION> n.mp3", the outro "outro <episode> EN n - <Region>.mp3".
- Episode folders do not sit in a channel folder (yet): `match` also catches "World Unpaved - " in the name.
- **No corner logo** (`logo_file: null`): neither the template nor the published FINAL has one.
- Lower third (`lower_third_style: "bar"`, `engine/render-lower-third-bar.py`): the template's "TITLE" graphic
  — section name in white Be Vietnam Pro Regular caps behind a red bar rgb(213, 39, 39). On every location AND
  story section (not intro / outro), and it **stays on for the whole section**: the bar grows (0.29-0.66 s),
  letters fly in from the right one by one (0.39-1.46 s), at 3.05-3.5 s everything shrinks to 70.9 % towards
  the bottom left (large: bar x 130-142 / y 1848-2023, caps 1888-1984; small: bar 58-66 / 1960-2084, caps
  1989-2057), then letters fly out right to left in the last 0.81 s and the bar goes. On V2 as **one clip** per section
  (`lower-third-<name>-<frames>f.mov`, QuickTime Animation + alpha, made from cached in / hold / out pieces;
  user-set 2026-10-29: three clips per section were too many layers). No number.
- Subscribe `Subscribe WORLD UNPAVED.mov` (1080p 25 fps, alpha, no sound) at 200 % centred, 7.04 s.
- Ending `End Screen WORLD UNPAVED-001.mov` (4K alpha, 22.2 s, no sound).
- No opening title, no quiz, no QR, no other languages (the script has ES / PT columns, empty so far).
