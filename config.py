# config.py
"""
Конфигурация IDLE-Ai-agent для разработки игр на Python
"""

import os
from pathlib import Path

# Базовые пути
PROJECT_ROOT = Path(__file__).parent
DATA_DIR = PROJECT_ROOT / "data"
GAMES_DIR = PROJECT_ROOT / "games"
LOGS_DIR = PROJECT_ROOT / "logs"
RAG_DB_DIR = PROJECT_ROOT / "rag_database"
PROMPTS_DIR = PROJECT_ROOT / "prompts"

# Создаем необходимые директории
for directory in [DATA_DIR, GAMES_DIR, LOGS_DIR, RAG_DB_DIR, PROMPTS_DIR]:
    directory.mkdir(exist_ok=True)

# Настройки Ollama
OLLAMA_API_URL = "http://localhost:11434/api/generate"
OLLAMA_TIMEOUT = 120  # секунд
OLLAMA_MAX_RETRIES = 3

# Модели для разных задач
MODELS = {
    "planner": "phi3:mini",           # Планировщик - понимание задач
    "coder": "codellama:7b-instruct", # Конструктор кода
    "fixer": "qwen2.5:3b-instruct",   # Анализатор ошибок
    "default": "phi3:mini"            # Модель по умолчанию
}

# Настройки RAG
EMBEDDING_MODEL = "all-MiniLM-L6-v2"
CHROMA_PERSIST_DIR = DATA_DIR / "chroma_db"
SIMILARITY_TOP_K = 3  # Количество возвращаемых примеров

# Категории RAG
# config.py - обновляем структуру RAG
RAG_CATEGORIES = {
    # Для планировщика - разбиение на подзадачи
    "task_plans": {
        "file": RAG_DB_DIR / "task_plans.json",
        "description": "Примеры декомпозиции игр на подзадачи",
        "examples_needed": 5
    },
    
    # Для конструктора - шаблоны кода PyGame
    "code_templates": {
        "file": RAG_DB_DIR / "code_templates.json",
        "description": "Базовые паттерны и шаблоны PyGame",
        "examples_needed": 7
    },
    
    # Для фиксера - паттерны ошибок
    "error_patterns": {
        "file": RAG_DB_DIR / "error_patterns.json",
        "description": "Симптомы ошибок и их решения",
        "examples_needed": 5
    },

    "sd_prompts": {
        "file": RAG_DB_DIR / "sd_prompts.json",
        "description": "Простые промпты для Stable Diffusion (скелет, бочка, меч)",
        "examples_needed": 10
    }
}

# Настройки безопасности
MAX_CODE_EXECUTION_TIME = 30  # секунд
ALLOWED_IMPORTS = ["pygame", "random", "math", "sys", "time"]  # Разрешённые импорты

# Настройки логирования
LOG_LEVEL = "INFO"
LOG_FILE = LOGS_DIR / "agent.log"

# Системные промпты (будут загружены из файлов)
SYSTEM_PROMPTS = {
    "planner": "",
    "coder": "",
    "fixer": ""
}

# Добавить в конец config.py:

# Настройки интерфейса
INTERFACE_TYPE = "cli"  # cli | web | gui

# Настройки Fine-tuning (если ещё нет)
FINETUNE_DATA_DIR = DATA_DIR / "finetune_dataset"
FINETUNE_EPOCHS = 3
FINETUNE_LEARNING_RATE = 0.0001
FINETUNE_MODEL_SUFFIX = "-finetuned"

# Создать директорию
FINETUNE_DATA_DIR.mkdir(exist_ok=True)

# В config.py добавляем:
# Настройки Stable Diffusion
STABLE_DIFFUSION_URL = "http://localhost:7860"  # URL вашего сервера A1111
SD_MODEL = "v1-5-pruned-emaonly"  # Или любая другая модель
SD_STEPS = 20
SD_CFG_SCALE = 7.5
SD_WIDTH = 128
SD_HEIGHT = 128
SD_SAMPLER = "Euler a"

# Настройки генерации спрайтов
SPRITE_TYPES = {
    "character": "pixel art character, video game sprite, front view, centered",
    "enemy": "pixel art enemy, monster, video game sprite, hostile",
    "item": "pixel art item, collectible, power-up, game asset",
    "background": "pixel art background, game environment, parallax layers"
}

# Папки для сохранения
SPRITES_DIR = PROJECT_ROOT / "games" / "sprites"
SPRITES_DIR.mkdir(exist_ok=True)

# Настройки генерации спрайтов (улучшенные)
SPRITE_GENERATION = {
    "width": 256,           # Увеличил для детализации
    "height": 256,
    "steps": 30,            # Больше шагов = лучше качество
    "cfg_scale": 9.0,       # Выше = сильнее следует промпту
    "sampler": "DPM++ 2M Karras",  # Лучший для деталей
    "negative_prompt": "low quality, blurry, deformed",
    
    # Промпт-шаблоны для разных типов
    "prompt_templates": {
        "character": "pixel art {description}, video game character sprite, {style}, front view, centered, symmetrical, clean lines, game ready asset",
        "enemy": "pixel art {description}, video game enemy sprite, {style}, threatening pose, monster design, contrasting colors",
        "item": "pixel art {description}, video game item sprite, {style}, collectible, glowing effect, simple shape"
    },
    
    # Стили pixel art
    "styles": {
        "nes": "8-bit NES style, 16-color palette, dithering",
        "snes": "16-bit SNES style, vibrant colors, smooth animation",
        "gameboy": "Gameboy palette, 4 shades, monochrome green",
        "modern": "modern pixel art, clean anti-aliasing, detailed"
    }
}