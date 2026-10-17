---
name: cr-planfix
description: >-
  把 aispec/codereview/（config paths.docs_codereview）的每日 code review 裡所有「🐛 潛在 bug / 風險」條目
  抽出來，依系統模塊（見 .agent/spec/modules.json）分類，
  輸出成可勾選的待修清單到 aispec/codereview/planfix/。
  當用戶呼叫 /cr-planfix（可選帶日期 2026-05-14 或區間 2026-05-01..2026-05-31）時觸發。
  純彙整既有 review，不重新 review code、不碰 git、不回寫 WePages。
version: 1.0.0
origin: project
---

# cr-planfix — Code Review 風險彙整成待修清單

`cr-daily` 每天產出 `aispec/codereview/YYYY-MM-DD.md` 工程回顧，裡面每個 commit 區段都有一行
`🐛 潛在 bug / 風險：…`。本 skill 把這些風險**跨檔抽出來、依系統模塊分類**，變成一份
可以拿著逐項修的 planfix 清單。

| 輸入 | 處理 | 輸出 |
|------|------|------|
| `aispec/codereview/*.md` 的 `🐛 風險：` 行 | 抽取 → 分類 → 排序 | `aispec/codereview/planfix/<模塊>.md` + `README.md` 索引 |

> 定位：這是**檢視器 / 彙整器**，讀的是現成 review 結論，不重看 code、不分析 diff。
> 要產生 review 本身請用 `/cr-daily`。

## 路徑常數

皆為 repo 相對路徑，由腳本從 `.agent/config.json` 讀取（不硬編）：

```
SRC     = <paths.docs_codereview>            # aispec/codereview，來源日報
OUT     = <paths.docs_codereview>/planfix    # 輸出
SCRIPT  = .agent/capabilities/skills/cr-planfix/extract_risks.py
MODULES = <paths.modules_spec>               # .agent/spec/modules.json，模塊詞表
```

## 執行方式

主流程就是跑腳本，**不需要逐檔自己讀**（腳本是確定性解析，比手抽快又不漏）：

```bash
# 全部日報
python .agent/capabilities/skills/cr-planfix/extract_risks.py

# 只處理某天
python .agent/capabilities/skills/cr-planfix/extract_risks.py --date 2026-05-14

# 處理某區間
python .agent/capabilities/skills/cr-planfix/extract_risks.py --date 2026-05-01..2026-05-31
```

腳本會**先清掉上一輪自己產生的檔案**再重寫，可安全重跑（idempotent）。
跑完把終端輸出的「各模塊項數」摘要回報給用戶即可。

## 解析規則（腳本內部，給維護者參考）

每個 `### <commit> [標籤] <標題>` 區段抽一條：

1. 抓區段的 `- 檔案：` 路徑、`- 🐛 …風險：` 內文（含換行續行）。
2. 風險內文是「無」「低」之類無實質內容 → **略過**。
3. 模塊分類優先序：
   `檔案路徑關鍵字` → `標題 [標籤]/關鍵字` → `風險內文裡的檔名` → `其他/系統`。
4. 依措辭粗分嚴重度（高 / 中 / 低）：含「重要 / NRE / 洩漏 / 卡死 / race / 倒置 / 漏抽」等 → 高。

## 輸出格式

`OUT/<模塊>.md`，依嚴重度分段、每段內日期新到舊：

```markdown
## 嚴重度：高
- [ ] **2026-10-02** `b077f30` 技能冷卻結束後未重置施放旗標
  - 風險：（格式範例）冷卻歸零時…
  - 檔案：src/Battle/SkillSystem.cs:441-453
```

`OUT/README.md` 是索引表（模塊 / 項數 / 連結，依項數排序）。
勾掉 `- [ ]` 代表該風險已處理。

## 擴充模塊

模塊定義的權威來源是 `.agent/spec/modules.json`（與 git 模組 tag、curate feature 同源），
陣列順序即優先序。新系統出現時**只改 modules.json**；腳本頂端的 `_FALLBACK_MODULES`
只在 config 讀取失敗時使用。落到「其他 / 系統」太多時，就是該把該群抽成新模塊的訊號。

## 邊界

- 不重新 review、不讀原始碼、不跑 git / 不碰 WePages。
- 只認 `🐛` 標記的風險行；review 裡的 `⚡ 效能` / `🧹 品質` 不納入。
- 來源日報的 `🐛` 格式若改版，需同步更新腳本的 `BUG_RE`。
