import os
from flask import Flask, request, render_template_string, redirect
from mcrcon import MCRcon
from dotenv import load_dotenv  # 引入环境变量读取库

# 加载同目录下的 .env 文件
load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("WEB_SECRET_KEY", "default_secret_key")

# 从环境变量读取配置，不再硬编码
RCON_CONFIG = {
    'ip': '127.0.0.1',
    'port': 27018,
    'password': os.getenv("RCON_PASSWORD")
}

# 检查密码是否存在
if not RCON_CONFIG['password']:
    raise ValueError("错误：未在 .env 文件中找到 RCON_PASSWORD！")

PANEL_HTML = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Teio RCON Safe</title>
    <style>
        body { background: #121212; color: white; font-family: sans-serif; text-align: center; padding: 20px; }
        .box { max-width: 350px; margin: auto; background: #1e1e1e; padding: 20px; border-radius: 12px; }
        .btn { display: block; width: 100%; padding: 18px; margin: 10px 0; background: #4CAF50; color: white; 
               text-decoration: none; border-radius: 8px; font-weight: bold; border: none; font-size: 16px;}
        .status { padding: 10px; margin-bottom: 10px; border-radius: 5px; background: #333; font-size: 13px;}
    </style>
</head>
<body>
    <div class="box">
        <h3>🎮 CS2 远程控制 (安全版)</h3>
        <div class="status">{{ status }}</div>
        <a href="/send?cmd=css_start" class="btn">🚀 强制开赛</a>
        <a href="/send?cmd=css_pause" class="btn" style="background:#2196F3">⏸️ 暂停比赛</a>
        <a href="/send?cmd=css_unpause" class="btn" style="background:#2196F3">▶️ 继续比赛</a>
        <a href="/send?cmd=matchzy_everyone_is_admin+1" class="btn" style="background:#ff9800">👑 全员管理员</a>
    </div>
</body>
</html>
"""

@app.route("/")
def index():
    status = request.args.get("status", "系统就绪")
    return render_template_string(PANEL_HTML, status=status)

@app.route("/send")
def send():
    cmd = request.args.get("cmd")
    if not cmd: return redirect("/")
    try:
        with MCRcon(RCON_CONFIG['ip'], RCON_CONFIG['password'], port=int(RCON_CONFIG['port']), timeout=2) as mcr:
            mcr.command(cmd)
        return render_template_string(PANEL_HTML, status=f"✅ 已发送: {cmd}")
    except Exception as e:
        return render_template_string(PANEL_HTML, status=f"❌ 失败: {str(e)}")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, ssl_context='adhoc', threaded=True)