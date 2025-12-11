"""
Модуль исполнителя - генерирует код по конкретным задачам
"""
from typing import Dict, Optional
from ollama_client import OllamaClient
from config import AgentConfig

class Implementer:
    def __init__(self):
        self.config = AgentConfig()
        self.ollama = OllamaClient(model=self.config.IMPLEMENTER_MODEL)
        
    def implement_step(self, 
                      step: Dict[str, any], 
                      project_snapshot: Dict[str, str],
                      step_number: int,
                      total_steps: int) -> Optional[str]:
        """
        Генерирует код для конкретного шага
        
        Args:
            step: Шаг из плана аналитика
            project_snapshot: Текущее состояние ВСЕГО проекта
            step_number: Номер текущего шага
            total_steps: Всего шагов
            
        Returns:
            Код Python для файла или None
        """
        # Формируем промпт для исполнителя
        prompt = self._build_implementer_prompt(step, project_snapshot, step_number, total_steps)
        
        # Отправляем запрос
        response = self.ollama.generate_response(
            messages=[
                {"role": "system", "content": self.config.IMPLEMENTER_SYSTEM_PROMPT},
                {"role": "user", "content": prompt}
            ],
            format_json=False  # Исполнитель возвращает чистый код
        )
        
        if not response:
            return None
            
        # Валидируем что это код (не JSON)
        return self._validate_code_response(response, step["file"])
    
    def _build_implementer_prompt(self, 
                                 step: Dict[str, any], 
                                 snapshot: Dict[str, str],
                                 step_number: int,
                                 total_steps: int) -> str:
        """Строит промпт для исполнителя"""
        
        # Получаем текущий контент файла (если существует)
        target_file = step["file"]
        current_content = snapshot.get(target_file, "")
        
        # Форматируем весь проект для контекста
        project_context = self._format_snapshot_for_implementer(snapshot)
        
        # Формируем промпт без тройных кавычек
        prompt_lines = [
            "# КОНТЕКСТ ВСЕГО ПРОЕКТА:",
            project_context,
            "",
            f"# ТЕКУЩАЯ ЗАДАЧА (шаг {step_number}/{total_steps}):",
            f"Файл: {target_file}",
            f"Задача: {step['task']}",
            f"Требования: {', '.join(step.get('requirements', []))}",
            "",
            f"# ТЕКУЩЕЕ СОДЕРЖИМОЕ ФАЙЛА {target_file}:",
            "```python"
        ]
        
        # Добавляем содержимое файла
        if current_content:
            prompt_lines.append(current_content)
        else:
            prompt_lines.append("# Файл не существует, нужно создать")
        
        prompt_lines.extend([
            "```",
            "",
            "# ИНСТРУКЦИЯ:",
            f"Реализуй указанную задачу для файла {target_file}.",
            "Учитывай весь проект для согласованности импортов и структуры.",
            "Верни ТОЛЬКО код Python (без пояснений, без JSON)."
        ])
        
        return "\n".join(prompt_lines)
    
    def _format_snapshot_for_implementer(self, snapshot: Dict[str, str]) -> str:
        """Форматирует снапшот для исполнителя"""
        if not snapshot:
            return "Проект пуст"
        
        formatted_parts = []
        for file_path, content in sorted(snapshot.items()):
            # Ограничиваем длину каждого файла для экономии токенов
            max_lines = 50
            lines = content.split('\n')
            if len(lines) > max_lines:
                content_preview = '\n'.join(lines[:max_lines]) + f"\n# ... (еще {len(lines) - max_lines} строк)"
            else:
                content_preview = content
                
            formatted_parts.append(f"=== {file_path} ===")
            formatted_parts.append(content_preview)
            formatted_parts.append("")  # Пустая строка между файлами
        
        return "\n".join(formatted_parts)
    
    def _validate_code_response(self, response: str, filename: str) -> Optional[str]:
        """Валидирует ответ исполнителя"""
        if not response or not response.strip():
            print(f"❌ Пустой ответ от исполнителя для {filename}")
            return None
        
        # Очищаем от markdown code blocks
        cleaned = self._strip_markdown_code_blocks(response)
        
        # Проверяем, что это не JSON
        if cleaned.startswith('{') and cleaned.endswith('}'):
            print(f"❌ Исполнитель вернул JSON вместо кода для {filename}")
            return None
        
        return cleaned
    
    def _strip_markdown_code_blocks(self, text: str) -> str:
        """
        Убирает markdown code blocks (```python ... ```) из текста
        """
        lines = text.strip().split('\n')
        result_lines = []
        in_code_block = False
        
        for line in lines:
            stripped = line.strip()
            
            # Начало или конец code block
            if stripped.startswith('```'):
                in_code_block = not in_code_block
                continue  # Пропускаем строку с ```
            
            # Если не внутри code block, добавляем строку
            if not in_code_block:
                result_lines.append(line)
            # Если внутри code block, но это не строка с ```, тоже добавляем
            # (это сам код)
            else:
                result_lines.append(line)
        
        result = '\n'.join(result_lines).strip()
        
        # Если после очистки пусто, возвращаем оригинал (на случай если не было code blocks)
        if not result:
            return text.strip()
        
        return result