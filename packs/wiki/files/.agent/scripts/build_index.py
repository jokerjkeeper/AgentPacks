#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""build_index.py — 從 wiki/<前綴>*.md 的 frontmatter 生成 wiki/INDEX.md 路由表（AgentPacks / wiki pack）。

INDEX.md 是 /stopic 的 LLM 判讀素材（模組｜摘要｜features｜別名｜頁面｜權威），禁止手改。
INDEX.md 若有 `<!-- AUTO-INDEX:START … -->` / `<!-- AUTO-INDEX:END -->` 標記，只改寫標記之間，標記外的手寫路由保留。

用法：
    python .agent/scripts/build_index.py           # 重生 INDEX.md
    python .agent/scripts/build_index.py --check   # 只檢查是否過期（過期 exit 1，供提交前驗證）

設定讀 .agent/config.json：paths.wiki（repo 相對路徑）、wiki.page_prefix（預設「主題-」）。
摘要：frontmatter `summary:` 優先；沒有則取正文第一句（相容舊頁面）。
不依賴 PyYAML，只解析 frontmatter 用到的子集：`key: value`、`key: [a, b]`、`- item` 區塊清單。
"""
import argparse
import json
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_PREFIX = "主題-"
# INDEX.md 上半部若有手寫路由，用這組標記圈出自動區塊；標記行後面可加說明文字
AUTO_START_PREFIX = "<!-- AUTO-INDEX:START"
AUTO_END = "<!-- AUTO-INDEX:END -->"


def load_settings() -> tuple:
    """讀 config 的 paths.wiki 與 wiki.page_prefix；缺漏時退回預設。"""
    try:
        cfg = json.loads((REPO_ROOT / ".agent" / "config.json").read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        print(f"[WARN] 讀取 .agent/config.json 失敗（{error}），改用預設 wiki/ 與「{DEFAULT_PREFIX}」", file=sys.stderr)
        return REPO_ROOT / "wiki", DEFAULT_PREFIX
    wiki = cfg.get("paths", {}).get("wiki") or "wiki"
    prefix = cfg.get("wiki", {}).get("page_prefix") or DEFAULT_PREFIX
    return REPO_ROOT / wiki, prefix


def parse_scalar(raw: str):
    """解析單一值：inline 清單 [a, b] 或去引號字串。"""
    value = raw.strip()
    if value.startswith("[") and value.endswith("]"):
        inner = value[1:-1].strip()
        return [item.strip().strip("'\"") for item in inner.split(",") if item.strip()] if inner else []
    return value.strip("'\"")


def split_page(text: str) -> tuple:
    """拆出 (frontmatter dict, 正文)；沒有 frontmatter 回傳 (None, 全文)。"""
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return None, text
    data, current_key, end = {}, None, len(lines)
    for index, line in enumerate(lines[1:], start=1):
        if line.strip() == "---":
            end = index
            break
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if stripped.startswith("- ") and current_key is not None:
            if not isinstance(data.get(current_key), list):
                data[current_key] = []
            data[current_key].append(stripped[2:].strip().strip("'\""))
            continue
        if ":" in line and not line.startswith((" ", "\t")):
            key, _, raw = line.partition(":")
            current_key = key.strip()
            data[current_key] = parse_scalar(raw) if raw.strip() else []
    return data, "\n".join(lines[end + 1:])


def first_sentence(body: str) -> str:
    """取正文第一個非標題 / 非引用 / 非分隔線的段落行，作為摘要後備。"""
    for line in body.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith(("#", ">", "---", "|", "[^")):
            continue
        return stripped
    return ""


def as_text(value) -> str:
    """表格儲存格：清單以頓號連接，並跳脫管線符號。"""
    if isinstance(value, list):
        value = "、".join(str(item) for item in value)
    return str(value or "").replace("|", "\\|").replace("\n", " ")


def build(wiki: Path, prefix: str) -> tuple:
    """掃描主題頁並組出 (INDEX.md 全文, 主題頁數, 警告清單)；依模組、檔名排序，輸出穩定。"""
    rows, warns = [], []
    name_re = re.compile(r"^" + re.escape(prefix) + r"\S+\.md$")
    for page in sorted(wiki.glob(prefix + "*.md")):
        if not name_re.match(page.name):
            continue                                         # 排除含空白的暫存筆記
        meta, body = split_page(page.read_text(encoding="utf-8"))
        if meta is None:
            warns.append(f"{page.name}: 無 frontmatter，略過")
            continue
        summary = as_text(meta.get("summary")) or as_text(first_sentence(body))
        authority = as_text(meta.get("authority"))
        sources = meta.get("sources") if isinstance(meta.get("sources"), list) else []
        if not authority and any("codereview" in str(src) for src in sources):
            authority = "confirmed*"                         # 由 Tier1 來源推得
            warns.append(f"{page.name}: frontmatter 缺 authority，已由 codereview 來源推為 confirmed")
        if not summary:
            warns.append(f"{page.name}: 缺 summary（也無正文首句）")
        if not meta.get("aliases"):
            warns.append(f"{page.name}: 缺 aliases（/stopic 關鍵詞命中會變差）")
        if str(meta.get("module_provisional", "")).lower() == "true":
            warns.append(f"{page.name}: module_provisional，建議把模組納入 modules.json")
        rows.append((
            as_text(meta.get("system")) or page.stem[len(prefix):],
            summary,
            as_text(meta.get("features")),
            as_text(meta.get("aliases")),
            f"[[{page.stem}]]",
            authority or "—",
        ))
    rows.sort(key=lambda row: (row[0], row[4]))
    lines = [
        "# Wiki 路由表（INDEX）",
        "",
        f"> 由 `.agent/scripts/build_index.py` 從各 `{prefix}*.md` frontmatter 自動生成，**禁止手改**。",
        "> 供 `/stopic` 語意判讀：依「摘要 / features / 別名」決定載入哪些主題頁。",
        "> 權威 `*` = 由 codereview 來源推得，建議補回頁面 frontmatter。",
        "",
    ]
    if not rows:
        lines += ["（尚無主題頁；執行 `/curate` 後會出現。）", ""]
        return "\n".join(lines), 0, warns
    lines += ["| 模組 | 摘要 | features | 別名 | 頁面 | 權威 |", "|---|---|---|---|---|---|"]
    lines += ["| " + " | ".join(row) + " |" for row in rows]
    lines.append("")
    return "\n".join(lines), len(rows), warns


def merge(current, content: str) -> str:
    """INDEX.md 有 AUTO-INDEX 標記時只換標記內（保留標記外的手寫路由），否則整份使用生成內容。"""
    if current is None:
        return content
    start = current.find(AUTO_START_PREFIX)
    end = current.find(AUTO_END, start + 1) if start >= 0 else -1
    if start < 0 or end < 0:
        return content
    start_line_end = current.find("\n", start)
    if start_line_end < 0 or start_line_end > end:
        return content
    body = content.split("\n", 2)[2] if content.startswith("# ") else content   # 去掉生成內容的標題，標記外已有標題
    return current[:start_line_end + 1] + "\n" + body.rstrip("\n") + "\n\n" + current[end:]


def main() -> int:
    parser = argparse.ArgumentParser(description="生成 wiki/INDEX.md 路由表")
    parser.add_argument("--check", action="store_true", help="只檢查 INDEX.md 是否過期")
    args = parser.parse_args()

    wiki, prefix = load_settings()
    if not wiki.is_dir():
        print(f"[ERR] wiki 目錄不存在：{wiki}", file=sys.stderr)
        return 2
    index_path = wiki / "INDEX.md"
    content, page_count, warns = build(wiki, prefix)
    for warn in warns:
        print(f"[WARN] {warn}", file=sys.stderr)
    try:
        current = index_path.read_text(encoding="utf-8") if index_path.exists() else None
    except OSError as error:
        print(f"[ERR] 無法讀取 {index_path}：{error}", file=sys.stderr)
        return 2
    content = merge(current, content)

    if args.check:
        if current != content:
            print(f"[STALE] {index_path} 已過期，請執行 python .agent/scripts/build_index.py")
            return 1
        print(f"[OK] {index_path} 為最新")
        return 0

    if current == content:
        print(f"[OK] {index_path} 無變更")
        return 0
    try:
        index_path.write_text(content, encoding="utf-8", newline="\n")
    except OSError as error:
        print(f"[ERR] 無法寫入 {index_path}：{error}", file=sys.stderr)
        return 2
    print(f"[OK] 已寫入 {index_path}（{page_count} 個主題頁）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
