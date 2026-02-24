import os
import csv
import json
import re
import time
import subprocess
import threading
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

# ================= 配置区域 =================
# 仓库根目录
REPO_ROOT = r"D:\CS2Server\Teio_Server"
# 本地战绩读取目录
CSV_DIR = r"D:\CS2Server\steamapps\common\Counter-Strike Global Offensive\game\csgo\MatchZy_Stats"
TXT_DIR = r"D:\CS2Server\steamapps\common\Counter-Strike Global Offensive\game\csgo"

# 纯数据存放地 (matches.json)
GITHUB_DATA_DIR = os.path.join(REPO_ROOT, "data")
# 静态网页存放地 (match_xx.html)
GITHUB_WEBSITE_DIR = os.path.join(REPO_ROOT, "website")
# ============================================

def get_final_txt_for_match(match_id):
    max_round = -1
    final_file = None
    pattern = re.compile(rf'matchzy_{match_id}_\d+_round(\d+)\.txt')
    if os.path.exists(TXT_DIR):
        for f in os.listdir(TXT_DIR):
            m = pattern.match(f)
            if m:
                if int(m.group(1)) > max_round:
                    max_round = int(m.group(1))
                    final_file = os.path.join(TXT_DIR, f)
    return final_file

def generate_html(match_data):
    """根据数据动态生成单独的比赛 HTML 网页 (宽屏优化版)"""
    teams_html = ""
    for team_name, players in match_data['teams'].items():
        players.sort(key=lambda x: x['rating'], reverse=True)
        rows = ""
        for p in players:
            r_class = "rtg-high" if p['rating'] > 1.05 else ("rtg-low" if p['rating'] < 0.95 else "")
            # 核心修复 2：加入 white-space: nowrap 禁止换行，并使用 text-overflow: ellipsis 让超长名字显示为省略号
            rows += f"""<tr>
                <td style="text-align:left; padding-left:15px; font-weight:bold; white-space:nowrap; max-width:200px; overflow:hidden; text-overflow:ellipsis;" title="{p['name']}">{p['name']}</td>
                <td style="color:#888; white-space:nowrap;">{p['k']} - {p['d']}</td>
                <td>{p['adr']}</td>
                <td>{p['entry']}</td>
                <td>{p['clutch']}</td>
                <td style="color:#ffa726; font-weight:bold;">{p['impact']}</td>
                <td class="{r_class}" style="font-weight:bold; font-size:1.1em;">{p['rating']}</td>
            </tr>"""
            
        teams_html += f"""
        <div style="background:#252525; border-radius:6px; overflow:hidden; border:1px solid #333; box-shadow: 0 4px 10px rgba(0,0,0,0.2);">
            <div style="padding:15px; font-weight:bold; background:#333; font-size:1.1em; border-bottom:2px solid #555; text-align:center;">{team_name}</div>
            <table style="width:100%; border-collapse:collapse; table-layout: auto;">
                <tr><th style="text-align:left; padding:12px 15px;">选手</th><th>K-D</th><th>ADR</th><th>首杀</th><th>残局</th><th>Impact</th><th>Rating</th></tr>
                {rows}
            </table>
        </div>"""

    # 核心修复 1：将 max-width 从 1000px 扩大到 1400px
    html_content = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8"><title>Match #{match_data['id']} Details</title>
    <style>
        body {{ font-family: 'Segoe UI', system-ui, sans-serif; background: #121212; color: white; padding: 30px 20px; margin: 0; }}
        /* 扩大容器宽度，适应现代宽屏 */
        .container {{ max-width: 1400px; margin: auto; background: #1e1e1e; border-radius: 12px; padding: 30px; border: 1px solid #333; box-shadow: 0 10px 30px rgba(0,0,0,0.5); }}
        th {{ background: #2a2a2a; color: #888; font-size: 0.85em; padding: 12px 10px; white-space: nowrap; }}
        td {{ padding: 14px 10px; text-align: center; border-bottom: 1px solid #333; }}
        .rtg-high {{ color: #4CAF50; }} .rtg-low {{ color: #ff5252; }}
        .btn-back {{ color: #aaa; text-decoration: none; margin-bottom: 20px; display: inline-block; font-size: 1.1em; transition: 0.2s; }}
        .btn-back:hover {{ color: #4CAF50; transform: translateX(-5px); }}
        .grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 40px; margin-top: 30px; }}
        @media (max-width: 1100px) {{ .grid {{ grid-template-columns: 1fr; }} }}
    </style>
</head>
<body>
    <div style="max-width: 1400px; margin: auto;">
        <a href="../stats.html" class="btn-back">← 返回战绩大厅</a>
        <div class="container">
            <div style="display:flex; justify-content:space-between; color:#888; font-size:0.95em; border-bottom:1px solid #222; padding-bottom:15px; margin-bottom:25px;">
                <span>结束时间: {match_data['timestamp']} &nbsp;|&nbsp; 地图: {match_data['map']} &nbsp;|&nbsp; 总局数: {match_data['total_rounds']} 局</span>
                <span>ID: #{match_data['id']}</span>
            </div>
            <div style="text-align:center; font-size:2.5em; font-weight:900; margin-bottom:30px; display:flex; justify-content:center; align-items:center; gap:30px;">
                <span style="font-size:0.4em; color:#ccc; width:250px; text-align:right; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;">{match_data['team1']}</span>
                <span style="background:#000; color:#4CAF50; padding:10px 30px; border-radius:8px; border: 1px solid #222;">{match_data['score1']} : {match_data['score2']}</span>
                <span style="font-size:0.4em; color:#ccc; width:250px; text-align:left; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;">{match_data['team2']}</span>
            </div>
            <div class="grid">{teams_html}</div>
        </div>
    </div>
</body>
</html>"""
    
    # 写入到 website/ 文件夹中
    import os
    with open(os.path.join(GITHUB_WEBSITE_DIR, f"match_{match_data['id']}.html"), "w", encoding="utf-8") as f:
        f.write(html_content)
    """根据数据动态生成单独的比赛 HTML 网页"""
    teams_html = ""
    for team_name, players in match_data['teams'].items():
        players.sort(key=lambda x: x['rating'], reverse=True)
        rows = ""
        for p in players:
            r_class = "rtg-high" if p['rating'] > 1.05 else ("rtg-low" if p['rating'] < 0.95 else "")
            rows += f"""<tr>
                <td style="text-align:left; padding-left:15px; font-weight:bold;">{p['name']}</td>
                <td style="color:#888;">{p['k']}-{p['d']}</td>
                <td>{p['adr']}</td>
                <td>{p['entry']}</td>
                <td>{p['clutch']}</td>
                <td style="color:#ffa726; font-weight:bold;">{p['impact']}</td>
                <td class="{r_class}" style="font-weight:bold;">{p['rating']}</td>
            </tr>"""
            
        teams_html += f"""
        <div style="background:#252525; border-radius:4px; overflow:hidden; border:1px solid #333;">
            <div style="padding:12px; font-weight:bold; background:#333; font-size:0.9em; border-bottom:2px solid #444;">{team_name}</div>
            <table style="width:100%; border-collapse:collapse;">
                <tr><th style="text-align:left; padding:10px 15px;">选手</th><th>K-D</th><th>ADR</th><th>首杀</th><th>残局</th><th>Impact</th><th>Rating</th></tr>
                {rows}
            </table>
        </div>"""

    html_content = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8"><title>Match #{match_data['id']} Details</title>
    <style>
        body {{ font-family: system-ui; background: #121212; color: white; padding: 20px; }}
        .container {{ max-width: 1000px; margin: auto; background: #1e1e1e; border-radius: 8px; padding: 20px; border: 1px solid #333; }}
        th {{ background: #2a2a2a; color: #666; font-size: 0.75em; padding: 10px; }}
        td {{ padding: 12px 6px; text-align: center; border-bottom: 1px solid #333; }}
        .rtg-high {{ color: #4CAF50; }} .rtg-low {{ color: #ff5252; }}
        .btn-back {{ color: #888; text-decoration: none; margin-bottom: 20px; display: inline-block; }}
        .btn-back:hover {{ color: #4CAF50; }}
        .grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-top: 30px; }}
        @media (max-width: 800px) {{ .grid {{ grid-template-columns: 1fr; }} }}
    </style>
</head>
<body>
    <div style="max-width: 1000px; margin: auto;">
        <a href="../stats.html" class="btn-back">← 返回战绩大厅</a>
        <div class="container">
            <div style="display:flex; justify-content:space-between; color:#888; font-size:0.85em; border-bottom:1px solid #222; padding-bottom:10px; margin-bottom:20px;">
                <span>📅 {match_data['timestamp']} &nbsp;|&nbsp; 🗺️ {match_data['map']} &nbsp;|&nbsp; ♻️ {match_data['total_rounds']} 局</span>
                <span>ID: #{match_data['id']}</span>
            </div>
            <div style="text-align:center; font-size:2em; font-weight:900; margin-bottom:10px;">
                <span style="font-size:0.4em; color:#ccc;">{match_data['team1']}</span>
                <span style="background:#000; color:#4CAF50; padding:5px 20px; border-radius:5px; margin:0 15px;">{match_data['score1']} : {match_data['score2']}</span>
                <span style="font-size:0.4em; color:#ccc;">{match_data['team2']}</span>
            </div>
            <div class="grid">{teams_html}</div>
        </div>
    </div>
</body>
</html>"""
    
    with open(os.path.join(GITHUB_WEBSITE_DIR, f"match_{match_data['id']}.html"), "w", encoding="utf-8") as f:
        f.write(html_content)

def sync_all():
    """核心缝合与建站逻辑"""
    if not os.path.exists(GITHUB_DATA_DIR): os.makedirs(GITHUB_DATA_DIR)
    if not os.path.exists(GITHUB_WEBSITE_DIR): os.makedirs(GITHUB_WEBSITE_DIR)
    
    matches_summary = []
    
    for root, dirs, files in os.walk(CSV_DIR):
        for f in files:
            if f.startswith("match_data_") and f.endswith(".csv"):
                mid = int(re.findall(r"(\d+).csv", f)[0])
                csv_path = os.path.join(root, f)
                
                players = []
                with open(csv_path, 'r', encoding='utf-8') as cf:
                    reader = csv.DictReader(cf)
                    for row in reader:
                        r = {k.lower(): v for k, v in row.items()}
                        if not r.get('name'): continue
                        players.append({
                            "name": r['name'], "team": r['team'],
                            "k": int(r['kills']), "d": int(r['deaths']), "a": int(r['assists']),
                            "dmg": int(r['damage']), "k3": int(r.get('enemy3ks',0) or 0),
                            "k4": int(r.get('enemy4ks',0) or 0), "k5": int(r.get('enemy5ks',0) or 0),
                            "entry": 0, "clutch": 0
                        })
                
                txt_path = get_final_txt_for_match(mid)
                total_rounds = 24
                timestamp = "未知"
                map_name = "Unknown"
                team1, team2 = "Team_A", "Team_B"
                s1, s2 = 0, 0
                
                if txt_path:
                    with open(txt_path, 'r', encoding='utf-8', errors='ignore') as tf:
                        txt = tf.read()
                        
                    m_round = re.search(r'"round"\s+"(\d+)"', txt)
                    total_rounds = int(m_round.group(1)) if m_round else 24
                    
                    timestamp = (re.search(r'"timestamp"\s+"([^"]+)"', txt) or [0,""])[1]
                    map_name = (re.search(r'"map"\s+"([^"]+)"', txt) or [0,""])[1]
                    team1 = (re.search(r'"team1"\s+"([^"]+)"', txt) or [0,"T1"])[1]
                    team2 = (re.search(r'"team2"\s+"([^"]+)"', txt) or [0,"T2"])[1]
                    
                    for block in ['FirstHalfScore', 'SecondHalfScore', 'OvertimeScore']:
                        bm = re.search(rf'"{block}"\s*{{([^}}]+)}}', txt)
                        if bm:
                            s1 += int((re.search(r'"team1"\s+"(\d+)"', bm.group(1)) or [0,0])[1])
                            s2 += int((re.search(r'"team2"\s+"(\d+)"', bm.group(1)) or [0,0])[1])

                    # 指纹匹配缝合
                    for match in re.finditer(r'"Totals"\s*{([^}]+)}', txt):
                        chunk = match.group(1)
                        tk = int((re.search(r'"Kills"\s+"(\d+)"', chunk) or [0,0])[1])
                        td = int((re.search(r'"Deaths"\s+"(\d+)"', chunk) or [0,0])[1])
                        ta = int((re.search(r'"Assists"\s+"(\d+)"', chunk) or [0,0])[1])
                        tdmg = int((re.search(r'"Damage"\s+"(\d+)"', chunk) or [0,0])[1])
                        
                        entry = int((re.search(r'"EntryWins"\s+"(\d+)"', chunk) or [0,0])[1])
                        c1 = int((re.search(r'"1v1Wins"\s+"(\d+)"', chunk) or [0,0])[1])
                        c2 = int((re.search(r'"1v2Wins"\s+"(\d+)"', chunk) or [0,0])[1])
                        
                        for p in players:
                            if p['k'] == tk and p['d'] == td and p['a'] == ta and p['dmg'] == tdmg:
                                p['entry'] = entry
                                p['clutch'] = c1 + c2
                                break

                teams_dict = {}
                for p in players:
                    kpr = p['k'] / total_rounds
                    apr = p['a'] / total_rounds
                    adr = p['dmg'] / total_rounds
                    
                    imp = 2.13 * kpr + 0.42 * apr - 0.41 + (p['entry']/total_rounds)*0.9 + (p['clutch']/total_rounds)*0.5 + (p['k3']*0.05 + p['k4']*0.12 + p['k5']*0.25)/total_rounds
                    
                    kr = kpr / 0.679
                    sr = (total_rounds - p['d']) / total_rounds / 0.317
                    dr = adr / 80
                    
                    rtg = 0.175 * kr + 0.175 * sr + 0.25 * dr + 0.40 * (imp / 1.1)
                    p['impact'] = round(imp, 2)
                    p['rating'] = round(rtg * 1.05, 2)
                    p['adr'] = round(adr, 1)
                    
                    if p['team'] not in teams_dict: teams_dict[p['team']] = []
                    teams_dict[p['team']].append(p)

                match_info = {
                    "id": mid, "timestamp": timestamp, "map": map_name,
                    "team1": team1, "team2": team2, "score1": s1, "score2": s2,
                    "total_rounds": total_rounds, "teams": teams_dict
                }
                
                generate_html(match_info)
                
                matches_summary.append({
                    "id": mid, "timestamp": timestamp, "map": map_name,
                    "team1": team1, "team2": team2, "score1": s1, "score2": s2, "total_rounds": total_rounds
                })

    matches_summary.sort(key=lambda x: x['id'], reverse=True)
    with open(os.path.join(GITHUB_DATA_DIR, "matches.json"), "w", encoding="utf-8") as f:
        json.dump(matches_summary, f, ensure_ascii=False)
    
    print(f"✅ 成功生成 {len(matches_summary)} 个比赛网页！")

def run_git_push():
    try:
        subprocess.run(["git", "add", "."], cwd=REPO_ROOT, check=True)
        status = subprocess.run(["git", "status", "--porcelain"], cwd=REPO_ROOT, capture_output=True, text=True)
        if status.stdout.strip():
            subprocess.run(["git", "commit", "-m", "Auto-update match stats and pages"], cwd=REPO_ROOT, check=True)
            subprocess.run(["git", "push"], cwd=REPO_ROOT, check=True)
            print("🚀 数据与网页已极速推送至云端！")
    except Exception as e:
        print(f"❌ Git 推送失败: {e}")

def handle_new_match():
    time.sleep(2) # 等待 CSV 彻底写入
    print("🏁 检测到比赛结束，正在启动建站引擎...")
    sync_all()
    run_git_push()

class MatchHandler(FileSystemEventHandler):
    def on_created(self, event):
        # 依然监听 CSV 作为比赛结束的信号
        if event.src_path.endswith(".csv") and "match_data_" in os.path.basename(event.src_path):
            threading.Thread(target=handle_new_match).start()

if __name__ == "__main__":
    print("=========================================")
    print("   Teio Server 自动建站监控 (Pro) 已启动  ")
    print("=========================================")
    sync_all() # 启动时先整理一遍现有的
    
    observer = Observer()
    observer.schedule(MatchHandler(), CSV_DIR, recursive=True)
    observer.start()
    try:
        while True: time.sleep(1)
    except KeyboardInterrupt: observer.stop()
    observer.join()