#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""cr_collect.py — 每日 code review 的「純 git 收集器」（AgentPacks / wiki pack）。

職責：列出指定範圍內「有意義程式變更」的日子與 commit，輸出 JSON 給 cr-daily skill 的 agent。
本腳本不做 code review、不寫報告、不抓 diff 內容（diff 由 agent 之後按需 git show）。

過濾規則讀 .agent/config.json：
    paths.code_roots   只收這些目錄下的檔（repo 相對；空 = 不限；全部不存在時警告並改為不限）
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
# 統計「副檔名不符 / 不在 code_roots」被濾掉的檔時，只計這些程式類副檔名（避免 .md / .json 灌水）
SOURCE_LIKE_EXTS = (".cs", ".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs", ".vue", ".svelte", ".py", ".go", ".rs",
                    ".java", ".kt", ".swift", ".c", ".cc", ".cpp", ".h", ".hpp", ".m", ".mm", ".lua", ".php",
                    ".rb", ".dart", ".gd")


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
    """讀 .agent/config.json 的 collect 區塊與 paths.code_roots；讀不到時用內建預設並警告。"""
    try:
        cfg = json.loads((Path(root) / ".agent" / "config.json").read_text(encoding="utf-8"))
        collect = cfg.get("collect", {})
        code_roots = (cfg.get("paths") or {}).get("code_roots") or []
    except (OSError, ValueError) as error:
        sys.stderr.write("[WARN] 讀取 .agent/config.json 失敗（%s），改用內建過濾規則\n" % error)
        collect, code_roots = {}, []
    exts = tuple(ext.lower() for ext in collect.get("code_exts") or DEFAULT_EXTS)
    excludes = tuple(part.lower().replace("\\", "/") for part in collect.get("excludes") or DEFAULT_EXCLUDES)
    return exts, excludes, collect.get("ref") or "HEAD", code_roots


def resolve_roots(code_roots, root, ref):
    """code_roots 正規化成小寫前綴（"services/"）；ref 中不存在的目錄警告並略過，全部不存在時回傳空（不限）。"""
    roots = []
    for raw in code_roots:
        rel = str(raw).replace("\\", "/").strip().strip("/")
        if rel in ("", "."):
            return ()  # 含 repo 根 = 不限目錄
        roots.append(rel)
    existing = []
    for rel in roots:
        if git(["ls-tree", "-d", "--name-only", ref, "--", rel], cwd=root).strip():
            existing.append(rel.lower() + "/")
        else:
            sys.stderr.write("[WARN] code_roots 的 %s 在 %s 中不存在，已略過（請到 launcher 重新安裝 wiki pack 偵測）\n" % (rel, ref))
    if roots and not existing:
        sys.stderr.write("[WARN] code_roots 全部不存在，本次改為不限目錄收集\n")
    return tuple(existing)


def make_filter(exts, excludes, roots):
    """建立 classify(path)：回傳 None（收）或濾掉原因 "excluded" / "outside_roots" / "ext"。"""
    def classify(path):
        norm = path.replace("\\", "/")
        low = ("/" + norm).lower()
        if any(part in low for part in excludes):
            return "excluded"
        if roots and not norm.lower().startswith(roots):
            return "outside_roots"
        if not low.endswith(exts):
            return "ext"
        return None
    return classify


def new_skip_stats():
    """被濾掉的檔案統計，讓 agent 察覺 config 漏收（例：只收 .py 但大量 .js 變更）。"""
    return {"by_ext": {}, "outside_roots": {}, "excluded": 0}


def record_skip(stats, reason, path):
    """依濾掉原因累計：by_ext 依副檔名、outside_roots 依頂層目錄；兩者只計程式類副檔名。"""
    norm = path.replace("\\", "/")
    if reason == "excluded":
        stats["excluded"] += 1
        return
    name = norm.rsplit("/", 1)[-1].lower()
    ext = "." + name.rsplit(".", 1)[-1] if "." in name else ""
    if ext not in SOURCE_LIKE_EXTS:
        return
    if reason == "ext":
        stats["by_ext"][ext] = stats["by_ext"].get(ext, 0) + 1
    else:
        top = norm.split("/", 1)[0] if "/" in norm else "(repo 根)"
        stats["outside_roots"][top] = stats["outside_roots"].get(top, 0) + 1


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


def changed_code_files(sha, root, classify, skipped):
    """取得單一 commit 的程式變更檔（已過濾；被濾掉的計入 skipped）。"""
    out = git(["diff-tree", "--root", "--no-commit-id", "-r", "-M", "--name-status", sha], cwd=root)
    files = []
    for line in out.splitlines():
        if not line.strip():
            continue
        cols = line.split("\t")
        status, path = cols[0], cols[-1]      # rename/copy 時最後一欄是新路徑
        reason = classify(path)
        if reason:
            record_skip(skipped, reason, path)
            continue
        files.append({"path": path, "status": status, "rename_only": status == "R100"})
    return files


def build_output(commits, root, ref, classify, roots):
    """把 commit 依日期分組，只保留有程式變更的日子；附上生效的 code_roots 與被濾掉的統計。"""
    head_sha = git(["rev-parse", ref], cwd=root).strip()
    head_date = git(["log", ref, "-1", "--date=format-local:%Y-%m-%d", "--pretty=%cd"], cwd=root).strip()

    by_date = {}
    skipped = new_skip_stats()
    for sha, date, subject in commits:
        files = changed_code_files(sha, root, classify, skipped)
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
    return {
        "days": days,
        "head_sha": head_sha,
        "head_date": head_date,
        "code_roots": [r.rstrip("/") for r in roots],
        "skipped": skipped,
    }


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
    exts, excludes, config_ref, code_roots = load_collect_config(root)
    ref = args.ref or config_ref
    roots = resolve_roots(code_roots, root, ref)
    classify = make_filter(exts, excludes, roots)

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

    output = build_output(commits, root, ref, classify, roots)
    sys.stdout.write(json.dumps(output, ensure_ascii=False, indent=2))
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
