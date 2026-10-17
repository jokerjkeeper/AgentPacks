---
name: cr-daily
description: >-
  每日 code review：對前一日（或指定日期/區間）的 commit 做工程 code review。
  產兩種產物並嚴格分流——(a) 工程回顧報告留在 aispec/codereview/，
  (b) 純「程式做了什麼」的知識素材寫進 .agent/codereview/，供本 repo /curate 直讀策展
  （合併模式；設了 agent_raw_codereview 則為拆解模式，另複製一份到該外部 inbox）。
  路徑一律讀 .agent/config.json，不硬編。
  當用戶呼叫 /cr-daily（可帶日期 2026-03-15 或區間 2026-03-01..2026-05-31 或 --force）時觸發。
  做到寫出 (b) 即停，不碰 /curate、不回寫 WePages。
version: 1.0.0
origin: project
---

# cr-daily — 每日 Code Review

對前一日（或指定日期/區間）的 git commit 做工程 code review，產出**兩種嚴格分流**的東西：

| 產物 | 內容 | 去處 |
|------|------|------|
| **(a) 工程回顧報告** | 改了啥、bug、效能風險、品質評價、建議 | `aispec/codereview/YYYY-MM-DD.md`（留本地）|
| **(b) 知識素材** | code「做了什麼」的程式事實 + `檔案:行號` | `<CODEREVIEW_OUT>/YYYY-MM-DD.md`（code 數據家，本 repo `/curate` 直讀）；**拆解模式**（config 設了 `AGENT_RAW`）另複製到 `<AGENT_RAW>/` |

> 你扮演 wiki 來源體系的「robot 適配器」：**你寫 (b) 到 CODEREVIEW_OUT，本 repo 的 `/curate` 之後直讀它策展**（合併模式，預設）。
> (b) 的三鐵律與格式即本檔下方所述，須嚴守。

## Step 0：讀路徑配置（不硬編）

先讀 `.agent/config.json` 的 `paths`，綁定以下名稱（全文用這些名稱）：

| 名稱 | config key | 用途 |
|------|-----------|------|
| `DOCS_A` | `docs_codereview` | (a) 工程報告輸出 |
| `CODEREVIEW_OUT` | `codereview_out` | (b) 知識素材輸出（code 數據家，`/curate` 直讀） |
| `AGENT_RAW` | `agent_raw_codereview` | **拆解模式**才用：外部 wiki repo 的攝取 inbox。`null` / 未設＝**合併模式**（預設），不複製 |
| `CURSOR` | `cursor` | 向前 review 游標 |
| `COLLECT` | `collector` | git 收集器 cr_collect.py（canonical：`.agent/capabilities/skills/cr-daily/cr_collect.py`） |

> config 的 `collector` 若仍指向舊位置 `.claude/skills/cr-daily/cr_collect.py` 而該檔不存在（wiki pack v1 遷移後），改用 canonical 位置執行，並提醒用戶更新 `.agent/config.json`。

**執行前確認 `CODEREVIEW_OUT` 目錄存在**（`ls` 一下，不存在可建——這是本 repo 自己的目錄）。
**`AGENT_RAW` 為 null / 未設 / 目錄不存在**：即合併模式，略過 Step 3.5 導入（這是預設、不是錯誤）；不要 mkdir 別人的庫。

## 鐵則（不可違反）

寫 **(b) 知識素材**時，照對接規格三鐵律：

1. **只講 code 做了什麼**——可觀察行為，且**每條附 `檔案:行號`** 讓人能翻 code 稽核。
2. **不准臆測**——不寫「為什麼這樣設計 / 設計意圖 / 玩法好不好」。
3. **不夾帶評價**——bug / 效能風險 / 品質意見一律只進 (a)，**絕不進 (b)**。

> 為何不違反 wiki「不推論」原則：code 本身是真實人類來源，讀 code 報告其行為＝轉述（同讀工單），非臆測。

**其餘評價、bug、風險、好壞判斷 → 全進 (a)，那才是本專案自己的工程報告。**

## 執行流程

### Step 1：解析參數，決定 collector 模式

| 用戶輸入 | collector 指令 | 動游標? |
|----------|---------------|---------|
| `/cr-daily`（無參數）| 讀 `CURSOR` → `--since-commit <last_commit>`；**若 CURSOR 不存在（首跑）→ `--head-only`** | ✅ 會更新 |
| `/cr-daily 2026-03-15` | `--date 2026-03-15` | ❌ 不動 |
| `/cr-daily 2026-03-01..2026-05-31` | `--range 2026-03-01..2026-05-31` | ❌ 不動 |
| `--force`（可與上述併用）| 同上，但覆蓋已存在當日檔 | 依模式 |

首跑（無 CURSOR）用 `--head-only` 安全起步，並提示用戶：「歷史補跑請用 `/cr-daily 起日..迄日`，逐月順跑」。

### Step 2：跑收集器

```
python <COLLECT> <模式參數>
```

拿到 JSON：`{ days: [{date, commit_range, commit_count, commits:[{sha, subject, files:[{path,status,rename_only}]}]}], head_sha, head_date }`。
diff 不在 JSON 裡——下一步自己抓。

### Step 3：逐日處理（順跑，不平行）

對 `days` 裡每個 `date`（已由舊到新排序）：

1. **冪等跳過**：若 `DOCS_A\<date>.md` 已存在且未帶 `--force` → 跳過該日（批次中斷後重跑安全）。
2. **抓 diff 與行號**：對該日每個 commit/檔案，`git show <sha> -- <path>` 看 diff；要寫精確 `檔案:行號` 時，Read 該檔對應段落確認。
   - `rename_only: true` 或純格式化/純註解 → **(b) 不產條目**（(a) 可一句帶過）。
3. **產 (a) 工程報告** → 寫 `DOCS_A\<date>.md`（格式見下）。
4. **產 (b) 知識素材** → 寫 `CODEREVIEW_OUT\<date>.md`（格式見下，守三鐵律）。
   - 該日若所有變更都是純改名/格式/無行為意義 → (b) 可只寫 frontmatter + 一行「本日無對外行為變更」，或不寫檔（但仍要在摘要說明）。
5. `reviewed_at` 用 `date -Iseconds`（或 `date +%Y-%m-%dT%H:%M:%S%z`）取當下時間。

> **空日**（collector `days` 為空 = 該範圍無有意義的程式變更）：不寫任何檔，但游標仍要前進（見 Step 4）。

### Step 3.5：導入外部 inbox（僅拆解模式；純複製，不跑 curate）

**合併模式（`AGENT_RAW` 為 null / 未設，預設）**：跳過本步——`/curate` 直接讀 `CODEREVIEW_OUT`，無需複製。

**拆解模式（`AGENT_RAW` 設了外部路徑）**：把本次寫出的每個 `<CODEREVIEW_OUT>\<date>.md` **複製一份**到 `<AGENT_RAW>\<date>.md`（覆蓋同名）。這是外部 wiki repo 的攝取 inbox，該端的 `/curate` 之後會讀它。

```
cp <CODEREVIEW_OUT>\<date>.md  <AGENT_RAW>\<date>.md   # 對本次每個產出的 date
```

- 只複製本次新寫/更新的 (b) 檔，不整碟同步。
- **`AGENT_RAW` 目錄不存在** → 略過，摘要註記「未導入」；**絕不**在外部 repo 做 git 或跑 /curate。
- 空日不複製（沒檔）。

### Step 4：更新游標（僅無參數 / 首跑模式）

**只有無參數（含首跑）模式**才寫游標；`--date`/`--range` 歷史補跑**不動游標**（它們補的是過去，游標只代表「向前 review 到哪」）。

```
寫 CURSOR = { "last_commit": <head_sha>, "last_date": <head_date> }
```

**空日也要前進**（即使這次沒產任何檔，也把游標推到 head_sha）。`.state\` 目錄不存在就先建。

### Step 5：輸出摘要

```
=== cr-daily 摘要 ===
模式：<無參數游標 / 單日 / 區間>  範圍：<...>
處理：2026-06-04（9 commit → (a) 1 檔、(b) 5 條）, 2026-06-05（...）
跳過（已存在）：<日期清單>
空日：<日期清單>
導入外部 inbox：<合併模式(免導入) / 已複製 N 檔到 AGENT_RAW / 未導入(目錄不存在)>
游標：<更新到 head_sha / 未更新(歷史模式)>
====================
```

## (a) 工程報告格式 `aispec/codereview/YYYY-MM-DD.md`

```markdown
---
date: 2026-06-04
commit_range: 29ebe2f..e1a3c54
commit_count: 9
reviewed_at: 2026-06-05T09:00:00+08:00
---
# Code Review 工程回顧 2026-06-04

## 摘要
（這天動了哪些系統、整體品質一句話）

## 逐項
### <短sha> <一句話描述 commit>
- 檔案：src/.../X.cs:40-78
- 改了什麼：
- 🐛 潛在 bug / 風險：（無則寫「無」）
- ⚡ 效能：（無則寫「無」）
- 🧹 品質 / 可維護性：
- 建議：

## 待追蹤
- （需後續關注的點；無則省略本段）
```

寫作要求：(a) 是給工程團隊看的，**可以有判斷與評價**（這正是它跟 (b) 的差別）。聚焦真正有意義的變更，純機械改動一句帶過。

## (b) 知識素材格式 `<CODEREVIEW_OUT>/YYYY-MM-DD.md`

嚴格照對接規格 §3：

```markdown
---
source: codereview
source_id: codereview-2026-06-04
date: 2026-06-04
project: <config.project>
commit_range: "29ebe2f..e1a3c54"
commit_count: 9
reviewed_at: 2026-06-05T09:00:00+08:00
tags: [code-review]
---

## 變更：<一句話描述 code 做了什麼>

- **commit**: <短sha>
- **檔案**: src/Battle/SkillSystem.cs:92-108
- **分類**: 玩法            # 必填，取自 config categories[].name，讓 wiki 端能分辨知識性質
- **feature 提示**: 戰鬥/技能冷卻        # 選填；不確定就留空，wiki 端會指派
- **程式行為（事實）**: <只描述可觀察行為，能對應到 檔案:行號；不寫意圖、不寫好壞>
- **關聯既有知識**: <選填；只客觀指出「觸及哪個功能」，不下「推翻/定案」結論>
```

### 分類詞表（`分類` 欄位用，每條必填一個）

> 詞表在 `.agent/config.json` 的 `categories[]`（`name` / `desc`；`route` 是 `/curate` 的分流去向）。**只能用詞表內的 name**；專案要調整分類就改 config，不要改本檔。
> 對接規格把 `分類` 列為**選填**，但生產端**一律填寫**——成本低且讓 wiki 分流更準。

預設詞表：`玩法`（規則 / 機制 / 數值）、`UI`（介面與輸入互動）、`系統`（事件 / 流程 / 時序 plumbing）、`編輯器`（開發 / 測試 / 工具，**非對外功能**）、`渲染`（視覺內部實作）。

> **重要**：編輯器工具、渲染內部這類「非玩法知識」**也要產 (b) 條目**，靠 `分類` 標註讓 wiki 端自行決定是否納入策展——**不要**自行在生產端就把它們濾掉。唯一不產 (b) 的是純改名 / 純格式 / 純註解（無任何行為意義）的變更。

要點：
- **一個 commit 可拆多條**（動了多個功能）；**多個 commit 也可合成一條**（同一功能的連續改動）。
- `分類`（性質）與 `feature`（跨來源對齊鍵 `模組/功能`）互補：前者讓 wiki 分流知識性質，後者讓 wiki 對齊同一功能。canonical feature 名由 wiki 端治理，你只給提示。
- 「程式行為」只描述**可觀察行為**；「關聯既有知識」只客觀指出觸及哪個功能，**不要**寫「這推翻了 X」「定案為 Y」（那是 wiki 端 /curate 的對賬職責）。

## 不做（明確邊界）

- **不跑 `/curate`**、不碰 wiki 策展、不寫 `<paths.state>/` 的 manifest / features.json（全歸 `/curate`）。
- 你只往 `CODEREVIEW_OUT` 寫檔；拆解模式才另複製一份到 `AGENT_RAW`，且**不在外部 repo 做任何 git 操作**。
- **不回寫 WePages**（避免數據污染）。
- **不設 schedule / cron**（目前手動呼叫；之後用戶決定再轉）。

## 注意事項

- collector 已依 config `collect.code_exts` / `collect.excludes` 過濾（生成碼、第三方、建置產物等）；你拿到的都是該 review 的程式檔。過濾不對就改 config，不要在本流程手動跳檔。
- 批次大區間（如補 3 個月）：**逐月順跑**，靠「(a) 檔存在即跳過」冪等，中斷後重跑會自動接續。
- 一天一檔；若一次 catch up 跨多日，會產生多個 dated 檔（符合「一天一檔」，wiki 端對賬才對得準）。
- 寫 (b) 前先 `ls CODEREVIEW_OUT`（本 repo 目錄，不存在可建）；導入前 `ls AGENT_RAW`（未設/不存在則略過導入）。
- 路徑全部來自 `.agent/config.json`（Step 0，皆為 repo 相對路徑），跨成員/機器改 config 即可，勿在本檔寫死。
