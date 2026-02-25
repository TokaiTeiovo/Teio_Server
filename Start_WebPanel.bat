@echo off
title Teio Web 控制中心
color 0b

echo =========================================
echo       Teio Server 专属手机控制台
echo =========================================
echo.
echo 正在启动 Flask Web 服务...
echo 请确保 SakuraFrp 已经映射了本地的 5000 端口！
echo.

:: 自动切换到当前 .bat 文件所在的目录，防止找不到 Python 文件
cd /d "%~dp0"

:: 运行网页后端脚本
python web_panel.py

:: 如果脚本意外崩溃或退出，暂停窗口让你能看到报错信息，而不是直接闪退
echo.
echo [警告] Web 控制台已关闭或遇到错误！
pause