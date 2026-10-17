#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""cr_collect.py — 每日 code review 的「純 git 收集器」（AgentPacks / wiki pack）。

職責：列出指定範圍內「有意義程式變更」的日子與 commit，輸出 JSON 給 cr-daily skill 的 agent。
本腳本不做 code review、不寫報告、不抓 diff 內容（diff 由 agent 之後按需 git show）。

過濾規則讀 .agent/config.json：
    collect.code_exts  要收的副檔名（例 [".cs", ".ts"]）
    collect.excludes   路徑片段（不分大小寫、正斜線；以 / 開頭代表從 repo 根比對）
    collect.ref        預設 git 參照（未給 --ref 時使用；缺省 HEAD）

用法（四選一）：
    python cr_collect.py --since-commit <sha>            # 游標模式：<sha>..ref
    python cr_collect.py --date 2026-03-15               # 單日
    python cr_collect.py --range 2026-03-01..2026-05-31  # 區間
    python cr_collect.py --head-only                     # 無游標首跑：只取最新一天

輸出（stdout, JSON）：見檔末 build_output 的結構。
"""

import argparse
import json
import subprocess
import sys
from pathlib import Path

DEFAULT_EXTS = (".cs", ".ts", ".tsx", ".js", ".mjs", ".py")
DEFAULT_EXCLUDES = ("/node_modules/", "/dist/", "/build/", "/plugins/", "/thirdparty/")


def git(args, cwd):
    """執行 git，回傳 stdout 字串（utf-8，壞字元以 replace 處理）。"""
    try:
        res = subprocess.run(
            ["git"] + args,
            cwd=cwd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            encoding="utf-8",
            errors="replace",
        )
    except OSError as error:
        sys.stderr.write("無法執行 git：%s\n" % error)
        sys.exit(2)
    if res.returncode != 0:
        sys.stderr.write("git %s 失敗：\n%s\n" % (" ".join(args), res.stderr))
        sys.exit(2)
    return res.stdout


def repo_root():
    """取得目前 repo 根目錄。"""
    return git(["rev-parse", "--show-toplevel"], cwd=".").strip()


def load_collect_config(root):
    """讀 .agent/config.json 的 collect 區塊；讀不到時用內建預設並警告。"""
    try:
        cfg = json.loads((Path(root) / ".agent" / "config.json").read_text(encoding="utf-8"))
        collect = cfg.get("collect", {})
    except (OSError, ValueError) as error:
        sys.stderr.write("[WARN] 讀取 .agent/config.json 失敗（%s），改用內建過濾規則\n" % error)
        collect = {}
    exts = tuple(ext.lower() for ext in collect.get("code_exts") or DEFAULT_EXTS)
    excludes = tuple(part.lower().replace("\\", "/") for part in collect.get("excludes") or DEFAULT_EXCLUDES)
    return exts, excludes, collect.get("ref") or "HEAD"


def make_filter(exts, excludes):
    """依副檔名與排除片段建立 is_excluded(path) 判斷函數。"""
    def is_excluded(path):
        low = ("/" + path.replace("\\", "/")).lower()
        if not low.endswith(exts):
            return True
        return any(part in low for part in excludes)
    return is_excluded


# ── 取得範圍內 commit（newest-first）：[(sha, date, subject), ...] ─────────
def list_commits(mode, value, root, ref):
    """ref：要 review 的 git 參照（自動化時可傳 origin/main，不依賴本地工作區）。"""
    pretty = "--pretty=%H%x09%cd%x09%s"
    datefmt = "--date=format-local:%Y-%m-%d"
    base = ["log", ref, "--no-merges", datefmt, pretty]

    if mode == "since-commit":
        out = git(["log", "--no-merges", datefmt, pretty, "%s..%s" % (value, ref)], cwd=root)
    elif mode == "date":
        out = git(base + ["--after=%s 00:00:00" % value, "--before=%s 23:59:59" % value], cwd=root)
    elif mode == "range":
        start, end = value
        out = git(base + ["--after=%s 00:00:00" % start, "--before=%s 23:59:59" % end], cwd=root)
    elif mode == "head-only":
        head_date = git(["log", ref, "-1", datefmt, "--pretty=%cd"], cwd=root).strip()
        out = git(base + ["--after=%s 00:00:00" % head_date, "--before=%s 23:59:59" % head_date], cwd=root)
    else:
        raise ValueError(mode)

    commits = []
    for line in out.splitlines():
        if not line.strip():
            continue
        parts = line.split("\t", 2)
        parts += [""] * (3 - len(parts))
        commits.append((parts[0], parts[1], parts[2]))
    return commits


def changed_code_files(sha, root, is_excluded):
    """取得單一 commit 的程式變更檔（已過濾排除）。"""
    out = git(["diff-tree", "--root", "--no-commit-id", "-r", "-M", "--name-status", sha], cwd=root)
    files = []
    for line in out.splitlines():
        if not line.strip():
            continue
        cols = line.split("\t")
        status, path = cols[0], cols[-1]      # rename/copy 時最後一欄是新路徑
        if is_excluded(path):
            continue
        files.append({"path": path, "status": status, "rename_only": status == "R100"})
    return files


def build_output(commits, root, ref, is_excluded):
    """把 commit 依日期分組，只保留有程式變更的日子。"""
    head_sha = git(["rev-parse", ref], cwd=root).strip()
    head_date = git(["log", ref, "-1", "--date=format-local:%Y-%m-%d", "--pretty=%cd"], cwd=root).strip()

    by_date = {}
    for sha, date, subject in commits:
        files = changed_code_files(sha, root, is_excluded)
        if not files:
            continue
        by_date.setdefault(date, []).append({"sha": sha, "subject": subject, "files": files})

    days = []
    for date in sorted(by_date.keys()):              # 日期由舊到新
        day_commits = list(reversed(by_date[date]))   # 該日內由舊到新
        oldest, newest = day_commits[0]["sha"], day_commits[-1]["sha"]
        days.append({
            "date": date,
            "commit_range": "%s..%s" % (oldest, newest) if oldest != newest else oldest,
            "commit_count": len(day_commits),
            "commits": day_commits,
        })
    return {"days": days, "head_sha": head_sha, "head_date": head_date}


def parse_args():
    """解析命令列參數。"""
    ap = argparse.ArgumentParser(description="code review 純 git 收集器")
    group = ap.add_mutually_exclusive_group(required=True)
    group.add_argument("--since-commit", metavar="SHA")
    group.add_argument("--date", metavar="YYYY-MM-DD")
    group.add_argument("--range", metavar="A..B")
    group.add_argument("--head-only", action="store_true")
    ap.add_argument("--ref", default=None, help="要 review 的 git 參照（預設讀 config collect.ref，再缺省 HEAD）")
    return ap.parse_args()


def main():
    args = parse_args()
    root = repo_root()
    exts, excludes, config_ref = load_collect_config(root)
    is_excluded = make_filter(exts, excludes)
    ref = args.ref or config_ref

    if args.since_commit:
        commits = list_commits("since-commit", args.since_commit, root, ref)
    elif args.date:
        commits = list_commits("date", args.date, root, ref)
    elif args.range:
        if ".." not in args.range:
            sys.stderr.write("--range 格式需為 A..B\n")
            sys.exit(2)
        start, end = args.range.split("..", 1)
        commits = list_commits("range", (start.strip(), end.strip()), root, ref)
    else:
        commits = list_commits("head-only", None, root, ref)

    output = build_output(commits, root, ref, is_excluded)
    sys.stdout.write(json.dumps(output, ensure_ascii=False, indent=2))
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
