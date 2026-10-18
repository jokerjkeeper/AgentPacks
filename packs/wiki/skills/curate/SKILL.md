---
name: curate
description: 每日策展：把 codereview、工單（raw/tickets）與 spec（raw/spec）的新增 / 變更策展進 wiki/，維護 feature 對齊、權威對賬與驗證佇列。當用戶呼叫 /curate 或要求策展知識庫時觸發；可帶來源（如 codereview）或 feature 限定範圍。
version: 2.0.0
origin: agentpacks/wiki
---

# /curate — 每日策展

掃描來源（codereview / tickets / spec），把新增/變更的內容策展進 `wiki/`，並維護驗證閉環狀態（feature 對齊、權威對賬、待審佇列）。
**來源：codereview + ticket + spec**（discord/wiki/版本/營運 不納入本系統）。

> 設計依據（狀態檔 schema / 驗證閉環 / 拆檔 / feature 命名）見 `.agent/spec/wiki.md`。
> 模組詞表見 `.agent/spec/modules.json`。

## 0. 讀路徑（不得硬編）

先讀 `.agent/config.json` 取 `paths`（raw / state / wiki / outputs / scripts_root / **codereview_src** / **modules_spec**）與 `sources` / `authority_tiers`。以下 `<RAW>` `<STATE>` `<WIKI>` `<CODEREVIEW_SRC>` 皆指 config 中的 repo 相對路徑；`<MODULES>` 指 `paths.modules_spec` 載入的模組受控詞表（見 step 5）。

## 執行步驟

1. **讀狀態**：`<STATE>/manifest.json`、`features.json`、`review_queue.json`。
   - **首次策展（模組詞表初始化）**：`manifest` 為空且 `<MODULES>` 只有 seed 的初始模組（`系統`＝agent / 專案設定）時，先**不寫任何 wiki**：
     1. 依 `paths.code_roots` 的目錄結構（含次層目錄）＋本批 codereview 的 `feature 提示` / `檔案` 路徑，提出**產品模組清單**（每筆 `name` / `key` / `label` / `aliases` / `path_hints`，粗粒度、通常 4~10 個；名稱不可與 config `categories[].name` 相同）。
     2. 用一次提問給用戶確認 / 調整（附「模組 → 涵蓋目錄 / 代表 feature」對照）。
     3. 確認後寫入 `<MODULES>`（保留原有模組，新模組依 `_order` 規則插在 `系統` 之前），再開始 step 2 正常策展。
   - 非首次策展時，遇到落不進模組的內容才走 step 5 的 `module_provisional` 流程。
2. **找增量**：遍歷 `<CODEREVIEW_SRC>/*.md`（codereview，cr-daily 的 (b) 產出直讀）與 `<RAW>/**/*.md`（看 `tickets/`、`spec/`），每檔算 sha256 與 manifest 比對（新增 / 變更 / 跳過）。
3. **路由（codereview / ticket / spec）**：
   - **codereview 依 `分類` 分流**（避免工程內部污染功能 wiki）；分類詞表與去向見 config `categories[]`（`route` 欄位）：
     - `route: player` → 使用者面向的模組主題頁（`system:` = 該 feature 的模組，取自 `<MODULES>`）
     - `route: engineering` → 工程主題頁（`system:` 用該分類名，如 `架構` / `渲染`，與功能頁隔離）
     - `route: tool` → 工具主題頁（`system: 工具`）
     - 所有分類**都納入**，靠 `system:` 隔離，不丟棄。
     - 分類名與模組名共用 `system:` 命名空間：若 config 的分類名與 `<MODULES>` 某模組 `name` 相同（舊版預設「系統」會撞名），**停下回報**，建議改 config 分類名（例 `系統` → `架構`），不要自行決定歸屬。
   - **ticket** → 可復用技術知識抽進 `wiki/` 主題頁；若該工單為明確「決策 / 進度串」，得另記其時序（佈告欄為選用，預設併入主題頁 `> 來源`，本系統不強制建佈告欄區）。
   - **spec（功能設計 / 架構文檔，閱讀層骨幹）** → 與 codereview（每日 diff、補充細點）性質不同：
     - spec **主餵閱讀層**（功能概述 / 設計規則 / 架構決策），歸入對應模組主題頁的新或既有 feature；模組層仍走 `<MODULES>` 封閉詞表（step 5）。
     - spec 內的 `檔案:行號` 是**撰寫當下快照、會漂移，不可照搬**——先在內文標 `待驗 file:line`，對本 repo 現行程式（`paths.code_roots`）重新定位後，curate 再把 footnote 換成校正值（產物：`<OUTPUTS>/待驗-*.md` ↔ `<OUTPUTS>/驗證結果-*.md`）。
     - **回填時修正 spec 內容錯誤**：若驗證指出 spec 的符號 / 狀態有誤（標 dead code 實際未刪、建構點標錯、符號查無…），**以驗證結果為準，wiki 勿照抄 spec 的錯誤**。
4. **策展（忠實整理，不推論，每點標來源）**：
   - 跨多主題的來源建 `<WIKI>/來源/來源-XXX.md`；單主題直接於主題頁 `> 來源` 引 raw（混合制）。
   - 概念整理進 `主題-XXX.md` 的 `## 功能：X` section；**口語化、不夾 code**，精確 `檔案:行號` 放檔末 `[^id]` footnote（見 `.agent/spec/wiki.md`）。
   - **拆檔門檻**：小 feature inline；大 / 獨立 feature 拆成自己的頁，master 頁留索引（規則見 `.agent/spec/wiki.md`）。
5. **指派 feature（粗 key，見 `.agent/spec/wiki.md` §6）**：feature 是**粗的功能群**（一個 key 罩多個細點），不與每筆 codereview 1:1。**先讀現有 `features.json` 與該模組頁的粗 feature，能歸入既有就歸入；只有真正新功能群才新增粗 key**（保持收斂、不膨脹）。頁面用兩層（粗 `##` 章節 → 細 bullet + 行號 footnote）。寫頁面 frontmatter `features:` + 更新 `features.json`（pages / sources / tier / date）。
   - **模組層＝受控詞表 `<MODULES>`（封閉）**：載入 `paths.modules_spec`（`modules.json`）。feature 鍵前綴（`<模組>/<功能>`）的 `<模組>` **只能取自詞表的 `name`**；判斷歸哪個模組時以該模組的 `aliases` 做語意對照（與 `/stopic` 同源）。歸入詞表內模組者，`features.json` 該 feature 的 `module_provisional` 設 `false`（或省略）。
   - **落不進任何現有模組**才暫新增：沿用既有名 → 直接用；確為新系統 → 暫命名並標 `module_provisional: true`，且**回報「建議納入 `modules.json`」**（詞表是單一權威來源，新模組要回填該檔，勿讓 git tag / wiki / cr-planfix 三處漂移；詞表結構見 `.agent/spec/wiki.md` §3~§4）。
6. **權威對賬（核心）**：tier＝codereview/code/人工(1) > ticket / spec(2)。
   - 標頁面 + section `authority`：Tier1/2 → `confirmed`。
   - 撞同一 `feature`：**高 tier 覆蓋低 tier（不論日期）；同 tier 才比來源日期**。被覆蓋者標「已被實作修正 / 已被工單取代」。
   - codereview 只取「程式行為（事實）」＋ `檔案:行號`；**不得引入 bug / 評價 / 設計意圖**。
   - **spec authority 依功能狀態標**：已實作 `⟨confirmed⟩`；條件編譯 / 未啟用 / 已擱置 `⟨provisional⟩` 或 `📝 設計中`。spec 主供閱讀層敘事，**code-fact（file:line）仍以 codereview / 驗證回填為準**（spec tier 低於 codereview）。
   - **時效收斂（spec 同源跨來源）**：以「最後驗證」日期判新舊——新者覆蓋舊者的**數字 / 狀態**，舊**架構敘事保留**並標來源日期。
   - 更新 `features.json` 的 `current_authority` / `status`；能被高權威自動裁決的 `review_queue` 項 → `resolved`。
7. **待審佇列 flag**（寫 `review_queue.json`）：
   - 同 feature 跨來源衝突且無 Tier1 可裁決 → `conflict`
   - ticket 規格無 code 佐證、需實作確認 → `unverified`
8. **維護導覽**：重跑 `python .agent/scripts/build_index.py` 重生 `<WIKI>/INDEX.md`（從各 `主題-*.md` frontmatter 自動生成路由表，**勿手改**；格式見 `.agent/spec/wiki.md` §5）、檢查 `[[]]` 連結與孤立頁。
9. **收尾**：更新 `manifest.json`（hash / curated_at / pages / features）、`features.json`、`review_queue.json`。

## 規則

忠實整理、不臆測、每點標來源、區分 confirmed/（待確認）。schema、權威分級、拆檔與模組封閉詞表皆以 `.agent/spec/wiki.md` 為準。

可選參數：只策展某來源（如 `codereview`）或某 `feature`。
