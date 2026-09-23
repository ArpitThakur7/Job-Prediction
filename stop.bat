@echo off
title JOB-AI 3D Platform Shutdown Utility
cls
echo ======================================================
echo           Stopping JOB-AI 3D Platform
echo ======================================================
echo.

echo [1/3] Closing Server Command Windows...
taskkill /FI "WINDOWTITLE eq JOB-AI Backend API*" /F /T >nul 2>&1
taskkill /FI "WINDOWTITLE eq JOB-AI Next.js 3D Frontend*" /F /T >nul 2>&1

echo [2/3] Freeing Port 8000 (FastAPI Backend) ^& Port 3000 (Next.js)...
powershell -Command "Get-NetTCPConnection -LocalPort 8000, 3000 -ErrorAction SilentlyContinue | ForEach-Object { Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue }" >nul 2>&1

echo [3/3] Stopping Local MongoDB Daemon...
taskkill /IM mongod.exe /F >nul 2>&1
taskkill /IM node.exe /F >nul 2>&1
taskkill /IM python.exe /F >nul 2>&1

echo.
echo ======================================================
echo  ✅ JOB-AI Platform servers successfully stopped!
echo ======================================================
echo.
ping 127.0.0.1 -n 4 >nul
