---
name: ui-verify
description: 實際操作畫面驗收：跑測試、列案例、操作、截圖、比對分析，寫 verification/ver_*/meta.json 並產生 HTML 報告。做完使用者看得到的功能或修正、回報完成前，或用戶呼叫 /ui-verify、說「驗收這個功能 / 實際跑一遍並截圖」時觸發。工單驗收組用 wp-verify。
version: 1.0.0
origin: agentpacks/verification
---

# /ui-verify — 畫面驗收

1. 完整讀 `.agent/spec/verification.md` 與 `.agent/spec/verification-project.md`；後者的環境欄位還是範例時，先從專案查明或問用戶，再填入。
2. 判斷要不要驗收（規範 §1）；不需要就說明理由並改報測試結果。
3. 依規範 §2 執行：測試 → 案例 → 實際操作 → 截圖 → 分析，寫進 `verification/ver_<YYYYMMDD>_<NN>_<slug>/meta.json`。
4. 產生報告：`python .agent/scripts/build_verification.py`，有錯就修正 meta.json 後重跑。
5. 回報各案例結果、問題與報告路徑。沒有實際操作到的案例標 `blocked`，不可標 `pass`；沒有瀏覽器工具時照實說明。
