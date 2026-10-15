@echo off
REM ── 每日 codereview 前置規劃器（AgentPacks / wiki pack）──────────────────
REM 交 Windows 工作排程器每日跑（建議清晨）。純規劃：fetch + 判斷落後 + 算到昨天的窗口
REM + 收集 + 出 digest，不觸發 LLM、不改 wiki。digest 寫到 <paths.outputs>\curate-preflight-YYYY-MM-DD.md。
REM
REM 前置：git 對 remote 須免密碼（ssh-agent 或憑證管理員），否則 fetch 會失敗。
REM python 選擇：設環境變數 AGENT_PYTHON 指向 python.exe（排程器 PATH 可能與終端不同）；未設則用 PATH 上的 python。

setlocal
REM 本檔位於 <repo>\.agent\scripts\，repo 根在上兩層
cd /d "%~dp0\..\.."
set "PY=%AGENT_PYTHON%"
if "%PY%"=="" set "PY=python"
if not exist "outputs" mkdir "outputs"
"%PY%" ".agent\scripts\daily_preflight.py" >> "outputs\preflight.log" 2>&1
endlocal
