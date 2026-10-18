# AgentPacks

可安裝到任何專案的 **agent 能力包**，支援 Claude Code / Codex / OpenCode。每個 pack 是一組 skill、`.agent/` 規範與腳本，外加安裝參數。
skill 與規範只在 `.agent/` 維護一份（canonical），各家 agent 目錄只放自動產生的薄入口（見「多 agent 結構」）。

安裝方式：**Claude Launcher → 「Agent 套件」分頁**（勾選 pack → 選目標專案 → 填參數 → 安裝 / 更新）。
Launcher 預設從本 GitHub repo 取得最新 pack，並內建一份快照供離線使用。

## Packs

| id | 名稱 | 內容 |
|----|------|------|
| `agent-env` | Agent 環境 | **基礎套件**：`AGENTS.md` 索引（seed）、`CLAUDE.md` 的 `@AGENTS.md` 區塊、`.agent/agent-env.json`（勾選的 agent）、`.agent/layout.json`（seed，頂層非程式目錄約定，見 `spec/layout.md`）、`.agent/spec/`、`.agent/capabilities/skills/`、`sync_agent_skills.py`。其他 pack 都依賴它 |
| `wiki` | 程式 Wiki | `cr-daily` 每日 code review → `curate` 策展 → `wiki/` 知識庫；`stopic` `ask` `resolve` `cr-planfix` skill；每日前置規劃器 |
| `codegraph` | CodeGraph 索引 | `.codegraph/.gitignore`、AGENTS.md 使用說明、可選 `codegraph init` |
| `git-spec` | Git 提交規範 | `.agent/spec/git.md`（通用：`[type][模組]` 格式、分組規則）、`git-project.md`（seed，專案自有的分支策略）、`modules.json`（seed）、`git` skill |
| `taskhub` | TaskHub 工單（項目綁定） | `.claude/api.conf` + `.agent/spec/wepages.md`，綁定整個 TaskHub 項目 |
| `wepages` | WePages 工單（task 綁定） | `.claude/api.conf` + `.agent/spec/wepages.md`，綁定 `WEPAGES_TASK_IDS` 白名單；與 taskhub 寫同一組檔案，擇一 |
| `unity-cli` | Unity CLI / Editor MCP | `unity pipeline install`（`com.unity.pipeline`）、CLAUDE.md 使用說明、`unity-inspector` 唯讀 subagent；可選在 `.mcp.json` 固定本專案的 `unity-editor-mcp`（Claude Code 專屬） |

## 多 agent 結構

```
AGENTS.md                         索引；agentpacks:index 區塊由 launcher 依 lock 重生
CLAUDE.md                         agent-env 區塊：@AGENTS.md
.agent/agent-env.json             { "agents": ["claude","codex","opencode"] }
.agent/spec/*                     規範本體（pack.json specs[]）
.agent/capabilities/skills/<n>/   skill 本體（pack.json skills[]）
.claude/skills/<n>/SKILL.md       Claude Code 入口
.agents/skills/<n>/SKILL.md       Codex 入口（OpenAI 官方位置；注意是複數 .agents）
.opencode/skills/<n>/SKILL.md     只勾 OpenCode 時才產生（OpenCode 相容讀前兩者，避免重複）
```

入口 = canonical 的 frontmatter + 一句「完整閱讀並依 canonical 執行」。launcher 安裝時產生；沒有 launcher 時跑 `python .agent/scripts/sync_agent_skills.py`（`--check` 檢查漂移），兩者輸出逐字一致。

## 目錄結構

```
agentpacks.json          repo 描述（schema 版本）
packs/<id>/
  pack.json              pack 清單：參數、預設組合、檔案與安裝模式、安裝後步驟
  files/                 依目標專案相對路徑擺放的檔案
  blocks/                以標記區塊插入既有檔案的片段（AGENTS.md、CLAUDE.md、.gitignore）
  skills/<name>/         skill 本體（SKILL.md 必須有 YAML frontmatter），裝到 .agent/capabilities/skills/<name>/
  specs/<file>           規範，裝到 .agent/spec/<file>
```

## pack.json

| 欄位 | 說明 |
|------|------|
| `schema` | `1`（舊格式）或 `2`（支援 `requires_packs` / `skills` / `specs` / `multi` 參數） |
| `id` / `name` / `version` / `description` | 基本資訊；`version` 採 semver，改內容就要升版 |
| `requires_packs[]` | 相依 pack id；目標未安裝且本批次沒勾時拒絕安裝（launcher 勾選時會自動帶上） |
| `legacy[]` | 舊版放檔位置（結尾 `/` 表示目錄），例：wiki 的 `.claude/skills/cr-daily/`、`.claude/commands/curate.md`。勾「接管舊結構」安裝時，存在且不屬於任何 pack 的項目會先備份到 `.agent/legacy-backup/<時間>/` |
| `skills[]` | skill 名稱，來源 `skills/<name>/`；裝成 managed 檔，並依目標的 agent-env 產生各家入口 |
| `specs[]` | `{ file, title, load: auto\|ondemand, when, mode?, template? }`：來源 `specs/<file>`，`mode` 預設 managed；寫入 AGENTS.md 索引表，`auto` 另加 `@` 匯入行 |
| `requires_tools[]` | `{ name, cmd, hint, optional }`：安裝前檢查的外部工具（`cmd` 結束碼 0 即通過） |
| `params[]` | `{ key, label, type: string\|list\|multi, options?, default, help, required, secret }`（`multi` 為多選，`options: [{ value, label }]`）；`default` 可用 `{{dirname}}`（目標資料夾名）；`required: false` 允許留空；`secret: true` 以密碼框輸入且不寫入 lock（token 用）；`detect: code_roots\|code_exts` 由 launcher 掃描目標 repo 自動帶入（依 `.agent/layout.json`，見下方「程式碼偵測」） |
| `presets{}` | `{ <id>: { label, values: { key: value } } }`：依專案類型帶入參數預設值 |
| `files[]` | `{ path, source?, mode, template?, sync? }`，見下表；`source` 相對 pack 目錄，預設 `files/<path>`；`sync`（僅 seed 的 .json 模板）列出重新安裝時要以新參數覆寫的 JSON 路徑（例 `paths.code_roots`），其餘欄位保留專案手改 |
| `post_install[]` | `{ id, label, check, skip_if_exists, run: [argv…], default }`：安裝後可勾選執行的指令 |

### 檔案模式

| mode | 行為 |
|------|------|
| `managed` | pack 擁有。更新時：目標檔未被手改（hash 與 lock 相同）→ 覆蓋；被手改過 → 另存 `<檔名>.pack-new`，不覆蓋 |
| `seed` | 只在目標不存在時建立，之後歸專案所有（config、modules.json、狀態檔、wiki/INDEX.md）；有 `sync` 時重新安裝只同步那幾個 JSON 欄位 |
| `block` | 以 `<!-- agentpacks:<id>:start/end -->`（.md）或 `# agentpacks:<id>:start/end`（其他）標記區塊插入或替換，不動區塊外內容；新版不再宣告的區塊會被移除 |
| `dir` | 只建立空目錄（不需來源檔；不要用 `.gitkeep`，electron-builder 打包時會濾掉） |

### 模板

`template: true` 的檔案做 `{{key}}` 替換：`.json` 檔內的值以 JSON 輸出（字串含引號、清單為陣列），其他檔案字串原樣、清單輸出 JSON。可用變數：所有 `params` 與 `{{target}}`、`{{dirname}}`。

## 程式碼偵測（code_roots）

各專案的程式不一定在 `src/`，也常是多語言混合。agent-env 在目標專案放一份 `.agent/layout.json`（seed，可依專案增減）：

- `reserved_dirs`：頂層**非程式**目錄（`.*` 代表所有點開頭目錄，另有 `design` `aispec` `docs` `temp` `raw` `wiki` `outputs` `spec`、建置產物等）
- `source_exts`：視為程式碼的副檔名

launcher 選到有 `detect` 參數的 pack（wiki）時，以 `git ls-files`（非 git repo 則走訪目錄）掃描目標，扣掉 reserved 與 `excludes` 後，**含程式檔的頂層目錄 = `code_roots`、出現的程式副檔名 = `code_exts`**。新安裝自動帶入；已安裝則在表單顯示偵測結果與差異（目錄不存在、漏收的目錄 / 副檔名），按「套用偵測結果」再重新安裝即可同步 `.agent/config.json`。

## 安裝紀錄

安裝後目標專案會有 `.agent/agent-packs.lock.json`（舊版在 `.claude/`，升級時自動搬移），記錄每個 pack 的版本、來源 commit、參數、managed 檔與入口 hash、skills / specs / blocks；Launcher 據此判斷「可更新」與「被手改」。
新版已移除的 managed 檔：本機沒改過就刪除，改過則保留並提示。

## 開發流程

1. 修改 `packs/<id>/` 內容並升 `version`。
2. Launcher 來源切到「本機路徑」指向本 repo，可即時測試安裝。
3. push 到 GitHub 後，所有 Launcher 按「檢查更新」即取得新版。
4. 發佈新版 Launcher 前，在 ClaudeCodeEg 跑 `scripts/sync-packs` 更新內建快照。
