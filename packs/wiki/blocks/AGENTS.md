## 程式 Wiki（AgentPacks / wiki）

本專案用「程式 wiki」累積 code 知識，路徑集中在 `.agent/config.json`（一律讀它，不得硬編）。

- 每日流程：`cr-daily` 產 (a) 工程報告 → `aispec/codereview/`、(b) 程式事實 → `.agent/codereview/`；再由 `curate` 策展進 `wiki/`，狀態維護在 `.state/`。
- 查詢：`stopic <口語需求>` 圈相關主題頁、`ask <問題>` 只讀 wiki 回答；待審項用 `resolve` 處理；`cr-planfix` 彙整風險待修清單。
- `wiki/INDEX.md` 由 `python .agent/scripts/build_index.py` 生成，禁止手改。
- 每日前置（可排程）：`.agent/scripts/daily_preflight.bat`。
