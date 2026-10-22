# ES / PT version of an episode

Chosen by the user (2026-10-21): **clone the finished EN edit and swap the audio** — not a new edit.
Channels with languages: see `languages` in their `channel.json` (Tripinsight ES + PT, Earthcue ES).

1. The EN edit must exist (`<episode>/EN/.autoedit/_work` or `<episode>/.autoedit/_work`); if not, build it
   first (`edit-episode.md`).
2. `./autoedit lang "<episode>" ES` (or `PT`), in the background. Output `<episode>/<LANG>/<name LANG>.xml`.
3. `./autoedit check` the XML. Report its length and the warnings.

What it does (`engine/make-language.py`):

- Sections are put in the language's order: the numbers in the script's ES / PT headings. A quiz stays
  after its location.
- VO from `<episode>/<LANG>/AUDIO <LANG>` (files named "… (sửa câu cuối)" replace the plain one). Each
  section's files are cut at their longest silences into as many slices as the EN section has sentence
  slices; slice i replaces EN slice i and the shots / graphics under it are re-timed piecewise (the whole
  section is stretched when the language has more files than EN has slices). Footage is not re-matched to
  the translated text.
- Graphics per language (`channel.json` `languages.<LANG>`): logo, lower third (`plain`, `box` = Tripinsight ES
  orange, `frame` = Tripinsight PT green; `engine/render-lower-third-lang.py`), subscribe, ending; quiz
  re-rendered with the language's question; QR kept.
- Music: the EN songs in the same order, re-laid to the new length.

Tripinsight ES has no Subscribe on purpose: the editor adds SUB ES (a MOGRT) by hand in Premiere
(`subscribe_manual`, user-set 2026-10-22) — do not report it as missing.
