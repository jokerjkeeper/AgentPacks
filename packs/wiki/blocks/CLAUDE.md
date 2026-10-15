## 程式 Wiki（AgentPacks / wiki）

本專案用「程式 wiki」累積 code 知識，設定集中在 `.agent/config.json`（路徑一律讀它，不得硬編）。

| 指令 | 用途 |
|------|------|
| `/cr-daily [日期\|A..B] [--force]` | 每日 code review：(a) 工程報告 → `aispec/codereview/`，(b) 程式事實 → `.agent/codereview/` |
| `/curate [來源\|feature]` | 把 codereview / `raw/tickets` / `raw/spec` 策展進 `wiki/`，維護 `.state/` |
| `/stopic <口語需求>` | 讀 `wiki/INDEX.md` 語意召回相關主題頁 |
| `/ask <問題>` | 只讀 wiki 回答，依據不足時寫入 review_queue |
| `/resolve [id]` | 處理 `.state/review_queue.json` 待審項 |
| `/cr-planfix [日期]` | 把工程報告的 🐛 風險彙整成待修清單 |

- 規格：`.agent/spec/wiki.md`（頁面結構 / 狀態檔 / 權威分級）、`.agent/spec/recon.md`（接工單先 `/stopic` + codegraph 再讀 code）、`.agent/spec/modules.json`（模組封閉詞表）。
- `wiki/INDEX.md` 由 `python .agent/scripts/build_index.py` 生成，禁止手改。
- 每日前置（可排程）：`.agent/scripts/daily_preflight.bat`。
