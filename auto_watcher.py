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
    """生成 HLTV 风格：上下队伍 + 严格 24 槽位时间轴"""
    
    t1_name = match_data.get('team1', 'Team_1')
    t2_name = match_data.get('team2', 'Team_2')
    
    t_keys = list(match_data['teams'].keys())
    if t1_name not in t_keys and len(t_keys) > 0: t1_name = t_keys[0]
    if t2_name not in t_keys and len(t_keys) > 1: t2_name = t_keys[1]

    t1_players = match_data['teams'].get(t1_name, [])
    t2_players = match_data['teams'].get(t2_name, [])
    t1_players.sort(key=lambda x: x['rating'], reverse=True)
    t2_players.sort(key=lambda x: x['rating'], reverse=True)

    def build_rows(players):
        rows = ""
        for p in players:
            r_class = "rtg-high" if p['rating'] > 1.05 else ("rtg-low" if p['rating'] < 0.95 else "")
            rows += f"""<tr>
                <td style="text-align:left; padding-left:15px; font-weight:bold; white-space:nowrap; max-width:200px; overflow:hidden; text-overflow:ellipsis;" title="{p['name']}">{p['name']}</td>
                <td style="color:#888; white-space:nowrap;">{p['k']} - {p['d']}</td>
                <td>{p['adr']}</td>
                <td>{p['entry']}</td>
                <td style="color:#aaa; font-size:0.85em;">{p['k3']}/{p['k4']}/{p['k5']}</td>
                <td>{p['clutch']}</td>
                <td style="color:#ffa726; font-weight:bold;">{p['impact']}</td>
                <td class="{r_class}" style="font-weight:bold; font-size:1.1em;">{p['rating']}</td>
            </tr>"""
        return rows

    t1_html = f"""
    <div style="background:#252525; border-radius:6px; overflow:hidden; border:1px solid #333; box-shadow: 0 4px 10px rgba(0,0,0,0.2);">
        <div style="padding:15px; font-weight:bold; background:#2a2a2a; font-size:1.1em; border-bottom:2px solid #4a90e2; color:#4a90e2;">{t1_name}</div>
        <table style="width:100%; border-collapse:collapse; table-layout: auto;">
            <tr><th style="text-align:left; padding:12px 15px;">选手</th><th>K-D</th><th>ADR</th><th>首杀</th><th>3k/4k/5k</th><th>残局</th><th>Impact</th><th>Rating</th></tr>
            {build_rows(t1_players)}
        </table>
    </div>"""

    t2_html = f"""
    <div style="background:#252525; border-radius:6px; overflow:hidden; border:1px solid #333; box-shadow: 0 4px 10px rgba(0,0,0,0.2);">
        <div style="padding:15px; font-weight:bold; background:#2a2a2a; font-size:1.1em; border-bottom:2px solid #ff5252; color:#ff5252;">{t2_name}</div>
        <table style="width:100%; border-collapse:collapse; table-layout: auto;">
            <tr><th style="text-align:left; padding:12px 15px;">选手</th><th>K-D</th><th>ADR</th><th>首杀</th><th>3k/4k/5k</th><th>残局</th><th>Impact</th><th>Rating</th></tr>
            {build_rows(t2_players)}
        </table>
    </div>"""

    # 严格渲染 24 个格子
    blocks_html = ""
    for i in range(24):
        t1_win = match_data['timeline'][i]
        if t1_win is True: 
            blocks_html += """
            <div style="position: relative; z-index: 2; flex: 1; height: 40px; display: flex; flex-direction: column; justify-content: center; margin: 0 2px;">
                <div style="height: 18px; width: 100%; background: #4a90e2; border-radius: 2px; margin-bottom: 4px;"></div>
                <div style="height: 18px; width: 100%;"></div>
            </div>"""
        elif t1_win is False: 
            blocks_html += """
            <div style="position: relative; z-index: 2; flex: 1; height: 40px; display: flex; flex-direction: column; justify-content: center; margin: 0 2px;">
                <div style="height: 18px; width: 100%; margin-bottom: 4px;"></div>
                <div style="height: 18px; width: 100%; background: #ff5252; border-radius: 2px;"></div>
            </div>"""
        else: # 真正未进行的回合，空缺，仅留灰线
            blocks_html += """
            <div style="position: relative; z-index: 2; flex: 1; height: 40px; margin: 0 2px;"></div>"""

    timeline_html = f"""
    <div style="display: flex; align-items: center; justify-content: space-between; position: relative; height: 60px; margin: 10px 0; padding: 0 10px; background: #1a1a1a; border-radius: 8px; border: 1px solid #222;">
        <div style="position: absolute; left: 10px; right: 10px; height: 4px; background: #333; top: 50%; transform: translateY(-50%); z-index: 1; border-radius: 2px;"></div>
        {blocks_html}
    </div>
    """

    html_content = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8"><title>Match #{match_data['id']} Details</title>
    <style>
        body {{ font-family: 'Segoe UI', system-ui, sans-serif; background: #121212; color: white; padding: 30px 20px; margin: 0; }}
        .container {{ max-width: 1100px; margin: auto; background: #1e1e1e; border-radius: 12px; padding: 30px; border: 1px solid #333; box-shadow: 0 10px 30px rgba(0,0,0,0.5); }}
        th {{ background: #2a2a2a; color: #888; font-size: 0.85em; padding: 12px 10px; white-space: nowrap; }}
        td {{ padding: 14px 10px; text-align: center; border-bottom: 1px solid #333; }}
        .rtg-high {{ color: #4CAF50; }} .rtg-low {{ color: #ff5252; }}
        .btn-back {{ color: #aaa; text-decoration: none; margin-bottom: 20px; display: inline-block; font-size: 1.1em; transition: 0.2s; }}
        .btn-back:hover {{ color: #4CAF50; transform: translateX(-5px); }}
    </style>
</head>
<body>
    <div style="max-width: 1100px; margin: auto;">
        <a href="../stats.html" class="btn-back">← 返回战绩大厅</a>
        <div class="container">
            <div style="display:flex; justify-content:space-between; color:#888; font-size:0.95em; border-bottom:1px solid #222; padding-bottom:15px; margin-bottom:25px;">
                <span>结束时间: {match_data['timestamp']} &nbsp;|&nbsp; 地图: {match_data['map']} &nbsp;|&nbsp; 总局数: {match_data['total_rounds']} 局</span>
                <span>ID: #{match_data['id']}</span>
            </div>
            <div style="text-align:center; font-size:2.5em; font-weight:900; margin-bottom:20px; display:flex; justify-content:center; align-items:center; gap:30px;">
                <span style="font-size:0.4em; color:#ccc; width:250px; text-align:right; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;">{match_data['team1']}</span>
                <span style="background:#000; color:#4CAF50; padding:10px 30px; border-radius:8px; border: 1px solid #222;">{match_data['score1']} : {match_data['score2']}</span>
                <span style="font-size:0.4em; color:#ccc; width:250px; text-align:left; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;">{match_data['team2']}</span>
            </div>
            
            <div style="display:flex; flex-direction:column; gap: 5px; margin-top: 20px;">
                {t1_html}
                {timeline_html}
                {t2_html}
            </div>
        </div>
    </div>
</body>
</html>"""
    
    with open(os.path.join(GITHUB_WEBSITE_DIR, f"match_{match_data['id']}.html"), "w", encoding="utf-8") as f:
        f.write(html_content)

def sync_all():
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
                timeline = [None] * 24  # 严格锁定 24 回合
                
                if txt_path:
                    with open(txt_path, 'r', encoding='utf-8', errors='ignore') as tf:
                        txt = tf.read()
                        
                    timestamp = (re.search(r'"timestamp"\s+"([^"]+)"', txt) or [0,""])[1]
                    map_name = (re.search(r'"map"\s+"([^"]+)"', txt) or [0,""])[1]
                    team1 = (re.search(r'"team1"\s+"([^"]+)"', txt) or [0,"T1"])[1]
                    team2 = (re.search(r'"team2"\s+"([^"]+)"', txt) or [0,"T2"])[1]
                    
                    fh_match = re.search(r'"FirstHalfScore"\s*{([^}]+)}', txt)
                    h1_t1 = int((re.search(r'"team1"\s+"(\d+)"', fh_match.group(1)) or [0,0])[1]) if fh_match else 0
                    h1_t2 = int((re.search(r'"team2"\s+"(\d+)"', fh_match.group(1)) or [0,0])[1]) if fh_match else 0

                    for block in ['FirstHalfScore', 'SecondHalfScore', 'OvertimeScore']:
                        bm = re.search(rf'"{block}"\s*{{([^}}]+)}}', txt)
                        if bm:
                            s1 += int((re.search(r'"team1"\s+"(\d+)"', bm.group(1)) or [0,0])[1])
                            s2 += int((re.search(r'"team2"\s+"(\d+)"', bm.group(1)) or [0,0])[1])

                    # 绝对真理：用最终得分相加，确定真正的比赛回合数！
                    real_total_rounds = s1 + s2 if (s1 + s2) > 0 else 24

                    rr_match = re.search(r'"RoundResults"\s*{([^}]+)}', txt)
                    results = [-1] * 24
                    if rr_match:
                        rr_chunk = rr_match.group(1)
                        for i in range(1, 25):
                            m = re.search(rf'"round{i}"\s+"(\d+)"', rr_chunk)
                            if m: results[i-1] = int(m.group(1))

                    # 移除 0 (防坑)，只收录真实的 T 阵营胜利代码
                    group_A = [1, 2, 3, 9] 
                    a_h1 = sum(1 for r in results[:12] if r in group_A)
                    b_h1 = sum(1 for r in results[:12] if r != -1 and r != 0 and r not in group_A)
                    
                    t1_is_A_in_h1 = True
                    if a_h1 == h1_t1 and b_h1 != h1_t1: t1_is_A_in_h1 = True
                    elif b_h1 == h1_t1 and a_h1 != h1_t1: t1_is_A_in_h1 = False
                    else: 
                        h2_t1, h2_t2 = s1 - h1_t1, s2 - h1_t2
                        a_h2 = sum(1 for r in results[12:24] if r in group_A)
                        b_h2 = sum(1 for r in results[12:24] if r != -1 and r != 0 and r not in group_A)
                        if a_h2 == h2_t2 and b_h2 != h2_t2: t1_is_A_in_h1 = True
                        elif b_h2 == h2_t2 and a_h2 != h2_t2: t1_is_A_in_h1 = False

                    # 🚨 终极截断修复：超出绝对回合数的，一律置为 None（空位）
                    for i in range(24):
                        if i >= real_total_rounds:
                            timeline[i] = None
                            continue
                            
                        r = results[i]
                        # 防范 MatchZy 的 0 占位符和最后一回合未记录的 bug
                        if r == -1 or r == 0: 
                            continue

                        is_A = r in group_A
                        if i < 12: timeline[i] = (is_A == t1_is_A_in_h1)
                        else: timeline[i] = (is_A != t1_is_A_in_h1)

                    # 🤖 自动疗伤系统：如果 MatchZy 没记录完最后一回合，我们用最终比分把它逆推补齐！
                    t1_wins_found = timeline.count(True)
                    t2_wins_found = timeline.count(False)
                    for i in range(min(24, real_total_rounds)):
                        if timeline[i] is None:
                            if t1_wins_found < s1:
                                timeline[i] = True
                                t1_wins_found += 1
                            else:
                                timeline[i] = False
                                t2_wins_found += 1

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
                    kpr = p['k'] / real_total_rounds
                    apr = p['a'] / real_total_rounds
                    adr = p['dmg'] / real_total_rounds
                    
                    imp = 2.13 * kpr + 0.42 * apr - 0.41 + (p['entry']/real_total_rounds)*0.9 + (p['clutch']/real_total_rounds)*0.5 + (p['k3']*0.05 + p['k4']*0.12 + p['k5']*0.25)/real_total_rounds
                    kr = kpr / 0.679
                    sr = (real_total_rounds - p['d']) / real_total_rounds / 0.317
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
                    "total_rounds": real_total_rounds, "teams": teams_dict, # 顶部显示也同步为真实的局数
                    "timeline": timeline 
                }
                
                generate_html(match_info)
                
                matches_summary.append({
                    "id": mid, "timestamp": timestamp, "map": map_name,
                    "team1": team1, "team2": team2, "score1": s1, "score2": s2, "total_rounds": real_total_rounds
                })

    matches_summary.sort(key=lambda x: x['id'], reverse=True)
    with open(os.path.join(GITHUB_DATA_DIR, "matches.json"), "w", encoding="utf-8") as f:
        json.dump(matches_summary, f, ensure_ascii=False)
    print(f"✅ 成功提取并生成 {len(matches_summary)} 个HLTV风格比赛网页！")

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