# Nabil Aviation — Air Disaster Chronicles EP01: Flying Tiger Line Flight 66 (1989)

A TikTok video (9:16, 1080×1920, 24 fps, about 73 s) in Bahasa Melayu, drawn in the same flat 2D motion-graphics style as the Tenerife episode, with simple top-view aircraft icons.

## Scenes
| Narration | Visual |
|---|---|
| Hook: "Korang tahu tak… Malaysia" | Map zooms into Malaysia, pulse on Subang |
| "…jumbo jet Boeing 747" | Flying Tigers 747 icon flying through cloud streaks |
| "…menghampiri Lapangan Terbang Subang" | Approach view down a lit runway |
| "…tahun 1989" | Title: 1989 · FLYING TIGER LINE · FLIGHT 66 |
| Flight details | Info card: date, 747-249F, freighter, N807FT, 4 crew |
| Route | Animated map Singapura → Kuala Lumpur → Hong Kong |
| "…Runway 33" | Approach diagram: runway 33, NDB, hills at Puchong |
| Miscommunication | Radio excerpt: "descend two four zero zero" / "Okay, four zero zero" |
| 2,400 vs 400 | "TWO" heard as "TO": 2,400 FT struck out → 400 FT |
| Descent | Profile: aircraft descends past 2,400 ft into the hill at Puchong, then silence |
| Aftermath | Archival crash-site photo (06:36 am), then "4 NYAWA TERKORBAN" over the 1989 Malay newspaper |
| Closing | Dusk over hills: "SETIAP ARAHAN. SETIAP PERKATAAN." |
| End card | Nabil Aviation logo · "Learning from Aviation History." |

## Files
- `output/NabilAviation_EP01_FlyingTiger66.mp4`: final video
- `output/voiceover_with_music.mp3`, `output/subtitles_ms.srt`
- `comp/gfx.py` (shared 2D toolkit, plus the Flying Tigers livery), `comp/render.py` (scenes), `audio/mix.py` (score, SFX, VO), `tools/` (TTS + timeline)
- `assets/sea_map.json`: Natural Earth 1:110m country outlines (public domain, via the geopandas 0.14 dataset)
- `./build.sh` rebuilds everything
