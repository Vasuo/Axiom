"""
interface_bridge.py
Мост между агентом и интерфейсами
"""

import asyncio
import logging
from typing import Dict, Any, Optional, AsyncGenerator
from datetime import datetime
import json

logger = logging.getLogger(__name__)

class InterfaceBridge:
    """Центральный мост для всех интерфейсов"""
    
    def __init__(self, agent):
        self.agent = agent
        self.clients = []  # WebSocket клиенты для веб-интерфейса
        self.status_history = []
        logger.info("InterfaceBridge инициализирован")
    
    async def get_agent_status(self) -> Dict[str, Any]:
        """Получение полного статуса агента"""
        if not self.agent.current_state:
            return {
                "agent": "idle",
                "timestamp": datetime.now().isoformat(),
                "stats": self.agent.get_stats() if hasattr(self.agent, 'get_stats') else {}
            }
        
        state = self.agent.current_state
        return {
            "agent": "active",
            "task_id": state.task_id,
            "original_task": state.original_task,
            "status": state.task_status.value,
            "progress": state.progress_percentage if hasattr(state, 'progress_percentage') else 0,
            "current_subtask": state.current_subtask,
            "subtask_index": state.current_subtask_index,
            "total_subtasks": len(state.subtasks),
            "validation_status": state.validation_status.value,
            "errors_count": len(state.errors_detected),
            "code_length": len(state.current_code),
            "timestamp": datetime.now().isoformat(),
            "stats": self.agent.get_stats() if hasattr(self.agent, 'get_stats') else {}
        }
    
    async def stream_logs(self, level: str = "INFO") -> AsyncGenerator[str, None]:
        """Поток логов в реальном времени"""
        # Создаем свой логгер для перехвата
        import io
        import sys
        
        class LogStream:
            def __init__(self):
                self.buffer = io.StringIO()
            
            def write(self, message):
                if message.strip():
                    yield f"data: {json.dumps({'log': message.strip()})}\n\n"
        
        log_stream = LogStream()
        
        # Временно перенаправляем вывод
        old_stdout = sys.stdout
        sys.stdout = log_stream
        
        try:
            while True:
                # Получаем новые логи из буфера
                log_stream.buffer.seek(0)
                content = log_stream.buffer.read()
                if content:
                    yield f"data: {json.dumps({'log': content})}\n\n"
                    log_stream.buffer.truncate(0)
                
                await asyncio.sleep(0.5)
        finally:
            sys.stdout = old_stdout
    
    async def update_rag(self, category: str, data: Dict) -> bool:
        """Обновление RAG базы через интерфейс"""
        try:
            if not self.agent.rag:
                return False
            
            # Добавляем пример в RAG
            self.agent.rag.add_document(
                text=data["text"],
                metadata={
                    "category": category,
                    "tags": ",".join(data.get("tags", [])),
                    "id": f"user_{int(datetime.now().timestamp())}",
                    "type": data.get("type", "user_example")
                }
            )
            
            logger.info(f"Добавлен пример в RAG: {category}")
            return True
            
        except Exception as e:
            logger.error(f"Ошибка обновления RAG: {e}")
            return False
    
    async def search_rag(self, query: str, category: Optional[str] = None) -> list:
        """Поиск в RAG базе"""
        try:
            if not self.agent.rag:
                return []
            
            results = self.agent.rag.search(query, category)
            return results[:5]  # Ограничиваем для интерфейса
            
        except Exception as e:
            logger.error(f"Ошибка поиска RAG: {e}")
            return []
    
    async def execute_code(self, code: str) -> Dict[str, Any]:
        """Выполнение кода и возврат результата"""
        from modules.fixer import FixerDetector
        
        try:
            # Используем фиксер для безопасного выполнения
            fixer = FixerDetector(self.agent.ollama_client)
            result = await fixer._execute_code_safe(code)
            
            return {
                "success": result["success"],
                "output": result["output"],
                "return_code": result.get("return_code", -1)
            }
            
        except Exception as e:
            return {
                "success": False,
                "output": f"Execution error: {str(e)}",
                "return_code": -1
            }
    
    async def broadcast_status(self, status: Dict[str, Any]):
        """Широковещательная рассылка статуса (для веб-интерфейса)"""
        for client in self.clients:
            try:
                await client.send(json.dumps({
                    "type": "status_update",
                    "data": status
                }))
            except:
                # Удаляем отключенных клиентов
                self.clients.remove(client)
    
    def add_web_client(self, client):
        """Добавление веб-клиента"""
        self.clients.append(client)
    
    def remove_web_client(self, client):
        """Удаление веб-клиента"""
        if client in self.clients:
            self.clients.remove(client)