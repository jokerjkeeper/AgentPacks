"""Build the visual verification reports under verification/.

Each run lives in verification/ver_<YYYYMMDD>_<NN>_<slug>/ with a meta.json (cases,
steps, expected/actual, result, screenshots, findings, optional tests) and its screenshots in shots/.
This script writes, from those meta.json files only:

    verification/ver_.../index.html   one run: cases with screenshots and findings
    verification/index.html           every run, newest first, with pass/fail counts

Usage:  python .agent/scripts/build_verification.py
The procedure itself is described in .agent/spec/verification.md.
"""
from __future__ import annotations

import html
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent / "verification"

RESULT = {  # label and colour per result, shared by cases and runs
    "pass": ("通過", "#16a34a"),
    "fail": ("失敗", "#dc2626"),
    "blocked": ("無法驗證", "#d97706"),
    "partial": ("部分通過", "#d97706"),
}
SEVERITY = {"high": ("高", "#dc2626"), "medium": ("中", "#d97706"), "low": ("低", "#6b7280")}
STATUS = {  # findings without a status count as open
    "open": ("待處理", "#dc2626"),
    "fixed": ("已修待複驗", "#d97706"),
    "verified": ("已複驗", "#16a34a"),
    "wontfix": ("不處理", "#6b7280"),
}

STYLE = """
:root { --bg:#f5f6f8; --panel:#fff; --line:#e3e6eb; --text:#1a1d24; --muted:#6b7280; }
@media (prefers-color-scheme: dark) { :root { --bg:#0f1218; --panel:#171b23; --line:#2a303c; --text:#e6e8ee; --muted:#9aa3b2; } }
* { box-sizing: border-box; }
body { margin:0; background:var(--bg); color:var(--text); font:14px/1.6 system-ui,"Microsoft JhengHei",sans-serif; }
main { max-width:1180px; margin:0 auto; padding:28px 16px 60px; }
h1 { margin:0 0 4px; font-size:24px; } h2 { margin:0; font-size:17px; }
a { color:#2563eb; }
.muted { color:var(--muted); }
.chip { display:inline-block; padding:1px 10px; border-radius:12px; font-size:12px; font-weight:600; color:#fff; white-space:nowrap; }
.card { background:var(--panel); border:1px solid var(--line); border-radius:12px; padding:18px 20px; margin-top:16px; }
.head { display:flex; align-items:center; gap:10px; flex-wrap:wrap; }
.facts { display:grid; grid-template-columns:110px 1fr; gap:4px 12px; margin:12px 0 0; font-size:13px; }
.facts dt { color:var(--muted); }
.facts dd { margin:0; }
ol { margin:6px 0 0; padding-left:20px; }
.shots { display:grid; grid-template-columns:repeat(auto-fill,minmax(320px,1fr)); gap:12px; margin-top:14px; }
.shots figure { margin:0; }
.shots img { width:100%; border:1px solid var(--line); border-radius:8px; display:block; cursor:zoom-in; }
.shots figcaption { font-size:12px; color:var(--muted); margin-top:4px; }
table { width:100%; border-collapse:collapse; }
th, td { text-align:left; padding:8px 10px; border-bottom:1px solid var(--line); vertical-align:top; }
th { font-size:12px; color:var(--muted); font-weight:600; }
.counts { display:flex; gap:6px; flex-wrap:wrap; }
"""


def chip(label: str, colour: str) -> str:
    return f'<span class="chip" style="background:{colour}">{html.escape(label)}</span>'


def result_chip(result: str) -> str:
    label, colour = RESULT.get(result, (result, "#6b7280"))
    return chip(label, colour)


def finding_status(item: dict) -> str:
    """Status chip of a finding, plus its fix commit and a link to the run that rechecked it."""
    status = item.get("status", "open")
    parts = [chip(*STATUS.get(status, (status, "#6b7280")))]
    if item.get("fix_commit"):
        parts.append(f'<br><code>{html.escape(item["fix_commit"])}</code>')
    if item.get("recheck"):
        run = html.escape(item["recheck"])
        parts.append(f'<br><a href="../{run}/index.html">{run}</a>')
    return "".join(parts)


def page(title: str, body: str) -> str:
    return (f'<!doctype html><html lang="zh-Hant"><head><meta charset="utf-8">'
            f'<meta name="viewport" content="width=device-width,initial-scale=1">'
            f'<title>{html.escape(title)}</title><style>{STYLE}</style></head>'
            f'<body><main>{body}</main></body></html>')


def run_report(meta: dict) -> str:
    """One run: header facts, then each case with its steps and screenshots, then findings."""
    esc = html.escape
    env = meta.get("environment", {})
    parts = [
        '<p><a href="../index.html">← 所有驗收</a></p>',
        f'<div class="head"><h1>{esc(meta["title"])}</h1>{result_chip(meta.get("result", ""))}</div>',
        f'<p class="muted">{esc(meta["id"])} · {esc(meta.get("date", ""))} · {esc(meta.get("agent", ""))}</p>',
        f'<p>{esc(meta.get("summary", ""))}</p>',
        '<div class="card"><h2>範圍與環境</h2><dl class="facts">',
        f'<dt>範圍</dt><dd>{esc(meta.get("scope", ""))}</dd>',
        *[f'<dt>{esc(key)}</dt><dd>{esc(str(value))}</dd>' for key, value in env.items()],
        '</dl></div>',
    ]
    tests = meta.get("tests", [])
    if tests:
        rows = "".join(
            f'<tr><td>{esc(test.get("name", ""))}</td><td><code>{esc(test.get("command", ""))}</code></td>'
            f'<td>{result_chip(test.get("result", ""))}</td><td>{esc(test.get("summary", ""))}</td></tr>' for test in tests)
        parts.append(f'<div class="card"><h2>自動測試</h2><table><tr><th>名稱</th><th>指令</th><th>結果</th><th>摘要</th></tr>{rows}</table></div>')
    for case in meta.get("cases", []):
        steps = "".join(f"<li>{esc(step)}</li>" for step in case.get("steps", []))
        shots = "".join(
            f'<figure><a href="{esc(shot)}" target="_blank"><img src="{esc(shot)}" alt="" loading="lazy"></a>'
            f'<figcaption>{esc(Path(shot).stem)}</figcaption></figure>' for shot in case.get("shots", []))
        parts.append(
            f'<div class="card"><div class="head"><h2>{esc(case["id"])} · {esc(case["title"])}</h2>'
            f'{result_chip(case.get("result", ""))}</div>'
            f'<dl class="facts"><dt>步驟</dt><dd><ol>{steps}</ol></dd>'
            f'<dt>預期</dt><dd>{esc(case.get("expected", ""))}</dd>'
            f'<dt>實際</dt><dd>{esc(case.get("actual", ""))}</dd></dl>'
            + (f'<div class="shots">{shots}</div>' if shots else "") + '</div>')
    findings = meta.get("findings", [])
    if findings:
        rows = "".join(
            f'<tr><td>{esc(item["id"])}</td><td>{chip(*SEVERITY.get(item.get("severity", "low"), ("?", "#6b7280")))}</td>'
            f'<td>{esc(item["text"])}</td><td>{finding_status(item)}</td></tr>' for item in findings)
        parts.append(f'<div class="card"><h2>發現的問題</h2><table><tr><th>編號</th><th>嚴重度</th><th>內容</th><th>狀態</th></tr>{rows}</table></div>')
    return page(meta["title"], "".join(parts))


def overview(runs: list[dict]) -> str:
    """Every run, newest first, with how many cases passed and how many findings were raised."""
    esc = html.escape
    rows = []
    for meta in runs:
        cases = meta.get("cases", [])
        counts = {key: sum(1 for case in cases if case.get("result") == key) for key in RESULT}
        badges = "".join(chip(f"{RESULT[key][0]} {count}", RESULT[key][1]) for key, count in counts.items() if count)
        findings = meta.get("findings", [])
        unresolved = sum(1 for item in findings if item.get("status", "open") in ("open", "fixed"))
        rows.append(
            f'<tr><td>{esc(meta.get("date", ""))}</td>'
            f'<td><a href="{esc(meta["id"])}/index.html">{esc(meta["title"])}</a><br>'
            f'<span class="muted">{esc(meta.get("summary", ""))}</span></td>'
            f'<td>{result_chip(meta.get("result", ""))}</td><td><div class="counts">{badges}</div></td>'
            f'<td>{unresolved} / {len(findings)}</td></tr>')
    body = ('<h1>驗收紀錄</h1><p class="muted">每次驗收：實際操作案例 → 截圖 → 比對預期 → 記錄問題。'
            '由 .agent/scripts/build_verification.py 依各目錄的 meta.json 產生。</p>'
            '<div class="card"><table><tr><th>日期</th><th>驗收</th><th>結果</th><th>案例</th><th>問題（未結 / 全部）</th></tr>'
            + "".join(rows) + '</table></div>')
    return page("驗收紀錄", body)


def main() -> int:
    """Build every report; a broken meta.json is reported and skipped, and makes the exit code 1."""
    ROOT.mkdir(exist_ok=True)
    runs, failed = [], 0
    for meta_path in sorted(ROOT.glob("ver_*/meta.json"), reverse=True):
        try:
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
            if meta["id"] != meta_path.parent.name:
                raise ValueError(f'id "{meta["id"]}" does not match the directory name')
            (meta_path.parent / "index.html").write_text(run_report(meta), encoding="utf-8")
        except (OSError, ValueError, KeyError, TypeError, AttributeError) as err:
            print(f"error: {meta_path}: {type(err).__name__}: {err}", file=sys.stderr)
            failed += 1
            continue
        runs.append(meta)
    (ROOT / "index.html").write_text(overview(runs), encoding="utf-8")
    print(f"built {len(runs)} run(s) -> {ROOT / 'index.html'}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
