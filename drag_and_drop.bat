@echo off
chcp 65001 >nul
cd /d "%~dp0"

:: 環境チェック関数
call :check_environment
if %errorlevel% neq 0 (
    pause
    exit /b 1
)

if "%~1"=="" (
    echo ファイルをドラッグ＆ドロップしてください
    timeout /t 3
    exit /b 1
)

echo 処理中: %~nx1
.venv\Scripts\python.exe "main.py" "%~1"
pause
exit /b 0

:check_environment
if not exist ".venv\Scripts\python.exe" (
    echo ❌ 仮想環境が見つかりません
    echo.
    echo 💡 解決策:
    echo python -m venv .venv
    echo .venv\Scripts\activate
    echo pip install -r requirements.txt
    exit /b 1
)

echo ✓ 仮想環境を確認
.venv\Scripts\python.exe -c "import requests, yaml, dotenv, yfinance, xmltodict" 2>nul
if %errorlevel% neq 0 (
    echo ❌ 必要なパッケージが不足しています
    echo.
    echo 📦 パッケージをインストールします...
    .venv\Scripts\python.exe -m pip install -r requirements.txt
    if %errorlevel% neq 0 (
        echo ❌ インストールに失敗しました
        exit /b 1
    )
    echo ✓ インストール完了
)
echo ✓ すべての依存関係を確認
exit /b 0