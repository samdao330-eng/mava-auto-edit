# House style (all channels)

Settled with the user. Change a rule only when the user asks, for every channel at once, and write the date
and "user-set" next to it. Channel assets (logo, lower third look, subscribe, ending, quiz size, QR) are not
style: they live in `channels/<slug>/channel.json`.

## Timeline layout (Premiere xmeml)

- Organised like the user's own projects (reference: Docs Untold - Arkansas): bins SOURCE/{ASSET, VIDEO,
  AUDIO, SOUND} and SEQUENCE/{0. INTRO, 1. <place> …, NN. OUTRO, FINAL}.
- One sequence per section: V1 footage (25-frame fades at its edges), A1 VO, empty A2–A4 for the editor's
  SFX (user-set 2026-10-19). No SFX from the toolkit.
- FINAL nests the sections on V1/A1; V2 graphics (title, lower thirds, quiz, subscribe, QR, ending), V3 logo
  (25-frame fades), A2 music, A3 the subscribe / ending sound. Graphics that overlap in time go on the next
  track up (V3, V4 …; logo above them) — xmeml cannot hold two overlapping clips on one track.
- 4K UHD 3840x2160, 29.97 fps. Audio tracks are stereo (see `premiere-xml.md`).
- Timeline length = max(last shot end, end of every overlay), so the ending is never cut.

## Footage and VO

- One shot per script row (`File name EN` → `VIDEO/<name>.*`; a name like `-<ID>` also matches), cut 0.25 s
  before its line.
- VO cut per spoken sentence (row ends with `.` `?` `!`) at the quietest point, then a **5 s pause**
  (3–5 s when the footage under it runs short, never below 3 s). Half-sentence rows stay joined.
- Footage stays on its own script line and never drifts from its VO. A clip shorter than its line plays in
  full from the line start and V1 is left **empty** for the rest — the editor fills it; the build prints
  each gap (user-set 2026-10-19).
- A row with footage but no text in the VO keeps its footage: it shares the previous line's time.
- Stills (photos in VIDEO) are scaled to 4K and held for their line.
- A section with no VO file of its own (the quiz, often read straight on at the end of the section before
  it) is cut out of that section's last file, in the silence before its first word (user-set 2026-10-23).

## Transitions

- 25-frame cross dissolve between shots, 30 frames at a new VO file.
- Between sections: fade to black + fade from black, 25 frames each (50 in total; user-set 2026-10-19).
- A quiz stays inside the section sequence of the location before it: no separate QUIZ sequence, no fade to
  black, 30-frame dissolve where its VO starts (user-set 2026-10-21).

## Graphics

- Lower third at the first cut of each location (and of story sections when the channel's
  `lower_third_kinds` says so), for the channel's `lower_third_seconds`.
- One Subscribe: where the VO starts the first line asking to subscribe; without one, the first line asking
  viewers to comment (not the quiz's "Comment your answer"); the middle of the video only if neither
  (user-set 2026-10-22). Placed and sized like the channel template (`subscribe_motion`), its sound on A3
  when the channel has one.
- QR card (`cta`): from `lead` seconds before the line that matches (e.g. "QR code").
- Ending right after the last VO, over the last footage; logo to the end.

## Music

- The episode's own music first (`Epidemic Sound/Music`, `SOUND/Music` or `PROJECT/Epidemic Sound/Music`),
  then the `BACKGROUND MUSIC` library, no repeats, -17 dB; the last song covers the end. Library songs are
  copied to `<out>/MEDIA` with ASCII names; everything else is referenced in place.
