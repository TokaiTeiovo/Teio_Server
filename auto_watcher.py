import os
import json
import re
import time
import subprocess
import threading
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

# ================= 配置区域 =================
# CSV 目录 (用于监听比赛是否彻底结束)
CSV_DIR = r"D:\CS2Server\steamapps\common\Counter-Strike Global Offensive\game\csgo\MatchZy_Stats"
# TXT 备份目录 (包含每回合详细数据的 csgo 根目录)
TXT_DIR = r"D:\CS2Server\steamapps\common\Counter-Strike Global Offensive\game\csgo"
# GitHub 数据存储目录
GITHUB_DATA_DIR = r"D:\CS2Server\Teio_Server\data"
# ============================================

def extract_val(pattern, text, default=0):
    m = re.search(pattern, text)
    return int(m.group(1)) if m else default

def extract_str(pattern, text, default=""):
    m = re.search(pattern, text)
    return m.group(1) if m else default

def get_final_txt_for_match(match_id):
    """在 TXT 目录中寻找该 match_id 对应的最大回合数备份文件"""
    max_round = -1
    final_file = None
    # 匹配文件名如: matchzy_14_0_round21.txt
    pattern = re.compile(rf'matchzy_{match_id}_\d+_round(\d+)\.txt')
    
    if os.path.exists(TXT_DIR):
        for f in os.listdir(TXT_DIR):
            m = pattern.match(f)
            if m:
                round_num = int(m.group(1))
                if round_num > max_round:
                    max_round = round_num
                    final_file = os.path.join(TXT_DIR, f)
    return final_file

def sync_data():
    if not os.path.exists(GITHUB_DATA_DIR):
        os.makedirs(GITHUB_DATA_DIR)
    
    matches = []
    completed_match_ids = set()
    
    # 1. 扫描 CSV 文件夹，获取所有【已彻底打完】的比赛 ID
    for root, dirs, files in os.walk(CSV_DIR):
        for f in files:
            if f.startswith("match_data_") and f.endswith(".csv"):
                mid_match = re.findall(r"(\d+).csv", f)
                if mid_match:
                    completed_match_ids.add(int(mid_match[0]))
                    
    # 2. 针对每个已完成的比赛，去解析它最终回合的 txt 数据
    for match_id in completed_match_ids:
        txt_path = get_final_txt_for_match(match_id)
        if not txt_path:
            continue # 如果意外找不到对应的 txt 备份，则跳过
            
        try:
            with open(txt_path, 'r', encoding='utf-8', errors='ignore') as file:
                content = file.read()
                
            # 提取全局基础信息
            timestamp = extract_str(r'"timestamp"\s+"([^"]+)"', content, "未知时间")
            team1_name = extract_str(r'"team1"\s+"([^"]+)"', content, "TEAM_1")
            team2_name = extract_str(r'"team2"\s+"([^"]+)"', content, "TEAM_2")
            map_name = extract_str(r'"map"\s+"([^"]+)"', content, "Unknown")
            total_rounds = extract_val(r'"round"\s+"(\d+)"', content, 24)
            
            # 自动计算总比分 (包含上下半场和加时赛)
            t1_score, t2_score = 0, 0
            for block in ['FirstHalfScore', 'SecondHalfScore', 'OvertimeScore']:
                b_match = re.search(rf'"{block}"\s*{{([^}}]+)}}', content)
                if b_match:
                    t1_score += extract_val(r'"team1"\s+"(\d+)"', b_match.group(1))
                    t2_score += extract_val(r'"team2"\s+"(\d+)"', b_match.group(1))
                    
            # 分割上下半场的玩家数据，确定队伍归属
            team2_index = content.find('"PlayersOnTeam2"')
            if team2_index == -1: team2_index = len(content)
            
            players = []
            names = [m for m in re.finditer(r'\t\t\t"name"\s+"([^"]+)"', content)]
            for i, n_match in enumerate(names):
                start_idx = n_match.start()
                end_idx = names[i+1].start() if i+1 < len(names) else len(content)
                chunk = content[start_idx:end_idx]
                
                team = team1_name if start_idx < team2_index else team2_name
                name = n_match.group(1)
                
                k = extract_val(r'"kills"\s+"(\d+)"', chunk)
                d = extract_val(r'"deaths"\s+"(\d+)"', chunk)
                a = extract_val(r'"assists"\s+"(\d+)"', chunk)
                k3 = extract_val(r'"enemy3Ks"\s+"(\d+)"', chunk)
                k4 = extract_val(r'"enemy4Ks"\s+"(\d+)"', chunk)
                k5 = extract_val(r'"enemy5Ks"\s+"(\d+)"', chunk)
                
                totals_match = re.search(r'"Totals"\s*{([^}]+)}', chunk)
                totals_chunk = totals_match.group(1) if totals_match else chunk
                
                dmg = extract_val(r'"Damage"\s+"(\d+)"', totals_chunk)
                entry = extract_val(r'"EntryWins"\s+"(\d+)"', totals_chunk)
                c1v1 = extract_val(r'"1v1Wins"\s+"(\d+)"', totals_chunk)
                c1v2 = extract_val(r'"1v2Wins"\s+"(\d+)"', totals_chunk)
                
                players.append({
                    "name": name, "team": team, 
                    "k": k, "d": d, "a": a, 
                    "dmg": dmg, "entry": entry, "clutch": c1v1 + c1v2,
                    "k3": k3, "k4": k4, "k5": k5
                })
                
            matches.append({
                "id": match_id,
                "timestamp": timestamp,
                "map": map_name,
                "team1": team1_name,
                "team2": team2_name,
                "team1_score": t1_score,
                "team2_score": t2_score,
                "total_rounds": total_rounds,
                "players": players
            })
        except Exception as e:
            print(f"解析文件 {txt_path} 时出错: {e}")
            
    matches.sort(key=lambda x: x['id'], reverse=True)
    with open(os.path.join(GITHUB_DATA_DIR, "matches.json"), "w", encoding="utf-8") as f:
        json.dump(matches, f, indent=4, ensure_ascii=False)
    print(f"📊 同步完成：共提取 {len(matches)} 场核心数据。")

def run_git_push():
    repo_root = GITHUB_DATA_DIR
    try:
        subprocess.run(["git", "add", "."], cwd=repo_root, check=True)
        status = subprocess.run(["git", "status", "--porcelain"], cwd=repo_root, capture_output=True, text=True)
        if status.stdout.strip():
            subprocess.run(["git", "commit", "-m", "Auto-update true HLTV stats"], cwd=repo_root, check=True)
            subprocess.run(["git", "push"], cwd=repo_root, check=True)
            print("🚀 数据已极速推送至云端！")
    except Exception as e:
        print(f"❌ Git 推送失败: {e}")

def handle_new_match():
    time.sleep(2) # 等待 CSV 彻底写入完毕
    sync_data()
    run_git_push()

class MatchHandler(FileSystemEventHandler):
    def on_created(self, event):
        # 核心修复：仅监听 CSV 作为比赛结束的触发器
        if event.src_path.endswith(".csv") and "match_data_" in os.path.basename(event.src_path):
            print(f"🏁 检测到比赛结束 (CSV已生成): {os.path.basename(event.src_path)}")
            # 开新线程处理，防止阻塞 watchdog
            threading.Thread(target=handle_new_match).start()

if __name__ == "__main__":
    sync_data() # 启动时先基于现有的 CSV 和 TXT 算一遍存量数据
    run_git_push()
    
    observer = Observer()
    # 监听 CSV 目录
    observer.schedule(MatchHandler(), CSV_DIR, recursive=True)
    observer.start()
    print("👀 战绩监控引擎 (完美版) 已启动，正在等待比赛结束...")
    try:
        while True: time.sleep(1)
    except KeyboardInterrupt: observer.stop()
    observer.join()