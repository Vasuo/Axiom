"""
Модуль аналитика - планирует выполнение задач в двух режимах
"""
import json
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
from ollama_client import OllamaClient
from config import AgentConfig

class Analyzer:
    def __init__(self):
        self.config = AgentConfig()
        self.ollama = OllamaClient(model=self.config.ANALYZER_MODEL)
        
    def create_plan(self, task: str, project_snapshot: Dict[str, str], 
                   history_context: str = None, mode: str = "dev") -> Optional[Dict[str, Any]]:
        """
        Создает план выполнения задачи
        
        Args:
            task: Задача от пользователя (уже очищенная от режима)
            project_snapshot: Текущее состояние проекта
            history_context: История предыдущих итераций
            mode: Режим работы ("dev" или "dbg")
            
        Returns:
            План в формате {"analysis": "...", "plan": [...], "mode": "..."} или None
        """
        print(f"🔍 Режим аналитика: {self.config.ANALYZER_MODES.get(mode, mode)}")
        
        # Формируем промпт
        prompt = self._build_analyzer_prompt(task, project_snapshot, history_context, mode)
        
        # Выбираем системный промпт
        if mode == "dbg":
            system_prompt = self.config.ANALYZER_DEBUGGER_PROMPT
        else:
            system_prompt = self.config.ANALYZER_DEVELOPER_PROMPT
        
        # Форматируем промпт
        system_prompt = system_prompt.format(
            history_context=history_context or "История отсутствует",
            format_instructions=self._get_format_instructions()
        )
        
        # Логируем запрос
        self._log_request("analyzer", mode, task, system_prompt[:500] + "...", prompt[:500] + "...")
        
        # Отправляем запрос
        response = self.ollama.generate_response(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ],
            format_json=True
        )
        
        # Логируем ответ
        if response:
            self._log_response("analyzer", mode, response)
        
        if not response:
            return None
            
        # Валидация ответа
        validated = self._validate_plan(response)
        if validated:
            validated["mode"] = mode
        return validated
    
    def _build_analyzer_prompt(self, task: str, snapshot: Dict[str, str], 
                              history_context: str, mode: str) -> str:
        """Строит промпт для аналитика"""
        
        # Форматируем ВЕСЬ код проекта (ограничиваем для экономии токенов)
        project_context = self._format_full_snapshot(snapshot)
        
        prompt_lines = [
            f"# РЕЖИМ РАБОТЫ: {self.config.ANALYZER_MODES.get(mode, mode).upper()}",
            "",
            "# ТЕКУЩЕЕ СОСТОЯНИЕ ВСЕГО ПРОЕКТА:",
            project_context,
            "",
            "# ЗАДАЧА ПОЛЬЗОВАТЕЛЯ:",
            task,
            "",
            "# ИНСТРУКЦИЯ:",
            "Проанализируй и создай план. Учитывай ВЕСЬ код выше."
        ]
        
        return "\n".join(prompt_lines)
    
    def _format_full_snapshot(self, snapshot: Dict[str, str]) -> str:
        """Форматирует ВЕСЬ снапшот проекта (с ограничениями)"""
        if not snapshot:
            return "ПРОЕКТ ПУСТ"
        
        formatted_parts = []
        
        for file_path, content in sorted(snapshot.items()):
            lines = content.split('\n')
            total_lines = len(lines)
            
            # Ограничиваем размер каждого файла
            max_lines = 100  # Увеличили для полного анализа
            if total_lines > max_lines:
                # Показываем начало и конец файла
                preview = '\n'.join(lines[:max_lines//2]) + "\n...\n" + '\n'.join(lines[-max_lines//2:])
                line_info = f" ({total_lines} строк, показано {max_lines})"
            else:
                preview = content
                line_info = f" ({total_lines} строк)"
            
            formatted_parts.append(f"=== {file_path}{line_info} ===")
            formatted_parts.append(preview)
            formatted_parts.append("")  # Пустая строка между файлами
        
        return "\n".join(formatted_parts)
    
    def _get_format_instructions(self) -> str:
        """Возвращает инструкции по формату ответа"""
        return """Возвращай ТОЛЬКО JSON:
{
    "analysis": "Краткий анализ задачи (1-2 предложения)",
    "plan": [
        {
            "file": "game.py",
            "task": "Конкретная задача для этого файла",
            "requirements": ["Требование 1", "Требование 2"]
        }
    ]
}"""
    
    def _validate_plan(self, response: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Валидирует план от аналитика"""
        required_keys = {"analysis", "plan"}
        if not all(key in response for key in required_keys):
            print("❌ Ответ аналитика не содержит обязательных полей")
            return None
            
        if not isinstance(response["plan"], list):
            print("❌ Поле 'plan' должно быть списком")
            return None
            
        if len(response["plan"]) == 0:
            print("⚠️  Аналитик не создал шагов плана")
            return None
            
        # Валидация каждого шага
        valid_steps = []
        for i, step in enumerate(response["plan"]):
            if not isinstance(step, dict):
                print(f"❌ Шаг {i} не является словарем")
                continue
                
            if "file" not in step or "task" not in step:
                print(f"❌ Шаг {i} не содержит 'file' или 'task'")
                continue
                
            if "requirements" not in step:
                step["requirements"] = []
                
            valid_steps.append(step)
        
        if not valid_steps:
            return None
            
        return {
            "analysis": response["analysis"],
            "plan": valid_steps
        }
    
    def _log_request(self, agent_type: str, mode: str, task: str, 
                    system_prompt: str, user_prompt: str):
        """Логирует запрос к ИИ"""
        try:
            log_entry = {
                "timestamp": datetime.now().isoformat(),
                "type": f"{agent_type}_request",
                "mode": mode,
                "task": task,
                "system_prompt_preview": system_prompt,
                "user_prompt_preview": user_prompt
            }
            
            with open(self.config.DETAILED_LOG_FILE, 'a', encoding='utf-8') as f:
                f.write(json.dumps(log_entry, ensure_ascii=False) + '\n')
        except Exception as e:
            print(f"⚠️  Ошибка логирования запроса: {e}")
    
    def _log_response(self, agent_type: str, mode: str, response: Any):
        """Логирует ответ от ИИ"""
        try:
            log_entry = {
                "timestamp": datetime.now().isoformat(),
                "type": f"{agent_type}_response", 
                "mode": mode,
                "response": response
            }
            
            with open(self.config.DETAILED_LOG_FILE, 'a', encoding='utf-8') as f:
                f.write(json.dumps(log_entry, ensure_ascii=False) + '\n')
        except Exception as e:
            print(f"⚠️  Ошибка логирования ответа: {e}")