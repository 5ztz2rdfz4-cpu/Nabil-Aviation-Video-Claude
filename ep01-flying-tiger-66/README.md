# Nabil Aviation — Air Disaster Chronicles EP01: Flying Tiger Line Flight 66 (1989)

Vertical 1080×1920 TikTok cut, 30 fps, ~70 s, with Bahasa Melayu voice-over and burned-in subtitles.

## Output
- `output/NabilAviation_EP01_FlyingTiger66.mp4`: final video
- `output/voiceover_with_ambience.mp3`: narration plus a low ambient bed, for re-editing in CapCut etc.
- `output/subtitles_ms.srt` / `.ass`: Malay captions (SRT for upload as closed captions)

## Scene plan
| Time | Narration | Visual |
|---|---|---|
| 0:00 | Hook | Episode poster, slow push-in |
| 0:15 | The flight | 747F in flight (date, route), then on the ground (747-249F, N807FT) |
| 0:33 | Final approach | Subang terminal (RWY 33) → "2,400 FT" card → struck out, "400 FT" in red |
| 0:47 | Impact | Crash site, Puchong |
| 0:52 | Aftermath | Malay and English newspaper clippings, "4 NYAWA TERKORBAN" |
| 0:58 | Closing | Monochrome 747, then the Nabil Aviation end card |

## Rebuilding
Source images come from the Google Drive folder (not committed). Download them into `<work>/drive/` named `f_<driveFileId>`, then run:
```
pip install edge-tts pillow
python3 tools/tts.py ms-MY-OsmanNeural +8% -8Hz tools/tts_lines.txt <work>/vo
python3 tools/build.py <work> out.mp4
```
`tools/tts_lines.txt` spells numbers out for the TTS engine (e.g. "tujuh empat tujuh"). The subtitles show the original script with numerals.
