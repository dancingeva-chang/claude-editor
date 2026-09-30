#!/usr/bin/env python3
"""剪片自動化流程：把 input/ 的素材一次處理成可發佈的成品。

每支影片的流程（每一步的產物都會保留，重跑時已完成的步驟會跳過）：
  1. cut       auto-editor 剪掉靜音 / 停頓            -> 01_cut.mp4
  2. loudnorm  ffmpeg 音量標準化（-16 LUFS）          -> 02_norm.mp4
  3. subs      faster-whisper 語音轉字幕 + 轉繁體     -> subtitles.srt
  4. burn      把字幕燒進畫面                          -> final.mp4
  5. cover     挑一張代表畫面當封面                    -> cover.jpg
最後輸出 output/<影片名>/report.json 與 output/REPORT.md 總表。

字幕模型下載失敗（例如網路擋 Hugging Face）時，會跳過 3、4 步，
final.mp4 改用沒有字幕的版本，流程不會中斷。

用法：
  python3 scripts/pipeline.py                 # 處理 input/ 全部影片
  python3 scripts/pipeline.py --no-subs       # 不做字幕
  python3 scripts/pipeline.py --force         # 全部重做
  python3 scripts/pipeline.py input/a.mp4     # 只處理指定檔案
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
VIDEO_EXTS = {".mp4", ".mov", ".mkv", ".m4v", ".webm"}
SUB_STYLE = (
    "FontName=Noto Sans CJK TC,FontSize=18,PrimaryColour=&H00FFFFFF,"
    "OutlineColour=&H00000000,BorderStyle=1,Outline=2,Shadow=0,MarginV=30"
)


def log(msg: str) -> None:
    print(f"[pipeline] {msg}", flush=True)


def run(cmd: list[str]) -> None:
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)


def duration(path: Path) -> float:
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=nw=1:nk=1", str(path)],
        check=True, capture_output=True, text=True,
    ).stdout.strip()
    return round(float(out), 2)


def step_cut(src: Path, dst: Path, margin: str) -> None:
    run(["auto-editor", str(src), "--margin", margin, "--no-open", "-q", "-o", str(dst)])


def step_loudnorm(src: Path, dst: Path) -> None:
    run(["ffmpeg", "-y", "-i", str(src), "-c:v", "copy",
         "-af", "loudnorm=I=-16:TP=-1.5:LRA=11", "-c:a", "aac", "-b:a", "192k", str(dst)])


def fmt_ts(t: float) -> str:
    ms = int(round(t * 1000))
    h, ms = divmod(ms, 3_600_000)
    m, ms = divmod(ms, 60_000)
    s, ms = divmod(ms, 1000)
    return f"{h:02}:{m:02}:{s:02},{ms:03}"


def step_subs(src: Path, dst: Path, model_name: str, lang: str | None) -> None:
    from faster_whisper import WhisperModel
    import opencc

    model = WhisperModel(model_name, device="cpu", compute_type="int8")
    segments, _ = model.transcribe(str(src), language=lang, vad_filter=True)
    to_tw = opencc.OpenCC("s2twp")
    lines = []
    for i, seg in enumerate(segments, 1):
        text = to_tw.convert(seg.text.strip())
        lines.append(f"{i}\n{fmt_ts(seg.start)} --> {fmt_ts(seg.end)}\n{text}\n")
    dst.write_text("\n".join(lines), encoding="utf-8")


def step_burn(src: Path, srt: Path, dst: Path) -> None:
    # subtitles filter 的路徑需要跳脫 : 和 '，直接用相對檔名最省事
    subprocess.run(
        ["ffmpeg", "-y", "-i", str(src),
         "-vf", f"subtitles={srt.name}:force_style='{SUB_STYLE}'",
         "-c:a", "copy", dst.name],
        check=True, cwd=dst.parent, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE,
    )


def step_cover(src: Path, dst: Path) -> None:
    run(["ffmpeg", "-y", "-i", str(src), "-vf", "thumbnail=150,scale=1280:-2",
         "-frames:v", "1", str(dst)])


def process(src: Path, out_root: Path, args: argparse.Namespace) -> dict:
    work = out_root / src.stem
    work.mkdir(parents=True, exist_ok=True)
    cut, norm, srt = work / "01_cut.mp4", work / "02_norm.mp4", work / "subtitles.srt"
    final, cover = work / "final.mp4", work / "cover.jpg"
    report = {"source": src.name, "steps": {}, "warnings": []}
    started = time.time()

    def do(name: str, target: Path, fn, *fn_args) -> bool:
        if target.exists() and not args.force:
            report["steps"][name] = "skipped (already done)"
            return True
        log(f"{src.name}: {name}")
        try:
            fn(*fn_args)
        except Exception as e:  # 單一步驟失敗不影響其他影片
            err = e.stderr.decode(errors="ignore")[-400:] if isinstance(e, subprocess.CalledProcessError) and e.stderr else str(e)
            report["steps"][name] = "failed"
            report["warnings"].append(f"{name}: {err.strip()}")
            target.unlink(missing_ok=True)
            return False
        report["steps"][name] = "done"
        return True

    stage = src
    if not args.no_cut and do("cut", cut, step_cut, src, cut, args.margin):
        stage = cut
    if do("loudnorm", norm, step_loudnorm, stage, norm):
        stage = norm

    subbed = False
    if not args.no_subs and do("subs", srt, step_subs, stage, srt, args.model, args.lang):
        subbed = do("burn", final, step_burn, stage, srt, final)
    if not subbed:
        if args.force or not final.exists():
            shutil.copyfile(stage, final)
        report["steps"].setdefault("burn", "skipped (no subtitles)")

    do("cover", cover, step_cover, final, cover)

    report["duration_in"] = duration(src)
    report["duration_out"] = duration(final)
    report["saved_seconds"] = round(report["duration_in"] - report["duration_out"], 2)
    report["elapsed_seconds"] = round(time.time() - started, 1)
    (work / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report


def write_summary(reports: list[dict], out_root: Path) -> Path:
    rows = ["| 影片 | 原長 (s) | 成品 (s) | 剪掉 (s) | 字幕 | 警告 |", "| --- | --- | --- | --- | --- | --- |"]
    for r in reports:
        subs = "有" if r["steps"].get("burn") in ("done", "skipped (already done)") else "無"
        rows.append(f"| {r['source']} | {r['duration_in']} | {r['duration_out']} | "
                    f"{r['saved_seconds']} | {subs} | {len(r['warnings'])} |")
    path = out_root / "REPORT.md"
    path.write_text(f"# 剪片報告 {time.strftime('%Y-%m-%d %H:%M')}\n\n" + "\n".join(rows) + "\n", encoding="utf-8")
    return path


def main() -> int:
    p = argparse.ArgumentParser(description="input/ -> output/ 剪片自動化")
    p.add_argument("files", nargs="*", type=Path, help="指定影片；不給就處理 input/ 全部")
    p.add_argument("--output", type=Path, default=ROOT / "output")
    p.add_argument("--margin", default="0.3s", help="保留在說話段落前後的緩衝")
    p.add_argument("--model", default="small", help="faster-whisper 模型大小")
    p.add_argument("--lang", default="zh", help="語言代碼；給空字串自動偵測")
    p.add_argument("--no-cut", action="store_true", help="不剪靜音")
    p.add_argument("--no-subs", action="store_true", help="不做字幕")
    p.add_argument("--force", action="store_true", help="忽略已完成的步驟，全部重做")
    args = p.parse_args()
    args.lang = args.lang or None

    files = args.files or sorted(f for f in (ROOT / "input").iterdir() if f.suffix.lower() in VIDEO_EXTS)
    if not files:
        log("input/ 裡沒有影片")
        return 0

    reports = [process(f.resolve(), args.output, args) for f in files]
    summary = write_summary(reports, args.output)
    for r in reports:
        for w in r["warnings"]:
            log(f"警告 {r['source']} {w.splitlines()[-1] if w else ''}")
    log(f"完成 {len(reports)} 支，報告：{summary}")
    return 1 if any(r["steps"].get(s) == "failed" for r in reports for s in ("cut", "loudnorm", "cover")) else 0


if __name__ == "__main__":
    sys.exit(main())
