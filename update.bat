@echo off
echo [1/3] 正在扫描子目录并提取 CSV...
python sync_and_update.py

echo [2/3] 正在准备提交到 GitHub...
git add .
git commit -m "Auto-update match stats"

echo [3/3] 正在推送数据到云端...
git push origin main

echo Done! 战绩已更新。
pause