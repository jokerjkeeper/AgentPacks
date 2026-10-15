# /resolve — 處理驗證佇列

讀 `<STATE>/review_queue.json`，把待處理項落地（依人工意見或讀 code 驗證），更新 `wiki/` + `authority`，標 `resolved`。

> 改 wiki 一律是 CC 職責；UI / webapp 只把人工意見寫進 `.state`，不呼叫 CC。

## 0. 讀路徑

先讀 `.agent/config.json` 取 `paths`（state / wiki / scripts_root）。`scripts_root` = repo 根；code 範圍見 `paths.code_roots`，用於讀 code 驗證。

## 執行步驟

1. **讀**：`review_queue.json` + `features.json`，挑 `status ∈ {in_review, pending}`。
2. **逐項處理**：
   - **`in_review`（人工已給 `human.verdict`）**：
     - **對** → 該 feature/頁 `authority` 升 `confirmed`，`features.json` `status=confirmed`。
     - **錯** → 依 `human.note` 更正對應 wiki 頁：加「## 📌 實作確認 / 人工更正」段，舊內容標「已被修正」，`authority=confirmed`。
     - **不確定** → 維持 flagged；若有 `suggested_action`（查 code）先驗證再判。
   - **`pending` 且 `suggested_action` 指向 code** → 讀 `<scripts_root>` 下對應路徑驗證：一致則 `confirmed`、不符則更正 wiki，**附 `檔案:行號`**（讀 code＝轉述事實，不夾帶評價）。
3. **每處理一項**：更新 wiki 頁（authority / 內容 / callout）、`features.json`（`current_authority` / `status` / `last_reconciled_at`）、佇列項 `status=resolved` + `resolution` + `resolved_at`。
4. **收尾**：有新頁 / 狀態變動則更新 `INDEX.md`。

## 規則

高 tier（codereview/code/人工 1 > ticket 2）覆蓋低 tier；忠實依來源 / 人工意見，不臆測；讀 code 報告事實＝轉述（Tier1）。人類「對」只升信心，最終以 code / 工單 / 實作為 ground truth。見 `.agent/spec/wiki.md` §8。

可選 `$ARGUMENTS`：只處理某 `id` / `feature`。
