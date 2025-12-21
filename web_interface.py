"""
web_interface.py
Минимальный веб-интерфейс для агента
"""

from flask import Flask, render_template, jsonify, Response, request
import asyncio
import json
import threading

app = Flask(__name__)

# Глобальная ссылка на агента
current_agent = None

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/status')
def get_status():
    """Получение статуса агента"""
    if not current_agent:
        return jsonify({"error": "Agent not initialized"})
    
    # Запускаем асинхронную функцию в потоке
    status = asyncio.run_coroutine_threadsafe(
        current_agent.get_interface_status(),
        current_agent.loop
    ).result()
    
    return jsonify(status)

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

@app.route('/api/logs')
def stream_logs():
    """Поток логов"""
    def generate():
        if current_agent and current_agent.interface_bridge:
            # Здесь будет реализация потоковой передачи логов
            yield f"data: {json.dumps({'log': 'Log streaming not implemented'})}\n\n"
    
    return Response(generate(), mimetype='text/event-stream')

@app.route('/api/rag/search', methods=['GET'])
def search_rag():
    """Поиск в RAG"""
    if not current_agent:
        return jsonify({"error": "Agent not initialized"})
    
    query = request.args.get('q', '')
    category = request.args.get('category')
    
    if not query:
        return jsonify({"error": "No query provided"})
    
    results = asyncio.run_coroutine_threadsafe(
        current_agent.search_rag_from_interface(query, category),
        current_agent.loop
    ).result()
    
    return jsonify({"results": results})

def start_web_server(agent, host='localhost', port=8080):
    """Запуск веб-сервера"""
    global current_agent
    current_agent = agent
    
    print(f"Запуск веб-сервера на http://{host}:{port}")
    print("Для остановки нажмите Ctrl+C")
    
    # Создаем простой HTML шаблон
    import os
    template_dir = os.path.join(os.path.dirname(__file__), 'templates')
    os.makedirs(template_dir, exist_ok=True)
    
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>IDLE-Ai-agent</title>
        <meta charset="utf-8">
        <style>
            body { font-family: Arial, sans-serif; margin: 20px; }
            .container { max-width: 1200px; margin: 0 auto; }
            .status-box { background: #f5f5f5; padding: 20px; border-radius: 5px; margin-bottom: 20px; }
            .progress-bar { height: 20px; background: #ddd; border-radius: 10px; overflow: hidden; }
            .progress-fill { height: 100%; background: #4CAF50; transition: width 0.3s; }
            .log-box { background: #000; color: #0f0; padding: 10px; font-family: monospace; height: 300px; overflow-y: scroll; }
            .btn { background: #4CAF50; color: white; border: none; padding: 10px 20px; cursor: pointer; border-radius: 5px; }
            .btn:hover { background: #45a049; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🎮 IDLE-Ai-agent для разработки игр</h1>
            
            <div class="status-box">
                <h2>🤖 Статус агента</h2>
                <div id="status">Загрузка...</div>
                <div class="progress-bar">
                    <div id="progress-fill" class="progress-fill" style="width: 0%"></div>
                </div>
            </div>
            
            <div>
                <h2>🚀 Создать игру</h2>
                <input type="text" id="task-input" placeholder="Опишите игру..." style="width: 300px; padding: 10px;">
                <button class="btn" onclick="startTask()">Начать разработку</button>
                
                <h3>Примеры:</h3>
                <button class="btn" onclick="useExample('Создай окно 800x600 с синим фоном')">Окно с синим фоном</button>
                <button class="btn" onclick="useExample('Создай красный квадрат, управляемый стрелками')">Красный квадрат</button>
                <button class="btn" onclick="useExample('Создай упрощенную змейку')">Змейка</button>
            </div>
            
            <div style="margin-top: 30px;">
                <h2>📝 Логи</h2>
                <div id="log-box" class="log-box"></div>
            </div>
        </div>
        
        <script>
            let logBox = document.getElementById('log-box');
            
            // Обновление статуса
            function updateStatus() {
                fetch('/api/status')
                    .then(r => r.json())
                    .then(data => {
                        let statusDiv = document.getElementById('status');
                        let progressFill = document.getElementById('progress-fill');
                        
                        if (data.agent === 'active') {
                            statusDiv.innerHTML = `
                                <strong>Задача:</strong> ${data.original_task}<br>
                                <strong>Статус:</strong> ${data.status}<br>
                                <strong>Подзадача:</strong> ${data.current_subtask || 'N/A'}<br>
                                <strong>Ошибок:</strong> ${data.errors_count}
                            `;
                            progressFill.style.width = data.progress + '%';
                        } else {
                            statusDiv.innerHTML = 'Агент ожидает задачи';
                            progressFill.style.width = '0%';
                        }
                    });
                
                setTimeout(updateStatus, 2000);
            }
            
            // Запуск задачи
            function startTask() {
                let task = document.getElementById('task-input').value;
                if (!task) {
                    alert('Введите описание игры');
                    return;
                }
                
                fetch('/api/start_task', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({task: task})
                }).then(r => r.json())
                  .then(data => {
                      if (data.success) {
                          addLog('🚀 Задача запущена: ' + task);
                      } else {
                          addLog('❌ Ошибка: ' + data.error);
                      }
                  });
            }
            
            // Использование примера
            function useExample(example) {
                document.getElementById('task-input').value = example;
            }
            
            // Добавление лога
            function addLog(message) {
                let timestamp = new Date().toLocaleTimeString();
                logBox.innerHTML += `[${timestamp}] ${message}<br>`;
                logBox.scrollTop = logBox.scrollHeight;
            }
            
            // Запуск
            updateStatus();
            addLog('🌐 Веб-интерфейс запущен');
        </script>
    </body>
    </html>
    """
    
    with open(os.path.join(template_dir, 'index.html'), 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    # Запускаем Flask в отдельном потоке
    def run_flask():
        app.run(host=host, port=port, debug=False, use_reloader=False)
    
    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()
    
    return flask_thread