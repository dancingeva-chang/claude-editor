#!/usr/bin/env bash
# 安裝剪片環境：ffmpeg、音訊/圖片工具、中文字型，以及 Python 剪輯套件。
# 可重複執行；已安裝的東西會直接略過。
set -euo pipefail

cd "$(dirname "$0")/.."

APT_PKGS=(ffmpeg sox imagemagick mediainfo fonts-noto-cjk)
missing=()
for p in "${APT_PKGS[@]}"; do
  dpkg -s "$p" >/dev/null 2>&1 || missing+=("$p")
done
if [ ${#missing[@]} -gt 0 ]; then
  echo "[setup] apt install: ${missing[*]}"
  apt-get update -qq || true
  DEBIAN_FRONTEND=noninteractive apt-get install -y -qq "${missing[@]}"
fi

if ! python3 -c "import moviepy, pydub, faster_whisper, opencc" >/dev/null 2>&1 \
   || ! command -v auto-editor >/dev/null 2>&1; then
  echo "[setup] pip install -r requirements.txt"
  pip install -q -r requirements.txt
fi

mkdir -p input output
echo "[setup] ready: $(ffmpeg -version | head -1)"
