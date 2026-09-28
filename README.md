# claude-editor 剪片環境

每次開新的 Claude Code 雲端 session，`.claude/settings.json` 的 SessionStart hook 會自動執行 `scripts/setup.sh`，把環境裝好。手動安裝：

```bash
./scripts/setup.sh
```

## 裝了什麼

| 工具 | 用途 |
| --- | --- |
| ffmpeg / ffprobe | 剪接、轉檔、合併、壓字幕、調速、裁切 |
| auto-editor | 自動剪掉靜音 / 停頓 |
| moviepy | 用 Python 寫剪輯流程（疊字、轉場、拼接） |
| pydub、sox | 音訊處理（音量、降噪、淡入淡出） |
| faster-whisper | 語音轉字幕（SRT） |
| opencc | 簡體字幕轉繁體 |
| ImageMagick | 圖片、縮圖、封面處理 |
| mediainfo | 查看影片資訊 |
| Noto CJK 字型 | 燒錄中文字幕 |

## 資料夾

- `input/`：放原始素材
- `output/`：成品輸出

影音檔已加入 `.gitignore`，不會被 commit。

## 已知限制

目前環境的網路政策擋掉 Hugging Face，faster-whisper 無法下載語音模型。要用自動字幕，需要在環境的網路設定中允許 `huggingface.co`（以及 `*.hf.co` / `cdn-lfs.huggingface.co`）。
