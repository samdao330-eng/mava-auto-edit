# Fix a built episode (or the engine)

1. **Which episode**: the path in the request; otherwise the most recently built one (the newest
   `.autoedit/_work/edl.json` under `/Volumes/SAM/0-*/*/`) — say which one you are fixing.
   `./autoedit channel "<episode>"`, read `channels/<slug>/NOTES.md`.

2. **Understand before fixing**: match the screenshot / timecode against `.autoedit/_work/edl.json` and the
   XML to find the exact shot, overlay or VO line. If the editor changed the Premiere project, read it
   (gzip XML `.prproj`) to see what they did.

3. **Sort it**:
   - This episode only (one shot, one line, one place name …): fix the episode's data
     (`.autoedit/_work/script.json`, `episode.json`) and `./autoedit rebuild "<episode>"`.
   - The edit style or a graphic shared by a channel (durations, transitions, fonts, positions …): settled
     rules — confirm with the user in one sentence first. Style → `engine/` + `house-style.md`; one
     channel's look → `channels/<slug>/channel.json` + `NOTES.md`.
   - An engine bug (crash, wrong path, Premiere refusing the XML): fix it at the root in `engine/`, then
     `make test` (all channels) before committing.

4. **Rebuild**: `./autoedit rebuild "<episode>"` (ES / PT: `./autoedit rebuild "<episode>" ES`). Delete the
   generated graphic in `.autoedit/` first when its look changed so it is made again.
   `./autoedit check` the XML and confirm the requested change is in it. **No render** unless asked.

5. **Report**: what changed, which files, how it was checked, what is left. Append to `logchat.md`.
