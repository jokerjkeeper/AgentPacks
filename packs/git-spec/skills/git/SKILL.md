---
name: git
description: 「git commit 本次內容」——從雜亂工作區只把「某個功能」乾淨地 commit。辨識檔案(純/混/build-config)、選擇性 stage(混檔只挑本功能那幾行)、依類型拆筆、review 在 commit 之前、push 留給用戶。當用戶說「git commit 本次內容 / 幫我 commit 這個功能 / 把 XX 提交」時觸發。
version: 2.0.0
origin: agentpacks/git-spec
---

# Git Commit 本次內容 Skill

從一個**同時混了多個功能 + 一堆未追蹤檔**的雜亂工作區，只把「本次功能」乾淨地 commit，**不污染**也**不誤刪**其他人/其他工作的改動。

> 訊息格式、type 與模組詞表以 `.agent/spec/git.md` 為準；分支策略與例外以 `.agent/spec/git-project.md` 為準（**commit 前兩份都先讀**）。

## 核心原則（務必遵守）

1. **review 在 commit 之前**：選好檔 → 把「要提交哪些檔、每筆的訊息」列給用戶看 → 用戶確認才 `git commit`。**不要 commit 後再給看**。
2. **隔離本功能**：工作區常混著別的進行中改動（別人正在加的套件、暫存檔、未追蹤目錄）。只 stage 本功能，其餘原封不動留在工作區。
3. **混檔只 stage 本功能那幾行**，不整檔 commit。
4. **build-config 不 commit**（工具 / 編輯器自動改的暫時狀態，例：Unity 的 `packages-lock.json`、`ProjectSettings/*`、`UniversalRenderPipelineGlobalSettings.asset`；其他專案依 `git-project.md` 的例外），除非用戶明說要。
5. **一筆 commit 一個 type**：同一批改動同時是「新增」和「修正」就拆成多筆（`.agent/spec/git.md` §1、§4）。
6. **只 commit，不 push**。push 留給用戶。

## 流程

### 1. 辨識本功能的檔
```
git status --short
git diff --stat -- <疑似本功能的檔...>
```
逐檔 `git diff -- <檔>` 確認，分三類：
- **純功能檔**：整檔只有本功能改動 → 整檔 stage。
- **混檔**：同檔含本功能 + 別功能 / 別人加的內容 → 只能挑本功能那幾行。
- **build-config**：見核心原則 4 → **不 commit**。

⚠️ 別漏「編譯依賴」：新檔的 `.meta`、新加的 enum/常數、被引用的新型別/新檔。漏了 commit 出來會編不過。Unity 的 `.meta` 必須與資產配對提交。

### 2. 提交前檢查
```
git fetch                      # 只 fetch，不自動 pull
git status --short --branch    # 落後遠端就提醒用戶
```
確認目前分支符合 `.agent/spec/git-project.md` 的策略（例：工單分支 `task/<id>-<slug>`，或只有 `main`）；不符合要先問用戶。

### 3. 選擇性 stage 只放本功能
- **純功能檔**：逐檔列出 `git add <檔> ...`（**勿 `git add .`**，會把整個亂工作區都加進去）。
- **混檔**：用「**備份 → 把檔改成只剩本功能 → `git add` → 從備份還原工作區**」最穩（避免手刻 patch 的 tab/空白與行數問題）：
  ```
  cp <檔> <暫存區>/<檔>.bak                    # 1. 備份(含別功能)
  # 2. 用 Edit 把「別功能那幾行」從工作區檔移除，只留本功能
  git add <檔>                                # 3. stage「只剩本功能」的版本
  cp <暫存區>/<檔>.bak <檔>                    # 4. 還原工作區(別功能回來、未 stage)
  ```
  > Edit 若 old_string 不匹配會報錯＝安全網(白做就不會錯 commit)。git add 吃的是「當下檔內容」的快照，所以 add 後再還原工作區，index 仍是只剩本功能的版本。
  > 另一個做法：取 `git show HEAD:<檔>` 的內容、只套用本功能的改動，用 `git hash-object -w` + `git update-index --cacheinfo` 直接放進 index，完全不動工作區。
- **build-config**：不碰。

### 4. ★ 停下來讓用戶 review（commit 之前）★
```
git diff --cached --stat            # 會進 commit 的全部檔一覽
git diff --cached -- <檔>           # 逐檔看實際會 commit 的內容
```
混檔的 `--cached` 只顯示已 stage 的本功能行＝實際會 commit 的，一行不多。
- 用戶要退某檔：`git restore --staged <檔>`（工作區內容不丟），改完重 `git add` 再 review。
- **等用戶明確說 OK 才往下做 commit。**（用戶已明確說「提交這批改動」時視為已確認，仍要在回報裡列出每筆的內容。）

### 5. commit（用戶確認後）
訊息照 `.agent/spec/git.md`：`[type][模組] 標題` + 選填內文（工單驅動時加 `工單: #<id>`）。
- 模組 tag 只能取自 `.agent/spec/modules.json`。
- **不加 `Co-Authored-By`**（`.agent/spec/git.md` §8 預設不加）。
- 多行訊息用 `git commit -F <檔>` 避免引號與編碼問題。

### 6. 驗證
`git log --oneline -<N>`（commit 在預期分支）、`git status --short`（別的改動仍在、未 commit）。

### 7. push 留給用戶
告訴用戶可以 `git push`。**若被拒**（期間有人上傳）：
```
git stash -u                        # 收起未提交亂改+未追蹤檔
git pull --rebase                   # 衝突只可能在本功能同檔同段，面極小；解完 git rebase --continue
git push
git stash pop                       # 還原工作區
```

## 不要做
- ❌ `git add .` / `git add -A`（會把整個雜亂工作區加進去）
- ❌ 整檔 commit 混檔（會夾帶別功能，甚至因依賴未追蹤檔而編不過）
- ❌ commit build-config
- ❌ 自己 push（push 是用戶的）
- ❌ commit 後才 review
- ❌ 違反 `git-project.md` 的分支策略（例：只有 main 的專案自行開 `develop` / 工單分支）
