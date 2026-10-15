# 工單偵察 SOP（Ticket Recon）— wiki + codegraph 雙查詢

> 由 AgentPacks wiki pack 提供；專案專屬的查找提示請寫在第 4 步下方。
>
> 適用：任何從工單（WePages `#id`）或口語需求進場、需要先定位 code 的流程（修 bug、改功能、新功能）。

## 目的

接到工單後，**先用知識庫與程式碼索引圈定範圍，再回真實 code 核對**——而不是一拿到工單就從頭盲掃整個 repo。
兩套查詢互補，合稱**雙查詢**：

| 查詢 | 工具 | 給你什麼 |
|------|------|----------|
| **知識面** | `/stopic`（讀 `wiki/`） | 口語需求 → 模組 / 功能脈絡 / 候選 `檔案:行號`（策展知識，寫入當下為真） |
| **結構面** | codegraph（`.codegraph/` 索引） | 符號 → 現行源碼、呼叫鏈、影響範圍（隨索引更新，比 wiki 新鮮） |

## 流程

1. **抽關鍵詞**：從工單標題 / 需求描述抽出**口語關鍵詞或一句需求**（例：「技能冷卻沒重置」「排行榜」「掉寶太少」），不是工單編號。
2. **知識面：`/stopic` 圈範圍**：以關鍵詞跑 `/stopic`，載入相關主題頁，取得候選模組與 footnote 的 `檔案:行號`。
   - `wiki/` 尚無內容或讀不到 → **靜默跳過本步**，直接走第 3 步。
3. **結構面：codegraph 追符號**：repo 根有 `.codegraph/` 時，把類別 / 方法名丟給 `codegraph_explore` 或 `codegraph explore "<符號>"`。
   - 沒有 `.codegraph/` → 跳過；是否 `codegraph init` 由使用者決定（AgentPacks 的 codegraph pack 或 `/code-intel`），勿自行建立。
4. **回 code 核對（不可略）**：wiki 是「策展知識、寫入當下為真」，**不是權威**；用 `檔案:行號` 去 Read / Grep 真實檔案確認現狀。
   - （專案專屬提示：例如同一規則在多個 code root 各有實作時，兩邊都要看。）
5. 之後才進入分析 / 方案 / 實作。

## 後備：兩者皆不可用

依模組詞表 `.agent/spec/modules.json` 的 `path_hints` 推出候選目錄，再 `Grep` / `Glob` 定位，其餘流程照舊。

## 一句話

> 工單 → `/stopic` 圈模組（知識面）→ codegraph 追符號（結構面，有索引時）→ **動手前一律以真實 code 為準**。
