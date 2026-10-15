# Git 規格（agent 依據）

> 由 AgentPacks wiki pack 產生的**起始版本**（pack 更新不會覆蓋本檔，請依專案調整）。
> 重點只有一條與 wiki 綁定：commit 的**模組 tag 取自 `.agent/spec/modules.json`**，讓 git tag ↔ wiki 系統頁 ↔ cr-planfix 分類同源。
> 若專案已採用其他格式（如 Conventional Commits `type(scope): …`），把 scope 對齊 modules.json 的 `name` / `key` 即可。

## 1. commit message 格式

```
[type][模組][模組…] 標題

內文（選填，與標題空一行；條列改了什麼、怎麼驗證）
工單: #<id>
```

- 框框全部連寫，最後一個框框與標題之間空一個半形空格。
- 標題不含框框，最少 3 字，上限 50 字，結尾不加句點。
- 一筆改動同時符合多個 type → 拆成多筆 commit；動到多個系統 → 掛多個模組 tag。

範例：
```
[新增][戰鬥] 技能加入冷卻顯示
[修正][戰鬥][背包] 技能消耗道具時數量未扣除
[組態][系統] 套用 agent 規範與知識庫流程
```

## 2. type 詞表（第一框・封閉）

`新增`、`合併`、`修改`、`修正`、`刪除`、`重構`、`效能`、`測試`、`退版`、`註解`、`組態`、`文件`。

## 3. 模組 tag（後續框・受控）

- **只能取自 `.agent/spec/modules.json` 的 `name`**。
- 相同系統不細分；與 wiki feature 前綴 / `system` / cr-planfix 分類同源。
- 真的落不進任何模組 → 先用 `[系統]`，並回報建議新增到 `modules.json`。

## 4. 分支與推送

- 不直接在 main 開發；`feature/<name>`、`fix/<name>`。
- agent 預設只 commit、不 push；禁止 force push。
