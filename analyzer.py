"""
Модуль аналитика - планирует выполнение задач
"""
import json
from typing import Dict, List, Any, Optional
from ollama_client import OllamaClient
from config import AgentConfig

class Analyzer:
    def __init__(self):
        self.config = AgentConfig()
        self.ollama = OllamaClient(model=self.config.ANALYZER_MODEL)
        
    def create_plan(self, task: str, project_snapshot: Dict[str, str]) -> Optional[Dict[str, Any]]:
        """
        Создает план выполнения задачи
        
        Args:
            task: Задача от пользователя
            project_snapshot: Текущее состояние проекта
            
        Returns:
            План в формате {"analysis": "...", "plan": [...]} или None
        """
        # Формируем промпт для аналитика
        prompt = self._build_analyzer_prompt(task, project_snapshot)
        
        # Отправляем запрос
        response = self.ollama.generate_response(
            messages=[
                {"role": "system", "content": self.config.ANALYZER_SYSTEM_PROMPT},
                {"role": "user", "content": prompt}
            ],
            format_json=True
        )
        
        if not response:
            return None
            
        # Валидация ответа
        return self._validate_plan(response)
    
    def _build_analyzer_prompt(self, task: str, snapshot: Dict[str, str]) -> str:
        """Строит промпт для аналитика"""
        # Ограничиваем размер контекста для аналитика
        context = self._format_snapshot_for_analyzer(snapshot)
        
        prompt = f"""# ТЕКУЩЕЕ СОСТОЯНИЕ ПРОЕКТА:
{context}

# ЗАДАЧА ПОЛЬЗОВАТЕЛЯ:
{task}

# ИНСТРУКЦИЯ:
Проанализируй задачу и создай пошаговый план.
Учитывай текущие файлы проекта и их содержимое.
Верни JSON строго в указанном формате.
"""
        return prompt
    
    def _format_snapshot_for_analyzer(self, snapshot: Dict[str, str]) -> str:
        """Форматирует снапшот для аналитика (только структура)"""
        if not snapshot:
            return "ПРОЕКТ ПУСТ"
        
        formatted = "ФАЙЛЫ ПРОЕКТА:\n"
        
        # Для аналитика показываем только структуру
        for file_path, content in sorted(snapshot.items()):
            lines = content.count('\n') + 1
            formatted += f"- {file_path} ({lines} строк)\n"
            
            # Показываем только первые 3 строки каждого файла для контекста
            first_lines = '\n'.join(content.split('\n')[:3])
            if first_lines:
                formatted += f"  ```\n  {first_lines}\n  ```\n"
        
        return formatted
    
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
                print(f"❌ Шаг {i} не содержит обязательных полей 'file' или 'task'")
                continue
                
            # Добавляем requirements если их нет
            if "requirements" not in step:
                step["requirements"] = []
                
            valid_steps.append(step)
        
        if not valid_steps:
            return None
            
        return {
            "analysis": response["analysis"],
            "plan": valid_steps
        }