# 驗收流程（實跑案例 → 截圖 → 分析 → 紀錄）

> AgentPacks verification 管理，勿在專案內手改；專案差異（網址、帳號、測試資料、清理、截圖是否進 git）
> 寫在 `.agent/spec/verification-project.md`，與本檔衝突時以該檔為準。
> 做完使用者看得到的功能或修正後、回報「完成」前讀這兩個檔。

## 1. 什麼時候要驗收

- 改了使用者看得到的流程，或修了用戶回報的問題。
- 純重構、純後端且有測試覆蓋的改動，用測試結果即可，不必開驗收目錄。

## 2. 怎麼做

1. **先跑測試**：專案有自動測試就先跑，結果寫進 `tests[]`；測試失敗先修，不能修就如實記錄。沒有測試則省略。
2. **列案例**：每個案例寫「步驟、預期」，涵蓋主要流程與用戶回報的情境。
3. **實際操作**：在專案檔指定的環境照步驟操作，不用假資料或改程式繞過。
   - 有費用或會影響外部系統的步驟，依專案檔的規定；沒寫就先問用戶。花費記在 `environment`。
   - 不要用程式改掉瀏覽器原生確認框；被原生視窗卡住就標 `blocked` 並記成問題。
   - 測試資料的命名與清理依專案檔。
4. **截圖**：每個案例至少一張關鍵畫面，存到 `shots/`，檔名 `NN-說明.jpg`。
   **畫面不可含密鑰、token、個資**；避不開就先遮蔽再存。
5. **比對與分析**：寫下實際結果，判定 `pass / fail / blocked`；過程中看到的其他毛病記進 `findings`。
6. **產生報告**：`python .agent/scripts/build_verification.py`，產生該次與總表的 HTML。
7. **回報用戶**：附總結、各案例結果、發現的問題，以及報告路徑 `verification/<id>/index.html`。

修好 `findings` 後，開新的一次驗收複驗，再回頭更新原項目的 `status`、`fix_commit`、`recheck` 並重新產生報告；案例的原始結果不改。

## 3. 目錄

```
verification/
  index.html                          總表（自動產生）
  ver_<YYYYMMDD>_<NN>_<slug>/
    meta.json                         案例、步驟、預期／實際、結果、截圖、問題（手寫）
    index.html                        該次報告（自動產生，勿手改）
    shots/NN-說明.jpg                 截圖
```

`NN` 為當天流水號，從 01 開始。截圖與報告預設進版控，專案檔可改。

## 4. meta.json 欄位

| 欄位 | 說明 |
|---|---|
| `id` `title` `date` `agent` | 目錄名（必須一致）、標題、日期、執行者 |
| `scope` `summary` | 驗什麼；一兩句總結 |
| `result` | 整體：`pass` / `fail` / `partial` / `blocked` |
| `environment` | 網址、帳號、輸入檔、花費等（鍵值自由，不寫密碼） |
| `tests[]` | 選填：`name` `command` `result`（`pass` / `fail` / `blocked`）`summary` |
| `cases[]` | `id` `title` `steps[]` `expected` `actual` `result` `shots[]`（相對路徑） |
| `findings[]` | `id` `severity`（`high` / `medium` / `low`）`text`；選填 `status`（`open` / `fixed` / `verified` / `wontfix`，省略視為 `open`）、`fix_commit`、`recheck`（複驗的驗收 id） |

## 5. 與 wp-verify 的分工

- 本流程：實際操作的證據與報告，放 `verification/`。
- `wp-verify`（wp-skills）：工單的驗收組與驗收清單；已有本流程的報告時，驗收文檔只附報告連結，不重複抄寫。
