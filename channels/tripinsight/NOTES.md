# Tripinsight

Assets and options: `channel.json` here. Shared style: `skills/house-style.md`.

## Tripinsight specifics (measured from "260414 Tripinsight - Colombia" EN project + FINAL)

- Episode layout: `<episode>/{xlsx, VIDEO, SOUND/Music, EN, ES, PT}`; each language folder has its own
  project, `AUDIO <LANG>` and `FINAL <LANG>`. EN: `EN/AUDIO EN` → output in `EN/`; ES / PT: `./autoedit lang`.
- Script sheet quirks handled by `engine/prepare-episode.py`: no "Intro" heading (the intro's pasted paragraph is
  the first heading); every section has its whole text pasted on the row under its heading (skipped);
  rows with footage but no English text share the previous spoken line's time on screen evenly.
- Logo `tripinsight-logo.png` (2048 px) at 10 %, centre (0.973, 0.048). `make-logo-overlay.py` crops to the
  opaque area first, so `logo_box` is that area: 147 px wide at (3663, 25) (ES/PT logos are 1024 px at 20 %).
- Lower third (LOWER_THIRDS_4K_20 MOGRT at 40 %), re-made by `render-lower-third-bracket.py`: location number in
  Montserrat ExtraBold 77 inside a white bracket + coral (246,103,80) offset bracket, place in Montserrat Bold 69
  white caps from x=361 (caps 1869-1916), region in Montserrat Medium 28 slanted (1939-1959); lines grow,
  name wipes in, number, then region; 5.97 s, fades out over the last 25 frames.
- Quiz = Earthcue's card (`render-quiz.py`) scaled 0.619 about (1920, 1135), answers bold ×1.19 (`quiz_fit`).
- CTA: `QR.mov` at 66.67 %, centre (0.175, 0.8657), from 4.5 s before the line saying "QR code" (`cta`).
- Ending `4k end.mp4` (21 s, opaque, with sound → FINAL A3, `ending_sound`). Subscribe `SUB EN.mov` full
  frame with its own sound (no subscribe line in the Colombia script → middle of the video, house style).
- ES / PT (user-chosen 2026-10-21: clone the EN edit, swap the audio): `./autoedit lang "<episode>" ES|PT` after
  EN is built. Sections reordered by the number in the ES / PT heading (quiz stays after its location); each
  section's VO files are cut at their longest silences (ffmpeg silencedetect, no transcription) into as many slices
  as the EN section has, slice i replaces EN slice i and the shots under it are re-timed piecewise (whole-section
  stretch when the language has more files than EN has slices). Per-language assets in `channel.json`
  `languages`: ES logo 151 px, lower third "box" (orange, 6.97 s; text sizes / letter spacing from the template's "09 LOCATION" sample, not the ES FINAL — user-set 2026-10-22), ending `ENDING ES NEW-001.mov` at 200 %,
  no Subscribe: the user adds SUB ES (a MOGRT) by hand in Premiere (user-set 2026-10-22) — do not raise it as an open issue; PT logo 147 px, lower third "frame" (green, 6.31 s; shapes, 2-digit number and animation matched frame by frame to the template's own render `PT LOWER THIRD_Rendered.mov` — user-set 2026-10-22),
  `SUB PT.mov`, `ending 4k PT.mov`. Both lower thirds: `render-lower-third-lang.py`. Files named
  "… (sửa câu cuối)" replace the plain one.
- The editor's own EN edit differs from the house style in: ~2.5 s pauses (not 5 s), music per section
  sequence (not FINAL A2), ambience SFX, an 8.5 s quiz countdown with "Grandfather Clock 01.wav", no Subscribe.
  Not adopted unless the user asks.
