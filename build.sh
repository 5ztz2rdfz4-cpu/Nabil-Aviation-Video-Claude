#!/usr/bin/env bash
# Full pipeline: narration -> frames -> audio -> final mp4
set -e
cd "$(dirname "$0")"
python3 tools/narration.py          # needs edge-tts + access to speech.platform.bing.com
python3 comp/render.py              # 2D frames -> build/frames
python3 audio/mix.py                # score + SFX + VO -> build/mix.wav
mkdir -p output
ffmpeg -y -framerate 24 -i build/frames/%05d.jpg -i build/mix.wav \
  -c:v libx264 -preset slow -crf 21 -maxrate 6M -bufsize 12M -pix_fmt yuv420p -profile:v high -movflags +faststart \
  -af loudnorm=I=-14:TP=-1.5:LRA=11 -c:a aac -b:a 192k -ar 48000 -shortest \
  output/Tenerife_1977_NabilAviation_1080x1920.mp4
