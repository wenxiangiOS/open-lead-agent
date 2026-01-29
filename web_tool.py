"""
简单Web界面 - 方便浏览器测试
"""

import sys
import os
import asyncio
import json
from pathlib import Path

if getattr(sys, 'frozen', False):
    src_path = os.path.join(os.path.dirname(sys.executable), 'src')
    if src_path not in sys.path:
        sys.path.insert(0, src_path)
else:
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from flask import Flask, render_template_string, request, jsonify
except ImportError:
    print("请先安装 Flask: pip install flask")
    sys.exit(1)

from src.config.portable_config import load_config, save_config

app = Flask(__name__)


# HTML模板
HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>小缘AI红娘 - 对话工具</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Arial, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            display: flex;
            justify-content: center;
            align-items: center;
            padding: 20px;
        }
        .container {
            width: 100%;
            max-width: 600px;
            background: white;
            border-radius: 20px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            overflow: hidden;
        }
        .header {
            background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
            color: white;
            padding: 20px;
            text-align: center;
        }
        .header h1 { font-size: 24px; }
        .chat-box {
            height: 400px;
            overflow-y: auto;
            padding: 20px;
            background: #f8f9fa;
        }
        .message {
            margin: 10px 0;
            padding: 12px 16px;
            border-radius: 18px;
            max-width: 80%;
            word-wrap: break-word;
        }
        .user {
            background: #007bff;
            color: white;
            margin-left: auto;
            border-bottom-right-radius: 4px;
        }
        .assistant {
            background: white;
            color: #333;
            border: 1px solid #e0e0e0;
            border-bottom-left-radius: 4px;
        }
        .input-area {
            padding: 20px;
            border-top: 1px solid #e0e0e0;
        }
        .input-row {
            display: flex;
            gap: 10px;
        }
        input[type="text"] {
            flex: 1;
            padding: 12px 16px;
            border: 2px solid #e0e0e0;
            border-radius: 25px;
            font-size: 16px;
            outline: none;
        }
        input[type="text"]:focus {
            border-color: #007bff;
        }
        button {
            padding: 12px 24px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            border-radius: 25px;
            font-size: 16px;
            cursor: pointer;
            transition: transform 0.2s;
        }
        button:hover { transform: scale(1.05); }
        button:disabled { opacity: 0.5; cursor: not-allowed; }
        .config-area {
            padding: 15px 20px;
            background: #fff3cd;
            border-top: 1px solid #ffeaa7;
        }
        .config-area input {
            width: 100%;
            padding: 8px 12px;
            border: 1px solid #ddd;
            border-radius: 8px;
            margin-top: 5px;
        }
        .config-area button {
            margin-top: 10px;
            font-size: 14px;
            padding: 8px 16px;
        }
        .hidden { display: none; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>💕 小缘AI红娘</h1>
            <p>同城脱单联盟首席客服</p>
        </div>
        <div class="chat-box" id="chatBox"></div>
        <div class="input-area">
            <div class="input-row">
                <input type="text" id="messageInput" placeholder="输入消息..." autofocus>
                <button onclick="sendMessage()">发送</button>
            </div>
        </div>
        <div class="config-area hidden" id="configArea">
            <p>⚠️ 请配置API密钥</p>
            <input type="text" id="apiKeyInput" placeholder="输入豆包API密钥">
            <button onclick="saveConfig()">保存配置</button>
        </div>
    </div>
    <script>
        const chatBox = document.getElementById('chatBox');
        const messageInput = document.getElementById('messageInput');
        const configArea = document.getElementById('configArea');
        const apiKeyInput = document.getElementById('apiKeyInput');

        // 加载配置
        fetch('/api/config')
            .then(r => r.json())
            .then(config => {
                if (!config.api_key) {
                    configArea.classList.remove('hidden');
                } else {
                    apiKeyInput.value = config.api_key;
                }
            });

        function addMessage(text, isUser) {
            const div = document.createElement('div');
            div.className = 'message ' + (isUser ? 'user' : 'assistant');
            div.textContent = text;
            chatBox.appendChild(div);
            chatBox.scrollTop = chatBox.scrollHeight;
        }

        async function sendMessage() {
            const text = messageInput.value.trim();
            if (!text) return;

            addMessage(text, true);
            messageInput.value = '';

            const btn = document.querySelector('.input-area button');
            btn.disabled = true;

            try {
                const res = await fetch('/api/chat', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ message: text })
                });
                const data = await res.json();
                if (data.error) {
                    alert('错误: ' + data.error);
                } else {
                    addMessage(data.response, false);
                }
            } catch (e) {
                alert('网络错误: ' + e.message);
            }

            btn.disabled = false;
        }

        function saveConfig() {
            const apiKey = apiKeyInput.value.trim();
            if (!apiKey) {
                alert('请输入API密钥');
                return;
            }
            fetch('/api/config', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ api_key: apiKey })
            }).then(() => {
                alert('配置已保存，刷新页面生效');
                location.reload();
            });
        }

        messageInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') sendMessage();
        });
    </script>
</body>
</html>
"""

# 全局配置（简单存储）
config_data = load_config()


@app.route('/')
def index():
    """主页"""
    return render_template_string(HTML_TEMPLATE)


@app.route('/api/config', methods=['GET'])
def get_config():
    """获取配置"""
    return jsonify({
        "api_key": config_data.get("ARK_API_KEY", ""),
        "model_name": config_data.get("MODEL_NAME", "")
    })


@app.route('/api/config', methods=['POST'])
def save_config_route():
    """保存配置"""
    data = request.json
    config_data["ARK_API_KEY"] = data.get("api_key", "")
    save_config(config_data)
    return jsonify({"success": True})


@app.route('/api/chat', methods=['POST'])
def chat():
    """对话接口"""
    if not config_data.get("ARK_API_KEY"):
        return jsonify({"error": "请先配置API密钥"})

    # 导入在路由内部，避免启动时检查
    from src.services.ai_service import AIService
    from src.models.personality import PersonalityProfile

    ai_service = AIService()
    ai_service.api_key = config_data["ARK_API_KEY"]
    ai_service.base_url = config_data["BASE_URL"]
    ai_service.model_name = config_data["MODEL_NAME"]

    personality = PersonalityProfile()

    try:
        import asyncio
        message = request.json.get("message", "")
        system_prompt = personality.get_conversation_context_prompt("你")

        response = asyncio.run(asyncio.to_thread(
            ai_service.client.chat.completions.create,
            model=ai_service.model_name,
            messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": message}],
            temperature=0.8,
            max_tokens=1000
        ))

        content = response.choices[0].message.content
        enhanced = personality.enhance_response(content)

        return jsonify({"response": enhanced})
    except Exception as e:
        return jsonify({"error": str(e)})


def run_web():
    """运行Web服务"""
    print("=" * 50)
    print("小缘AI红娘 - Web界面")
    print("=" * 50)
    print("\n请在浏览器中访问: http://127.0.0.1:5000")
    print("按 Ctrl+C 退出\n")
    app.run(host='0.0.0.0', port=5000, debug=False)


if __name__ == '__main__':
    run_web()
