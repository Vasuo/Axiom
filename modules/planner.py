"""
Модуль планировщика задач с RAG-контекстом
"""

import logging
from typing import List, Dict, Any
from rag_manager import get_rag
from config import MODELS

logger = logging.getLogger(__name__)

class TaskPlanner:
    """Интеллектуальный планировщик с использованием RAG"""
    
    def __init__(self, ollama_client):
        self.ollama = ollama_client
        self.rag = get_rag()
        logger.info("TaskPlanner инициализирован")
    
    async def decompose_task(self, task_description: str) -> List[str]:
        """
        Декомпозиция задачи на подзадачи с RAG-контекстом
        
        Args:
            task_description: Описание игры от пользователя
            
        Returns:
            List[str]: Список подзадач (3-7 элементов)
        """
        logger.info(f"Декомпозиция задачи: {task_description}")
        
        # 1. Поиск похожих планов в RAG
        similar_plans = self.rag.search(
            query=task_description,
            category="task_plans",
            n_results=2
        )
        
        # 2. Поиск похожих шаблонов кода для понимания структуры
        code_templates = self.rag.search(
            query=task_description,
            category="code_templates",
            n_results=1
        )
        
        # 3. Формирование контекста из RAG
        rag_context = self._build_rag_context(similar_plans, code_templates)
        
        # 4. Формирование промпта
        system_prompt = f"""Ты — архитектор игр на PyGame. Разбей задачу на логические подзадачи.

{rag_context}

ИНСТРУКЦИЯ:
1. Анализируй задачу пользователя
2. Разбей на 3-7 подзадач, от простого к сложному
3. Каждая подзадача должна быть атомарной и выполнимой
4. Учитывай зависимости между подзадачами
5. Формат: нумерованный список

Пример для "движущийся квадрат":
1. Инициализация PyGame и создание окна 800x600
2. Создание класса/объекта для квадрата с параметрами (цвет, размер, позиция)
3. Реализация управления квадратом с помощью стрелок клавиатуры
4. Обработка границ экрана (чтобы квадрат не выходил за пределы)
5. Настройка игрового цикла и отображения"""
        
        user_prompt = f"Задача: {task_description}\n\nСоздай план разработки этой игры на PyGame."
        
        # 5. Генерация плана
        try:
            response = await self.ollama.generate(
                model=MODELS["planner"],
                prompt=user_prompt,
                system=system_prompt,
                temperature=0.1,
                max_tokens=500
            )
            
            # 6. Парсинг и валидация подзадач
            subtasks = self._parse_subtasks(response.response)
            
            if not subtasks:
                subtasks = self._get_fallback_subtasks(task_description)
            
            logger.info(f"Создано {len(subtasks)} подзадач")
            return subtasks
            
        except Exception as e:
            logger.error(f"Ошибка декомпозиции: {e}")
            return self._get_fallback_subtasks(task_description)
    
    def _build_rag_context(self, similar_plans: List, code_templates: List) -> str:
        """Построение контекста из RAG результатов"""
        context = ""
        
        if similar_plans:
            context += "ПОХОЖИЕ ПЛАНЫ ИЗ БАЗЫ ЗНАНИЙ:\n\n"
            for i, plan in enumerate(similar_plans):
                context += f"План {i+1} ({plan['metadata'].get('type', 'план')}):\n"
                context += f"{plan['text'][:300]}...\n\n"
        
        if code_templates:
            context += "ПОХОЖИЕ ШАБЛОНЫ КОДА:\n\n"
            for i, template in enumerate(code_templates):
                context += f"Шаблон {i+1} ({template['metadata'].get('type', 'код')}):\n"
                context += f"Теги: {template['metadata'].get('tags', '')}\n"
                context += f"Сложность: {template['metadata'].get('complexity', 'неизвестно')}\n\n"
        
        return context if context else "Используй стандартные паттерны PyGame."
    
    def _parse_subtasks(self, response: str) -> List[str]:
        """Парсинг ответа модели в список подзадач"""
        subtasks = []
        lines = response.strip().split('\n')
        
        for line in lines:
            line = line.strip()
            
            # Пропускаем пустые и короткие строки
            if not line or len(line) < 10:
                continue
            
            # Извлекаем подзадачу из нумерованного списка
            import re
            
            # Паттерны: "1. задача", "1) задача", "- задача"
            patterns = [
                r'^\d+[\.\)]\s*(.+)$',  # "1. задача"
                r'^[\-\*•]\s*(.+)$',    # "- задача"
                r'^\d+\s+(.+)$'         # "1 задача"
            ]
            
            for pattern in patterns:
                match = re.match(pattern, line)
                if match:
                    subtask = match.group(1).strip()
                    # Фильтруем мусор
                    if (len(subtask) > 15 and 
                        not subtask.startswith('```') and
                        'пример' not in subtask.lower()):
                        subtasks.append(subtask)
                    break
        
        # Ограничиваем количество
        return subtasks[:7]
    
    def _get_fallback_subtasks(self, task_description: str) -> List[str]:
        """Fallback подзадачи если не удалось распарсить"""
        logger.warning(f"Используем fallback подзадачи для: {task_description}")
        
        # Базовые подзадачи для любой игры
        base_tasks = [
            "Инициализация PyGame и создание игрового окна",
            "Создание основного игрового объекта",
            "Реализация управления объектом",
            "Добавление игровой логики и механик",
            "Настройка отображения и интерфейса",
            "Тестирование и отладка"
        ]
        
        # Адаптируем под конкретную задачу
        if "змейк" in task_description.lower():
            return [
                "Инициализация PyGame и игрового поля",
                "Создание класса Змейки с движением",
                "Генерация еды на поле",
                "Реализация управления стрелками",
                "Обработка столкновений и роста змейки",
                "Отображение счета и игры"
            ]
        elif "платформер" in task_description.lower():
            return [
                "Создание окна и фона",
                "Реализация игрока с физикой и гравитацией",
                "Создание платформ и препятствий",
                "Реализация управления и прыжка",
                "Обнаружение столкновений с платформами",
                "Добавление врагов или собираемых предметов"
            ]
        
        return base_tasks