"""
Модуль для fine-tuning моделей на успешных примерах
"""

import json
import logging
import asyncio
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime
import subprocess
import tempfile

from config import (
    FINETUNE_DATA_DIR, 
    FINETUNE_EPOCHS, 
    FINETUNE_LEARNING_RATE,
    FINETUNE_MODEL_SUFFIX,
    MODELS
)

logger = logging.getLogger(__name__)


class ModelFinetuner:
    """Класс для fine-tuning моделей Ollama"""
    
    def __init__(self, ollama_client):
        self.ollama = ollama_client
        self.dataset_dir = FINETUNE_DATA_DIR
        logger.info("ModelFinetuner инициализирован")
    
    async def collect_training_data(self, state_manager) -> List[Dict[str, str]]:
        """
        Сбор данных для обучения из успешных состояний
        
        Args:
            state_manager: Экземпляр StateManager
            
        Returns:
            Список примеров для обучения
        """
        logger.info("Сбор данных для fine-tuning...")
        
        examples = []
        
        try:
            # Получаем список всех сохранённых состояний
            state_ids = state_manager.list_saved_states()
            
            for state_id in state_ids[:10]:  # Берём первые 10 для теста
                state = state_manager.load_state(state_id)
                
                if not state:
                    continue
                
                # Берём только успешные задачи
                if (hasattr(state, 'task_status') and 
                    state.task_status.value == "completed" and
                    state.current_code):
                    
                    # Создаём пример для планировщика
                    if state.subtasks:
                        examples.append({
                            "instruction": f"Разбей задачу на подзадачи: {state.original_task}",
                            "response": "\n".join([f"{i+1}. {subtask}" for i, subtask in enumerate(state.subtasks)]),
                            "model_type": "planner",
                            "task_id": state.task_id
                        })
                    
                    # Создаём примеры для конструктора кода
                    if hasattr(state, 'code_chunks') and state.code_chunks:
                        for chunk in state.code_chunks:
                            examples.append({
                                "instruction": f"Сгенерируй код PyGame для: {chunk.subtask}",
                                "response": chunk.code[:1000],  # Берём первые 1000 символов
                                "model_type": "coder",
                                "task_id": state.task_id
                            })
            
            logger.info(f"Собрано {len(examples)} примеров для обучения")
            return examples
            
        except Exception as e:
            logger.error(f"Ошибка сбора данных: {e}")
            return []
    
    def create_dataset_file(self, examples: List[Dict[str, str]]) -> Optional[Path]:
        """
        Создание файла датасета в формате JSONL
        
        Args:
            examples: Список примеров
            
        Returns:
            Путь к созданному файлу или None
        """
        if not examples:
            logger.warning("Нет примеров для создания датасета")
            return None
        
        try:
            # Создаём уникальное имя файла
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            dataset_path = self.dataset_dir / f"dataset_{timestamp}.jsonl"
            
            # Группируем по типу модели
            examples_by_type = {}
            for example in examples:
                model_type = example.get("model_type", "general")
                if model_type not in examples_by_type:
                    examples_by_type[model_type] = []
                examples_by_type[model_type].append(example)
            
            # Сохраняем в файл
            with open(dataset_path, 'w', encoding='utf-8') as f:
                for model_type, model_examples in examples_by_type.items():
                    for example in model_examples:
                        # Форматируем в стандартный формат для Ollama
                        formatted = {
                            "instruction": example["instruction"],
                            "input": "",
                            "output": example["response"],
                            "system": self._get_system_prompt_for_type(model_type)
                        }
                        f.write(json.dumps(formatted, ensure_ascii=False) + '\n')
            
            logger.info(f"Создан датасет: {dataset_path} ({len(examples)} примеров)")
            return dataset_path
            
        except Exception as e:
            logger.error(f"Ошибка создания датасета: {e}")
            return None
    
    def _get_system_prompt_for_type(self, model_type: str) -> str:
        """Системный промпт в зависимости от типа модели"""
        prompts = {
            "planner": "Ты — архитектор игр на PyGame. Разбивай задачи на логические подзадачи.",
            "coder": "Ты — эксперт по разработке игр на PyGame. Генерируй чистый, рабочий код.",
            "fixer": "Ты — анализатор ошибок PyGame. Находи и исправляй проблемы в коде.",
            "general": "Ты — ассистент для разработки игр на PyGame."
        }
        return prompts.get(model_type, prompts["general"])
    
    async def finetune_model(
        self, 
        base_model: str, 
        dataset_path: Path,
        model_type: str = "coder"
    ) -> Dict[str, Any]:
        """
        Запуск fine-tuning модели через Ollama
        
        Args:
            base_model: Базовая модель (например, "codellama:7b-instruct")
            dataset_path: Путь к датасету
            model_type: Тип модели (planner/coder/fixer)
            
        Returns:
            Результат fine-tuning
        """
        logger.info(f"Запуск fine-tuning для {base_model} с датасетом {dataset_path}")
        
        try:
            # 1. Создаём Modelfile
            modelfile_content = self._create_modelfile(
                base_model=base_model,
                dataset_path=dataset_path,
                model_type=model_type
            )
            
            # 2. Сохраняем Modelfile во временный файл
            with tempfile.NamedTemporaryFile(mode='w', suffix='.modelfile', delete=False, encoding='utf-8') as f:
                f.write(modelfile_content)
                modelfile_path = f.name
            
            # 3. Создаём имя для fine-tuned модели
            model_name = base_model.split(':')[0] + FINETUNE_MODEL_SUFFIX
            if model_type != "general":
                model_name = f"{model_name}-{model_type}"
            
            # 4. Запускаем команду ollama create
            logger.info(f"Создание модели {model_name}...")
            
            result = subprocess.run(
                ['ollama', 'create', model_name, '-f', modelfile_path],
                capture_output=True,
                text=True,
                timeout=600,  # 10 минут таймаут
                encoding='utf-8'
            )
            
            # 5. Удаляем временный файл
            import os
            os.unlink(modelfile_path)
            
            # 6. Анализируем результат
            if result.returncode == 0:
                logger.info(f"✅ Fine-tuning завершен успешно: {model_name}")
                logger.debug(f"Вывод команды: {result.stdout[:500]}...")
                
                # Обновляем конфиг с новой моделью
                self._update_model_config(model_type, model_name)
                
                return {
                    "success": True,
                    "model_name": model_name,
                    "output": result.stdout,
                    "base_model": base_model,
                    "examples_count": self._count_examples_in_dataset(dataset_path)
                }
            else:
                logger.error(f"❌ Ошибка fine-tuning: {result.stderr}")
                return {
                    "success": False,
                    "error": result.stderr,
                    "model_name": model_name,
                    "base_model": base_model
                }
                
        except subprocess.TimeoutExpired:
            logger.error("Таймаут fine-tuning (10 минут)")
            return {
                "success": False,
                "error": "Таймаут выполнения",
                "model_name": model_name,
                "base_model": base_model
            }
        except Exception as e:
            logger.error(f"Ошибка при fine-tuning: {e}")
            return {
                "success": False,
                "error": str(e),
                "model_name": model_name,
                "base_model": base_model
            }
    
    def _create_modelfile(
        self, 
        base_model: str, 
        dataset_path: Path,
        model_type: str
    ) -> str:
        """Создание Modelfile для Ollama"""
        
        system_prompt = self._get_system_prompt_for_type(model_type)
        
        modelfile = f"""FROM {base_model}

SYSTEM \"\"\"{system_prompt}\"\"\"

# Параметры fine-tuning
PARAMETER num_epoch {FINETUNE_EPOCHS}
PARAMETER learning_rate {FINETUNE_LEARNING_RATE}
PARAMETER num_ctx 4096

# Формат данных для обучения
TEMPLATE \"\"\"[INST] {{{{ .System }}}}
{{{{ .Prompt }}}} [/INST]
{{{{ .Response }}}}\"\"\"

# Использовать только указанный датасет
DATASET {dataset_path}
"""
        return modelfile
    
    def _count_examples_in_dataset(self, dataset_path: Path) -> int:
        """Подсчёт примеров в датасете"""
        try:
            with open(dataset_path, 'r', encoding='utf-8') as f:
                return sum(1 for _ in f)
        except:
            return 0
    
    def _update_model_config(self, model_type: str, model_name: str):
        """
        Обновление конфигурации MODELS после fine-tuning
        
        Note: Это обновляет конфиг в памяти, но не в файле config.py
        """
        from config import MODELS
        
        if model_type in ["coder", "planner", "fixer"]:
            MODELS[model_type] = model_name
            logger.info(f"Обновлена модель для {model_type}: {model_name}")
    
    async def auto_finetune_if_needed(self, state_manager, min_examples: int = 10):
        """
        Автоматический запуск fine-tuning при достаточном количестве данных
        
        Args:
            state_manager: Экземпляр StateManager
            min_examples: Минимальное количество примеров для запуска
        """
        logger.info("Проверка возможности автоматического fine-tuning...")
        
        # Собираем данные
        examples = await self.collect_training_data(state_manager)
        
        if len(examples) >= min_examples:
            logger.info(f"Достаточно данных ({len(examples)} примеров), запускаем fine-tuning...")
            
            # Создаём датасет
            dataset_path = self.create_dataset_file(examples)
            
            if dataset_path:
                # Fine-tuning для конструктора кода (самый важный)
                coder_examples = [e for e in examples if e.get("model_type") == "coder"]
                if coder_examples:
                    result = await self.finetune_model(
                        base_model=MODELS["coder"],
                        dataset_path=dataset_path,
                        model_type="coder"
                    )
                    
                    if result["success"]:
                        logger.info(f"✅ Fine-tuning конструктора кода завершен: {result['model_name']}")
                    else:
                        logger.warning(f"⚠️ Fine-tuning конструктора кода не удался: {result.get('error', 'неизвестная ошибка')}")
                
                # Можно добавить fine-tuning для других моделей
                # planner_examples = [e for e in examples if e.get("model_type") == "planner"]
                # ...
            
            else:
                logger.warning("Не удалось создать датасет для fine-tuning")
        else:
            logger.info(f"Недостаточно данных для fine-tuning: {len(examples)} из {min_examples} примеров")
    
    def get_finetuned_models(self) -> Dict[str, List[str]]:
        """
        Получение списка fine-tuned моделей
        
        Returns:
            Словарь с информацией о моделях
        """
        try:
            result = subprocess.run(
                ['ollama', 'list'],
                capture_output=True,
                text=True,
                encoding='utf-8'
            )
            
            if result.returncode == 0:
                lines = result.stdout.strip().split('\n')[1:]  # Пропускаем заголовок
                models = []
                
                for line in lines:
                    if line.strip():
                        parts = line.split()
                        if len(parts) >= 1:
                            model_name = parts[0]
                            if FINETUNE_MODEL_SUFFIX in model_name:
                                models.append(model_name)
                
                return {
                    "total_finetuned": len(models),
                    "models": models,
                    "raw_output": result.stdout
                }
            else:
                return {"error": result.stderr}
                
        except Exception as e:
            return {"error": str(e)}


# Синглтон для удобного доступа
_finetuner_instance: Optional[ModelFinetuner] = None

async def get_finetuner(ollama_client) -> ModelFinetuner:
    """Получение или создание экземпляра finetuner"""
    global _finetuner_instance
    if _finetuner_instance is None:
        _finetuner_instance = ModelFinetuner(ollama_client)
    return _finetuner_instance