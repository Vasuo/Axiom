# ollama_client.py
"""
Клиент для взаимодействия с Ollama API
"""

import aiohttp
import asyncio
import json
import logging
from typing import Dict, Any, Optional
from dataclasses import dataclass
from config import OLLAMA_API_URL, OLLAMA_TIMEOUT, OLLAMA_MAX_RETRIES

# Импортируем конфигурацию
try:
    from config import OLLAMA_API_URL, OLLAMA_TIMEOUT, OLLAMA_MAX_RETRIES, MODELS
except ImportError:
    # Fallback для дебага
    OLLAMA_API_URL = "http://localhost:11434/api/generate"
    OLLAMA_TIMEOUT = 120
    OLLAMA_MAX_RETRIES = 3
    MODELS = {
        "planner": "phi3:mini",
        "coder": "codellama:7b-instruct",
        "fixer": "qwen2.5:3b-instruct",
        "default": "phi3:mini"
    }
    print("⚠️ Используется fallback определение MODELS")

logger = logging.getLogger(__name__)

@dataclass
class OllamaResponse:
    """Структура ответа от Ollama"""
    model: str
    response: str
    done: bool
    context: Optional[list] = None
    total_duration: Optional[int] = None
    load_duration: Optional[int] = None
    prompt_eval_count: Optional[int] = None
    eval_count: Optional[int] = None


class OllamaClient:
    """Асинхронный клиент для работы с Ollama API"""
    
    def __init__(self, base_url: str = OLLAMA_API_URL):
        self.base_url = base_url
        self.session: Optional[aiohttp.ClientSession] = None
        
    async def __aenter__(self):
        await self.connect()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.disconnect()
        
    async def connect(self):
        """Создание сессии"""
        if self.session is None or self.session.closed:
            timeout = aiohttp.ClientTimeout(total=OLLAMA_TIMEOUT)
            self.session = aiohttp.ClientSession(timeout=timeout)
            logger.info("Ollama сессия создана")
            
    async def disconnect(self):
        """Закрытие сессии"""
        if self.session and not self.session.closed:
            await self.session.close()
            logger.info("Ollama сессия закрыта")
    
    async def generate(
        self,
        model: str,
        prompt: str,
        system: str = "",
        temperature: float = 0.3,
        max_tokens: int = 2000
    ) -> OllamaResponse:
        """
        Генерация текста с использованием Ollama
        
        Args:
            model: Имя модели в Ollama
            prompt: Пользовательский промпт
            system: Системный промпт
            temperature: Креативность (0.0-1.0)
            max_tokens: Максимальное количество токенов
            
        Returns:
            OllamaResponse: Структурированный ответ
            
        Raises:
            RuntimeError: При ошибке API или сети
        """
        payload = {
            "model": model,
            "prompt": prompt,
            "system": system,
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens
            }
        }
        
        for attempt in range(OLLAMA_MAX_RETRIES):
            try:
                logger.debug(f"Запрос к Ollama (попытка {attempt + 1}): model={model}, prompt_len={len(prompt)}")
                
                async with self.session.post(self.base_url, json=payload) as response:
                    if response.status == 200:
                        data = await response.json()
                        ollama_response = OllamaResponse(
                            model=data.get("model", model),
                            response=data.get("response", ""),
                            done=data.get("done", False),
                            context=data.get("context"),
                            total_duration=data.get("total_duration"),
                            load_duration=data.get("load_duration"),
                            prompt_eval_count=data.get("prompt_eval_count"),
                            eval_count=data.get("eval_count")
                        )
                        
                        logger.info(f"Успешный ответ от Ollama: model={model}, eval_count={ollama_response.eval_count}")
                        return ollama_response
                        
                    else:
                        error_text = await response.text()
                        logger.warning(f"Ошибка Ollama (статус {response.status}): {error_text}")
                        
            except aiohttp.ClientError as e:
                logger.error(f"Сетевая ошибка при запросе к Ollama: {e}")
                if attempt == OLLAMA_MAX_RETRIES - 1:
                    raise RuntimeError(f"Не удалось подключиться к Ollama после {OLLAMA_MAX_RETRIES} попыток: {e}")
                
            except json.JSONDecodeError as e:
                logger.error(f"Ошибка парсинга JSON от Ollama: {e}")
                if attempt == OLLAMA_MAX_RETRIES - 1:
                    raise RuntimeError(f"Некорректный ответ от Ollama: {e}")
            
            # Экспоненциальная задержка перед повторной попыткой
            await asyncio.sleep(2 ** attempt)
        
        raise RuntimeError(f"Не удалось получить ответ от Ollama после {OLLAMA_MAX_RETRIES} попыток")
    
    async def check_models_available(self) -> Dict[str, bool]:
        """
        Проверка доступности моделей
        
        Returns:
            Dict[str, bool]: Словарь с доступностью каждой модели
        """
        available = {}
        
        for role, model in MODELS.items():
            try:
                # Простой запрос для проверки доступности
                response = await self.generate(
                    model=model,
                    prompt="Привет",
                    system="Ответь 'готов'",
                    max_tokens=10
                )
                available[role] = response.done and len(response.response) > 0
                logger.info(f"Модель {model} для {role}: {'доступна' if available[role] else 'недоступна'}")
                
            except Exception as e:
                available[role] = False
                logger.warning(f"Модель {model} недоступна: {e}")
                
        return available


# Синглтон для удобного доступа
_client_instance: Optional[OllamaClient] = None

async def get_ollama_client() -> OllamaClient:
    """Получение или создание экземпляра клиента Ollama"""
    global _client_instance
    if _client_instance is None:
        _client_instance = OllamaClient()
        await _client_instance.connect()
    return _client_instance

'''
# Добавить в конец класса OllamaClient:
async def create_finetune_dataset(self, examples: list[Dict[str, str]]) -> str:
    """
    Создание датасета для fine-tuning
    
    Args:
        examples: Список примеров {"instruction": "...", "response": "..."}
    
    Returns:
        Путь к файлу датасета
    """
    import json
    
    dataset_path = config.FINETUNE_DATA_DIR / f"dataset_{int(time.time())}.jsonl"
    dataset_path.parent.mkdir(exist_ok=True)
    
    with open(dataset_path, 'w', encoding='utf-8') as f:
        for example in examples:
            formatted = {
                "instruction": example["instruction"],
                "input": "",
                "output": example["response"],
                "system": "Ты — эксперт по разработке игр на PyGame."
            }
            f.write(json.dumps(formatted, ensure_ascii=False) + '\n')
    
    logger.info(f"Создан датасет для fine-tuning: {dataset_path}")
    return str(dataset_path)

async def finetune_model(self, base_model: str, dataset_path: str) -> Dict[str, Any]:
    """
    Запуск fine-tuning через Ollama API
    
    Note: Требуется Ollama версии 0.1.25+ с поддержкой Modelfile
    """
    import tempfile
    
    # Создаем Modelfile
    modelfile_content = f"""FROM {base_model}
    
SYSTEM "Ты — эксперт по разработке игр на PyGame. Генерируй рабочий код на Python."

# Настройки fine-tuning
PARAMETER num_epoch {config.FINETUNE_EPOCHS}
PARAMETER learning_rate {config.FINETUNE_LEARNING_RATE}

# Данные для обучения
MESSAGE user "instruction"
MESSAGE assistant "response"
"""
    
    # Сохраняем Modelfile
    with tempfile.NamedTemporaryFile(mode='w', suffix='.modelfile', delete=False) as f:
        f.write(modelfile_content)
        modelfile_path = f.name
    
    try:
        # Используем команду ollama create (через subprocess)
        import subprocess
        model_name = f"{base_model.split(':')[0]}-finetuned"
        
        # Создание модели с fine-tuning
        result = subprocess.run(
            ['ollama', 'create', model_name, '-f', modelfile_path],
            capture_output=True,
            text=True,
            timeout=300
        )
        
        if result.returncode == 0:
            logger.info(f"Fine-tuning завершен успешно: {model_name}")
            return {
                "success": True,
                "model_name": model_name,
                "output": result.stdout
            }
        else:
            logger.error(f"Ошибка fine-tuning: {result.stderr}")
            return {
                "success": False,
                "error": result.stderr
            }
            
    finally:
        import os
        os.unlink(modelfile_path)
'''