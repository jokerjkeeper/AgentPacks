## Session 進度（AgentPacks / dev-base）

- **Session 開始**：先讀 `.agent/session.md`（現況快照），摘要進度並確認待辦；與目前 git 分支不一致時提醒用戶。
- **Session 結束或用戶要求存檔**：用 `save` skill 覆蓋更新快照（舊快照先追加到 `.agent/session-log/YYYY-MM.md`），快照**不超過 100 行**。
- `.agent/session.md` 不存在、但 `.agent/session-log/legacy-*.md` 存在時：用 `resume` skill 從舊紀錄合併出第一份快照。
- 中長期階段與跨 session 決策寫 `.agent/ROADMAP.md`（`roadmap` skill）。完整規範見 `.agent/spec/session.md`。
- 舊位置 `.claude/session.md`、`.codex/session.md`、`.claude/docs/ROADMAP.md` 已停用，**不要再寫入**。

@.agent/session.md
