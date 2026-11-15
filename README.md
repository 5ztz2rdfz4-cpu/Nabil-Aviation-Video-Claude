# Nabil Aviation – The Tenerife Airport Disaster (1977)

A TikTok documentary video (9:16, 1080×1920, 24 fps, about 3.5 min) in Bahasa Melayu,
made in a flat 2D motion-graphics style.

* `tools/narration.py` – the Malay voice-over (edge-tts `ms-MY-OsmanNeural`) plus timing
* `comp/gfx.py`, `comp/render.py` – the 2D scenes (icons, airport diagram, map, transcript cards, archival plates, fog, grain, subtitles)
* `audio/mix.py` – the synthesised score, ambience, radio static, the dramatic silence and the VO mix
* `assets/` – logo, archival photos (from the provided Drive folder), fonts, Canary Islands map data (Natural Earth via world-atlas)
* `build.sh` – full pipeline → `output/Tenerife_1977_NabilAviation_1080x1920.mp4`

Labels on screen tell the material apart: **FOTO ARKIB** (real 1977 photos), **ILUSTRASI** (2D recreation),
**TRANSKRIP RASMI** (quotes from the official CVR/ATC transcript; no voice recreation of the crews).
