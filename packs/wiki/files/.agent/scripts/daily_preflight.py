#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""daily_preflight.py — 每日 codereview 前置規劃器（確定性、無 LLM；AgentPacks / wiki pack）。

職責（只規劃、不 review、不寫 wiki）：
  1. git fetch（非破壞）→ 判斷本地是否落後遠端 ref。
  2. 決定 review 窗口：[上次 review 隔天 .. 昨天]，**排除今天**（今天 commit 未完）。
  3. 對 ref 跑 cr_collect 收集。
  4. 輸出 digest：落後狀態、窗口、有程式變更的日子、建議執行的 /cr-daily 指令；
     同時寫一份到 <paths.outputs>/curate-preflight-YYYY-MM-DD.md。

路徑與預設 ref 讀 .agent/config.json（paths.*、collect.ref），皆為 repo 相對路徑。
排程：交本機 Windows 工作排程器跑 daily_preflight.bat（雲端排程碰不到本地 git）。

用法（於 repo 根執行）：
    python .agent/scripts/daily_preflight.py                # ref 讀 config collect.ref
    python .agent/scripts/daily_preflight.py --ref HEAD --no-fetch
    python .agent/scripts/daily_preflight.py --json         # 機器可讀
"""
import argparse
import datetime as _dt
import json
import re
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
CANONICAL_COLLECTOR = ".agent/capabilities/skills/cr-daily/cr_collect.py"


def load_config() -> dict:
    """讀 .agent/config.json；失敗直接結束（沒有 config 無法規劃）。"""
    try:
        return json.loads((REPO_ROOT / ".agent" / "config.json").read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        sys.stderr.write("[ERR] 讀取 .agent/config.json 失敗：%s\n" % error)
        sys.exit(2)


def git(args, timeout=None) -> tuple:
    """執行 git，回傳 (returncode, stdout, stderr)。"""
    try:
        res = subprocess.run(["git"] + args, cwd=REPO_ROOT, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                             encoding="utf-8", errors="replace", timeout=timeout)
    except subprocess.TimeoutExpired:
        return 124, "", "timeout"
    except OSError as error:
        return 127, "", str(error)
    return res.returncode, res.stdout.strip(), res.stderr.strip()


def last_reviewed_date(paths: dict) -> tuple:
    """上次 review 到哪天：優先讀 cursor 的 last_date，否則掃 codereview 產出取最新日期。"""
    cursor = paths.get("cursor")
    if cursor and (REPO_ROOT / cursor).exists():
        try:
            data = json.loads((REPO_ROOT / cursor).read_text(encoding="utf-8"))
            date = data.get("last_date") or data.get("date")
            if date:
                return date, "cursor"
        except (OSError, ValueError):
            pass
    dates = []
    for key in ("codereview_out", "codereview_src"):
        folder = paths.get(key)
        if folder and (REPO_ROOT / folder).is_dir():
            for note in (REPO_ROOT / folder).glob("20??-??-??.md"):
                if re.match(r"\d{4}-\d{2}-\d{2}$", note.stem):
                    dates.append(note.stem)
    if dates:
        return max(dates), "scan"
    return None, "none"


def collect(paths: dict, ref: str, rng) -> tuple:
    """呼叫 cr_collect.py，回傳 (成功與否, JSON 或錯誤行)。"""
    collector = paths.get("collector") or CANONICAL_COLLECTOR
    if not (REPO_ROOT / collector).is_file() and (REPO_ROOT / CANONICAL_COLLECTOR).is_file():
        # 舊版 config 指向 .claude/skills/cr-daily/（wiki v1），已遷移到 canonical 位置
        collector = CANONICAL_COLLECTOR
    cmd = [sys.executable, str(REPO_ROOT / collector), "--ref", ref]
    cmd += ["--range", rng] if rng else ["--head-only"]
    try:
        res = subprocess.run(cmd, cwd=REPO_ROOT, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                             encoding="utf-8", errors="replace")
    except OSError as error:
        return False, [str(error)]
    if res.returncode != 0:
        return False, (res.stderr or "").splitlines()[:3]
    try:
        return True, json.loads(res.stdout)
    except ValueError as error:
        return False, ["collector 輸出非 JSON：%s" % error]


def render_digest(report: dict) -> str:
    """把報告轉成人類可讀的 markdown digest。"""
    lines = ["# /curate 每日前置 digest — %s" % report["today"], ""]
    lines.append("- review 對象 ref：`%s`（fetch：%s）" % (report["ref"], report["fetch"]))
    behind = report["behind"]
    lines.append("- 本地 HEAD 落後 ref：%s commit" % (behind if behind is not None else "?") +
                 ("（建議自動化對 ref 收集，免 pull）" if behind else "（已最新）"))
    last = report["last_reviewed"]
    lines.append("- 上次 review 到：%s（來源：%s）" % (last["date"] or "（無紀錄）", last["source"]))
    window = report["window"]
    lines.append("- 本次窗口：%s .. %s　**排除今天 %s**" % (window["start"] or "(head-only)", window["end"], report["today"]))
    status = report.get("status")
    if status == "up-to-date":
        lines.append("- 結論：✅ 已 review 到昨天，無待處理。")
    elif status == "no-code-changes":
        lines.append("- 結論：窗口內無有意義程式變更，無待處理。")
    elif status == "has-work":
        lines.append("- 待 review 的日子：")
        for day in report["days"]:
            lines.append("    - %s（%d commits）" % (day["date"], day["commits"]))
        lines.append("- 建議執行：`%s`" % report["recommend"])
    else:
        lines.append("- ⚠️ 收集失敗：%s" % report.get("error"))
    return "\n".join(lines) + "\n"


def main() -> int:
    cfg = load_config()
    paths = cfg.get("paths", {})
    default_ref = cfg.get("collect", {}).get("ref") or "HEAD"

    ap = argparse.ArgumentParser(description="每日 codereview 前置規劃器")
    ap.add_argument("--ref", default=default_ref, help="review 對象（預設 config collect.ref = %s）" % default_ref)
    ap.add_argument("--no-fetch", action="store_true", help="略過 git fetch")
    ap.add_argument("--json", action="store_true", help="輸出 JSON")
    args = ap.parse_args()

    ref = args.ref
    remote = ref.split("/", 1)[0] if "/" in ref else "origin"
    today = _dt.date.today()
    yesterday = today - _dt.timedelta(days=1)
    report = {"ref": ref, "today": today.isoformat(), "days": [], "recommend": None}

    if args.no_fetch or ref == "HEAD":
        report["fetch"] = "skipped"
    else:
        code, _, err = git(["fetch", remote], timeout=120)
        report["fetch"] = "ok" if code == 0 else "fail: " + (err.splitlines()[0] if err else "?")

    code, out, _ = git(["rev-list", "--count", "HEAD..%s" % ref])
    report["behind"] = int(out) if code == 0 and out.isdigit() else None

    last, source = last_reviewed_date(paths)
    report["last_reviewed"] = {"date": last, "source": source}
    start = (_dt.date.fromisoformat(last) + _dt.timedelta(days=1)).isoformat() if last else None
    end = yesterday.isoformat()
    report["window"] = {"start": start, "end": end}

    if start and start > end:
        report["status"] = "up-to-date"
    else:
        rng = "%s..%s" % (start, end) if start else None
        ok, data = collect(paths, ref, rng)
        if ok:
            report["days"] = [{"date": day["date"], "commits": day["commit_count"]}
                              for day in data["days"] if day["date"] <= end]
            report["status"] = "has-work" if report["days"] else "no-code-changes"
        else:
            report["status"] = "collect-fail"
            report["error"] = data

    if report["status"] == "has-work":
        target = "%s..%s" % (start, end) if start else end
        report["recommend"] = "/cr-daily %s   （ref=%s；產出後再 /curate codereview）" % (target, ref)

    if args.json:
        sys.stdout.write(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
        return 0

    digest = render_digest(report)
    sys.stdout.write(digest)
    try:
        outdir = REPO_ROOT / (paths.get("outputs") or "outputs")
        outdir.mkdir(parents=True, exist_ok=True)
        (outdir / ("curate-preflight-%s.md" % today.isoformat())).write_text(digest, encoding="utf-8")
    except OSError as error:
        sys.stderr.write("[WARN] 無法寫入 digest：%s\n" % error)
    return 0


if __name__ == "__main__":
    sys.exit(main())
