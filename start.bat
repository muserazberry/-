@echo off
REM 경기도 조례 추천 시스템 - 더블클릭 실행 (가상환경 활성화 불필요)
chcp 65001 >nul
cd /d "%~dp0"
set PYTHONUTF8=1
set PYTHONIOENCODING=utf-8

if not exist ".venv\Scripts\python.exe" (
  echo [오류] .venv 가 없습니다. 먼저 아래를 1회 실행하세요:
  echo     python -m venv .venv
  echo     .venv\Scripts\python.exe -m pip install -r requirements.txt
  pause
  exit /b 1
)

echo 서버를 시작합니다. 잠시 후 브라우저가 자동으로 열립니다.
echo (열리지 않으면 직접 http://127.0.0.1:8000 접속 / 종료하려면 이 창에서 Ctrl+C)
echo.
REM 서버가 뜰 시간(약 3초)을 준 뒤 브라우저를 연다. (먼저 열면 '연결 안됨'으로 뜸)
start "" /min powershell -NoProfile -WindowStyle Hidden -Command "Start-Sleep -Seconds 3; Start-Process 'http://127.0.0.1:8000'"
".venv\Scripts\python.exe" -m uvicorn app.api.main:app --host 127.0.0.1 --port 8000

echo.
echo 서버가 종료되었습니다.
pause
