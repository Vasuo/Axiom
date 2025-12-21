"""
Модуль конструктора кода с RAG
"""

import logging
from typing import Optional
from rag_manager import get_rag
from ollama_client import OllamaResponse
from config import MODELS
import re

logger = logging.getLogger(__name__)

class CodeConstructor:
    """Конструктор кода с использованием RAG шаблонов"""
    
    def __init__(self, ollama_client):
        self.ollama = ollama_client
        self.rag = get_rag()
        logger.info("CodeConstructor инициализирован")
    
    # modules/coder.py - полностью перерабатываю generate()

    async def generate(
        self, 
        current_code: str,        # Весь текущий код
        modification: str,        # Что нужно изменить/добавить
        temperature: float = 0.2,
        max_tokens: int = 1000
    ) -> str:
        """
        Генерация нового кода на основе текущего кода и модификации
        Возвращает ПОЛНЫЙ код после изменений
        """
        logger.info(f"Генерация кода для модификации: {modification}")
        
        # Стало:
        code_templates = self.rag.search(
            query=modification,
            category="code_templates",  # ✅
            n_results=2
        )

        # И также:
        task_plans = self.rag.search(
            query=modification,
            category="task_plans",
            n_results=1  # Можно 1, чтобы не перегружать контекст
        )
        
        # 3. Формирование контекста из RAG
        rag_context = ""
        if code_templates or task_plans:
            rag_context = "\n\n=== ПРИМЕРЫ ИЗ БАЗЫ ЗНАНИЙ ===\n"
            
            if code_templates:
                rag_context += "\nШаблоны кода:\n"
                for i, template in enumerate(code_templates):
                    rag_context += f"\nШаблон {i+1} ({template['metadata'].get('type', 'код')}):\n"
                    rag_context += f"```python\n{template['text'][:300]}...\n```\n"

            if task_plans:
                rag_context += "\nПримеры планов:\n"
                for i, plan in enumerate(task_plans):
                    rag_context += f"\nПлан {i+1} ({plan['metadata'].get('type', 'план')}):\n"
                    rag_context += f"{plan['text'][:400]}...\n"
        
        # 4. Формирование системного промпта
        system_prompt = f"""Ты — редактор кода PyGame. Тебе дан текущий код игры.
    Твоя задача — внести изменения: {modification}

    {rag_context if rag_context else "Используй стандартные паттерны PyGame."}

    === ИНСТРУКЦИЯ ===
    1. Верни ПОЛНЫЙ код после изменений (не только изменения)
    2. Не удаляй рабочий функционал без необходимости
    3. Изменяй минимально необходимое для выполнения задачи
    4. Сохрани структуру и стиль существующего кода
    5. Если нужно добавить новый элемент (класс, функцию, переменную) — добавь его
    6. Обеспечь, чтобы код оставался запускаемым

    Текущий код игры:
    ```python
    {current_code if current_code else "# Код отсутствует — создай игру с нуля"}
    === ТРЕБОВАНИЯ ===
    • Выводи только код Python (без Markdown, без пояснений)
    • Используй комментарии только для пояснения сложных моментов
    • Обеспечь правильные отступы и форматирование
    • Код должен компилироваться без ошибок

    Верни полный изменённый код:"""
        
        # 5. Формирование пользовательского промпта
        user_prompt = f"Внеси изменения в код PyGame: {modification}"

        # 6. Генерация кода через Ollama
        try:
            response = await self.ollama.generate(
                model=MODELS["coder"],
                prompt=user_prompt,
                system=system_prompt,
                temperature=temperature,
                max_tokens=max_tokens
            )
            
            generated_code = response.response.strip()
            
            # 7. Очистка вывода
            # Удаляем Markdown блоки если есть
            if '```python' in generated_code:
                generated_code = generated_code.split('```python')[1].split('```')[0].strip()
            elif '```' in generated_code:
                generated_code = generated_code.split('```')[1].split('```')[0].strip()
            
            # Удаляем пояснения типа "Вот изменённый код:"
            lines = generated_code.split('\n')
            code_lines = []
            for line in lines:
                stripped = line.strip()
                # Пропускаем строки-пояснения на русском/английском
                if (stripped.startswith('Вот ') or 
                    stripped.startswith('Изменённый ') or
                    stripped.startswith('Here ') or
                    stripped.startswith('Modified ')):
                    continue
                code_lines.append(line)
            
            generated_code = '\n'.join(code_lines).strip()
            
            # 8. Валидация
            if not self._validate_code(generated_code):
                logger.warning("Сгенерированный код не прошёл базовую валидацию")
            
            logger.info(f"Сгенерирован код ({len(generated_code)} символов)")
            logger.debug(f"Первые 500 символов:\n{generated_code[:500]}...")
            
            return generated_code
            
        except Exception as e:
            logger.error(f"Ошибка генерации кода: {e}")
            
            # Fallback: минимальный работающий код
            return f"""# Автоматически сгенерированный код для: {modification}
        Ошибка при обращении к модели: {str(e)[:100]}
        import pygame

        def main():
        pygame.init()
        screen = pygame.display.set_mode((800, 600))
        clock = pygame.time.Clock()
        running = True

        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
            
            screen.fill((0, 0, 0))
            pygame.display.flip()
            clock.tick(60)

        pygame.quit()
        if name == "main":
        main()"""

    def _validate_code(self, code: str) -> bool:
        """Минимальная валидация кода"""
        return "import pygame" in code and ("pygame.display.set_mode" in code or "pygame.display.set_mode" in code.lower())

# Синглтон для удобного доступа
_coder_instance: Optional[CodeConstructor] = None

async def get_coder(ollama_client) -> CodeConstructor:
    """Получение или создание экземпляра конструктора"""
    global _coder_instance
    if _coder_instance is None:
        _coder_instance = CodeConstructor(ollama_client)
    return _coder_instance