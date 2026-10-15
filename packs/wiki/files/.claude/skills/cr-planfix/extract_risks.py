#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
extract_risks.py — 從 <paths.docs_codereview>/YYYY-MM-DD.md（預設 aispec/codereview） 抽出「🐛 潛在 bug / 風險」條目，
依系統模塊分類，輸出到 aispec/codereview/planfix/。

用法:
    python extract_risks.py [--src DIR] [--out DIR] [--date 2026-05-14|2026-05-01..2026-05-31]

判定流程（每個 ### 區段一條）:
    1. 抓 ### 標題、`- 檔案：` 路徑、`- 🐛 ...風險：` 內文（含續行）
    2. 風險內文為「無」者略過
    3. 模塊分類優先序：檔案路徑關鍵字 > 標題 [標籤] > 標題關鍵字 > 其他
輸出: 每模塊一個 .md + README.md 索引（依日期新到舊、嚴重度排序）
"""
import argparse
import json
import re
import sys
from collections import defaultdict, OrderedDict
from pathlib import Path

# ── 模塊定義：(模塊名, 檔名 slug, [檔案路徑關鍵字], [標題/標籤關鍵字]) ──
# 路徑關鍵字比對 file 路徑（不分大小寫）；標題關鍵字比對標題+標籤文字。
# 順序即優先序，越前越優先命中。
#
# 權威來源是本 repo .agent/spec/modules.json（單一詞表，與 git 模組 tag /
# curate features 同源）。執行時由 _load_module_vocab() 從 config.paths.modules_spec
# 載入；config 缺漏時不分類，全部歸入「其他」。要新增/調整模組，請改 modules.json。
_FALLBACK_MODULES = []
_FALLBACK_OTHER = ("其他 / 系統", "misc")


def _load_module_vocab():
    """從本 repo .agent/spec/modules.json 載入模組詞表（單一權威來源）。

    定位：讀 .agent/config.json 的 paths.modules_spec。
    回傳 (modules, other)，modules 為 (label, slug, path_hints, title_hints) 串列、
    other 為 (label, slug)，與舊的寫死格式完全等價。
    任何失敗（config 缺漏 / 格式異常）→ 退回內建 fallback
    並印 stderr 警告，確保 cr-planfix 仍可獨立運作。
    """
    try:
        here = Path(__file__).resolve()
        root = here.parents[3]                                   # → repo 根（.claude/skills/cr-planfix/ 上三層）
        cfg = json.loads((root / ".agent" / "config.json").read_text(encoding="utf-8"))
        spec_path = root / cfg["paths"]["modules_spec"]          # config 內為 repo 相對路徑
        data = json.loads(spec_path.read_text(encoding="utf-8"))
        mods = [(m["label"], m["key"], m["path_hints"], m["title_hints"])
                for m in data["modules"]]
        fb = data["fallback"]
        return mods, (fb["label"], fb["key"])
    except Exception as e:
        print(f"[WARN] 載入 modules.json 失敗（{e}），改用內建 fallback 模組詞表。"
              f" 請確認 .agent/config.json 的 paths.modules_spec 指向 .agent/spec/modules.json。",
              file=sys.stderr)
        return list(_FALLBACK_MODULES), _FALLBACK_OTHER


MODULES, OTHER = _load_module_vocab()

SEV_ORDER = {"高": 0, "中": 1, "低": 2}


def severity(text: str) -> str:
    """依風險措辭粗分嚴重度。"""
    t = text
    if "重要" in t or "NRE" in t or "洩漏" in t or "崩" in t or "卡死" in t \
            or "race" in t.lower() or "倒置" in t or "死碼" in t or "漏抽" in t:
        return "高"
    if "需確認" in t or "需驗證" in t or "需回歸" in t or "誤判" in t \
            or "硬編" in t or "時序" in t or "重複" in t:
        return "中"
    return "低"


def classify(files: str, title: str, risk: str = "") -> tuple:
    """回傳 (模塊名, slug)。
    優先序：檔案路徑 > 標題標籤/關鍵字 > 風險內文檔名 > 風險內文關鍵字 > 其他。"""
    fl = files.lower()
    for name, slug, paths, _ in MODULES:
        if any(k in fl for k in paths):
            return name, slug
    tl = title.lower()
    for name, slug, _, kws in MODULES:
        if any(k.lower() in tl for k in kws):
            return name, slug
    rl = risk.lower()  # 無 檔案： 行時，掃風險內文裡提到的 .cs 檔名
    for name, slug, paths, _ in MODULES:
        if any(k in rl for k in paths):
            return name, slug
    for name, slug, _, kws in MODULES:
        if any(k.lower() in rl for k in kws):
            return name, slug
    return OTHER


# 略過：風險內文等於「無」或「低」之類無實質內容
SKIP_RE = re.compile(r"^(無|低(（[^）]*）)?|無[（(]|低[，。;；])")
BUG_RE = re.compile(r"^-\s*🐛\s*(?:潛在\s*bug\s*/\s*)?(?:風險|bug)\s*(?:（[^）]*）)?\s*[:：]\s*(.*)$")
FILE_RE = re.compile(r"^-\s*檔案\s*[:：]\s*(.*)$")
HEAD_RE = re.compile(r"^###\s+(.*)$")
HASH_RE = re.compile(r"^[0-9a-f]{6,}(?:\s*[/+]\s*[0-9a-f]{6,})*", re.I)


def parse_file(path: Path):
    """解析單一日報，yield dict(date, commit, title, files, risk, sev)。"""
    date = path.stem
    lines = path.read_text(encoding="utf-8").splitlines()
    i, n = 0, len(lines)
    cur = None  # 當前區段 {title, files, risk}
    results = []

    def flush():
        if cur and cur.get("risk"):
            risk = cur["risk"].strip()
            if risk and not SKIP_RE.match(risk):
                results.append({
                    "date": date,
                    "commit": cur["commit"],
                    "title": cur["title"],
                    "files": cur["files"],
                    "risk": risk,
                    "sev": severity(risk),
                })

    while i < n:
        line = lines[i]
        m = HEAD_RE.match(line)
        if m:
            flush()
            heading = m.group(1).strip()
            hm = HASH_RE.match(heading)
            commit = hm.group(0).strip() if hm else ""
            title = heading[len(commit):].strip() if commit else heading
            cur = {"commit": commit, "title": title, "files": "", "risk": None}
            i += 1
            continue
        if cur is not None:
            fm = FILE_RE.match(line)
            if fm:
                cur["files"] = fm.group(1).strip()
                i += 1
                continue
            bm = BUG_RE.match(line)
            if bm:
                buf = [bm.group(1)]
                i += 1
                # 收續行（非新 sibling bullet、非標題）
                while i < n and not lines[i].startswith("- ") \
                        and not lines[i].startswith("#"):
                    nxt = lines[i].strip()
                    if nxt:
                        buf.append(nxt)
                    i += 1
                cur["risk"] = " ".join(buf)
                continue
        i += 1
    flush()
    return results


def date_filter(stem: str, spec: str) -> bool:
    if not spec:
        return True
    if ".." in spec:
        lo, hi = spec.split("..", 1)
        return lo <= stem <= hi
    return stem == spec


def _repo_path(key: str, fallback: str) -> Path:
    """取 .agent/config.json 的 paths.<key>（repo 相對路徑），失敗時用 fallback。"""
    root = Path(__file__).resolve().parents[3]
    try:
        cfg = json.loads((root / ".agent" / "config.json").read_text(encoding="utf-8"))
        return root / cfg["paths"][key]
    except Exception:
        return root / fallback


def main():
    ap = argparse.ArgumentParser()
    here = Path(__file__).resolve()
    default_src = _repo_path("docs_codereview", "aispec/codereview")
    ap.add_argument("--src", default=str(default_src))
    ap.add_argument("--out", default=None)
    ap.add_argument("--date", default="")
    args = ap.parse_args()

    src = Path(args.src)
    out = Path(args.out) if args.out else src / "planfix"
    if not src.is_dir():
        print(f"[ERR] src 不存在: {src}", file=sys.stderr)
        return 2
    out.mkdir(parents=True, exist_ok=True)

    # 清掉上一輪本腳本產生的檔案（README + 各模塊 slug），避免殘留
    all_slugs = [m[1] for m in MODULES] + [OTHER[1]]
    for stale in [out / "README.md"] + [out / f"{s}.md" for s in all_slugs]:
        if stale.exists():
            stale.unlink()

    files = sorted(p for p in src.glob("20??-??-??.md"))
    files = [p for p in files if date_filter(p.stem, args.date)]
    if not files:
        print(f"[ERR] 找不到符合的日報（--date={args.date!r}）", file=sys.stderr)
        return 1

    by_mod = OrderedDict((m[1], {"name": m[0], "items": []}) for m in MODULES)
    by_mod[OTHER[1]] = {"name": OTHER[0], "items": []}

    total = 0
    for p in files:
        for it in parse_file(p):
            name, slug = classify(it["files"], it["title"], it["risk"])
            it["module"] = name
            by_mod[slug]["items"].append(it)
            total += 1

    # 輸出每模塊檔案
    written = []
    for slug, bucket in by_mod.items():
        items = bucket["items"]
        if not items:
            continue
        items.sort(key=lambda x: (SEV_ORDER.get(x["sev"], 3), x["date"]), reverse=False)
        items.sort(key=lambda x: (SEV_ORDER.get(x["sev"], 3), -_d2i(x["date"])))
        lines = [f"# 待修風險清單 — {bucket['name']}", "",
                 f"> 由 `extract_risks.py` 從 code review 自動抽取，共 {len(items)} 項。"
                 f"勾選代表已處理。", ""]
        cur_sev = None
        for it in items:
            if it["sev"] != cur_sev:
                cur_sev = it["sev"]
                lines.append(f"\n## 嚴重度：{cur_sev}\n")
            lines.append(f"- [ ] **{it['date']}** `{it['commit']}` {it['title']}")
            lines.append(f"  - 風險：{it['risk']}")
            if it["files"]:
                lines.append(f"  - 檔案：{it['files']}")
        out_path = out / f"{slug}.md"
        out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        written.append((bucket["name"], slug, len(items)))

    # README 索引
    idx = ["# planfix — 待修風險彙整索引", "",
           f"> 來源：`{src}` 的 code review；由 `extract_risks.py` 產生。",
           f"> 共 **{total}** 項風險，分布如下（依數量排序）：", "",
           "| 模塊 | 項數 | 檔案 |", "|------|------|------|"]
    for name, slug, cnt in sorted(written, key=lambda x: -x[2]):
        idx.append(f"| {name} | {cnt} | [{slug}.md]({slug}.md) |")
    idx.append("")
    (out / "README.md").write_text("\n".join(idx) + "\n", encoding="utf-8")

    print(f"[OK] 解析 {len(files)} 份日報，抽出 {total} 項風險，寫入 {out}")
    for name, slug, cnt in sorted(written, key=lambda x: -x[2]):
        print(f"     - {name}: {cnt}")
    return 0


def _d2i(d: str) -> int:
    return int(d.replace("-", ""))


if __name__ == "__main__":
    sys.exit(main())
