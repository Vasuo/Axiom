"""
Основной класс AI-агента для разработки игр
"""
import json
import os
from typing import Dict, Any, Optional, List
from pathlib import Path
from datetime import datetime

from config import AgentConfig
from ollama_client import OllamaClient
from executor import Executor

class GameDevAgent:
    def __init__(self, project_root: str = None):
        self.config = AgentConfig()
        self.project_root = Path(project_root or self.config.DEFAULT_PROJECT_ROOT).resolve()
        self.ollama = OllamaClient()
        self.executor = Executor(self.project_root)
        
        # Состояние агента
        self.iteration = 0
        self.history = []
        
        print(f"🎮 Инициализация AI-агента для разработки игр")
        print(f"📁 Проект: {self.project_root}")
        print(f"🤖 Модель: {self.config.MODEL_NAME}")
        
        # Проверка подключения к Ollama
        if not self.ollama.check_connection():
            print("❌ Не удалось подключиться к Ollama")
            print("Убедитесь, что Ollama запущен: ollama serve")
            models = self.ollama.list_models()
            if models:
                print(f"Доступные модели: {', '.join(models)}")
            else:
                print("Модели не найдены. Установите модель: ollama pull llama3.1:8b")
    
    def get_project_snapshot(self) -> Dict[str, str]:
        """
        Возвращает полный снимок текущего состояния проекта
        
        Returns:
            Словарь {путь_к_файлу: содержимое}
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
                    snapshot[str(rel_path)] = f"[ОШИБКА ЧТЕНИЯ: {e}]"
        
        return snapshot
    
    def format_snapshot_for_prompt(self, snapshot: Dict[str, str]) -> str:
        """
        Форматирует снимок проекта для промпта
        
        Args:
            snapshot: Словарь с содержимым файлов
            
        Returns:
            Форматированная строка
        """
        if not snapshot:
            return "ПРОЕКТ ПУСТ\n"
        
        formatted = "ТЕКУЩЕЕ СОСТОЯНИЕ ПРОЕКТА:\n\n"
        
        # Сортируем файлы для консистентности
        sorted_files = sorted(snapshot.items())
        
        for file_path, content in sorted_files:
            formatted += f"=== {file_path} ===\n"
            formatted += f"{content}\n\n"
        
        return formatted
    
    def ask_ai(self, task: str) -> Optional[Dict[str, Any]]:
        """
        Отправляет задачу и состояние проекта ИИ
        
        Args:
            task: Текст задачи от пользователя
            
        Returns:
            Ответ ИИ в формате JSON или None
        """
        # Получаем текущее состояние
        print("📊 Анализ текущего состояния проекта...")
        snapshot = self.get_project_snapshot()
        print(f"📁 Найдено файлов: {len(snapshot)}")
        
        # Формируем промпт
        user_message = self.format_snapshot_for_prompt(snapshot)
        user_message += f"\n🎯 ЗАДАЧА: {task}\n\n"
        user_message += "Пожалуйста, проанализируй задачу и предоставь изменения в формате JSON."
        
        # Подготавливаем сообщения
        messages = [
            {"role": "system", "content": self.config.SYSTEM_PROMPT},
            {"role": "user", "content": user_message}
        ]
        
        # Отправляем запрос
        response = self.ollama.generate_response(messages)
        
        if response:
            # Валидация ответа
            if "analysis" not in response or "files" not in response:
                print("❌ Некорректный формат ответа ИИ")
                return None
            
            # Проверяем, что files является словарем
            if not isinstance(response["files"], dict):
                print("❌ Поле 'files' должно быть словарем")
                return None
            
            return response
        
        return None
    
    def log_iteration(self, task: str, response: Dict[str, Any], 
                     results: Dict[str, str]) -> None:
        """
        Логирует итерацию работы
        
        Args:
            task: Исходная задача
            response: Ответ ИИ
            results: Результаты применения изменений
        """
        self.iteration += 1
        
        log_entry = {
            "iteration": self.iteration,
            "timestamp": datetime.now().isoformat(),
            "task": task,
            "analysis": response.get("analysis", ""),
            "files_changed": list(response.get("files", {}).keys()),
            "execution_results": results,
            "ai_response": response
        }
        
        self.history.append(log_entry)
        
        # Сохраняем в файл
        try:
            with open(self.config.HISTORY_FILE, 'a', encoding='utf-8') as f:
                f.write(f"\n{'='*60}\n")
                f.write(f"Итерация #{self.iteration} - {log_entry['timestamp']}\n")
                f.write(f"Задача: {task}\n")
                f.write(f"Анализ: {log_entry['analysis']}\n")
                f.write(f"Измененные файлы: {len(log_entry['files_changed'])}\n")
                for file, result in results.items():
                    f.write(f"  - {file}: {result}\n")
                f.write(f"{'='*60}\n")
        except Exception as e:
            print(f"⚠️ Ошибка записи лога: {e}")
    
    def run_single_iteration(self, task: str) -> bool:
        """
        Выполняет одну итерацию разработки
        
        Args:
            task: Задача от пользователя
            
        Returns:
            True если успешно, False если нужно завершить
        """
        print(f"\n🔄 Итерация #{self.iteration + 1}")
        print(f"🎯 Задача: {task}")
        
        # Получаем ответ от ИИ
        ai_response = self.ask_ai(task)
        if not ai_response:
            print("❌ Не удалось получить ответ от ИИ")
            return True  # Продолжаем цикл
        
        print(f"\n📋 Анализ ИИ: {ai_response.get('analysis', 'Нет анализа')}")
        
        # Показываем планируемые изменения
        files = ai_response.get("files", {})
        if not files:
            print("📁 ИИ не предложил изменений файлов")
            self.log_iteration(task, ai_response, {"INFO": "Нет изменений"})
            return True
        
        print(f"📁 Затронуто файлов: {len(files)}")
        for file_path, content in files.items():
            action = "🗑️  УДАЛИТЬ" if content is None else "📝 ИЗМЕНИТЬ/СОЗДАТЬ"
            print(f"  {action}: {file_path}")
        
        # Запрашиваем подтверждение
        print("\n💡 Выберите действие:")
        print("  1. Применить изменения (ok)")
        print("  2. Пропустить (skip)")
        print("  3. Показать код (view)")
        print("  4. Завершить (stop)")
        
        while True:
            choice = input("Введите команду: ").strip().lower()
            
            if choice in ['1', 'ok', 'apply']:
                # Применяем изменения
                is_valid, message = self.executor.validate_file_changes(files)
                if not is_valid:
                    print(f"❌ {message}")
                    continue
                
                results = self.executor.apply_changes(files)
                self.log_iteration(task, ai_response, results)
                return True
                
            elif choice in ['2', 'skip']:
                print("⏭️ Итерация пропущена")
                self.log_iteration(task, ai_response, {"STATUS": "Пропущено"})
                return True
                
            elif choice in ['3', 'view']:
                # Показываем код
                for file_path, content in files.items():
                    if content is not None:
                        print(f"\n--- {file_path} ---")
                        preview = content[:500]
                        print(preview)
                        if len(content) > 500:
                            print(f"... (еще {len(content) - 500} символов)")
                        print()
                
                # После просмотра спрашиваем снова
                continue
                
            elif choice in ['4', 'stop', 'exit']:
                return False
                
            else:
                print("❌ Неизвестная команда")
                continue
    
    def run_interactive(self):
        """Запускает интерактивный режим работы"""
        print("\n" + "="*50)
        print("🎮 AI-АГЕНТ РАЗРАБОТКИ ИГР НА PYGAME")
        print("="*50)
        
        # Проверка модели
        models = self.ollama.list_models()
        if not models:
            print("⚠️  Нет доступных моделей Ollama")
            print("Установите модель: ollama pull llama3.1:8b")
            return
        
        print(f"✅ Доступные модели: {', '.join(models)}")
        
        # Начальная задача
        print("\n🎯 Введите начальную задачу (или 'stop' для выхода):")
        task = input("> ").strip()
        
        if not task or task.lower() == 'stop':
            return
        
        # Главный цикл
        while True:
            try:
                should_continue = self.run_single_iteration(task)
                if not should_continue:
                    break
                
                # Следующая задача
                print("\n🎯 Введите следующую задачу (или 'stop' для выхода):")
                task = input("> ").strip()
                
                if not task or task.lower() == 'stop':
                    break
                    
            except KeyboardInterrupt:
                print("\n\n⚠️  Прервано пользователем")
                break
            except Exception as e:
                print(f"❌ Критическая ошибка: {e}")
                break
        
        # Финальная статистика
        print(f"\n{'='*50}")
        print(f"📊 Статистика работы:")
        print(f"   Итераций выполнено: {self.iteration}")
        print(f"   История сохранена в: {self.config.HISTORY_FILE}")
        print(f"   Лог агента: {self.config.LOG_FILE}")
        print(f"🎉 Работа завершена!")