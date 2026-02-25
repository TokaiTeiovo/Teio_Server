import os
from flask import Flask, request, render_template_string, redirect
from mcrcon import MCRcon
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("WEB_SECRET_KEY", "teio_rcon_secure")

RCON_CONFIG = {
    'ip': '127.0.0.1',
    'port': 27018,
    'password': os.getenv("RCON_PASSWORD")
}

if not RCON_CONFIG['password']:
    raise ValueError("错误：未在 .env 文件中找到 RCON_PASSWORD！")

# 炫酷的控制面板 UI
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>Teio CS2 控制台</title>
    <style>
        body { background: #0f0f0f; color: #e0e0e0; font-family: -apple-system, sans-serif; padding: 15px; margin: 0; }
        .container { max-width: 450px; margin: auto; background: #1a1a1a; padding: 20px; border-radius: 15px; box-shadow: 0 8px 30px rgba(0,0,0,0.5); }
        h3 { color: #4a90e2; text-align: center; margin-bottom: 20px; font-weight: 400; }
        
        .status-bar { 
            padding: 12px; 
            background: #252525; 
            border-radius: 8px; 
            font-size: 11px; 
            margin-bottom: 20px; 
            border-left: 4px solid #4a90e2; 
            
            /* --- 强力左对齐补丁 --- */
            display: block;
            text-align: left !important;
            white-space: pre-wrap;
            word-wrap: break-word;
            word-break: break-all;
            
            /* 强制消除可能存在的缩进影响 */
            direction: ltr; 
            unicode-bidi: bidi-override;
            
            font-family: 'Consolas', 'Monaco', 'Courier New', monospace; 
            width: 100%;
            box-sizing: border-box;
            max-height: 300px;          
            overflow-y: auto;           
        }
        
        .section-title { font-size: 12px; color: #666; text-transform: uppercase; margin: 15px 0 8px 5px; letter-spacing: 1px; }
        
        .grid { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }
        .btn { padding: 15px; border-radius: 8px; font-weight: bold; border: none; color: white; cursor: pointer; text-decoration: none; text-align: center; font-size: 14px; transition: 0.2s; }
        .btn:active { transform: scale(0.96); opacity: 0.8; }
        
        /* 颜色分类 */
        .btn-green { background: #2e7d32; }
        .btn-red { background: #c62828; }
        .btn-blue { background: #1565c0; }
        .btn-purple { background: #6a1b9a; }
        .btn-gray { background: #424242; }

        /* 输入区域 */
        .input-group { display: flex; gap: 5px; margin-top: 10px; }
        input { flex: 1; padding: 12px; background: #2a2a2a; border: 1px solid #3d3d3d; color: white; border-radius: 6px; outline: none; }
        .btn-send { padding: 0 15px; background: #4a90e2; border-radius: 6px; border: none; color: white; font-weight: bold; }
    </style>
</head>
<body>
    <div class="container">
        <h3>🎮 CS2 远程控制中心</h3>
        
        <div class="status-bar">{{ status }}</div>

        <div class="section-title">比赛控制</div>
        <div class="grid">
            <a href="/send?cmd=css_start" class="btn btn-green">开始比赛</a>
            <a href="/send?cmd=css_restart" class="btn btn-red">结束比赛</a>
            <a href="/send?cmd=css_forcepause" class="btn btn-blue">强制暂停</a>
            <a href="/send?cmd=css_forceunpause" class="btn btn-blue">解除暂停</a>
        </div>

        <div class="section-title">模式切换</div>
        <div class="grid">
            <a href="/send?cmd=css_prac" class="btn btn-purple">进入训练</a>
            <a href="/send?cmd=css_exitprac" class="btn btn-purple">退出训练</a>
        </div>

        <div class="section-title">高级命令</div>
        
        <form action="/send" method="get" class="input-group">
            <input type="number" name="arg" placeholder="回合数 (restore)">
            <input type="hidden" name="cmd" value="css_restore">
            <button class="btn-send">恢复</button>
        </form>

        <form action="/send" method="get" class="input-group">
            <input type="text" name="arg" placeholder="消息内容 (asay)">
            <input type="hidden" name="cmd" value="css_asay">
            <button class="btn-send">发送</button>
        </form>

        <form action="/send" method="get" class="input-group">
            <input type="text" name="arg" placeholder="地图代码 (de_dust2)">
            <input type="hidden" name="cmd" value="css_map">
            <button class="btn-send">更换</button>
        </form>

        <div class="section-title">全能终端</div>
        <form action="/send" method="get" class="input-group">
            <input type="text" name="arg" placeholder="输入任意指令...">
            <input type="hidden" name="cmd" value="raw">
            <button class="btn-send" style="background:#444">执行</button>
        </form>

        <p style="text-align:center; font-size:10px; color:#444; margin-top:20px;">Target: 127.0.0.1:27018</p>
    </div>
</body>
</html>
"""

@app.route("/")
def index():
    status = request.args.get("status", "等待指令...")
    return render_template_string(HTML_TEMPLATE, status=status)

@app.route("/send")
def send():
    cmd_type = request.args.get("cmd")
    arg = request.args.get("arg", "").strip()
    
    # 构建最终命令
    if cmd_type == "raw":
        final_cmd = arg
    elif arg:
        final_cmd = f"{cmd_type} {arg}"
    else:
        final_cmd = cmd_type

    if not final_cmd:
        return redirect("/")

    try:
        with MCRcon(RCON_CONFIG['ip'], RCON_CONFIG['password'], port=int(RCON_CONFIG['port']), timeout=3) as mcr:
            # 关键点：mcr.command() 会返回服务器的回传字符串
            response = mcr.command(final_cmd)
            
            # 如果是 status 这种有大量输出的命令，我们把结果存入 status
            if response and len(response.strip()) > 0:
                # 限制长度防止网页撑爆，同时处理换行
                msg = response.strip() if response else f"Success: {final_cmd}"
            else:
                msg = f"✅ 已执行: {final_cmd} (无回传内容)"
    except Exception as e:
        msg = f"❌ 失败: {str(e)}"
    
    # 为了能显示多行结果，建议将结果存入 session 或直接传给首页
    # 我们这里简单处理，直接把结果传回首页显示
    import urllib.parse
    safe_msg = urllib.parse.quote(msg)
    return redirect(f"/?status={safe_msg}")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, ssl_context='adhoc', threaded=True)