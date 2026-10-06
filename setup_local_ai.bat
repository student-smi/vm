@echo off
title Setup OmniRoute + Claude Code + RuFlow (Windows)
echo ============================================================
echo   Installing OmniRoute, Claude Code and RuFlow on Windows...
echo ============================================================
echo.
call npm install -g omniroute @anthropic-ai/claude-code ruflo
echo.
echo ============================================================
echo   Installation Completed Successfully!
echo ============================================================
echo.
echo - To launch OmniRoute AI Gateway:  run start_omniroute.bat (or type omniroute)
echo - To launch Claude Code:           type 'claude'
echo - To initialize RuFlow Swarm:      type 'ruflo init'
echo.
pause
