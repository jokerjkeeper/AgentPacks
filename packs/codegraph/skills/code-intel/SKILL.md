---
name: code-intel
description: 初始化程式碼智能工具：安裝 / 設定 CodeGraph（及 C# 專案的 SharpLens）CLI 與 MCP，建立索引。當用戶呼叫 /code-intel、說「建立 codegraph 索引 / 設定程式碼智能」時觸發。
version: 1.0.0
origin: agentpacks/codegraph
---

# Code Intel Init — 初始化 CodeGraph / SharpLens 程式碼智能工具

在**當前項目目錄**啓用程式碼智能索引工具。CodeGraph 適用任何語言(建 `.codegraph/` 索引);SharpLens 專用於 C# / .NET / Unity 項目(Roslyn 語意分析,靠 `.mcp.json` 綁定 `.sln`)。

---

## 步驟 0:確認當前項目目錄

- 執行 `pwd`(或讀取 cwd)確認要初始化的項目根目錄,後續所有操作都以此為基準,記為 `<PROJECT>`。
- 若當前目錄明顯不是項目根(例如在子資料夾),先詢問用戶要初始化哪個目錄。

## 步驟 1:讓用戶選擇要安裝啓用的工具

使用 **AskUserQuestion** 工具,單選,提供三個選項:

- **CodeGraph + SharpLens** — 兩者都啓用(C# / Unity 項目建議)
- **只裝 CodeGraph** — 通用程式碼圖譜,適用任何語言
- **只裝 SharpLens** — 僅 C# / .NET Roslyn 語意分析

依用戶選擇,執行下方對應區塊。**未被選中的工具跳過。**

---

## 區塊 A:啓用 CodeGraph

1. **確認 CLI**:執行 `codegraph --version`。
   - 若找不到指令 → 提示用戶需先跑 `codegraph install`(全機一次性),然後中止本區塊。
2. **檢查是否已有索引**:確認 `<PROJECT>/.codegraph/codegraph.db` 是否存在。
   - **已存在** → 告知用戶此項目已建過索引,詢問要「增量同步(`codegraph sync`)」、「整個重建(`codegraph index`)」或「跳過」,依回答執行。
   - **不存在** → 執行 `codegraph init "<PROJECT>"` 建立首次索引(依項目大小可能需數分鐘,耐心等待完成)。
3. **驗證**:執行 `codegraph status "<PROJECT>"`,回報索引的符號數 / 檔案數。
4. 提醒:CodeGraph 的 MCP server 是全域共用的,`/mcp` 只會顯示一個 `codegraph`;它會依當前目錄自動就近解析 `.codegraph/`,**不需要**為每個項目各加一份設定。

---

## 區塊 B:啓用 SharpLens

1. **前置檢查**
   - `dotnet --version` → 需 **8.0 以上**。若沒有 dotnet 或版本過低,警告並中止本區塊。
   - `sharplens --version` 或 `which sharplens` 確認全域工具已裝。
     - 若未裝 → 執行 `dotnet tool install -g SharpLensMcp`,裝完再確認 `sharplens` 已在 PATH。
2. **尋找 solution 檔**:在 `<PROJECT>` 根目錄(必要時往下一層)用 Glob 找 `*.sln` / `*.slnx`。
   - **找不到** → 這不是 C# 項目,告知用戶無法啓用 SharpLens,結束本區塊。
   - **只有一個** → 直接採用。
   - **多個** → 用 AskUserQuestion 讓用戶選;可先用 `grep -c "^Project(" <sln>` 顯示各檔的 project 數量輔助判斷(Unity 自動生成、project 數最多的那個通常型別解析最完整)。
   - 記所選路徑為 `<SLN>`。
3. **寫入 `.mcp.json`**(項目級,放在 `<PROJECT>` 根目錄)
   - **先讀取**現有的 `<PROJECT>/.mcp.json`(若存在),在其 `mcpServers` 物件中**合併**新增 `sharplens` 鍵,**不可覆蓋**既有的其他 server 條目。
   - 若檔案不存在則新建。條目內容:
     ```json
     {
       "mcpServers": {
         "sharplens": {
           "type": "stdio",
           "command": "sharplens",
           "env": {
             "DOTNET_SOLUTION_PATH": "<SLN 的絕對路徑>"
           }
         }
       }
     }
     ```
   - **路徑注意**:JSON 字串中的 Windows 反斜線要寫成 `\\`(如 `D:\\Git\\games\\cat\\cat.sln`);路徑含空格不需額外處理。
4. **提醒重啓**:SharpLens 每個項目要各自綁自己的 `.sln`(與 CodeGraph 的自動就近解析不同)。設定完成後需**重啓 Claude Code**,並在啓動時**允許/信任該項目的 `.mcp.json` server**,`/mcp` 才會出現 `sharplens`。

---

## 步驟 2:輸出摘要

以表格回報本次執行結果:

| 工具 | 動作 | 結果 | 備註 |
|------|------|------|------|
| CodeGraph | init / sync / 跳過 | ✅ / ⚠️ / — | 符號數、檔案數 |
| SharpLens | 寫入 .mcp.json / 跳過 | ✅ / ⚠️ / — | 綁定的 .sln、是否需重啓 |

- 若有任何工具需要用戶手動動作(重啓 Claude Code、跑 `codegraph install`、切換 dotnet 版本),在摘要下方用清單明確列出「你接下來要做的事」。
