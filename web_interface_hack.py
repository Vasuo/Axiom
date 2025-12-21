"""
web_interface_hack.py
Ретро-хакинг веб-интерфейс в стиле Матрицы
"""

from flask import Flask, render_template, jsonify, Response, request
import asyncio
import json
import threading
import time
from datetime import datetime

app = Flask(__name__)

# Глобальная ссылка на агента
current_agent = None

# Генератор "матричного" фона
def generate_matrix_code():
    """Генерация случайного матричного кода для фона"""
    import random
    chars = "01アイウエオカキクケコサシスセソタチツテト"
    lines = []
    for _ in range(15):
        line = ''.join(random.choice(chars) for _ in range(40))
        lines.append(line)
    return lines

@app.route('/')
def index():
    """Главная страница с хакинг интерфейсом"""
    matrix_code = generate_matrix_code()
    
    return f'''
<!DOCTYPE html>
<html>
<head>
    <title>IDLE-Ai-agent :: TERMINAL</title>
    <meta charset="utf-8">
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Source+Code+Pro:wght@300;400;600&display=swap');
        
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        
        body {{
            font-family: 'Source Code Pro', monospace;
            background: #000;
            color: #0f0;
            overflow-x: hidden;
            height: 100vh;
            position: relative;
        }}
        
        /* Матричный фон */
        #matrix-bg {{
            position: fixed;
            top: 0; left: 0;
            width: 100%; height: 100%;
            opacity: 0.1;
            z-index: -1;
            font-size: 14px;
            line-height: 1.2;
            white-space: pre;
            color: #0f0;
            pointer-events: none;
        }}
        
        /* Главный контейнер */
        .terminal {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            grid-template-rows: auto 1fr auto;
            gap: 10px;
            padding: 20px;
            height: 100vh;
            max-width: 2000px;
            margin: 0 auto;
            border: 1px solid #0f0;
            box-shadow: 
                0 0 20px #0f0,
                inset 0 0 20px rgba(0, 255, 0, 0.1);
            position: relative;
            overflow: hidden;
        }}
        
        /* Эффект старых мониторов */
        .terminal::before {{
            content: "";
            position: absolute;
            top: 0; left: 0;
            right: 0; bottom: 0;
            background: 
                repeating-linear-gradient(
                    0deg,
                    rgba(0, 20, 0, 0.15) 0px,
                    rgba(0, 20, 0, 0.15) 1px,
                    transparent 1px,
                    transparent 2px
                );
            pointer-events: none;
            z-index: 1;
        }}
        
        /* Заголовок */
        .header {{
            grid-column: 1 / -1;
            border-bottom: 1px solid #0f0;
            padding: 15px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            background: rgba(0, 30, 0, 0.7);
        }}
        
        .logo {{
            font-size: 24px;
            font-weight: 600;
            letter-spacing: 3px;
            text-shadow: 0 0 10px #0f0;
        }}
        
        .logo::before {{ content: ">>> "; color: #0f0; }}
        .logo::after {{ content: " <<<"; color: #0f0; }}
        
        .status-led {{
            width: 12px;
            height: 12px;
            border-radius: 50%;
            background: #0f0;
            box-shadow: 0 0 10px #0f0;
            animation: pulse 2s infinite;
        }}
        
        @keyframes pulse {{
            0%, 100% {{ opacity: 1; }}
            50% {{ opacity: 0.5; }}
        }}
        
        /* Блоки интерфейса */
        .panel {{
            background: rgba(0, 20, 0, 0.8);
            border: 1px solid #0f0;
            padding: 15px;
            position: relative;
            overflow: hidden;
        }}
        
        .panel::before {{
            content: "";
            position: absolute;
            top: 0; left: 0;
            right: 0; height: 1px;
            background: linear-gradient(90deg, transparent, #0f0, transparent);
        }}
        
        .panel-title {{
            color: #0f0;
            font-size: 14px;
            margin-bottom: 10px;
            text-transform: uppercase;
            letter-spacing: 2px;
            border-bottom: 1px solid #0f0;
            padding-bottom: 5px;
        }}
        
        /* Монитор статуса */
        #status-monitor {{
            grid-column: 1;
            grid-row: 2;
        }}
        
        .status-grid {{
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 10px;
            font-size: 12px;
        }}
        
        .status-item {{
            padding: 8px;
            background: rgba(0, 40, 0, 0.5);
            border: 1px solid #0f0;
        }}
        
        .status-label {{
            color: #8f8;
            font-size: 11px;
        }}
        
        .status-value {{
            color: #0f0;
            font-weight: 600;
            margin-top: 5px;
        }}
        
        .progress-container {{
            grid-column: 1 / -1;
            margin-top: 10px;
        }}
        
        .progress-bar {{
            height: 20px;
            background: rgba(0, 40, 0, 0.5);
            border: 1px solid #0f0;
            position: relative;
            overflow: hidden;
        }}
        
        .progress-fill {{
            height: 100%;
            background: #0f0;
            width: 0%;
            transition: width 0.5s;
            position: relative;
        }}
        
        .progress-fill::after {{
            content: "";
            position: absolute;
            top: 0; left: 0; right: 0; bottom: 0;
            background: linear-gradient(
                90deg,
                transparent,
                rgba(255, 255, 255, 0.3),
                transparent
            );
            animation: scan 2s infinite linear;
        }}
        
        @keyframes scan {{
            0% {{ transform: translateX(-100%); }}
            100% {{ transform: translateX(100%); }}
        }}
        
        /* Монитор логов */
        #log-monitor {{
            grid-column: 2;
            grid-row: 2;
        }}
        
        .log-container {{
            height: 300px;
            overflow-y: auto;
            background: rgba(0, 10, 0, 0.9);
            border: 1px solid #0f0;
            padding: 10px;
            font-size: 11px;
            line-height: 1.4;
        }}
        
        .log-entry {{
            margin-bottom: 5px;
            padding-left: 10px;
            border-left: 2px solid #0f0;
            animation: fadeIn 0.3s;
        }}
        
        @keyframes fadeIn {{
            from {{ opacity: 0; transform: translateY(-5px); }}
            to {{ opacity: 1; transform: translateY(0); }}
        }}
        
        .log-time {{
            color: #8f8;
        }}
        
        .log-message {{
            color: #0f0;
        }}
        
        /* Панель управления */
        #control-panel {{
            grid-column: 1;
            grid-row: 3;
        }}
        
        .control-grid {{
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 10px;
        }}
        
        .hack-button {{
            background: rgba(0, 40, 0, 0.7);
            border: 1px solid #0f0;
            color: #0f0;
            padding: 12px;
            font-family: 'Source Code Pro', monospace;
            font-size: 12px;
            cursor: pointer;
            text-transform: uppercase;
            letter-spacing: 1px;
            transition: all 0.2s;
            position: relative;
            overflow: hidden;
        }}
        
        .hack-button:hover {{
            background: rgba(0, 60, 0, 0.9);
            box-shadow: 0 0 15px #0f0;
            transform: translateY(-2px);
        }}
        
        .hack-button:active {{
            transform: translateY(0);
        }}
        
        .hack-button::before {{
            content: ">";
            position: absolute;
            left: 5px;
            opacity: 0;
            transition: opacity 0.2s;
        }}
        
        .hack-button:hover::before {{
            opacity: 1;
        }}
        
        /* Панель кода */
        #code-panel {{
            grid-column: 2;
            grid-row: 3;
        }}
        
        .code-display {{
            height: 200px;
            overflow-y: auto;
            background: rgba(0, 10, 0, 0.9);
            border: 1px solid #0f0;
            padding: 10px;
            font-size: 10px;
            line-height: 1.3;
            white-space: pre;
            font-family: 'Source Code Pro', monospace;
        }}
        
        .code-line {{
            counter-increment: line;
            position: relative;
            padding-left: 30px;
        }}
        
        .code-line::before {{
            content: counter(line);
            position: absolute;
            left: 0;
            width: 25px;
            text-align: right;
            color: #8f8;
            font-size: 9px;
        }}
        
        /* Футер */
        .footer {{
            grid-column: 1 / -1;
            border-top: 1px solid #0f0;
            padding: 10px;
            font-size: 11px;
            color: #8f8;
            display: flex;
            justify-content: space-between;
            background: rgba(0, 30, 0, 0.7);
        }}
        
        .connection-status::before {{
            content: "●";
            color: #0f0;
            margin-right: 5px;
            animation: pulse 2s infinite;
        }}
        
        /* Скроллбар */
        ::-webkit-scrollbar {{
            width: 8px;
        }}
        
        ::-webkit-scrollbar-track {{
            background: rgba(0, 30, 0, 0.5);
        }}
        
        ::-webkit-scrollbar-thumb {{
            background: #0f0;
            border-radius: 4px;
        }}
        
        ::-webkit-scrollbar-thumb:hover {{
            background: #0f0;
            box-shadow: 0 0 10px #0f0;
        }}
        
        /* Анимации строки ввода */
        .input-container {{
            margin-top: 15px;
        }}
        
        .hack-input {{
            width: 100%;
            background: transparent;
            border: none;
            border-bottom: 1px solid #0f0;
            color: #0f0;
            font-family: 'Source Code Pro', monospace;
            font-size: 14px;
            padding: 8px;
            outline: none;
        }}
        
        .hack-input::placeholder {{
            color: #8f8;
            opacity: 0.7;
        }}
        
        .hack-input:focus {{
            border-bottom-color: #0f0;
            box-shadow: 0 2px 10px rgba(0, 255, 0, 0.3);
        }}
        
        /* Схематичные линии для декора */
        .schematic-lines {{
            position: absolute;
            top: 0; left: 0; right: 0; bottom: 0;
            pointer-events: none;
            z-index: 0;
            opacity: 0.1;
        }}
        
        .schematic-line {{
            position: absolute;
            background: #0f0;
        }}
        
        .line-1 {{ top: 25%; left: 0; right: 0; height: 1px; }}
        .line-2 {{ top: 0; bottom: 0; left: 33%; width: 1px; }}
        .line-3 {{ top: 0; bottom: 0; left: 66%; width: 1px; }}
        .line-4 {{ top: 75%; left: 0; right: 0; height: 1px; }}
    </style>
</head>
<body>
    <!-- Матричный фон -->
    <div id="matrix-bg"></div>
    
    <!-- Декоративные линии -->
    <div class="schematic-lines">
        <div class="schematic-line line-1"></div>
        <div class="schematic-line line-2"></div>
        <div class="schematic-line line-3"></div>
        <div class="schematic-line line-4"></div>
    </div>
    
    <!-- Главный терминал -->
    <div class="terminal">
        <!-- Заголовок -->
        <div class="header">
            <div class="logo">IDLE-Ai-agent // GAME DEV TERMINAL v2.3.7</div>
            <div class="status-led"></div>
        </div>
        
        <!-- Монитор статуса -->
        <div id="status-monitor" class="panel">
            <div class="panel-title">SYSTEM STATUS</div>
            <div class="status-grid">
                <div class="status-item">
                    <div class="status-label">AGENT STATE</div>
                    <div id="agent-state" class="status-value">INITIALIZING...</div>
                </div>
                <div class="status-item">
                    <div class="status-label">TASK PROGRESS</div>
                    <div id="task-progress" class="status-value">0%</div>
                </div>
                <div class="status-item">
                    <div class="status-label">CURRENT MODULE</div>
                    <div id="current-module" class="status-value">IDLE</div>
                </div>
                <div class="status-item">
                    <div class="status-label">ERROR COUNT</div>
                    <div id="error-count" class="status-value">0</div>
                </div>
                <div class="status-item">
                    <div class="status-label">CODE SIZE</div>
                    <div id="code-size" class="status-value">0 bytes</div>
                </div>
                <div class="status-item">
                    <div class="status-label">RAG SEARCHES</div>
                    <div id="rag-searches" class="status-value">0</div>
                </div>
            </div>
            
            <div class="progress-container">
                <div class="progress-bar">
                    <div id="progress-fill" class="progress-fill"></div>
                </div>
            </div>
            
            <!-- Декоративная схема -->
            <div style="margin-top: 15px; font-size: 9px; color: #8f8; opacity: 0.7;">
                [USER] → [PLANNER] → [CODER] → [FIXER] → [VISUALIZER] → [GAME]
            </div>
        </div>
        
        <!-- Монитор логов -->
        <div id="log-monitor" class="panel">
            <div class="panel-title">SYSTEM LOGS [REAL-TIME]</div>
            <div id="log-container" class="log-container">
                <div class="log-entry">
                    <span class="log-time">[{datetime.now().strftime('%H:%M:%S')}]</span>
                    <span class="log-message">SYSTEM INITIALIZED...</span>
                </div>
                <div class="log-entry">
                    <span class="log-time">[{datetime.now().strftime('%H:%M:%S')}]</span>
                    <span class="log-message">CONNECTING TO AGENT CORE...</span>
                </div>
                <div class="log-entry">
                    <span class="log-time">[{datetime.now().strftime('%H:%M:%S')}]</span>
                    <span class="log-message">RAG DATABASE: ONLINE</span>
                </div>
                <div class="log-entry">
                    <span class="log-time">[{datetime.now().strftime('%H:%M:%S')}]</span>
                    <span class="log-message">READY FOR TASK INPUT</span>
                </div>
            </div>
        </div>
        
        <!-- Панель управления -->
        <div id="control-panel" class="panel">
            <div class="panel-title">CONTROL INTERFACE</div>
            <div class="control-grid">
                <button class="hack-button" onclick="startTask()">START GAME DEV</button>
                <button class="hack-button" onclick="pauseAgent()">PAUSE/RESUME</button>
                <button class="hack-button" onclick="viewCode()">VIEW CODE</button>
                <button class="hack-button" onclick="testRun()">TEST RUN</button>
                <button class="hack-button" onclick="exportProject()">EXPORT</button>
                <button class="hack-button" onclick="resetSystem()">RESET</button>
            </div>
            
            <div class="input-container">
                <input type="text" 
                       id="task-input" 
                       class="hack-input" 
                       placeholder="DESCRIBE GAME (e.g., 'CREATE SNAKE GAME')"
                       onkeypress="if(event.key==='Enter') startTask()">
            </div>
            
            <!-- Декоративные кодовые строки -->
            <div style="margin-top: 15px; font-size: 9px; color: #8f8; opacity: 0.5;">
                > class GameDevAgent: <br>
                > &nbsp;&nbsp;def __init__(self): <br>
                > &nbsp;&nbsp;&nbsp;&nbsp;self.state = TaskState() <br>
                > &nbsp;&nbsp;&nbsp;&nbsp;self.rag = FastRAG()
            </div>
        </div>
        
        <!-- Панель кода -->
        <div id="code-panel" class="panel">
            <div class="panel-title">GENERATED CODE [LIVE]</div>
            <div id="code-display" class="code-display">
                <div class="code-line"># CODE WILL APPEAR HERE</div>
                <div class="code-line"># WHEN AGENT IS ACTIVE</div>
                <div class="code-line"></div>
                <div class="code-line">import pygame</div>
                <div class="code-line">import sys</div>
                <div class="code-line"></div>
                <div class="code-line">def main():</div>
                <div class="code-line">    pygame.init()</div>
                <div class="code-line">    screen = pygame.display.set_mode((800, 600))</div>
                <div class="code-line">    clock = pygame.time.Clock()</div>
                <div class="code-line"></div>
                <div class="code-line">    # AGENT-GENERATED CODE WILL APPEAR BELOW</div>
                <div class="code-line">    # ...</div>
            </div>
        </div>
        
        <!-- Футер -->
        <div class="footer">
            <div class="connection-status">CONNECTED TO AGENT CORE</div>
            <div id="current-time">{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</div>
            <div>VERSION 2.3.7 // MODE: INTERACTIVE</div>
        </div>
    </div>
    
    <script>
        // Матричный фон
        function updateMatrixBg() {{
            const chars = "01アイウエオカキクケコサシスセソタチツテトナニヌネノハヒフヘホ";
            const bg = document.getElementById('matrix-bg');
            let content = '';
            
            for (let i = 0; i < 40; i++) {{
                let line = '';
                for (let j = 0; j < 80; j++) {{
                    if (Math.random() > 0.7) {{
                        line += chars[Math.floor(Math.random() * chars.length)];
                    }} else {{
                        line += ' ';
                    }}
                }}
                content += line + '\\n';
            }}
            
            bg.textContent = content;
        }}
        
        // Обновление времени
        function updateTime() {{
            const now = new Date();
            document.getElementById('current-time').textContent = 
                now.toISOString().replace('T', ' ').substr(0, 19);
        }}
        
        // Обновление статуса
        async function updateStatus() {{
            try {{
                const response = await fetch('/api/status');
                const data = await response.json();
                
                // Обновляем статус агента
                document.getElementById('agent-state').textContent = 
                    data.agent === 'active' ? 'ACTIVE' : 'IDLE';
                
                // Обновляем прогресс
                const progress = data.progress || 0;
                document.getElementById('task-progress').textContent = progress.toFixed(1) + '%';
                document.getElementById('progress-fill').style.width = progress + '%';
                
                // Обновляем другие поля
                if (data.agent === 'active') {{
                    document.getElementById('current-module').textContent = 
                        data.current_subtask ? 'CODER' : 'PLANNER';
                    document.getElementById('error-count').textContent = data.errors_count;
                    document.getElementById('code-size').textContent = data.code_length + ' bytes';
                    document.getElementById('rag-searches').textContent = 
                        data.stats?.rag_searches || 0;
                }}
                
                // Добавляем лог если статус изменился
                if (window.lastStatus !== data.status) {{
                    addLog(`STATUS CHANGE: ${{data.status}}`);
                    window.lastStatus = data.status;
                }}
                
            }} catch (error) {{
                console.error('Status update error:', error);
                addLog(`ERROR: Failed to fetch status`);
            }}
        }}
        
        // Добавление лога
        function addLog(message) {{
            const logContainer = document.getElementById('log-container');
            const now = new Date();
            const timeStr = now.toTimeString().substr(0, 8);
            
            const logEntry = document.createElement('div');
            logEntry.className = 'log-entry';
            logEntry.innerHTML = `
                <span class="log-time">[${{timeStr}}]</span>
                <span class="log-message">${{message}}</span>
            `;
            
            logContainer.appendChild(logEntry);
            logContainer.scrollTop = logContainer.scrollHeight;
            
            // Ограничиваем количество логов
            if (logContainer.children.length > 50) {{
                logContainer.removeChild(logContainer.firstChild);
            }}
        }}
        
        // Запуск задачи
        async function startTask() {{
            const taskInput = document.getElementById('task-input');
            const task = taskInput.value.trim();
            
            if (!task) {{
                addLog("ERROR: No task specified");
                return;
            }}
            
            addLog(`STARTING TASK: "${{task}}"`);
            taskInput.value = '';
            
            try {{
                const response = await fetch('/api/start_task', {{
                    method: 'POST',
                    headers: {{'Content-Type': 'application/json'}},
                    body: JSON.stringify({{task: task}})
                }});
                
                const data = await response.json();
                if (data.success) {{
                    addLog("TASK ACCEPTED: Processing started");
                }} else {{
                    addLog(`ERROR: ${{data.error}}`);
                }}
            }} catch (error) {{
                addLog(`NETWORK ERROR: ${{error.message}}`);
            }}
        }}
        
        // Просмотр кода
        async function viewCode() {{
            try {{
                const response = await fetch('/api/code');
                const data = await response.json();
                
                const codeDisplay = document.getElementById('code-display');
                if (data.code) {{
                    const lines = data.code.split('\\n');
                    let html = '';
                    for (let i = 0; i < Math.min(lines.length, 50); i++) {{
                        html += `<div class="code-line">${{escapeHtml(lines[i])}}</div>`;
                    }}
                    if (lines.length > 50) {{
                        html += `<div class="code-line"># ... ${{lines.length - 50}} more lines</div>`;
                    }}
                    codeDisplay.innerHTML = html;
                    addLog("CODE VIEWER: Loaded current code");
                }}
            }} catch (error) {{
                addLog(`ERROR: Failed to load code`);
            }}
        }}
        
        // Экранирование HTML
        function escapeHtml(text) {{
            const div = document.createElement('div');
            div.textContent = text;
            return div.innerHTML;
        }}
        
        // Остальные функции управления
        function pauseAgent() {{
            addLog("COMMAND: Pause/Resume agent - NOT IMPLEMENTED");
        }}
        
        function testRun() {{
            addLog("COMMAND: Test run game - NOT IMPLEMENTED");
        }}
        
        function exportProject() {{
            addLog("COMMAND: Export project - NOT IMPLEMENTED");
        }}
        
        function resetSystem() {{
            if (confirm("Reset system to idle state?")) {{
                addLog("SYSTEM RESET: Returning to idle state");
                document.getElementById('agent-state').textContent = 'IDLE';
                document.getElementById('progress-fill').style.width = '0%';
            }}
        }}
        
        // Инициализация
        window.lastStatus = null;
        
        // Запускаем обновления
        setInterval(updateMatrixBg, 100);
        setInterval(updateTime, 1000);
        setInterval(updateStatus, 2000);
        
        // Добавляем несколько декоративных логов
        setTimeout(() => addLog("SYSTEM: All modules operational"), 1000);
        setTimeout(() => addLog("RAG: Database contains 42 templates"), 3000);
        setTimeout(() => addLog("AI: Models phi3, codellama, qwen2.5 loaded"), 5000);
        
        // Примеры задач при клике на placeholder
        document.getElementById('task-input').addEventListener('click', function() {{
            if (!this.value) {{
                const examples = [
                    "CREATE SNAKE GAME",
                    "MAKE PLATFORMER WITH JUMPING",
                    "BUILD PONG GAME",
                    "CREATE SHOOTING GAME"
                ];
                this.placeholder = examples[Math.floor(Math.random() * examples.length)];
            }}
        }});
    </script>
</body>
</html>
'''

@app.route('/api/status')
def get_status():
    """Получение статуса агента"""
    if not current_agent:
        return jsonify({
            "agent": "disconnected",
            "status": "offline",
            "progress": 0,
            "errors_count": 0,
            "code_length": 0,
            "stats": {"rag_searches": 0}
        })
    
    # Запускаем асинхронную функцию в потоке
    try:
        status = asyncio.run_coroutine_threadsafe(
            current_agent.get_interface_status(),
            current_agent.loop
        ).result(timeout=2)
        return jsonify(status)
    except:
        return jsonify({"agent": "error", "status": "timeout"})

@app.route('/api/start_task', methods=['POST'])
def start_task():
    """Запуск новой задачи"""
    if not current_agent:
        return jsonify({"error": "Agent not initialized"})
    
    data = request.json
    task = data.get('task', '')
    
    if not task:
        return jsonify({"error": "No task provided"})
    
    # Запускаем в отдельном потоке
    def run_task():
        asyncio.run_coroutine_threadsafe(
            current_agent.develop_game(task),
            current_agent.loop
        )
    
    threading.Thread(target=run_task, daemon=True).start()
    
    return jsonify({"success": True, "message": "Task started"})

@app.route('/api/code')
def get_code():
    """Получение текущего кода"""
    if not current_agent or not current_agent.current_state:
        return jsonify({"code": "# No active task\n# Agent is idle"})
    
    state = current_agent.current_state
    code = state.current_code if hasattr(state, 'current_code') else ""
    
    return jsonify({
        "code": code[:5000],  # Ограничиваем для веба
        "length": len(code),
        "task": state.original_task
    })

@app.route('/api/logs_stream')
def logs_stream():
    """Поток логов"""
    def generate():
        # Простая имитация логов
        import random
        messages = [
            "RAG: Found 3 relevant templates",
            "CODER: Generating PyGame code",
            "FIXER: Analyzing potential errors",
            "PLANNER: Decomposed task into 5 subtasks",
            "EXECUTOR: Code executed successfully",
            "VISUALIZER: Generating sprites"
        ]
        
        while True:
            time.sleep(random.uniform(1, 3))
            message = random.choice(messages)
            yield f"data: {json.dumps({'log': message})}\n\n"
    
    return Response(generate(), mimetype='text/event-stream')

def start_hack_interface(agent, host='localhost', port=8080):
    """Запуск хакинг интерфейса"""
    global current_agent
    current_agent = agent
    
    print(f"\n{'='*60}")
    print("🚀 ЗАПУСК ХАКИНГ ИНТЕРФЕЙСА")
    print(f"{'='*60}")
    print("Стиль: Ретро-хакинг / Матрица")
    print(f"Адрес: http://{host}:{port}")
    print("Цветовая схема: Зелёный/Чёрный")
    print("Шрифт: Source Code Pro (моноширинный)")
    print(f"{'='*60}")
    print("Откройте в браузере для управления агентом")
    print("Для остановки нажмите Ctrl+C в этом окне")
    print(f"{'='*60}")
    
    # Сохраняем loop для асинхронных операций
    current_agent.loop = asyncio.get_event_loop()
    
    # Запускаем Flask в отдельном потоке
    def run_flask():
        app.run(host=host, port=port, debug=False, use_reloader=False, threaded=True)
    
    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()
    
    return flask_thread

# Для тестирования
if __name__ == "__main__":
    print("Тестовый запуск хакинг интерфейса...")
    app.run(host='localhost', port=8080, debug=True)