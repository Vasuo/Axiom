"""
Главный класс AI-агента для разработки игр (обновленная версия)
"""

import asyncio
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime
import json

from config import MODELS, LOG_FILE, PROJECT_ROOT, INTERFACE_TYPE
from ollama_client import OllamaClient, get_ollama_client
from state_manager import TaskState, StateManager, TaskStatus, ValidationStatus

from rag_manager import get_rag
from modules.planner import TaskPlanner
from modules.coder import CodeConstructor
from modules.fixer import FixerDetector
from modules.finetuner import ModelFinetuner, get_finetuner
from modules.visualizer import get_visualizer

logger = logging.getLogger(__name__)

class GameDevAgent:
    """
    Обновленный агент для разработки игр с полным конвейером
    
    Архитектура:
    User → Agent → [Planner → Coder → Fixer] → Visualizer → StateManager → User
    """
    
    def __init__(self, data_dir: Optional[str] = None):
        """Инициализация агента с полным набором модулей"""
        self._setup_logging()
        self.interface_bridge = None
        
        # Основные компоненты
        self.ollama_client: Optional[OllamaClient] = None
        self.state_manager: Optional[StateManager] = None
        self.rag = None
        
        # Модули
        self.planner: Optional[TaskPlanner] = None
        self.coder: Optional[CodeConstructor] = None
        self.fixer: Optional[FixerDetector] = None
        self.visualizer: Optional[VisualGenerator] = None
        self.finetuner: Optional[ModelFinetuner] = None
        
        # Текущее состояние
        self.current_state: Optional[TaskState] = None
        
        # Статистика
        self.stats = {
            "games_created": 0,
            "tasks_completed": 0,
            "errors_fixed": 0,
            "rag_searches": 0
        }
        
        # Инициализация
        self._initialize(data_dir)
        logger.info("GameDevAgent v2 инициализирован")
    
    def _setup_logging(self):
        """Настройка логирования с исправлением энкодинга"""
        import sys
        
        class SafeStreamHandler(logging.StreamHandler):
            def emit(self, record):
                try:
                    msg = self.format(record)
                    # Заменяем emoji для Windows
                    msg = msg.replace('✅', '[OK]').replace('⚠️', '[WARN]').replace('❌', '[ERR]')
                    stream = self.stream
                    stream.write(msg + self.terminator)
                    self.flush()
                except UnicodeEncodeError:
                    # Fallback для проблемных символов
                    pass
        
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(LOG_FILE, encoding='utf-8'),
                SafeStreamHandler()
            ]
        )
    
    def _initialize(self, data_dir: Optional[str]):
        """Инициализация всех компонентов"""
        try:
            # StateManager
            from pathlib import Path
            if data_dir:
                storage_dir = Path(data_dir) / "states"
            else:
                from config import DATA_DIR
                storage_dir = DATA_DIR / "states"
            
            self.state_manager = StateManager(storage_dir)
            logger.info(f"StateManager инициализирован: {storage_dir}")
            
        except Exception as e:
            logger.error(f"Ошибка инициализации StateManager: {e}")
            raise
    
    async def initialize_modules(self):
        """Асинхронная инициализация всех модулей"""
        try:
            # Ollama клиент
            self.ollama_client = await get_ollama_client()
            
            # Проверка моделей
            available = await self.ollama_client.check_models_available()
            for role, is_avail in available.items():
                if not is_avail:
                    logger.warning(f"Модель для {role} недоступна, используем fallback")
            
            # RAG система
            self.rag = get_rag()
            logger.info("RAG система инициализирована")
            
            # Инициализация модулей
            self.planner = TaskPlanner(self.ollama_client)
            self.coder = CodeConstructor(self.ollama_client)
            self.fixer = FixerDetector(self.ollama_client)
            self.finetuner = ModelFinetuner(self.ollama_client)
            
            # Визуализатор передаем RAG менеджер
            self.visualizer = await get_visualizer()
            if self.rag:
                self.visualizer.rag = self.rag  # Передаем RAG визуализатору
            
            # Инициализация интерфейсного моста
            from interface_bridge import InterfaceBridge
            self.interface_bridge = InterfaceBridge(self)
            
            logger.info("Все модули инициализированы")
            return True
            
        except Exception as e:
            logger.error(f"Ошибка инициализации модулей: {e}")
            return False
    
    async def get_interface_status(self) -> Dict[str, Any]:
        """Статус для интерфейса"""
        if self.interface_bridge:
            return await self.interface_bridge.get_agent_status()
        return {"error": "Interface bridge not initialized"}
    
    async def update_rag_from_interface(self, category: str, data: Dict) -> bool:
        """Обновление RAG из интерфейса"""
        if self.interface_bridge:
            return await self.interface_bridge.update_rag(category, data)
        return False
    
    async def search_rag_from_interface(self, query: str, category: Optional[str] = None) -> list:
        """Поиск в RAG из интерфейса"""
        if self.interface_bridge:
            return await self.interface_bridge.search_rag(query, category)
        return []

    async def run_finetuning(self):
        """Запуск fine-tuning на собранных данных"""
        if not self.finetuner or not self.state_manager:
            logger.error("Finetuner или StateManager не инициализированы")
            return False
        
        try:
            logger.info("Запуск автоматического fine-tuning...")
            await self.finetuner.auto_finetune_if_needed(
                self.state_manager, 
                min_examples=5  # Можно понизить для теста
            )
            return True
        except Exception as e:
            logger.error(f"Ошибка fine-tuning: {e}")
            return False

    async def start_new_task(self, task_description: str) -> str:
        """Начало новой задачи"""
        logger.info(f"Начало задачи: {task_description}")
        
        try:
            # Создание состояния
            self.current_state = self.state_manager.create_new_state(task_description)
            self.current_state.task_status = TaskStatus.PLANNING
            
            # Сохранение
            self.state_manager.save_state(self.current_state)
            
            logger.info(f"Создана задача ID: {self.current_state.task_id}")
            return self.current_state.task_id
            
        except Exception as e:
            logger.error(f"Ошибка создания задачи: {e}")
            raise
    
    async def plan_task(self) -> bool:
        """Планирование задачи с использованием TaskPlanner"""
        if not self.current_state or not self.planner:
            logger.error("Агент не инициализирован для планирования")
            return False
        
        try:
            logger.info("Этап планирования...")
            
            # Декомпозиция задачи
            subtasks = await self.planner.decompose_task(
                self.current_state.original_task
            )
            
            # Сохранение в состояние
            self.current_state.subtasks = subtasks
            self.current_state.current_subtask_index = 0
            self.current_state.current_subtask = subtasks[0] if subtasks else None
            self.current_state.task_status = TaskStatus.CODING
            self.current_state.models_used.append(MODELS["planner"])
            
            # Обновление статистики
            self.stats["rag_searches"] += 1
            
            # Сохранение
            self.state_manager.save_state(self.current_state)
            
            logger.info(f"Создано {len(subtasks)} подзадач")
            for i, subtask in enumerate(subtasks, 1):
                logger.debug(f"  {i}. {subtask}")
            
            return True
            
        except Exception as e:
            logger.error(f"Ошибка планирования: {e}")
            self.current_state.task_status = TaskStatus.FAILED
            return False
    
    async def execute_subtask(self, subtask_index: int) -> bool:
        """Выполнение конкретной подзадачи"""
        if not self.current_state or not self.coder or not self.fixer:
            logger.error("Агент не инициализирован для выполнения")
            return False
        
        if subtask_index >= len(self.current_state.subtasks):
            logger.error(f"Неверный индекс подзадачи: {subtask_index}")
            return False
        
        subtask = self.current_state.subtasks[subtask_index]
        logger.info(f"Выполнение подзадачи {subtask_index + 1}: {subtask}")
        
        try:
            # 1. Генерация кода
            current_code = self.current_state.current_code
            generated_code = await self.coder.generate(
                current_code=current_code,
                modification=subtask,
                temperature=0.2,
                max_tokens=1000
            )
            
            # 2. Анализ и исправление
            fix_result = await self.fixer.analyze_code(
                code=generated_code,
                task_description=self.current_state.original_task
            )
            
            # 3. Обновление состояния
            if fix_result["fix_applied"]:
                final_code = fix_result["fixed_code"]
                logger.info("Код успешно исправлен")
                self.stats["errors_fixed"] += 1
            else:
                final_code = generated_code
            
            # 4. Сохранение фрагмента кода
            self.current_state.add_code_chunk(
                subtask=subtask,
                new_full_code=final_code,
                model_used=MODELS["coder"]
            )
            
            # 5. Обновление ошибок если есть
            for error in fix_result.get("errors_detected", []):
                self.current_state.add_error(
                    error_type=error["type"],
                    description=error["description"],
                    code_context=final_code[-500:],  # Последние 500 символов
                    user_feedback=fix_result.get("user_feedback")
                )
            
            # 6. Обновление статистики
            self.stats["rag_searches"] += 2  # RAG поиск в конструкторе и фиксере
            
            logger.info(f"Подзадача выполнена, размер кода: {len(final_code)} символов")
            return True
            
        except Exception as e:
            logger.error(f"Ошибка выполнения подзадачи: {e}")
            self.current_state.add_error(
                error_type="execution_error",
                description=f"Ошибка при выполнении подзадачи: {str(e)[:100]}",
                code_context="",
                user_feedback=None
            )
            return False
    
    # В agent.py, метод generate_visuals():

    async def generate_visuals(self) -> bool:
        """Генерация спрайтов с ручным запуском SD"""
        if not self.current_state:
            return True
        
        print("\n" + "="*60)
        print("🎨 ЭТАП ВИЗУАЛИЗАЦИИ")
        print("="*60)
        
        # Получаем визуализатор
        if not self.visualizer:
            from modules.visualizer_enhanced import get_visualizer
            try:
                from modules.visualizer_enhanced import get_visualizer
                self.visualizer = await get_visualizer()
            except ImportError:
                # Fallback: создаем заглушку
                class DummyVisualizer:
                    async def generate_sprite(self, *args, **kwargs):
                        return {"success": False, "images": []}
                    async def analyze_code_for_sprites(self, *args, **kwargs):
                        return []
                    async def ensure_sd_ready(self):
                        return False
                
                self.visualizer = DummyVisualizer()
                logger.warning("Визуализатор не загружен, используем заглушку")
        
        # Анализируем код
        code = self.current_state.current_code
        sprite_descriptions = await self.visualizer.analyze_code_for_sprites(code)
        
        if not sprite_descriptions:
            print("📄 В коде не найдены описания для спрайтов")
            print("   Использую стандартные спрайты...")
            sprite_descriptions = [
                {"type": "character", "description": "игровой персонаж"},
                {"type": "item", "description": "игровой предмет"}
            ]
        
        print(f"\n🎯 Найдено объектов для спрайтов: {len(sprite_descriptions)}")
        for i, desc in enumerate(sprite_descriptions, 1):
            print(f"  {i}. {desc['type']}: {desc['description']}")
        
        # Выбор метода генерации
        print("\n🔧 ВЫБЕРИТЕ МЕТОД ГЕНЕРАЦИИ:")
        print("1. Быстрые простые спрайты (мгновенно)")
        print("2. Качественные спрайты через Stable Diffusion")
        print("3. Пропустить генерацию спрайтов")
        
        try:
            choice = input("\nВаш выбор (1-3, Enter=1): ").strip()
        except:
            choice = "1"
        
        if choice == "3":
            print("⏭️ Генерация спрайтов пропущена")
            return True
        
        use_sd = (choice == "2")
        
        # Если выбрали SD - гарантируем что он доступен
        if use_sd:
            print("\n🔌 ПОДГОТОВКА STABLE DIFFUSION")
            print("-" * 40)
            sd_ready = await self.visualizer.ensure_sd_ready()
            
            if not sd_ready:
                print("🔄 Использую простые спрайты...")
                use_sd = False
        
        # Генерация спрайтов
        generated = []
        for desc in sprite_descriptions:
            print(f"\n⚡ Генерация: {desc['description'][:30]}...")
            
            result = await self.visualizer.generate_sprite(
                description=desc['description'],
                sprite_type=desc['type']
            )
            
            if result["success"]:
                img = result["images"][0]
                generated.append(img)
                print(f"✅ Создан: {img['filename']}")
                print(f"   Метод: {img['method']}")
        
        # Добавляем в игру
        if generated:
            self._add_sprites_to_game(generated)
            print(f"\n🎉 В игру добавлено {len(generated)} спрайтов!")
        
        print("\n" + "="*60)
        return True

    def _add_sprites_to_game(self, sprites: List[Dict]):
        """Добавляет спрайты в игру"""
        if not sprites:
            return
        
        # Добавляем метаданные
        if not hasattr(self.current_state, 'metadata'):
            self.current_state.metadata = {}
        
        self.current_state.metadata["generated_sprites"] = sprites
        
        # Создаём код загрузки
        sprite_code = self._create_sprite_loading_code(sprites)
        
        # Внедряем в игру
        code = self.current_state.current_code
        self.current_state.current_code = self._inject_sprite_code(code, sprite_code)
        
        logger.info(f"✅ Добавлено {len(sprites)} спрайтов в игру")

    def _create_sprite_loading_code(self, sprites: List[Dict]) -> str:
        """Создание кода для загрузки спрайтов"""
        code_lines = ["\n# ===== АВТОМАТИЧЕСКИ СГЕНЕРИРОВАННЫЕ СПРАЙТЫ =====\n"]
        
        for sprite in sprites:
            var_name = sprite['type'] + "_sprite"
            path = sprite['path'].replace('\\', '/')  # Для кроссплатформенности
            
            code_lines.extend([
                f"try:",
                f"    {var_name} = pygame.image.load('{path}').convert_alpha()",
                f"    print(f'Загружен спрайт: {sprite['description'][:20]}...')",
                f"except Exception as e:",
                f"    print(f'Ошибка загрузки спрайта {sprite['filename']}: {{e}}')",
                f"    {var_name} = None  # Fallback\n"
            ])
        
        return '\n'.join(code_lines)

    def _inject_sprite_code(self, game_code: str, sprite_code: str) -> str:
        """Внедрение кода загрузки спрайтов в игру"""
        # Ищем подходящее место для вставки (после инициализации PyGame)
        lines = game_code.split('\n')
        
        for i, line in enumerate(lines):
            if 'pygame.display.set_mode' in line:
                # Вставляем после создания окна
                lines.insert(i + 1, sprite_code)
                return '\n'.join(lines)
        
        # Если не нашли, добавляем в конец перед main()
        if 'if __name__ == "__main__":' in game_code:
            parts = game_code.split('if __name__ == "__main__":')
            return parts[0] + sprite_code + '\n\nif __name__ == "__main__":' + parts[1]
        
        # Иначе просто добавляем в конец
        return game_code + '\n\n' + sprite_code
    
    def _extract_sprite_descriptions(self, code: str) -> List[Dict[str, str]]:
        """Извлечение описаний спрайтов из кода"""
        descriptions = []
        
        # Простой анализ кода для поиска описаний объектов
        lines = code.split('\n')
        for line in lines:
            line_lower = line.lower()
            
            # Поиск комментариев с описанием
            if '#' in line and any(keyword in line_lower for keyword in ['игрок', 'player', 'враг', 'enemy', 'предмет', 'item']):
                desc = line.split('#')[1].strip()
                if len(desc) > 5:
                    sprite_type = "character"
                    if 'враг' in line_lower or 'enemy' in line_lower:
                        sprite_type = "enemy"
                    elif 'предмет' in line_lower or 'item' in line_lower:
                        sprite_type = "item"
                    
                    descriptions.append({
                        "type": sprite_type,
                        "description": desc
                    })
        
        # Если не нашли в комментариях, создаем по умолчанию
        if not descriptions:
            task = self.current_state.original_task.lower()
            if "змейк" in task:
                descriptions = [
                    {"type": "character", "description": "зеленая пиксельная змейка для игры"},
                    {"type": "item", "description": "красное яблоко для змейки"}
                ]
            elif "платформер" in task:
                descriptions = [
                    {"type": "character", "description": "пиксельный персонаж для платформера"},
                    {"type": "enemy", "description": "пиксельный враг для платформера"}
                ]
            else:
                descriptions = [
                    {"type": "character", "description": "пиксельный персонаж для игры"}
                ]
        
        return descriptions
    
    async def develop_game(self, task_description: str) -> TaskState:
        """
        Полный цикл разработки игры
        
        Returns:
            TaskState: Финальное состояние задачи
        """
        logger.info(f"Запуск полного цикла: {task_description}")
        
        try:
            # Инициализация если нужно
            if not self.ollama_client:
                success = await self.initialize_modules()
                if not success:
                    raise RuntimeError("Не удалось инициализировать модули")
            
            # 1. Начало задачи
            task_id = await self.start_new_task(task_description)
            logger.info(f"Задача ID: {task_id}")
            
            # 2. Планирование
            if not await self.plan_task():
                raise RuntimeError("Планирование не удалось")
            
            # 3. Выполнение подзадач
            for i in range(len(self.current_state.subtasks)):
                self.current_state.current_subtask_index = i
                self.current_state.current_subtask = self.current_state.subtasks[i]
                
                success = await self.execute_subtask(i)
                if not success:
                    logger.warning(f"Не удалось выполнить подзадачу {i + 1}")
                    # Продолжаем с следующей подзадачей
            
            # 4. Генерация визуалов
            await self.generate_visuals()
            
            # 5. Финальная проверка
            self.current_state.task_status = TaskStatus.TESTING
            
            # Запускаем финальный код для проверки
            if self.current_state.current_code:
                fix_result = await self.fixer.analyze_code(
                    code=self.current_state.current_code,
                    task_description=task_description
                )
                
                if fix_result["execution_success"]:
                    self.current_state.validation_status = ValidationStatus.PASSED
                    self.current_state.task_status = TaskStatus.COMPLETED
                    logger.info("[OK] Разработка игры завершена успешно!")
                    self.stats["games_created"] += 1
                else:
                    self.current_state.validation_status = ValidationStatus.FAILED
                    logger.warning("Игра имеет ошибки, требуется ручная доработка")
            else:
                logger.error("Код не был сгенерирован")
                self.current_state.task_status = TaskStatus.FAILED
            
            # 6. Сохранение финального состояния
            self.state_manager.save_state(self.current_state)
            self.stats["tasks_completed"] += 1
            
            # 7. Сохранение кода в файл
            self._save_game_code()
            
            return self.current_state
            
        except Exception as e:
            logger.error(f"Критическая ошибка в цикле разработки: {e}")
            if self.current_state:
                self.current_state.task_status = TaskStatus.FAILED
                self.state_manager.save_state(self.current_state)
            raise
    
    # В методе _save_game_code() исправить:
    def _save_game_code(self):
        """Сохранение сгенерированного кода в файл"""
        if not self.current_state or not self.current_state.current_code:
            return
        
        try:
            from pathlib import Path
            from datetime import datetime
            
            games_dir = Path("games") / "generated"
            games_dir.mkdir(parents=True, exist_ok=True)
            
            # Создаем имя файла
            task_slug = self.current_state.original_task[:50].replace(' ', '_').replace('/', '_')
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"game_{task_slug}_{timestamp}.py"
            
            filepath = games_dir / filename
            
            # Сохраняем код
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(self.current_state.current_code)
            
            logger.info(f"Игра сохранена: {filepath}")
            
            # Исправление: добавляем metadata если нет
            if not hasattr(self.current_state, 'metadata'):
                self.current_state.metadata = {}
            self.current_state.metadata["saved_file"] = str(filepath)
            
        except Exception as e:
            logger.error(f"Ошибка сохранения игры: {e}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Получение статистики агента"""
        return {
            **self.stats,
            "current_task": self.current_state.task_id if self.current_state else None,
            "total_states": len(self.state_manager.list_saved_states()) if self.state_manager else 0
        }
    
    async def interactive_development(self):
        """Интерактивный режим разработки с CLI"""
        print("\n" + "="*60)
        print("IDLE-Ai-agent для разработки игр на Python")
        print("="*60)
        
        while True:
            print("\nМЕНЮ:")
            print("1. Создать новую игру")
            print("2. Просмотреть сохраненные игры")
            print("3. Запустить тестовый сценарий")
            print("4. Статистика агента")
            print("5. Выйти")
            print("6. Запустить fine-tuning на собранных данных")
            
            try:
                choice = input("\nВыберите действие (1-5): ").strip()
                
                if choice == "1":
                    task = input("\nОпишите игру (например: 'Создай змейку'): ").strip()
                    if task:
                        print(f"\nНачинаю разработку: {task}")
                        state = await self.develop_game(task)
                        print(f"\nГотово! Статус: {state.task_status.value}")
                        if state.metadata.get("saved_file"):
                            print(f"Файл сохранен: {state.metadata['saved_file']}")
                
                elif choice == "2":
                    states = self.state_manager.list_saved_states()
                    if states:
                        print(f"\nСохраненные игры ({len(states)}):")
                        for i, state_id in enumerate(states[:10], 1):
                            state = self.state_manager.load_state(state_id)
                            if state:
                                status_icon = "✓" if state.task_status == TaskStatus.COMPLETED else "…"
                                print(f"  {i}. [{status_icon}] {state.original_task[:50]}...")
                    else:
                        print("\nНет сохраненных игр")
                
                elif choice == "3":
                    test_tasks = [
                        "Создай окно PyGame 800x600 с синим фоном",
                        "Создай красный квадрат, управляемый стрелками",
                        "Создай упрощенную змейку"
                    ]
                    
                    print("\nТестовые сценарии:")
                    for i, task in enumerate(test_tasks, 1):
                        print(f"  {i}. {task}")
                    
                    try:
                        test_choice = int(input("\nВыберите сценарий (1-3): ")) - 1
                        if 0 <= test_choice < len(test_tasks):
                            print(f"\nЗапуск теста: {test_tasks[test_choice]}")
                            await self.develop_game(test_tasks[test_choice])
                    except:
                        print("Неверный выбор")
                
                elif choice == "4":
                    stats = self.get_stats()
                    print("\nСТАТИСТИКА АГЕНТА:")
                    print(f"  Создано игр: {stats['games_created']}")
                    print(f"  Завершено задач: {stats['tasks_completed']}")
                    print(f"  Исправлено ошибок: {stats['errors_fixed']}")
                    print(f"  RAG поисков: {stats['rag_searches']}")
                    print(f"  Сохранено состояний: {stats['total_states']}")
                
                elif choice == "5":
                    print("\nЗавершение работы...")
                    if self.ollama_client:
                        await self.ollama_client.disconnect()
                    break
                
                elif choice == "6":
                    print("\nЗапуск fine-tuning...")
                    success = await self.run_finetuning()
                    if success:
                        print("Fine-tuning запущен. Проверьте логи для деталей.")
                    else:
                        print("Не удалось запустить fine-tuning.")

                else:
                    print("Неверный выбор")
                    
            except KeyboardInterrupt:
                print("\n\nПрервано пользователем")
                break
            except Exception as e:
                print(f"\nОшибка: {e}")


async def main():
    """Главная функция"""
    print("Запуск IDLE-Ai-agent v2...")
    
    try:
        agent = GameDevAgent()
        
        # Инициализация модулей
        print("Инициализация модулей...")
        success = await agent.initialize_modules()
        if not success:
            print("Ошибка инициализации модулей")
            return
        
        # Запуск интерактивного режима
        await agent.interactive_development()
        
        print("\nРабота завершена.")
        
    except Exception as e:
        print(f"Ошибка: {e}")
        import traceback
        traceback.print_exc()


async def main():
    """Главная функция с выбором интерфейса"""
    print("Запуск IDLE-Ai-agent v2...")
    
    try:
        agent = GameDevAgent()
        
        # Инициализация модулей
        print("Инициализация модулей...")
        success = await agent.initialize_modules()
        if not success:
            print("Ошибка инициализации модулей")
            return
        
        print("\n" + "="*60)
        print("ВЫБЕРИТЕ РЕЖИМ РАБОТЫ:")
        print("1. Расширенный CLI интерфейс")
        print("2. Веб-интерфейс (стандартный)")
        print("3. ХАКИНГ ИНТЕРФЕЙС (ретро/матрица)")
        print("4. Автоматический режим (тесты)")
        print("="*60)
        
        try:
            choice = input("\nВаш выбор (1-4): ").strip()
            
            if choice == "1":
                from cli_interface import CLIInterface
                cli = CLIInterface(agent)
                await cli.show_main_menu()
                
            elif choice == "2":
                from web_interface import start_web_server
                print("\nЗапуск стандартного веб-интерфейса...")
                agent.loop = asyncio.get_event_loop()
                flask_thread = start_web_server(agent)
                
                try:
                    while True:
                        await asyncio.sleep(1)
                except KeyboardInterrupt:
                    print("\nОстановка...")
                
            elif choice == "3":
                from web_interface_hack import start_hack_interface
                print("\nЗапуск хакинг интерфейса...")
                agent.loop = asyncio.get_event_loop()
                flask_thread = start_hack_interface(agent)
                
                try:
                    while True:
                        await asyncio.sleep(1)
                except KeyboardInterrupt:
                    print("\nОстановка...")
                
            elif choice == "4":
                # Автоматический режим с тестами
                test_tasks = [
                    "Создай окно PyGame 800x600 с синим фоном",
                    "Создай красный квадрат, управляемый стрелками"
                ]
                
                for task in test_tasks:
                    print(f"\nТест: {task}")
                    state = await agent.develop_game(task)
                    print(f"Результат: {state.task_status.value}")
                    
                    if state.metadata.get("saved_file"):
                        print(f"Файл: {state.metadata['saved_file']}")
                    
                    await asyncio.sleep(2)
                
            else:
                print("Неверный выбор, запускаю хакинг интерфейс...")
                from web_interface_hack import start_hack_interface
                agent.loop = asyncio.get_event_loop()
                flask_thread = start_hack_interface(agent)
                
                try:
                    while True:
                        await asyncio.sleep(1)
                except KeyboardInterrupt:
                    print("\nОстановка...")
        
        except KeyboardInterrupt:
            print("\n\nЗавершение работы...")
        
        print("\nРабота завершена.")
        
    except Exception as e:
        print(f"Ошибка: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())