---
name: export-arch-html
description: 把技術架構文檔 arch.md 轉成美觀的 HTML 頁面供內部瀏覽。當用戶呼叫 /export-arch-html 時觸發。
version: 1.0.0
origin: agentpacks/doc-tools
---

# Export Architecture HTML - 技術架構文檔轉 HTML

將項目的技術架構文檔（`arch.md`）轉換為美觀的 HTML 頁面，供內部成員透過瀏覽器查看。

## 執行步驟

1. **檢查來源檔案**
   - 確認 `arch.md` 是否存在於專案根目錄或 `.agent/` 目錄
   - 若不存在，提示用戶先執行 `/architecture` 生成架構文檔，或手動建立 `arch.md`

2. **讀取架構文檔**
   - 讀取 `arch.md` 的完整內容
   - 解析 Markdown 結構（標題、表格、程式碼區塊、列表、Mermaid 圖表等）

3. **生成 HTML 轉換腳本**
   - 生成或更新 `src/gen_arch_html.py` 腳本
   - 使用 `markdown` 庫進行 Markdown → HTML 轉換
   - 內嵌 CSS 樣式，確保單一 HTML 檔案即可獨立瀏覽
   - 風格：簡約技術文檔風，深色側邊導航 + 淺色內容區

4. **HTML 頁面規範**
   - 響應式設計，支援桌面與平板瀏覽
   - 自動生成側邊目錄導航（根據 h1/h2/h3 標題）
   - 程式碼區塊語法高亮（使用 highlight.js CDN 或內嵌）
   - 表格自動加上邊框與斑馬紋樣式
   - 頁首顯示專案名稱與生成時間
   - 頁尾顯示「本文檔由 Claude Code 自動生成」

5. **執行生成**
   - 運行 `python src/gen_arch_html.py` 生成 HTML 文件
   - 輸出路徑預設為 `docs/architecture.html`
   - 告知用戶輸出路徑，可直接用瀏覽器開啟

6. **後續調整**
   - 詢問用戶是否需要調整樣式或內容
   - 支持重新生成

## 技術規範

- 使用 `markdown` 庫（含 `tables`、`fenced_code`、`toc` 擴展）
- 單一 HTML 檔案，CSS 內嵌，無需額外資源即可瀏覽
- 確保依賴已安裝：`pip install markdown`
- 編碼：UTF-8
- 配色方案：
  - 側邊導航背景：#1e293b（深藍灰）
  - 內容區背景：#ffffff
  - 標題色：#1e40af
  - 程式碼背景：#f1f5f9
  - 表格標題行：#e2e8f0

## 參數

- `$ARGUMENTS`：來源檔案路徑（可選，預設為 `arch.md`）
