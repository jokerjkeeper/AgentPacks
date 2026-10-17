# Git 本專案現況（分支 / push）

> **專案自有檔**：AgentPacks git-spec 只在不存在時建立一次，之後由本專案直接修改，更新套件不會覆蓋。
> 通用規則（commit 格式、type、模組 tag、分組、.meta、不自動 pull、cc 不 push）見 `.agent/spec/git.md`；
> 本檔只記**本專案的分支策略與例外**，與 `git.md` 衝突時以本檔為準。

## 分支策略（擇一，刪掉不用的那段）

### A. 工單分支 + 測試 gate（預設）

```
develop ──┬─ task/<id>-<slug>   (cc 在此 commit)
          └─ …
   人工 push task 分支 → 測試人 pull 該分支測試 → 確認 → merge 回 develop → push develop
```

- cc 從 `develop` 切本地分支 `task/<id>-<slug>`，於分支上 commit。
- 批量：cc 可一次處理 N 筆工單，逐筆切分支、各自拆 commit，互不污染。
- task 分支與 develop 的 push、merge 皆由人操作。
- 禁止直接在 `main` / `master` 開發或 push；非預期分支要警告。

### B. 只有 main

- 本專案目前**只有 `main`，直接在 `main` commit**，不開 `develop` 或工單分支。
- cc 每次 commit 前先讓用戶知道（要提交哪些檔、訊息怎麼寫）。
- cc 不 push `main`。

## 本專案例外

- （例：哪些目錄 / 檔案類型不 commit、特定模組的額外規則…）
