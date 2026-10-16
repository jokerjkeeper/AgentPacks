## Unity Editor MCP（AgentPacks / unity-cli）

本專案可透過 Unity CLI 的 `unity-editor-mcp`（`mcp__unity-editor-mcp__*`，約 140 個工具）直接讀寫開著的 Unity Editor。

**前提**（工具呼叫失敗時先逐項檢查）：

- Unity Editor 已開啟本專案；CLI 經 `127.0.0.1:7800` 連線 Editor。
- 專案已安裝 `com.unity.pipeline`：`unity pipeline list` 的 `Pipeline` 欄為 `true`、`Server Reachable` 為 `true`。沒有就跑 `unity pipeline install --project-path .`，再切回 Editor 讓它解析套件。
- 同時開多個 Editor 時，全域 MCP 可能連到別的專案；用 `editor_status` 確認專案路徑，必要時在 `.mcp.json` 改用 `unity mcp --project-path <本專案>`。
- 工具列為 deferred 時，先用 tool search 載入（例：`select:mcp__unity-editor-mcp__list_open_scenes`）。

**使用原則**：

- 查場景、物件、元件、Console、設定：優先用 MCP（`list_open_scenes`、`find_gameobjects`、`get_component_properties`、`get_console_logs`…），不要去解析 `.unity` / `.prefab` YAML。
- `get_scene_hierarchy`、大量 `find_assets` 等輸出很大的讀取，交給 **`unity-inspector`** subagent 執行並回摘要，避免塞爆主 context。
- 寫入類操作（`set_*`、`create_*`、`delete_*`、`build`、`bake_*`、`package_add/remove`）會直接改動 Editor 狀態；先說明要改什麼，工具有 `dry_run` 參數時先 dry run。改完記得 `save_scene` / `save_all`。
- 改完 C# 用 `recompile` + `get_console_logs` 確認無編譯錯誤；跑測試用 `run_tests` / `test_status`。
- Shell 備援：`unity command` 列出 Editor 指令；`unity --help` 看 CLI 全部功能。
