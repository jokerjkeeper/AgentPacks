# AgentPacks

可安裝到任何專案的 **Claude Code agent 能力包**。每個 pack 是一組 `.claude/` commands / skills、`.agent/` 規格與腳本，外加安裝參數。

安裝方式：**Claude Launcher → 「Agent 套件」分頁**（勾選 pack → 選目標專案 → 填參數 → 安裝 / 更新）。
Launcher 預設從本 GitHub repo 取得最新 pack，並內建一份快照供離線使用。

## Packs

| id | 名稱 | 內容 |
|----|------|------|
| `wiki` | 程式 Wiki | `/cr-daily` 每日 code review → `/curate` 策展 → `wiki/` 知識庫；`/stopic` `/ask` `/resolve` `/cr-planfix`；每日前置規劃器 |
| `codegraph` | CodeGraph 索引 | `.codegraph/.gitignore`、CLAUDE.md 使用說明、可選 `codegraph init` |

## 目錄結構

```
agentpacks.json          repo 描述（schema 版本）
packs/<id>/
  pack.json              pack 清單：參數、預設組合、檔案與安裝模式、安裝後步驟
  files/                 依目標專案相對路徑擺放的檔案
  blocks/                以標記區塊插入既有檔案的片段（CLAUDE.md、.gitignore）
```

## pack.json

| 欄位 | 說明 |
|------|------|
| `id` / `name` / `version` / `description` | 基本資訊；`version` 採 semver，改內容就要升版 |
| `requires_tools[]` | `{ name, cmd, hint, optional }`：安裝前檢查的外部工具（`cmd` 結束碼 0 即通過） |
| `params[]` | `{ key, label, type: string\|list, default, help }`；`default` 可用 `{{dirname}}`（目標資料夾名） |
| `presets{}` | `{ <id>: { label, values: { key: value } } }`：依專案類型帶入參數預設值 |
| `files[]` | `{ path, source?, mode, template? }`，見下表；`source` 相對 pack 目錄，預設 `files/<path>` |
| `post_install[]` | `{ id, label, check, skip_if_exists, run: [argv…], default }`：安裝後可勾選執行的指令 |

### 檔案模式

| mode | 行為 |
|------|------|
| `managed` | pack 擁有。更新時：目標檔未被手改（hash 與 lock 相同）→ 覆蓋；被手改過 → 另存 `<檔名>.pack-new`，不覆蓋 |
| `seed` | 只在目標不存在時建立，之後歸專案所有（config、modules.json、狀態檔、wiki/INDEX.md） |
| `block` | 以 `<!-- agentpacks:<id>:start/end -->`（.md）或 `# agentpacks:<id>:start/end`（其他）標記區塊插入或替換，不動區塊外內容 |
| `dir` | 只建立空目錄（不需來源檔；不要用 `.gitkeep`，electron-builder 打包時會濾掉） |

### 模板

`template: true` 的檔案做 `{{key}}` 替換：`.json` 檔內的值以 JSON 輸出（字串含引號、清單為陣列），其他檔案字串原樣、清單輸出 JSON。可用變數：所有 `params` 與 `{{target}}`、`{{dirname}}`。

## 安裝紀錄

安裝後目標專案會有 `.claude/agent-packs.lock.json`，記錄每個 pack 的版本、來源 commit、參數與 managed 檔 hash；Launcher 據此判斷「可更新」與「被手改」。

## 開發流程

1. 修改 `packs/<id>/` 內容並升 `version`。
2. Launcher 來源切到「本機路徑」指向本 repo，可即時測試安裝。
3. push 到 GitHub 後，所有 Launcher 按「檢查更新」即取得新版。
4. 發佈新版 Launcher 前，在 ClaudeCodeEg 跑 `scripts/sync-packs` 更新內建快照。
