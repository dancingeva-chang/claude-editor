# 個人 × 工作 自動化工作流設計

目標：把「重複、有固定步驟」的事交給機器，人只負責**決策**與**創作**。

## 設計原則

1. **一個收件匣，一條流水線**：所有東西先進固定入口（`input/`、信箱標籤、待辦清單），再由固定流程處理，不靠記憶。
2. **每個流程都有報告**：跑完一定留下可以快速掃過的摘要（`REPORT.md`、晨報、週報），人只看摘要做決定。
3. **可重跑、可中斷**：步驟產物保留，重跑自動跳過已完成的部分；單一步驟失敗不拖垮整批。
4. **先半自動，再全自動**：新流程先用 slash command 手動觸發，穩定兩週後再改成排程（Routine）。
5. **工作與個人分道**：分開的 Routine、分開的輸出，避免互相干擾；共用同一套回顧節奏。

## 整體架構

```
            ┌──────────── 觸發 ────────────┐
            │ 排程 Routine │ Slash 指令 │ 放檔案 │
            └──────┬───────────────────────┘
                   ▼
  收集 ──► 處理 ──────────► 產出 ──────────► 回顧
  input/     scripts/pipeline.py   output/<片名>/   output/REPORT.md
  Gmail      Claude + 連接器       晨報 / 週報       每週回顧（人做決策）
  行事曆                           待辦草稿
```

## 工作流清單

| # | 工作流 | 分類 | 觸發 | 由誰執行 | 產出 | 狀態 |
| --- | --- | --- | --- | --- | --- | --- |
| W1 | 剪片流水線 | 工作 | 素材放進 `input/` 後執行 `/process-footage` | `scripts/pipeline.py` | 成品影片、字幕、封面、報告 | ✅ 已實作 |
| W2 | 工作晨報 | 工作 | 平日 08:50 Routine | Claude + Gmail / 行事曆連接器 | 今日會議、待回信件、三件要事 | 📝 提示詞已備，需接連接器 |
| W3 | 會議後整理 | 工作 | 會議錄音放進 `input/` | pipeline（字幕）+ Claude | 會議紀錄、行動項目 | 📝 提示詞已備，需開通字幕模型 |
| W4 | 每週成果週報 | 工作 | 週五 17:00 Routine | Claude + git 紀錄 + `REPORT.md` | 本週產出、下週計畫 | 📝 提示詞已備 |
| P1 | 個人晨間簡報 | 個人 | 每日 07:30 Routine | Claude + 行事曆 | 天氣、行程、習慣打卡提醒 | 📝 提示詞已備，需接連接器 |
| P2 | 月度財務 / 訂閱檢查 | 個人 | 每月 1 日 Routine | Claude + Gmail（帳單信） | 本月帳單、即將續約的訂閱 | 📝 提示詞已備，需接連接器 |
| P3 | 每週回顧 | 個人 + 工作 | 週日 20:00，或 `/weekly-review` | Claude | 本週回顧、下週三大目標 | ✅ 可手動執行 |

提示詞都放在 [`workflows/routines/`](../workflows/routines/)，每個檔案開頭寫了建議的排程與需要的連接器。

## W1 剪片流水線（已實作）

```bash
# 1. 素材放進 input/
# 2. 執行（或在 Claude Code 輸入 /process-footage）
python3 scripts/pipeline.py
```

| 步驟 | 工具 | 產物 |
| --- | --- | --- |
| 剪靜音 | auto-editor（前後保留 0.3 秒） | `01_cut.mp4` |
| 音量標準化 | ffmpeg loudnorm（-16 LUFS，適合 YouTube / 社群平台） | `02_norm.mp4` |
| 語音轉字幕 | faster-whisper + OpenCC 轉台灣繁體 | `subtitles.srt` |
| 燒字幕 | ffmpeg + Noto Sans CJK TC | `final.mp4` |
| 封面 | ffmpeg thumbnail 挑代表畫面 | `cover.jpg` |
| 報告 | — | `report.json`、`output/REPORT.md` |

常用選項：`--no-subs`（不做字幕）、`--no-cut`（不剪靜音）、`--margin 0.5s`、`--model medium`、`--force`（全部重做）。

字幕需要下載 whisper 模型；目前網路政策擋掉 Hugging Face，所以字幕步驟會記一筆警告後跳過，`final.mp4` 改用無字幕版本。開通 `huggingface.co` 後不必改任何程式。

## 導入步驟

1. **第 1 週**：只用 W1 和 `/weekly-review`，確認流程順手。
2. **第 2 週**：到 claude.ai 的 Settings → Connectors 接上 Gmail、Google Calendar，先手動貼 `workflows/routines/` 的提示詞跑幾次 W2、P1。
3. **第 3 週**：把穩定的提示詞設成 Routine（排程）。在 Claude Code 裡可以直接說「把 `workflows/routines/work-morning-brief.md` 設成平日 08:50 的 Routine」。
4. **之後每月**：週回顧時問自己「這個月哪件事做了三次以上？」，把它寫成新的提示詞或腳本，加進上面的表格。

## 安全界線

- Routine 只**讀取**與**起草**：回信、付款、刪除等對外動作一律只產生草稿，由人確認後才送出。
- 素材、成品與個人資料不進 git（`.gitignore` 已排除影音檔與 `input/`、`output/`）。
