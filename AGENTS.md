# MAVA AUTO EDIT

MAVA AUTO EDIT builds Premiere Pro timelines (xmeml `.xml`) for the travel channels (Earthcue, Docs Untold,
Tripinsight, Chaseland, World Unpaved, …) from an episode folder: script `.xlsx` + VO + footage. **All channels share one
edit style; only the assets differ** (`channels/<slug>/channel.json`). Python tools in `engine/` do the work;
the Markdown in `skills/` says how. Everything runs through `./autoedit` (it picks the channel from the
episode folder).

The user and the editors speak Vietnamese: answer in Vietnamese, short.

## First action

**Before your first reply, read the file in the first matching row.** This file is only a router.

| The user… | Read first |
|---|---|
| — and `~/.auto-edit-venv/bin/python` does not exist (machine not set up) | run `./autoedit setup`, then continue down this table |
| gives an episode folder and wants it built ("dựng tập này", `/edit`) | `skills/edit-episode.md` |
| wants the ES / PT version of an episode | `skills/language-version.md` |
| wants something changed in a built episode, or reports a wrong edit ("sửa", `/fix`, a screenshot) | `skills/fix-episode.md` |
| says Premiere will not import an XML, or media is offline | `skills/premiere-xml.md` |
| brings a channel that has no `channels/<slug>/` yet | `skills/new-channel.md` |
| wants the edit style changed (pauses, transitions, fonts, positions …) | `skills/house-style.md` — settled rules, confirm before changing |
| asks what this can do | `README.md` |

Before working on one channel, also read `channels/<slug>/NOTES.md` (what was measured for it, its quirks).

## Always

- One command: `./autoedit edit|lang|rebuild|check|final|preview|channel "<episode>"`. Never copy engine
  scripts into an episode or a per-channel folder: there is one engine for every channel.
- A channel difference goes in `channels/<slug>/channel.json` (+ its `NOTES.md`), not in an `if channel ==`
  in the engine. A new option in `channel.json` gets a default that keeps the other channels unchanged.
- Every XML handed to the user passes `./autoedit check "<file.xml>"` (parses, every file exists, no clips
  overlapping on a track — Premiere refuses the whole file otherwise).
- **Do not render video** (`final`, `preview`) unless the user asks for it. The user wants timelines.
- The house style in `skills/house-style.md` is settled by the user. Change it only when they ask, and then
  for every channel; note the date and "user-set" next to the rule.
- An engine change is checked with `make test` (builds the reference episodes of every channel) before it
  is committed.
- Append a `logchat.md` entry after each session (format in that file). Conventional commits, no AI
  references in messages; never commit `.env`, tokens or credentials. Ask before pushing.
- Asked your version: `MAVA AUTO EDIT v` + the `VERSION` file.
