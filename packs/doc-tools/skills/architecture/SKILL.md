---
name: architecture
description: 掃描專案結構與模組依賴，輸出 Excalidraw 架構圖 .agent/architecture.excalidraw。當用戶呼叫 /architecture、說「畫架構圖」時觸發。
version: 1.0.0
origin: agentpacks/doc-tools
---

# Architecture Diagram

分析當前專案結構，同時輸出 Excalidraw 架構圖與 Markdown 架構文檔。

## 執行步驟

1. 掃描專案目錄結構，識別：
   - 主要模組與服務
   - 資料庫相關文件
   - API 端點
   - 外部服務整合
   - 前端 / 後端分層
   - 設定檔與建置流程

2. 分析模組間的依賴與資料流關係：
   - import / require 依賴
   - API 調用關係
   - 資料庫存取路徑
   - 事件或消息傳遞

3. **輸出一：Excalidraw 架構圖**

   使用以下節點類型映射生成 Excalidraw JSON：

   | 概念 | Excalidraw 圖形 | 顏色 |
   |------|-----------------|------|
   | 模組 / 服務 | 矩形 (rectangle) | #a5d8ff |
   | 資料庫 | 圓柱體 (ellipse) | #ffd8a8 |
   | API 端點 | 圓角矩形 (rectangle, roundness) | #b2f2bb |
   | 外部服務 | 菱形 (diamond) | #ffec99 |
   | 資料流 | 箭頭 (arrow) | #868e96 |
   | 使用者 | 橢圓 (ellipse) | #eebefa |

   保存到 `.agent/architecture.excalidraw`

4. **輸出二：Markdown 架構文檔（`arch.md`）**

   在專案根目錄生成 `arch.md`，內容包含：

   ```markdown
   # 專案架構文檔
   ## 最後更新: YYYY-MM-DD

   ### 專案概述
   - 專案名稱、類型、技術棧摘要

   ### 目錄結構
   - 主要目錄與其用途（樹狀結構）

   ### 核心模組
   - 各模組名稱、職責、所在路徑
   - 模組間的依賴關係

   ### 資料流
   - 主要資料流路徑的文字描述
   - 關鍵流程（如啟動流程、請求處理流程）

   ### 外部依賴
   - 第三方套件 / 服務 / SDK

   ### 架構圖
   - 文字版架構示意（ASCII 或 Mermaid）
   - 提示可用 Excalidraw 開啟 `.agent/architecture.excalidraw` 查看完整圖形
   ```

5. 輸出架構摘要，包含：
   - 識別到的模組數量
   - 主要的資料流路徑
   - 告知用戶兩個輸出檔案的路徑：
     - `.agent/architecture.excalidraw` — 用 Excalidraw 開啟查看圖形
     - `arch.md` — Markdown 格式架構文檔，可搭配 `/export-arch-html` 轉為 HTML
