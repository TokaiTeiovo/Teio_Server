import os
import shutil
import json
import re
import time
import subprocess
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

# ================= 配置区域 =================
# 1. 你服务器存放战绩的绝对路径
LOCAL_STATS_DIR = r"D:\CS2Server\steamapps\common\Counter-Strike Global Offensive\game\csgo\MatchZy_Stats"
# 2. 你 GitHub 仓库本地文件夹里的 data 路径
GITHUB_DATA_DIR = r"C:\Your_Repo_Path\data"
# ===========================================

def sync_stats():
    match_list = []
    if not os.path.exists(GITHUB_DATA_DIR): os.makedirs(GITHUB_DATA_DIR)
    
    for root, dirs, files in os.walk(LOCAL_STATS_DIR):
        for filename in files:
            if filename.startswith("match_data_") and filename.endswith(".csv"):
                match_id_match = re.findall(r"(\d+).csv", filename)
                if not match_id_match: continue
                
                match_id = int(match_id_match[0])
                source_path = os.path.join(root, filename)
                
                # 获取结束时间（文件最后修改时间）
                mtime = os.path.getmtime(source_path)
                end_time_str = time.strftime('%Y-%m-%d %H:%M', time.localtime(mtime))
                
                target_filename = f"match_{match_id}.csv"
                shutil.copy2(source_path, os.path.join(GITHUB_DATA_DIR, target_filename))
                
                match_list.append({
                    "id": match_id,
                    "file": target_filename,
                    "start_time": end_time_str, # 在网页端将其视作结束时间并逆推
                    "score": "VS"
                })

    match_list.sort(key=lambda x: x['id'], reverse=True)
    with open(os.path.join(GITHUB_DATA_DIR, "matches.json"), "w", encoding="utf-8") as f:
        json.dump(match_list, f, indent=4, ensure_ascii=False)

def run_git_push():
    try:
        subprocess.run(["git", "add", "."], cwd=os.path.dirname(GITHUB_DATA_DIR), check=True)
        subprocess.run(["git", "commit", "-m", "Auto-stats update"], cwd=os.path.dirname(GITHUB_DATA_DIR), check=True)
        subprocess.run(["git", "push"], cwd=os.path.dirname(GITHUB_DATA_DIR), check=True)
        print("✅ 战绩已上传。")
    except Exception as e: print(f"❌ 推送失败: {e}")

class MyHandler(FileSystemEventHandler):
    def on_created(self, event):
        if event.src_path.endswith(".csv"):
            time.sleep(2)
            sync_stats()
            run_git_push()

if __name__ == "__main__":
    sync_stats() # 启动时先同步一次
    observer = Observer()
    observer.schedule(MyHandler(), LOCAL_STATS_DIR, recursive=True)
    observer.start()
    try:
        while True: time.sleep(1)
    except KeyboardInterrupt: observer.stop()
    observer.join()