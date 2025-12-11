"""
Основной класс AI-агента для разработки игр
"""
import json
import os
from typing import Dict, Any, Optional, List
from pathlib import Path
from datetime import datetime
from typing import Tuple  # Добавить в импорты

from config import AgentConfig
from analyzer import Analyzer
from implementer import Implementer
from executor import Executor


class GameDevAgent:
    def __init__(self, project_root: str = None):
        self.config = AgentConfig()
        self.project_root = Path(project_root or self.config.DEFAULT_PROJECT_ROOT).resolve()
        self.analyzer = Analyzer()
        self.implementer = Implementer()
        self.executor = Executor(self.project_root)
        
        # Состояние агента
        self.iteration = 0
        self.history = []
        self.iteration_history = []  # История для аналитика
        self.max_history_length = 3
        
        print(f"🎮 Инициализация AI-агента для разработки игр")
        print(f"📁 Проект: {self.project_root}")
        print(f"🔍 Аналитик: {self.config.ANALYZER_MODEL}")
        print(f"🔧 Исполнитель: {self.config.IMPLEMENTER_MODEL}")
        print(f"📝 Подробные логи: {self.config.DETAILED_LOG_FILE}")
        
        # Проверка подключения
        if not self.analyzer.ollama.check_connection():
            print("❌ Не удалось подключиться к Ollama")
            models = self.analyzer.ollama.list_models()
            if models:
                print(f"Доступные модели: {', '.join(models)}")
    
    def parse_task_and_mode(self, user_input: str) -> Tuple[str, str]:
        """
        Парсит ввод пользователя на режим и задачу
        
        Args:
            user_input: Строка от пользователя
            
        Returns:
            (очищенная_задача, режим)
        """
        user_input = user_input.strip()
        
        # Проверяем явное указание режима
        if user_input.startswith(('dev ', 'dbg ')):
            mode = user_input[:3].strip()
            task = user_input[3:].strip()
            return task, mode
        
        # Автоматическое определение по ключевым словам
        user_lower = user_input.lower()
        debug_keywords = ['исправь', 'ошибка', 'проблема', 'не работает', 'баг', 'дебаг', 'почему']
        dev_keywords = ['создай', 'добавь', 'сделай', 'реализуй', 'напиши', 'новый']
        
        # Считаем ключевые слова
        debug_score = sum(1 for kw in debug_keywords if kw in user_lower)
        dev_score = sum(1 for kw in dev_keywords if kw in user_lower)
        
        # Учитываем историю
        if self.iteration_history:
            last_entry = self.iteration_history[-1]
            if last_entry.get('mode') == 'dbg' and 'проблема' in last_entry.get('summary', '').lower():
                debug_score += 1
        
        # Выбираем режим
        mode = "dbg" if debug_score > dev_score else "dev"
        
        return user_input, mode

    def get_project_snapshot(self) -> Dict[str, str]:
        """
        Возвращает полный снимок текущего состояния проекта
        """
        snapshot = {}
        
        for root, dirs, files in os.walk(self.project_root):
            # Фильтрация исключенных директорий
            dirs[:] = [d for d in dirs if d not in self.config.EXCLUDED_DIRS]
            
            for file in files:
                file_path = Path(root) / file
                rel_path = file_path.relative_to(self.project_root)
                
                # Проверка исключений
                if (file in self.config.EXCLUDED_FILES or 
                    file_path.suffix not in self.config.ALLOWED_EXTENSIONS):
                    continue
                
                # Чтение файла
                try:
                    with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                        content = f.read()
                        snapshot[str(rel_path)] = content
                except Exception as e:
                    snapshot[str(rel_path)] = f"# ОШИБКА ЧТЕНИЯ: {e}"
        
        return snapshot
    
    def run_single_iteration(self, user_input: str) -> bool:
        """
        Выполняет одну итерацию разработки
        
        Args:
            user_input: Ввод пользователя (может содержать режим)
            
        Returns:
            True если успешно, False если нужно завершить
        """
        print(f"\n{'='*60}")
        print(f"🔄 Итерация #{self.iteration + 1}")
        
        # Парсим режим и задачу
        task, mode = self.parse_task_and_mode(user_input)
        print(f"🎯 Задача: {task}")
        print(f"📊 Режим: {self.config.ANALYZER_MODES.get(mode, mode)}")
        
        # Шаг 1: Получаем снапшот проекта
        print("\n📊 Анализ текущего состояния проекта...")
        snapshot = self.get_project_snapshot()
        print(f"📁 Найдено файлов: {len(snapshot)}")
        
        # Шаг 2: Получаем историю для аналитика
        history_context = self.format_history_for_prompt()
        
        # Шаг 3: Аналитик создает план
        print(f"\n🔍 Консультация с аналитиком...")
        plan_result = self.analyzer.create_plan(task, snapshot, history_context, mode)
        
        if not plan_result:
            print("❌ Не удалось создать план")
            return True
            
        analysis = plan_result["analysis"]
        plan = plan_result["plan"]
        plan_mode = plan_result.get("mode", mode)
        
        print(f"📋 Анализ: {analysis}")
        print(f"📋 План из {len(plan)} шагов:")
        for i, step in enumerate(plan, 1):
            print(f"  {i}. {step['file']}: {step['task']}")
        
        # Шаг 4: Исполняем план шаг за шагом
        print("\n🔧 Начинаем выполнение плана...")
        results = {}
        
        for i, step in enumerate(plan, 1):
            print(f"\n📝 Шаг {i}/{len(plan)}: {step['file']}")
            print(f"   Задача: {step['task']}")
            
            # Получаем актуальный снапшот
            current_snapshot = self.get_project_snapshot()
            
            # Исполнитель генерирует код
            print(f"   Генерация кода...")
            code = self.implementer.implement_step(
                step, 
                current_snapshot, 
                step_number=i,
                total_steps=len(plan)
            )
            
            if not code:
                print(f"   ❌ Не удалось сгенерировать код")
                results[step['file']] = "FAILED: Не удалось сгенерировать код"
                continue
            
            # Применяем изменения БЕЗ подтверждения
            print(f"   Применение изменений ({len(code)} символов)...")
            file_changes = {step['file']: code}
            
            is_valid, message = self.executor.validate_file_changes(file_changes)
            if not is_valid:
                print(f"   ❌ {message}")
                results[step['file']] = f"FAILED: {message}"
                continue
            
            # Применяем изменения
            step_results = self.executor.apply_changes(file_changes)
            results.update(step_results)
            
            print(f"   ✅ Шаг выполнен")
        
        # Шаг 5: Получаем фидбек от пользователя
        feedback = self.get_user_feedback()
        
        # Шаг 6: Добавляем в историю
        feedback_summary = feedback["summary"] if feedback else "Фидбек не получен"
        self.add_to_history(
            task=task,
            summary=feedback_summary,
            files_changed=list(results.keys()),
            mode=plan_mode
        )
        
        # Шаг 7: Обновляем архитектурный файл
        iteration_info = {
            "iteration": self.iteration + 1,
            "timestamp": datetime.now().isoformat(),
            "task": task,
            "summary": feedback_summary,
            "files_changed": list(results.keys()),
            "mode": plan_mode
        }
        self.update_architecture_file(iteration_info)
        
        # Шаг 8: Логируем итерацию
        self.log_iteration(task, plan_result, results, feedback)
        self.iteration += 1
        
        # Шаг 9: Показываем итоги
        print(f"\n📊 Итоги итерации #{self.iteration}:")
        for file, result in results.items():
            status = "✅" if "✅" in str(result) or "UPDATED" in str(result) else "❌"
            print(f"  {status} {file}: {result}")
        
        if feedback:
            print(f"📝 Фидбек: {feedback['summary']}")
        
        return True
    
    def log_iteration(self, task: str, plan: Dict[str, Any], results: Dict[str, str], feedback: Dict[str, Any] = None) -> None:
        """Логирует итерацию работы"""
        log_entry = {
            "iteration": self.iteration + 1,
            "timestamp": datetime.now().isoformat(),
            "task": task,
            "analysis": plan.get("analysis", ""),
            "plan": plan.get("plan", []),
            "execution_results": results
        }
        
        self.history.append(log_entry)
        
        # Сохраняем в файл
        try:
            with open(self.config.HISTORY_FILE, 'a', encoding='utf-8') as f:
                f.write(f"\n{'='*60}\n")
                f.write(f"Итерация #{log_entry['iteration']} - {log_entry['timestamp']}\n")
                f.write(f"Задача: {task}\n")
                f.write(f"Анализ: {log_entry['analysis']}\n")
                
                f.write(f"План:\n")
                for i, step in enumerate(log_entry["plan"], 1):
                    f.write(f"  {i}. {step['file']}: {step['task']}\n")
                
                f.write(f"Результаты:\n")
                for file, result in results.items():
                    f.write(f"  - {file}: {result}\n")
                
                if feedback:
                    f.write(f"Фидбек: {feedback.get('summary', 'Нет фидбека')}\n")
                
                f.write(f"{'='*60}\n")
        except Exception as e:
            print(f"⚠️ Ошибка записи лога: {e}")
    
    def run_interactive(self):
        """Запускает интерактивный режим работы"""
        print("\n" + "="*50)
        print("🎮 AI-АГЕНТ РАЗРАБОТКИ ИГР (Многоуровневая архитектура v2)")
        print("="*50)
        print("📝 Формат: [режим] задача")
        print("   • dev - режим разработки (по умолчанию)")
        print("   • dbg - режим отладки")
        print("   Пример: 'dbg Исправь чёрный экран'")
        print("="*50)
        
        # Проверка модели
        models = self.analyzer.ollama.list_models()
        if not models:
            print("⚠️ Нет доступных моделей Ollama")
            return
        
        print(f"✅ Доступные модели: {', '.join(models)}")
        
        # Главный цикл
        while True:
            try:
                print("\n🎯 Введите задачу (или 'stop' для выхода):")
                user_input = input("> ").strip()
                
                if not user_input or user_input.lower() == 'stop':
                    break
                
                should_continue = self.run_single_iteration(user_input)
                if not should_continue:
                    break
                    
            except KeyboardInterrupt:
                print("\n\n⚠️ Прервано пользователем")
                break
            except Exception as e:
                print(f"❌ Критическая ошибка: {e}")
                import traceback
                traceback.print_exc()
                break
        
        # Финальная статистика
        print(f"\n{'='*50}")
        print(f"📊 Статистика работы:")
        print(f"   Итераций выполнено: {self.iteration}")
        print(f"   История сохранена в: {self.config.HISTORY_FILE}")
        print(f"   Подробные логи: {self.config.DETAILED_LOG_FILE}")
        print(f"   Архитектура: {self.config.ARCHITECTURE_FILE}")
        print(f"🎉 Работа завершена!")
    
    def get_user_feedback(self) -> Optional[Dict[str, Any]]:
        """
        Запускает игру и получает фидбек от пользователя
        
        Returns:
            Словарь с фидбеком или None если пропущено
        """
        print("\n🎮 ЗАПУСК ИГРЫ ДЛЯ ТЕСТИРОВАНИЯ")
        print("=" * 40)
        
        # Запускаем игру
        success, output = self._run_game()
        
        if not success:
            print(f"❌ Игра НЕ запустилась")
            print(f"📋 Ошибка: {output[:300]}...")
            game_state = "ERROR"
        else:
            print("✅ Игра запустилась успешно")
            if output:
                print(f"📺 Вывод игры: {output[:200]}...")
            game_state = "RUNNING"
        
        print("\n" + "=" * 40)
        print("📝 ОПИШИТЕ РЕЗУЛЬТАТ:")
        print("  • Что видите на экране?")
        print("  • Что работает/не работает?")
        print("  • Или введите 'skip' чтобы пропустить")
        print("=" * 40)
        
        feedback = input("> ").strip()
        
        if feedback.lower() == 'skip':
            return None
        
        # Генерируем краткое summary
        summary = self._generate_feedback_summary(feedback, game_state, output)
        
        return {
            "raw_feedback": feedback,
            "summary": summary,
            "game_state": game_state,
            "game_output": output[:500] if output else None
        }
    
    def _run_game(self) -> Tuple[bool, str]:
        """
        Запускает игру и возвращает результат
        
        Returns:
            (успех, вывод/ошибка)
        """
        import subprocess
        import sys
        
        # Ищем основной файл для запуска
        snapshot = self.get_project_snapshot()
        main_files = []
        
        for filename in snapshot.keys():
            if filename.endswith('main.py'):
                main_files.append(filename)
            elif filename.endswith('game.py') and not main_files:
                main_files.append(filename)
        
        if not main_files:
            return False, "Не найден файл для запуска (main.py или game.py)"
        
        main_file = main_files[0]
        main_path = self.project_root / main_file
        
        try:
            # Запускаем с таймаутом
            result = subprocess.run(
                [sys.executable, str(main_path)],
                capture_output=True,
                text=True,
                timeout=10,  # 10 секунд
                cwd=self.project_root,
                encoding='utf-8',
                errors='ignore'
            )
            
            # Если программа завершилась с кодом 0 - успех
            if result.returncode == 0:
                return True, result.stdout
            else:
                return False, result.stderr or f"Код ошибки: {result.returncode}"
                
        except subprocess.TimeoutExpired:
            # Программа запустилась и не упала - считаем успехом
            return True, "Программа запущена (таймаут через 10 секунд)"
        except FileNotFoundError:
            return False, f"Файл не найден: {main_file}"
        except Exception as e:
            return False, f"Ошибка запуска: {str(e)}"
    
    def _generate_feedback_summary(self, feedback: str, game_state: str, 
                                  game_output: str) -> str:
        """
        Генерирует краткое описание результата итерации
        
        Args:
            feedback: Фидбек от пользователя
            game_state: Состояние игры (RUNNING/ERROR)
            game_output: Вывод игры
            
        Returns:
            Краткое summary (1-2 предложения)
        """
        # Простая логика без запроса к ИИ (пока)
        if game_state == "ERROR":
            if "рекурсия" in feedback.lower() or "рекурсия" in (game_output or "").lower():
                return "Ошибка рекурсии в коде"
            elif "import" in (game_output or "").lower() or "module" in (game_output or "").lower():
                return "Проблема с импортами модулей"
            else:
                return f"Ошибка выполнения: {feedback[:50]}..."
        
        # Если игра запустилась
        feedback_lower = feedback.lower()
        
        if any(word in feedback_lower for word in ['черный', 'черный экран', 'ничего не видно']):
            return "Игра запускается, но отображается только черный экран"
        elif any(word in feedback_lower for word in ['белый прямоугольник', 'квадрат', 'прямоугольник']):
            return "Отображается только белый прямоугольник на черном фоне"
        elif any(word in feedback_lower for word in ['двигается', 'передвигается', 'ходит']):
            return "Игра работает, управление функционирует"
        elif any(word in feedback_lower for word in ['не двигается', 'не ходит', 'не перемещается']):
            return "Игра запускается, но управление не работает"
        else:
            return f"Результат: {feedback[:60]}..."
    
    def format_history_for_prompt(self) -> str:
        """Форматирует историю для промпта аналитика"""
        if not self.iteration_history:
            return "История отсутствует"
        
        formatted = "📜 ИСТОРИЯ ПОСЛЕДНИХ ИТЕРАЦИЙ:\n\n"
        
        for i, entry in enumerate(self.iteration_history[-self.max_history_length:], 1):
            formatted += f"─── Итерация #{entry.get('iteration', i)} ───\n"
            formatted += f"Задача: {entry.get('task', 'Нет')}\n"
            
            summary = entry.get('summary')
            if summary:
                formatted += f"Результат: {summary}\n"
            
            mode = entry.get('mode')
            if mode:
                mode_name = self.config.ANALYZER_MODES.get(mode, mode)
                formatted += f"Режим: {mode_name}\n"
            
            files = entry.get('files_changed', [])
            if files:
                formatted += f"Изменено файлов: {len(files)}\n"
            
            formatted += "\n"
        
        return formatted
    
    def add_to_history(self, task: str, summary: str = None, 
                      files_changed: List[str] = None, mode: str = None):
        """Добавляет итерацию в историю"""
        entry = {
            "iteration": self.iteration,
            "task": task,
            "timestamp": datetime.now().isoformat(),
            "summary": summary,
            "files_changed": files_changed or [],
            "mode": mode
        }
        
        self.iteration_history.append(entry)
        
        # Ограничиваем длину истории
        if len(self.iteration_history) > self.max_history_length:
            self.iteration_history = self.iteration_history[-self.max_history_length:]
    
    def update_architecture_file(self, iteration_info: Dict[str, Any]):
        """Обновляет файл архитектуры проекта"""
        arch_file = self.project_root / self.config.ARCHITECTURE_FILE
        
        # Читаем текущую архитектуру
        current_arch = ""
        if arch_file.exists():
            try:
                with open(arch_file, 'r', encoding='utf-8') as f:
                    current_arch = f.read()
            except:
                pass
        
        # Простое обновление - добавляем новую запись
        with open(arch_file, 'w', encoding='utf-8') as f:
            if current_arch:
                f.write(current_arch)
                f.write("\n\n")
            
            f.write(f"## Итерация #{iteration_info['iteration']} - {iteration_info['timestamp'][:10]}\n")
            f.write(f"**Задача:** {iteration_info['task']}\n")
            if iteration_info.get('summary'):
                f.write(f"**Результат:** {iteration_info['summary']}\n")
            if iteration_info.get('files_changed'):
                f.write(f"**Измененные файлы:** {', '.join(iteration_info['files_changed'])}\n")
            if iteration_info.get('mode'):
                mode_name = self.config.ANALYZER_MODES.get(iteration_info['mode'], iteration_info['mode'])
                f.write(f"**Режим:** {mode_name}\n")