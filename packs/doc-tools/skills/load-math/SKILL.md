---
name: load-math
description: 讀取 .agent/math.md 的數學模型作為當前對話上下文。當用戶呼叫 /load-math 時觸發。
version: 1.0.0
origin: agentpacks/doc-tools
---

# Load Math Models

讀取 `.agent/math.md` 中的數學模型作為當前對話的上下文。

## 執行步驟

1. 讀取 `.agent/math.md` 文件
2. 如果文件不存在，告知用戶尚未有任何數學模型記錄，建議先使用 `/export-math` 匯出
3. 如果文件存在，解析內容並向用戶摘要：
   - 記錄中包含的所有數學模型/公式列表
   - 每個模型的用途簡述
   - 最後更新時間
4. 告知用戶這些數學模型已載入為上下文，後續對話可以直接引用這些模型
5. 詢問用戶是否要針對某個特定模型進行操作（修改、擴展、應用等）
