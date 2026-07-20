@echo off
title AI Learning System

echo ============================================
echo   AI ResGen Learning Multi-Agent System
echo   Smart Learning Platform
echo ============================================
echo.

:: Check external dependencies
echo [Check] External dependencies:
echo.

mysql --version >nul 2>&1
if errorlevel 1 (
    echo   [X] MySQL not installed - https://dev.mysql.com/downloads/installer/
) else (
    echo   [OK] MySQL
)

redis-cli ping >nul 2>&1
if errorlevel 1 (
    echo   [X] Redis not installed - https://github.com/tporadowski/redis/releases
) else (
    echo   [OK] Redis
)

ffmpeg -version >nul 2>&1
if errorlevel 1 (
    echo   [X] FFmpeg not installed - https://www.gyan.dev/ffmpeg/builds/
) else (
    echo   [OK] FFmpeg
)

echo.

:: Install Python dependencies
echo [1/3] Installing Python dependencies...
pip install -r requirements.txt
echo.

:: Install Playwright browser
echo [2/3] Installing Playwright browser...
playwright install chromium
echo.

:: Install frontend dependencies
echo [3/3] Installing frontend dependencies...
cd frontend
npm install
cd ..

:: Copy .env if not exists
if not exist .env (
    echo Copying .env.example to .env ...
    copy .env.example .env
)

echo.
echo ============================================
echo   Setup complete!
echo ============================================
echo.
echo   Backend:  python main.py
echo   Frontend: cd frontend && npm run dev
echo.
echo   URLs:
echo     http://localhost:8000       (API)
echo     http://localhost:5173       (Web)
echo     http://localhost:8000/docs  (Swagger)
echo.
echo   Default admin: admin / admin123
echo.

set /p START="Start services now? (Y/N): "
if /i "%START%"=="Y" (
    start "Backend" python main.py
    timeout /t 3 /nobreak
    cd frontend
    start "Frontend" cmd /c "npm run dev"
    cd ..
    echo.
    echo Services started!
    timeout /t 5 /nobreak
    start http://localhost:5173
)

pause
