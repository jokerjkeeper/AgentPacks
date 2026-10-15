# Wiki 規格（agent 依據・canonical）

> 知識頁的結構、拆檔門檻、feature 命名、狀態檔 schema 與驗證閉環。供 `/curate`、`/ask`、`/resolve`、`/stopic` 遵循。
> 由 `CLAUDE.md`（AgentPacks 區塊）索引。路徑一律讀 `.agent/config.json` 的 `paths`（以下 `<WIKI>`、`<STATE>` 等皆指 repo 相對路徑）。
> 由 AgentPacks wiki pack 提供（pack 更新會覆蓋本檔）；頁名前綴讀 `config.wiki.page_prefix`（預設 `主題-`）。

## 1. 頁面分層（單檔同時服務人與 AI，不做兩份）

| 層 | 位置 | 對象 | 內容 |
|----|------|------|------|
| 機器層 | frontmatter | AI / 索引 | `system` / `summary` / `features` / `authority` / `sources` / **`aliases`**（關鍵詞別名，供 `/stopic` 命中）|
| 閱讀層 | `## <模組>/<feature>` section | 企劃 / 製作 | 口語化、條列，**不夾 code** |
| 引用層 | 檔末 `[^id]` footnote | 人點 + AI 追溯 | 精確 `檔案:行號`|

- 每 section 末標 `> 來源：…`。
- footnote 用 Obsidian 語法 `[^id]`，id 用功能前綴避免衝突（`[^undo-1]`）。
- **`aliases`**：列企劃可能用的口語 / 同義詞 / code 命名（如 戰鬥 → 技能, 冷卻, 傷害, SkillSystem）。初值取自 `modules.json` 的 `aliases`。

主題頁範本（`<WIKI>/主題-戰鬥.md`）：

```markdown
---
system: 戰鬥
summary: 戰鬥流程中的技能施放、冷卻與傷害結算
features: [戰鬥/技能冷卻, 戰鬥/傷害結算]
authority: confirmed
aliases: [技能, 冷卻, CD, 傷害, SkillSystem]
sources: [.agent/codereview/2026-10-01.md]
updated: 2026-10-02
---
# 主題：戰鬥

## 戰鬥/技能冷卻
技能施放後進入冷卻，冷卻期間無法再次施放。
- **冷卻歸零**：冷卻時間倒數到 0 時重置施放狀態，可再次施放 [^cd-1]
> 來源：.agent/codereview/2026-10-01.md（分類：玩法）

[^cd-1]: src/Battle/SkillSystem.cs:92-108
```

> `summary:` 是 INDEX 摘要來源；舊頁面沒有 `summary:` 時，`build_index.py` 會退回取正文第一句。

## 2. 拆檔門檻（混合制：小 inline、大拆頁）

```
模組 master 頁（主題-<模組>.md）= 概覽 + 索引
   ├─ 小 feature → 直接 inline 為 master 內的 ## section
   └─ 大 / 獨立 feature → 拆成自己的頁（主題-<模組>-<功能>.md），master 留一行索引連過去
features.json 永遠是 feature→頁面 的機器索引（不論 inline 或拆檔）
```

**拆頁觸發條件（任一即拆）**：section 過長（約超過一螢幕 / 多個子功能）；該 feature 會獨立、頻繁變動；跨多模組被引用。
**否則 inline**：小而穩定、附屬於模組的 feature 直接留在 master 頁。

## 3. feature 命名（模組/功能）

- 格式：兩層 `模組/功能`（單一字串），例 `戰鬥/技能冷卻`、`背包/堆疊上限`、`關卡資料/難度曲線`。
- **模組層** = `modules.json` 的 `name`（封閉詞表），小而穩定，可按模組捲總（列 `戰鬥/*`）。
- **功能層** 精準對齊單一功能跨來源。
- canonical 名固定於 `features.json` 防漂移；curate 指派 feature 時對照此表。

### 模組層受控清單（`.agent/spec/modules.json`）

- **單一權威來源**：引擎經 `config.paths.modules_spec` 載入。
- 每筆 `{ name, key, label, aliases, path_hints, title_hints }`：`aliases` 供 curate / `/stopic` 語意召回；`path_hints` / `title_hints` 僅供 cr-planfix 確定性分類。
- **三處同源共用**：(1) `/curate` 指派 feature 模組層 (2) git commit 模組 tag（`.agent/spec/git.md` §3）(3) cr-planfix 風險分類。
- 新系統出現：curate 暫命名 + 標 `module_provisional: true`，並回報「建議納入 `modules.json`」；確認後**只改 `modules.json` 一處**。

## 4. 與 git 模組 tag 同源

git commit 的模組 tag = 本檔「模組層」。功能層只存在於 wiki / features.json，不進 commit tag。

## 5. 按需載入（`/stopic` + INDEX 路由）

**路由表 `<WIKI>/INDEX.md`**：
- 每個主題頁一列：`模組｜摘要｜features｜別名｜頁面｜權威`。**摘要 + features + 別名**是 LLM 判斷相關性的素材。
- **由 `.agent/scripts/build_index.py` 從各 `主題-*.md` frontmatter 自動生成，禁止手改**；頁面變動後重跑（`/curate` 收尾亦會重生）。`--check` 可在提交前驗證是否過期。

**`/stopic <關鍵詞>`**：讀 INDEX → 語意判讀（不限字面命中）→ 多頁召回（一個需求常橫跨數模組，如「掉寶太少」→ 戰鬥 + 掉落 + 關卡資料）→ 載入供需求分析。

## 6. feature 粒度：粗 key 罩細點（一份兩層）

**feature key 是粗的（功能群），不與每筆 codereview 1:1。** 頁面兩層：

```
## <模組>/<粗 feature>          ← 粗 key：人導航 + features.json 對齊軸
<一句該群概述>
- **<細點標題>**：<口語事實> [^id]   ← 細點：每筆改動一條
> 來源：.agent/codereview/<dates>.md（分類：…）
[^id]: 檔案:行號 …                ← 行號全留，不因收斂而刪
```

- **內容不刪**：收斂只動「分組與 key」，口語說明與 footnote 全保留。
- **粗細決策**：一個模組通常 3~8 個粗 feature；前綴須等於所屬模組。
- **收斂**：先讀現有 `features.json` 與該模組頁，能歸入既有就歸入；只有真正的新功能群才新增粗 key。

## 7. 狀態檔 schema（`<STATE>/`）

| 檔案 | 內容 |
|------|------|
| `manifest.json` | `{ "sources": { "<repo 相對路徑>": { "sha256", "kind": "codereview\|ticket\|spec", "curated_at", "pages": [], "features": [] } } }` |
| `features.json` | `{ "features": { "<模組>/<功能>": { "module", "module_provisional", "pages": [], "sources": [{ "path", "tier", "date" }], "current_authority", "status", "last_reconciled_at" } } }` |
| `review_queue.json` | `{ "items": [{ "id", "kind": "conflict\|unverified\|qa_negative", "feature", "pages": [], "detail", "suggested_action", "status": "pending\|in_review\|resolved", "human": { "verdict": "對\|錯\|不確定", "note" }, "resolution", "created_at", "resolved_at" }] }` |
| `cr_cursor.json` | cr-daily 游標 `{ "last_commit", "last_date" }` |

`authority` / `current_authority`：`confirmed`（Tier1 或 Tier2 已對賬）、`provisional`（未啟用 / 設計中）、`unverified`（只有 ticket/spec、缺 code 佐證）。
`status`：`confirmed` / `flagged` / `superseded`。

## 8. 驗證閉環與權威分級

- **Tier**（`config.authority_tiers`）：codereview / code / 人工 = 1 > ticket / spec = 2。
- **撞同一 feature**：高 tier 覆蓋低 tier（不論日期）；同 tier 比來源日期。被覆蓋內容標「已被實作修正 / 已被工單取代」，不刪。
- **忠實整理**：只轉述來源，不推論、不臆測定案；codereview 只取「程式行為（事實）」，bug / 評價不進 wiki。
- **閉環**：`/curate` 產生 `conflict` / `unverified` → 人工在佇列填 `human.verdict` → `/resolve` 落地並標 `resolved`；`/ask` 依據不足時加 `qa_negative`。
- 人工「對」只升信心；最終以 code 為 ground truth。
