"""
Основной класс AI-агента для разработки игр
"""
import json
import os
from typing import Dict, Any, Optional, List
from pathlib import Path
from datetime import datetime

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
        self.current_plan = None
        
        print(f"🎮 Инициализация AI-агента для разработки игр")
        print(f"📁 Проект: {self.project_root}")
        print(f"🔍 Аналитик: {self.config.ANALYZER_MODEL}")
        print(f"🔧 Исполнитель: {self.config.IMPLEMENTER_MODEL}")
        
        # Проверка подключения
        if not self.analyzer.ollama.check_connection():
            print("❌ Не удалось подключиться к Ollama")
            models = self.analyzer.ollama.list_models()
            if models:
                print(f"Доступные модели: {', '.join(models)}")
    
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
    
    def run_single_iteration(self, task: str) -> bool:
        """
        Выполняет одну итерацию разработки по новой архитектуре
        
        Returns:
            True если успешно, False если нужно завершить
        """
        print(f"\n{'='*60}")
        print(f"🔄 Итерация #{self.iteration + 1}")
        print(f"🎯 Задача: {task}")
        
        # Шаг 1: Получаем снапшот проекта
        print("\n📊 Анализ текущего состояния проекта...")
        snapshot = self.get_project_snapshot()
        print(f"📁 Найдено файлов: {len(snapshot)}")
        
        # Шаг 2: Аналитик создает план
        print("\n🔍 Консультация с архитектором-аналитиком...")
        plan_result = self.analyzer.create_plan(task, snapshot)
        
        if not plan_result:
            print("❌ Не удалось создать план")
            return True
            
        analysis = plan_result["analysis"]
        plan = plan_result["plan"]
        
        print(f"📋 Анализ: {analysis}")
        print(f"📋 План из {len(plan)} шагов:")
        for i, step in enumerate(plan, 1):
            print(f"  {i}. {step['file']}: {step['task']}")
        
        # Сохраняем план
        self.current_plan = plan_result
        
        # Шаг 3: Исполняем план шаг за шагом
        print("\n🔧 Начинаем выполнение плана...")
        results = {}
        
        for i, step in enumerate(plan, 1):
            print(f"\n📝 Шаг {i}/{len(plan)}: {step['file']}")
            print(f"   Задача: {step['task']}")
            
            # Получаем актуальный снапшот (после предыдущих шагов)
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
            
            # Проверяем код перед применением
            print(f"   Проверка кода ({len(code)} символов)...")
            
            # Применяем изменения
            file_changes = {step['file']: code}
            
            is_valid, message = self.executor.validate_file_changes(file_changes)
            if not is_valid:
                print(f"   ❌ {message}")
                results[step['file']] = f"FAILED: {message}"
                continue
            
            # Показываем diff пользователю
            old_content = current_snapshot.get(step['file'], "")
            if old_content and old_content != code:
                print(f"   📊 Изменения в файле:")
                print(f"      Было: {len(old_content)} символов")
                print(f"      Стало: {len(code)} символов")
                
                # Просим подтверждение для важных изменений
                if len(old_content) > 100:  # Если файл был значительного размера
                    print(f"   ⚠️  Файл будет перезаписан. Продолжить? (y/n)")
                    choice = input("   > ").strip().lower()
                    if choice not in ['y', 'yes', 'ok']:
                        print(f"   ⏭️ Пропущено")
                        results[step['file']] = "SKIPPED: Пользователь отменил"
                        continue
            
            # Применяем изменения
            step_results = self.executor.apply_changes(file_changes)
            results.update(step_results)
            
            print(f"   ✅ Шаг выполнен")
        
        # Шаг 4: Логируем итерацию
        self.log_iteration(task, plan_result, results)
        self.iteration += 1
        
        # Шаг 5: Показываем итоги
        print(f"\n📊 Итоги итерации #{self.iteration}:")
        for file, result in results.items():
            status = "✅" if "✅" in str(result) or "UPDATED" in str(result) else "❌"
            print(f"  {status} {file}: {result}")
        
        return True
    
    def log_iteration(self, task: str, plan: Dict[str, Any], results: Dict[str, str]) -> None:
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
                
                f.write(f"{'='*60}\n")
        except Exception as e:
            print(f"⚠️ Ошибка записи лога: {e}")
    
    def run_interactive(self):
        """Запускает интерактивный режим работы"""
        print("\n" + "="*50)
        print("🎮 AI-АГЕНТ РАЗРАБОТКИ ИГР (Многоуровневая архитектура)")
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
                task = input("> ").strip()
                
                if not task or task.lower() == 'stop':
                    break
                
                should_continue = self.run_single_iteration(task)
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
        print(f"🎉 Работа завершена!")