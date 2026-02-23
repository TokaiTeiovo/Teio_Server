import os
import shutil
import json
import re
import time

# ================= 配置区域 =================
# 你服务器存放战绩的绝对路径
LOCAL_STATS_DIR = r"D:\CS2Server\steamapps\common\Counter-Strike Global Offensive\game\csgo\MatchZy_Stats"
# 你 GitHub 仓库本地文件夹里的 data 路径
GITHUB_DATA_DIR = "./data"
# ===========================================

if not os.path.exists(GITHUB_DATA_DIR):
    os.makedirs(GITHUB_DATA_DIR)

def sync_stats():
    match_list = []
    
    # 遍历 MatchZy_Stats 下的所有文件夹和文件
    for root, dirs, files in os.walk(LOCAL_STATS_DIR):
        for filename in files:
            # 匹配 match_data_map0_X.csv 格式
            if filename.startswith("match_data_") and filename.endswith(".csv"):
                # 提取 Match ID
                match_id_match = re.findall(r"(\d+).csv", filename)
                if not match_id_match: continue
                
                match_id = int(match_id_match[0])
                source_path = os.path.join(root, filename)
                target_filename = f"match_{match_id}.csv"
                target_path = os.path.join(GITHUB_DATA_DIR, target_filename)
                ctime = os.path.getctime(source_path)
                start_time_str = time.strftime('%Y-%m-%d %H:%M', time.localtime(ctime))
                # 复制文件到 GitHub 目录
                shutil.copy2(source_path, target_path)
                
                match_list.append({
                    "id": match_id,
                    "file": target_filename,
                    "start_time": start_time_str, # 自动获取本地文件创建时间
                    "score": "VS"
                })

    # 按 ID 从新到旧排序
    match_list.sort(key=lambda x: x['id'], reverse=True)

    # 生成索引文件
    with open(os.path.join(GITHUB_DATA_DIR, "matches.json"), "w", encoding="utf-8") as f:
        json.dump(match_list, f, indent=4, ensure_ascii=False)
    
    print(f"✅ 同步完成！共找到 {len(match_list)} 场比赛战绩。")

if __name__ == "__main__":
    sync_stats()