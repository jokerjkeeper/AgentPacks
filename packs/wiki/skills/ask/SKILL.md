---
name: ask
description: 知識庫問答：只讀 wiki/ 回答問題，標明依據頁與可信度，依據不足時寫入 review_queue。當用戶呼叫 /ask <問題> 時觸發。
version: 2.0.0
origin: agentpacks/wiki
---

# /ask — 知識庫問答

讀 `wiki/` 回答使用者的問題。

## 0. 讀路徑

先讀 `.agent/config.json` 取 `paths`（wiki / outputs / state，皆為 repo 相對路徑）。

## 執行步驟

1. **只讀已策展內容**：以 `<WIKI>/` 為主要依據；必要時才回溯原文（tickets / spec 在 `<RAW>/`，codereview 在 `paths.codereview_src`）。先讀 `<WIKI>/INDEX.md` 路由到相關 feature 頁。
2. **結構化問題直接讀欄位**（不用語意猜）：feature 權威 → 頁面 frontmatter `authority` + `features.json` `current_authority`；資源位置 → footnote `檔案:行號`。
3. **回答標明依據頁面** `[[...]]`，**區分可信度**：`confirmed`（codereview/工單/人工）可當事實；待確認 / `unverified` 須聲明「未必反映實作」。
4. **答不出**：明確告知知識空白，建議補哪類 raw 來源，**不編造**。
5. **輸出**：重要查詢寫 `<OUTPUTS>/<主題>查詢結果.md`，**不回流改 wiki/**。
6. **回饋閉環**：若答案主要依據未確認內容、或需人工核實 → `review_queue.json` 新增一筆（`kind: qa_negative`，記問題 + 引用頁 + 疑點），供 UI 人工處理、再由 `/resolve` 落地。

## 規則

整理不推論、不臆測定案、查詢不回流；區分 confirmed / 未確認（見 `.agent/spec/wiki.md` §8）。
