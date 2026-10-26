---
name: export-math
description: 把本次 session 用到的數學模型與公式整理匯出到 .agent/math.md。當用戶呼叫 /export-math 時觸發。
version: 1.0.0
origin: agentpacks/doc-tools
---

# Export Math Models

將本次 session 中使用的數學模型、公式匯出到 `.agent/math.md`。

## 執行步驟

1. 回顧本次 session 的對話內容，識別所有涉及的：
   - 數學公式與方程式
   - 統計模型
   - 演算法的數學描述
   - 損失函數、優化目標
   - 資料轉換公式
   - 任何以數學形式表達的邏輯

2. 如果 `.agent/math.md` 已存在，先讀取現有內容，避免重複寫入

3. 將識別到的數學內容整理並寫入 `.agent/math.md`，格式如下：

```markdown
# 數學模型記錄
## 最後更新: YYYY-MM-DD

### <模型/公式名稱>
- **用途**: <描述這個公式的用途>
- **公式**: <LaTeX 或純文字格式的公式>
- **參數說明**:
  - `param1`: <說明>
  - `param2`: <說明>
- **適用場景**: <何時使用>
```

4. 完成後告知用戶已匯出的數學模型數量及摘要
