# Chaseland

Assets and options: `channel.json` here. Shared style: `skills/house-style.md`.

## Chaseland specifics (measured from "260822 Chaseland - Australia" project + FINAL)

- Episode: `<episode>/{xlsx, VIDEO, AUDIO, PROJECT/Epidemic Sound/Music, FINAL}`; VO in `AUDIO` (EN only).
- Script quirks handled by `engine/prepare-episode.py`: headings carry a timestamp ("15:19 Sydney Harbour") and no
  number — the timestamp is dropped and the number taken from the VO files ("1. Sydney Harbour 1.mp3");
  story sections (History, Current life, Cuisine) take the VO named after them ("History 1.mp3");
  `AUDIO/<Region>.mp3` ("Australia.mp3") is the region name said over the opening title (`title_vo`).
- Opening: region title in Futura Medium caps (macOS system font), centred, caps 921-1303, comes out of a
  blur 0.8-1.8 s and blurs away 4.2-6.9 s (`render-caption.py title`), on V2 from 1.3 s for 7.04 s; the
  title VO 2.34 s after it; the intro VO starts at 8.9 s (`intro_lead`).
- Lower third: section name in white Be Vietnam Pro Regular caps, bottom left (x=95, caps 1950-2069), fades
  in 0.8 s / out 25 frames, 7.2 s — on locations AND story sections (`lower_third_kinds`). No number.
- Watermark `WATERMARK.png` ("CHASELAND") at 30 %: visible part 304 px wide at (3482, 52).
- Subscribe `subscribe-box.mov` (1080p, no sound) at 200 % centred, at the "subscribe" line (History).
- Ending `Ending Screen Chaseland.mov` (alpha, 15 s, with sound → A3) over the last footage after the VO.
- No quiz, no QR, no other languages on this channel (so far).
