---
description: 把 input/ 的影片跑完剪片流水線，並摘要結果
argument-hint: "[pipeline.py 選項，例如 --no-subs 或指定檔案]"
---

執行剪片流水線：

```bash
python3 scripts/pipeline.py $ARGUMENTS
```

跑完後讀 `output/REPORT.md` 與各影片的 `output/<片名>/report.json`，用繁體中文回報：

- 每支影片原長、成品長度、剪掉幾秒、有沒有字幕
- 所有警告，以及建議的處理方式（例如字幕失敗多半是網路擋 Hugging Face，見 README 的已知限制）
- 需要我人工檢查的地方（例如剪掉比例超過 40% 的影片，可能剪過頭）
