# Add a channel

A new channel is a new `channels/<slug>/` — never a copy of the engine.

1. Ask the user for one **published** episode of the channel (its folder with the Premiere project and
   `FINAL` video) and the channel's template folder in `/Volumes/SAM/0-SAM ASSET/`.
2. `channels/<slug>/channel.json`: start from the closest channel. Required: `channel`, `match`
   (e.g. `["/0-NEWCHANNEL/"]`, the episodes' parent folder), `template`, `music_lib`, `logo_file`,
   `logo_box`, `ending_file`, `subscribe_file`. Measure the rest from the project / FINAL frames:
   logo visible box, subscribe placement (`subscribe_motion` [scale %, cx, cy]), lower third style
   (`plain`, `pin`, `bracket`, `caption`, or a new renderer in `engine/` when none fits) and seconds,
   intro title, quiz size (`quiz_fit`), QR (`cta`), ending / subscribe sound, languages.
3. `channels/<slug>/NOTES.md`: what was measured and from which episode, the episode folder layout and
   script quirks.
4. Build the published episode with `./autoedit edit` into a scratch `--out`, compare it with the
   published FINAL (graphics position / size / timing), adjust, then add it to `tests/regression.sh`.
5. Fonts the renderer needs go in `engine/fonts/`.
