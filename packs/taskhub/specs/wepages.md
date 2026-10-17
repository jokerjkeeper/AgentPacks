# TaskHub 工單系統 — API 參考（項目級綁定：{{project_name}}）

本目錄綁定到 TaskHub 項目 **#{{project_id}} {{project_name}}**，所有工單操作預設限定在此項目範圍內。

> TaskHub 是自託管工單系統（自 wepages 抽核心改造），服務跑在 **{{url}}**。
> 為相容既有 `api.conf` 與 `/wp` 工具，環境變數仍沿用 `WEPAGES_` 前綴（名稱不變、指向 TaskHub）。

## 連線設定

設定檔位於 `.claude/api.conf`，包含：
- `WEPAGES_TOKEN` — API 認證 Token（TaskHub 專屬，與舊 wepages/5002 不同）
- `WEPAGES_URL` — 服務地址（TaskHub，`{{url}}`）
- `WEPAGES_PROJECT_ID` — 綁定的項目 ID（={{project_id}}）
- `WEPAGES_PROJECT_NAME` — 綁定的項目名稱（={{project_name}}）

使用前先載入：`source .claude/api.conf`

## 呼叫格式

```bash
curl -s "$WEPAGES_URL/<endpoint>" \
  -H "Authorization: Bearer $WEPAGES_TOKEN" \
  -H "Content-Type: application/json" \
  -d '<json_body>'
```

## 常用端點（已限定 {{project_name}} 項目）

| 操作 | 範例 |
|------|------|
| 列出本項目工單 | `curl "$WEPAGES_URL/api/task/list?project_id=$WEPAGES_PROJECT_ID&limit=100" -H "Authorization: Bearer $WEPAGES_TOKEN"` |
| 取得單一工單 | `curl "$WEPAGES_URL/api/task/get?id=<id>" -H "Authorization: Bearer $WEPAGES_TOKEN"` |
| 建立工單 | `curl -X POST "$WEPAGES_URL/api/task/create" -H "Authorization: Bearer $WEPAGES_TOKEN" -H "Content-Type: application/json" -d '{"title":"...","project_id":'$WEPAGES_PROJECT_ID'}'` |
| 更新工單 | `curl -X POST "$WEPAGES_URL/api/task/update" -H "Authorization: Bearer $WEPAGES_TOKEN" -H "Content-Type: application/json" -d '{"id":<id>,"status":"in_progress"}'` |
| 完成工單 | `curl -X POST "$WEPAGES_URL/api/task/complete" -H "Authorization: Bearer $WEPAGES_TOKEN" -d '{"id":<id>}'` |
| 子清單列表 | `curl "$WEPAGES_URL/api/task/checklist/list?task_id=<id>" -H "Authorization: Bearer $WEPAGES_TOKEN"` |
| 新增子清單 | `curl -X POST "$WEPAGES_URL/api/task/checklist/add" -H "Authorization: Bearer $WEPAGES_TOKEN" -d '{"task_id":<id>,"items":["..."]}'` |
| 勾選子清單 | `curl -X POST "$WEPAGES_URL/api/task/checklist/toggle/<id>" -H "Authorization: Bearer $WEPAGES_TOKEN"` |
| 列出項目 | `curl "$WEPAGES_URL/api/task/projects" -H "Authorization: Bearer $WEPAGES_TOKEN"` |
| 建驗收組 | `curl -X POST "$WEPAGES_URL/api/task/acceptance/group/add" -H "Authorization: Bearer $WEPAGES_TOKEN" -H "Content-Type: application/json" -d '{"task_id":<id>,"title":"<標題>","doc_path":"aispec/valid/<id>-<slug>.md"}'` → 回 `group_id` |
| 加驗收項 | `curl -X POST "$WEPAGES_URL/api/task/acceptance/item/add" -H "Authorization: Bearer $WEPAGES_TOKEN" -H "Content-Type: application/json" -d '{"group_id":<gid>,"items":["驗收點1","驗收點2"]}'` |
| 取驗收清單 | `curl "$WEPAGES_URL/api/task/acceptance/get?task_id=<id>" -H "Authorization: Bearer $WEPAGES_TOKEN"` |
| 待驗收聚合 | `curl "$WEPAGES_URL/api/task/acceptance/pending" -H "Authorization: Bearer $WEPAGES_TOKEN"` |
| 勾選驗收項 | 沿用 `POST /api/task/checklist/toggle/<item_id>`（驗收項本質即 checklist row） |

## 任務欄位

- status: `pending` / `in_progress` / `reviewing` / `completed` / `cancelled`
- priority: `low` / `medium` / `high` / `urgent`
- task_type: `bug` / `feature` / `discuss` / `optimize` / `other`
- note: 新增備注時傳入，會自動追加到備注列表

## 關鍵注意事項

1. **list 必帶 `?project_id=$WEPAGES_PROJECT_ID`**（={{project_id}}），否則會看到其他項目的工單
2. **建立工單必帶 `"project_id": {{project_id}}`**，否則新 task 會落到「無項目」
3. 後端 list 預設會自動過濾 completed / archived
4. 本目錄是「項目級綁定」（全 {{project_name}}），新建 task 自動納入，不需 `/wp-attach`
5. 若要切換為 task_ids 白名單模式（只處理特定幾筆 task），跑 `/wp-init`
6. 切換到別的項目：重新跑 `/wp-bind-project <name>` 即可覆蓋

## MCP vs REST

TaskHub 同時提供 REST API 與 MCP server。**本地預設走 REST（curl）**——`/wp` 等工具會自動偵測：
若當前 session 有 `mcp__*` 工單工具就用 MCP，否則改走上面的 curl 端點（功能等價）。
若專案 `.mcp.json` 未註冊 TaskHub MCP，就走 curl。
