# Earthcue

Assets and options: `channel.json` here. Shared style: `skills/house-style.md`.

## Earthcue specifics

- Episode: `<episode>/{xlsx, VIDEO, EN/AUDIO, Epidemic Sound/Music, ES/AUDIO ES, FINAL}`; VO in `EN/AUDIO`
  (`INTRO … 1/2`, `STORY … 1/2/3`, `QUIZ …`, `1. <Place> EN 1/2/3`, `OUTRO …`). No `QUIZ …` file: the quiz
  is read at the end of the location before it and cut out of that file (`skills/house-style.md`).
- Logo `Logo góc Earthcue.png`: visible part 415 px wide at (3355, 62).
- Lower third: section heading without its number, Jost Regular, white caps, x=130, baseline 2068, 4 s
  (`render-lower-third.py`, style `plain`).
- Quiz card: user-supplied design (Quiz Time!, Montserrat, blue countdown bar, 2x2 white boxes), same size
  as Tripinsight's — scaled 0.619 about (1920, 1135), answers bold ×1.19 (`quiz_fit`, user-set 2026-10-23).
- Subscribe `YSB THIRD 4K2.mov` (alpha, full frame as in the template), its sound from `YSB THIRD 4K sfx.mov`
  (that file has no alpha: never use its picture). Ending `ENDING EARTHCUE.mov`.
- Story-section centre title (not built yet): centred white caps, Be Vietnam Pro Regular — an extra graphic,
  the Jost lower third stays as it is (user-set 2026-10-19).

## Spanish (ES) version

- `./autoedit lang "<episode>" ES` after the EN edit (same script as Tripinsight ES/PT, user-chosen 2026-10-21:
  clone the EN edit, swap the audio). Sections reordered by the number in the script's ES headings; VO from
  `<episode>/ES/AUDIO ES`; output `<episode>/ES/<name ES>.xml`.
- ES assets (`channel.json` `languages.ES`, measured from "260914 Earthcue - The Pacific Northwest" ES project):
  logo `logo GÓC Earthcue ES (Horizonte Azula).png` at 25 % (visible part 383 px at 3410, 48); ending
  `ENDING EARTH ES.mov` (1080p) at 200 %, no sound (as EN); same Subscribe (YSB THIRD + sfx), QR, quiz card
  (Spanish question) and plain lower third as EN.
- QR card (`cta`): `QR.mov` at 67 %, centre (0.175, 0.8657), 4.5 s before the "QR code" line — as in the EN project.
