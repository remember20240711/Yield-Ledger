@echo off
setlocal

REM Windows 一键启动：自动准备 .env、启动 Docker，并打开浏览器。
cd /d "%~dp0"

where docker >nul 2>nul
if errorlevel 1 (
  echo [ERROR] Docker 未安装，请先安装 Docker Desktop。
  pause
  exit /b 1
)

docker compose version >nul 2>nul
if errorlevel 1 (
  where docker-compose >nul 2>nul
  if errorlevel 1 (
    echo [ERROR] 未检测到 docker compose，请检查 Docker Desktop。
    pause
    exit /b 1
  )
  set "COMPOSE=docker-compose"
) else (
  set "COMPOSE=docker compose"
)

if not exist ".env" (
  copy ".env.example" ".env" >nul
  echo [INFO] 已根据 .env.example 创建 .env
)

if not exist "data" mkdir "data"

echo [INFO] 正在启动服务...
%COMPOSE% up -d --build
if errorlevel 1 (
  echo [ERROR] 启动失败，请检查 Docker Desktop 是否已启动。
  pause
  exit /b 1
)

set "URL=http://127.0.0.1:8000"
echo [OK] 服务已启动：%URL%
start "" "%URL%"

endlocal
