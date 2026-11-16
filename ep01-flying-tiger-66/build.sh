#!/usr/bin/env bash
# Full pipeline: narration -> timeline -> 2D frames -> audio mix -> final mp4
set -e
cd "$(dirname "$0")"
mkdir -p build/vo output
python3 tools/tts.py ms-MY-OsmanNeural +8% -8Hz tools/tts_lines.txt build/vo   # needs edge-tts + speech.platform.bing.com
python3 tools/timeline.py
python3 comp/render.py
python3 audio/mix.py
ffmpeg -y -framerate 24 -i build/frames/%05d.jpg -i build/mix.wav \
  -c:v libx264 -preset slow -crf 21 -maxrate 6M -bufsize 12M -pix_fmt yuv420p -profile:v high -movflags +faststart \
  -af loudnorm=I=-14:TP=-1.5:LRA=11 -c:a aac -b:a 192k -ar 48000 -shortest \
  output/NabilAviation_EP01_FlyingTiger66.mp4
