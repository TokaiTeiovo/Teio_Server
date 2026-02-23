import os
import shutil
import json
import re
import time
import subprocess
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

# ================= 配置区域 (请根据实际路径修改) =================
# CSV 目录
CSV_DIR = r"D:\CS2Server\steamapps\common\Counter-Strike Global Offensive\game\csgo\MatchZy_Stats"
# Demo 目录
DEMO_DIR = r"D:\CS2Server\steamapps\common\Counter-Strike Global Offensive\game\csgo\MatchZy"
# GitHub 仓库本地 data 目录
GITHUB_DATA_DIR = r"D:\CS2Server\Teio_Server\data"
# =============================================================

def sync_stats():
    """核心同步逻辑：匹配 CSV 和 Demo 并生成索引"""
    match_list = []
    if not os.path.exists(GITHUB_DATA_DIR):
        os.makedirs(GITHUB_DATA_DIR)
    
    # 1. 递归扫描所有子目录下的 CSV
    csv_map = {}
    for root, dirs, files in os.walk(CSV_DIR):
        for f in files:
            if f.startswith("match_data_") and f.endswith(".csv"):
                match_id_match = re.findall(r"(\d+).csv", f)
                if match_id_match:
                    mid = match_id_match[0]
                    csv_map[mid] = os.path.join(root, f)

    # 2. 扫描 Demo 目录并建立 ID 索引
    demo_map = {}
    if os.path.exists(DEMO_DIR):
        for f in os.listdir(DEMO_DIR):
            if f.endswith(".dem"):
                # 按照你提供的格式提取 ID: 2026-02-24_00-41-15_13_de_dust2...
                parts = f.split('_')
                if len(parts) > 2:
                    demo_id = parts[2]
                    demo_map[demo_id] = f

    # 3. 匹配数据并复制到 GitHub 目录
    for mid, csv_path in csv_map.items():
        # 复制 CSV
        target_csv = f"match_{mid}.csv"
        shutil.copy2(csv_path, os.path.join(GITHUB_DATA_DIR, target_csv))
        
        # 获取结束时间（文件最后修改时间）
        mtime = os.path.getmtime(csv_path)
        end_time_str = time.strftime('%Y-%m-%d %H:%M', time.localtime(mtime))
        
        match_entry = {
            "id": int(mid),
            "file": target_csv,
            "end_time": end_time_str,
            "score": "VS",
            "demo_file": None
        }

        # 如果 Demo 的 ID 与 CSV 匹配，则复制并记录
        if mid in demo_map:
            demo_name = demo_map[mid]
            shutil.copy2(os.path.join(DEMO_DIR, demo_name), os.path.join(GITHUB_DATA_DIR, demo_name))
            match_entry["demo_file"] = demo_name
            
        match_list.append(match_entry)

    # 4. 按 ID 从新到旧排序并保存索引
    match_list.sort(key=lambda x: x['id'], reverse=True)
    with open(os.path.join(GITHUB_DATA_DIR, "matches.json"), "w", encoding="utf-8") as f:
        json.dump(match_list, f, indent=4, ensure_ascii=False)
    print(f"📊 同步完成：共处理 {len(match_list)} 场比赛数据。")

def run_git_push():
    """执行 Git 推送"""
    repo_root = os.path.dirname(GITHUB_DATA_DIR)
    try:
        subprocess.run(["git", "add", "."], cwd=repo_root, check=True)
        subprocess.run(["git", "commit", "-m", "Auto-update match stats & demos"], cwd=repo_root, check=True)
        subprocess.run(["git", "push"], cwd=repo_root, check=True)
        print("🚀 数据与 Demo 已成功同步至云端！")
    except Exception as e:
        print(f"❌ Git 推送失败: {e}")

class MatchHandler(FileSystemEventHandler):
    def on_created(self, event):
        if event.src_path.endswith(".csv"):
            print(f"检测到新战绩: {os.path.basename(event.src_path)}")
            time.sleep(2)  # 等待文件写入完成
            sync_stats()
            run_git_push()

if __name__ == "__main__":
    sync_stats()  # 脚本启动时先同步一次存量数据
    observer = Observer()
    observer.schedule(MatchHandler(), CSV_DIR, recursive=True)
    observer.start()
    print(f"👀 正在监控 CSV 目录: {CSV_DIR}")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()