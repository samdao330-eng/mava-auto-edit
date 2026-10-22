# Premiere XML: import problems and rules already solved

Run `./autoedit check "<file.xml>"` first: it names the cause of most refusals.

| Symptom | Cause | Fix |
|---|---|---|
| Premiere refuses the whole file ("file cannot be imported") | two clips overlap on one track (e.g. a Subscribe running into the next lower third, 2026-10-22 Chaseland Australia) | `engine/export-premiere-xml.py` spreads overlapping graphics / sounds over extra tracks (`lanes()`); music ends at `frame(start + length)` so songs meet without a 1-frame overlap. Rebuild with the current engine. |
| Every stereo file lands on two mono tracks | plain FCP7 audio tracks | each audio track is two exploded xmeml tracks (`premiereTrackType="Stereo"`, L = channel 1, R = 2, clips linked in pairs), master clips carry both channels, `<layout>stereo</layout>` |
| Media offline / Link Media dialog | file moved, or SAM mounted under another name | `check` lists the missing paths; point Link Media at `VIDEO` |
| Logo too big | the PNG has a transparent margin | `make-logo-overlay.py` crops the opaque area first; `logo_box` = the visible area `[x, y, width, opacity]` |
| Ending cut off | last clip shorter than its line | timeline length = max(last shot, every overlay end) |

Other notes:

- Generated graphics are ProRes 4444 with alpha (`.mov`, rendered with PIL → ffmpeg) in `<out>/.autoedit`.
- Channel template assets (subscribe, ending, logo) are referenced in place on SAM: every machine has them.
- Embedded source timecode is added to clip starts in the Resolve FCPXML (only with `"export_resolve": true`).
- Resolve App Store build is sandboxed: add SAM in Settings → System → Media Storage. Its projects can be
  read with sqlite3 (`~/Library/Containers/com.blackmagic-design.DaVinciResolveLite/.../Project.db`,
  `Sm2TiItem`) to see manual edits.
