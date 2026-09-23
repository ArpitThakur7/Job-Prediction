@echo off
title JOB-AI 3D Platform Launcher
cls
echo ======================================================
echo           Starting JOB-AI 3D Platform
echo ======================================================
echo.

:: Get directory path without trailing backslash
set "PROJECT_DIR=%~dp0"
if "%PROJECT_DIR:~-1%"=="\" set "PROJECT_DIR=%PROJECT_DIR:~0,-1%"
cd /d "%PROJECT_DIR%"

:: Set system resource & memory limits to prevent crashes / 100% RAM & CPU thrashing
set NODE_OPTIONS=--max-old-space-size=4096
set RAYON_NUM_THREADS=2
set OMP_NUM_THREADS=2
set TORCH_NUM_THREADS=2
set MKL_NUM_THREADS=2
set OPENBLAS_NUM_THREADS=2
set NUMEXPR_NUM_THREADS=2
set VECLIB_MAXIMUM_THREADS=2
set KMP_DUPLICATE_LIB_OK=TRUE

:: Ensure MongoDB Directory exists
set "MONGO_DATA_DIR=%PROJECT_DIR%\data\mongo_db"
if not exist "%MONGO_DATA_DIR%" mkdir "%MONGO_DATA_DIR%"

:: Clean up stale lock files if mongod is not currently running
powershell -NoProfile -ExecutionPolicy Bypass -Command "$conn = Get-NetTCPConnection -LocalPort 27017 -ErrorAction SilentlyContinue; if (-not $conn) { $lock = '%MONGO_DATA_DIR%\mongod.lock'; if (Test-Path $lock) { Remove-Item $lock -Force -ErrorAction SilentlyContinue } }"

:: Check and start MongoDB Daemon if port 27017 is free
powershell -NoProfile -ExecutionPolicy Bypass -Command "$conn = Get-NetTCPConnection -LocalPort 27017 -ErrorAction SilentlyContinue; if (-not $conn) { $exe = (Get-Command mongod.exe -ErrorAction SilentlyContinue).Source; if (-not $exe) { foreach ($p in @('C:\Program Files\MongoDB\Server\8.3\bin\mongod.exe', 'C:\Program Files\MongoDB\Server\8.0\bin\mongod.exe', 'C:\Program Files\MongoDB\Server\7.0\bin\mongod.exe', 'C:\Program Files\MongoDB\Server\6.0\bin\mongod.exe')) { if (Test-Path $p) { $exe = $p; break } } }; if ($exe) { Start-Process -FilePath $exe -ArgumentList '--dbpath', '%MONGO_DATA_DIR%', '--port', '27017', '--wiredTigerCacheSizeGB', '0.5' -WindowStyle Hidden } }"

:: Free Ports 8000 and 3000 if currently occupied by previous crashed runs
powershell -NoProfile -ExecutionPolicy Bypass -Command "Get-NetTCPConnection -LocalPort 8000, 3000 -ErrorAction SilentlyContinue | ForEach-Object { Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue }" >nul 2>&1

:: Determine Python executable (venv or system python)
set "PYTHON_EXE=python"
if exist "%PROJECT_DIR%\venv\Scripts\python.exe" (
    set "PYTHON_EXE=%PROJECT_DIR%\venv\Scripts\python.exe"
)

echo [1/2] Booting Backend Server on port 8000...
start "JOB-AI Backend API" cmd /k cd /d "%PROJECT_DIR%" ^&^& set KMP_DUPLICATE_LIB_OK=TRUE ^&^& set OMP_NUM_THREADS=2 ^&^& set TORCH_NUM_THREADS=2 ^&^& set MKL_NUM_THREADS=2 ^&^& "%PYTHON_EXE%" -m uvicorn backend.main:app --port 8000 --reload

echo [2/2] Booting Next.js 3D Frontend on port 3000...
start "JOB-AI Next.js 3D Frontend" cmd /k cd /d "%PROJECT_DIR%\frontend" ^&^& set NODE_OPTIONS=--max-old-space-size=4096 ^&^& set RAYON_NUM_THREADS=2 ^&^& npm run dev

echo.
echo Waiting for backend API to finish initializing...
powershell -NoProfile -ExecutionPolicy Bypass -Command "$retry=0; while ($retry -lt 30) { try { $r = Invoke-WebRequest -Uri 'http://localhost:8000/health' -UseBasicParsing -TimeoutSec 2 -ErrorAction Stop; if ($r.StatusCode -eq 200) { break } } catch { Start-Sleep -Seconds 1; $retry++ } }"

echo Launching 3D Website in browser...
start http://localhost:3000

echo.
echo ======================================================
echo  JOB-AI Platform is running!
echo  Web App: http://localhost:3000
echo  Backend API: http://localhost:8000/docs
echo ======================================================
echo.


