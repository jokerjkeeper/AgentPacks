## CodeGraph（AgentPacks / codegraph）

本 repo 由 CodeGraph 建立索引（`.codegraph/`）。需要理解或定位程式碼時，**先用 CodeGraph，再 grep / 讀檔**：

- **MCP 工具**（可用時）：`codegraph_explore` 一次回傳相關符號的原始碼與呼叫路徑；若列為 deferred，先用 tool search 載入。
- **Shell**（一定可用）：`codegraph explore "<符號或問題>"`。
- 索引由背景 daemon 自動更新；疑似過期時跑 `codegraph sync`。
- 本機未安裝 CodeGraph CLI 或沒有 `.codegraph/codegraph.db` 時跳過，改用一般搜尋；是否建立索引由使用者決定（AgentPacks「Agent 套件」或 `/code-intel`）。
