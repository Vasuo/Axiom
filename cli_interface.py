"""
cli_interface.py
Расширенный CLI интерфейс для агента
"""

import asyncio
import os
import sys
from typing import Optional
from datetime import datetime
import json

class CLIInterface:
    """Расширенный CLI с интерактивным управлением"""
    
    def __init__(self, agent):
        self.agent = agent
        self.running = True
    
    def clear_screen(self):
        """Очистка экрана"""
        os.system('cls' if os.name == 'nt' else 'clear')
    
    def print_header(self, title: str):
        """Печать заголовка"""
        print("\n" + "="*60)
        print(f" {title}")
        print("="*60)
    
    async def show_main_menu(self):
        """Главное меню"""
        while self.running:
            self.clear_screen()
            self.print_header("IDLE-Ai-agent ДЛЯ РАЗРАБОТКИ ИГР")
            
            # Показываем статус агента
            status = await self.agent.get_interface_status()
            self._print_status(status)
            
            print("\nМЕНЮ:")
            print("1. 🎮 Создать новую игру")
            print("2. 📊 Детальный просмотр состояния")
            print("3. 🔍 Управление RAG базой")
            print("4. 🧪 Тестирование и отладка")
            print("5. 📈 Статистика и логи")
            print("6. ⚙️  Настройки")
            print("7. 🌐 Запустить веб-интерфейс")
            print("8. 🚪 Выход")
            
            try:
                choice = input("\nВыберите действие (1-8): ").strip()
                
                if choice == "1":
                    await self.create_new_game()
                elif choice == "2":
                    await self.show_detailed_status()
                elif choice == "3":
                    await self.manage_rag()
                elif choice == "4":
                    await self.testing_menu()
                elif choice == "5":
                    await self.show_statistics()
                elif choice == "6":
                    await self.settings_menu()
                elif choice == "7":
                    await self.start_web_interface()
                elif choice == "8":
                    self.running = False
                    print("\nЗавершение работы...")
                else:
                    print("Неверный выбор")
                    await asyncio.sleep(1)
                    
            except KeyboardInterrupt:
                print("\n\nПрервано пользователем")
                self.running = False
                break
            except Exception as e:
                print(f"\nОшибка: {e}")
                await asyncio.sleep(2)
    
    def _print_status(self, status: dict):
        """Печать статуса агента"""
        if status.get("agent") == "idle":
            print("🤖 Статус: Ожидает задачи")
        else:
            print(f"🤖 Статус: {status.get('status', 'unknown')}")
            print(f"📋 Задача: {status.get('original_task', 'N/A')[:50]}...")
            print(f"📊 Прогресс: {status.get('progress', 0):.1f}%")
            print(f"🔧 Текущая подзадача: {status.get('current_subtask', 'N/A')}")
        
        if "stats" in status:
            stats = status["stats"]
            print(f"🎮 Создано игр: {stats.get('games_created', 0)}")
            print(f"🔍 RAG поисков: {stats.get('rag_searches', 0)}")
    
    async def create_new_game(self):
        """Создание новой игры"""
        self.clear_screen()
        self.print_header("СОЗДАНИЕ НОВОЙ ИГРЫ")
        
        print("\nПримеры задач:")
        print("1. Создай окно 800x600 с синим фоном")
        print("2. Создай красный квадрат, управляемый стрелками")
        print("3. Создай упрощенную змейку")
        print("4. Создай простой платформер")
        print("5. Своя задача")
        
        try:
            choice = input("\nВыберите пример или введите свою задачу: ").strip()
            
            if choice == "1":
                task = "Создай окно 800x600 с синим фоном"
            elif choice == "2":
                task = "Создай красный квадрат, управляемый стрелками"
            elif choice == "3":
                task = "Создай упрощенную змейку"
            elif choice == "4":
                task = "Создай простой платформер"
            else:
                task = choice if len(choice) > 5 else input("Введите описание игры: ")
            
            if task:
                print(f"\n🚀 Начинаю разработку: {task}")
                
                # Показываем прогресс в реальном времени
                await self.show_development_progress(task)
                
        except KeyboardInterrupt:
            print("\nОтменено")
    
    async def show_development_progress(self, task: str):
        """Отображение прогресса разработки в реальном времени"""
        self.clear_screen()
        self.print_header("РАЗРАБОТКА В РЕАЛЬНОМ ВРЕМЕНИ")
        
        print(f"Задача: {task}")
        print("\n" + "-"*60)
        
        # Создаем задачу
        task_id = await self.agent.start_new_task(task)
        
        # Мониторим прогресс
        last_status = None
        while True:
            status = await self.agent.get_interface_status()
            
            # Обновляем только при изменении
            if status != last_status:
                self.clear_screen()
                self.print_header("РАЗРАБОТКА В РЕАЛЬНОМ ВРЕМЕНИ")
                print(f"Задача: {task}")
                print("\n" + "-"*60)
                
                # Прогресс-бар
                progress = status.get('progress', 0)
                bar_length = 40
                filled = int(bar_length * progress / 100)
                bar = '█' * filled + '░' * (bar_length - filled)
                print(f"\nПрогресс: [{bar}] {progress:.1f}%")
                
                # Текущая подзадача
                if status.get('current_subtask'):
                    print(f"\nТекущая подзадача: {status['current_subtask']}")
                
                # Ошибки
                if status.get('errors_count', 0) > 0:
                    print(f"\n⚠️  Обнаружено ошибок: {status['errors_count']}")
                
                last_status = status
            
            # Проверяем завершение
            if status.get('status') in ['completed', 'failed']:
                break
            
            await asyncio.sleep(1)
        
        # Показываем результат
        print("\n" + "="*60)
        print("РАЗРАБОТКА ЗАВЕРШЕНА!")
        
        if status.get('status') == 'completed':
            print("✅ Успешно!")
            
            # Предлагаем посмотреть код
            print("\nДействия:")
            print("1. Просмотреть код")
            print("2. Запустить игру")
            print("3. Вернуться в меню")
            
            choice = input("\nВыберите действие (1-3): ")
            if choice == "1":
                await self.view_generated_code(task_id)
            elif choice == "2":
                await self.run_game(task_id)
        
        await asyncio.sleep(3)
    
    async def show_detailed_status(self):
        """Детальный просмотр состояния"""
        self.clear_screen()
        self.print_header("ДЕТАЛЬНЫЙ СТАТУС АГЕНТА")
        
        status = await self.agent.get_interface_status()
        
        print(json.dumps(status, indent=2, ensure_ascii=False))
        
        input("\nНажмите Enter для возврата...")
    
    async def manage_rag(self):
        """Управление RAG базой"""
        self.clear_screen()
        self.print_header("УПРАВЛЕНИЕ RAG БАЗОЙ")
        
        print("\nДействия:")
        print("1. Поиск в базе")
        print("2. Добавить пример")
        print("3. Просмотр статистики")
        print("4. Вернуться")
        
        choice = input("\nВыберите действие (1-4): ").strip()
        
        if choice == "1":
            query = input("Введите запрос для поиска: ")
            category = input("Категория (оставьте пустым для всех): ") or None
            
            results = await self.agent.search_rag_from_interface(query, category)
            
            if results:
                print(f"\nНайдено {len(results)} результатов:")
                for i, result in enumerate(results, 1):
                    print(f"\n{i}. Категория: {result['metadata']['category']}")
                    print(f"   Схожесть: {result['similarity']:.3f}")
                    print(f"   Текст: {result['text'][:100]}...")
            else:
                print("Результатов не найдено")
            
            input("\nНажмите Enter для продолжения...")
    
    async def testing_menu(self):
        """Меню тестирования"""
        self.clear_screen()
        self.print_header("ТЕСТИРОВАНИЕ И ОТЛАДКА")
        
        print("\nДействия:")
        print("1. Тест планировщика")
        print("2. Тест конструктора кода")
        print("3. Тест фиксера")
        print("4. Запустить произвольный код")
        print("5. Вернуться")
        
        choice = input("\nВыберите действие (1-5): ").strip()
        
        if choice == "4":
            print("\nВведите код Python (Ctrl+D для завершения):")
            print("="*60)
            
            code_lines = []
            try:
                while True:
                    line = input()
                    code_lines.append(line)
            except EOFError:
                pass
            
            code = "\n".join(code_lines)
            
            if code:
                print("\nЗапускаю код...")
                result = await self.agent.interface_bridge.execute_code(code)
                
                print(f"\nРезультат: {'✅ Успешно' if result['success'] else '❌ Ошибка'}")
                print(f"Вывод: {result['output'][:500]}...")
            
            input("\nНажмите Enter для продолжения...")
    
    async def start_web_interface(self):
        """Запуск веб-интерфейса"""
        print("\nЗапуск веб-интерфейса...")
        print("Откройте в браузере: http://localhost:8080")
        print("Для остановки нажмите Ctrl+C в этом окне")
        
        # Импортируем и запускаем веб-сервер
        try:
            from web_interface import start_web_server
            await start_web_server(self.agent)
        except ImportError:
            print("Веб-интерфейс не настроен")
            input("\nНажмите Enter для продолжения...")
    
    async def view_generated_code(self, task_id: str):
        """Просмотр сгенерированного кода"""
        from state_manager import StateManager
        
        # Загружаем состояние
        state = self.agent.state_manager.load_state(task_id)
        if not state or not state.current_code:
            print("Код не найден")
            return
        
        self.clear_screen()
        self.print_header("СГЕНЕРИРОВАННЫЙ КОД")
        
        print(f"Задача: {state.original_task}")
        print(f"Размер кода: {len(state.current_code)} символов")
        print("\n" + "="*60 + "\n")
        
        # Показываем код с нумерацией строк
        lines = state.current_code.split('\n')
        for i, line in enumerate(lines[:50], 1):  # Показываем первые 50 строк
            print(f"{i:3d} | {line}")
        
        if len(lines) > 50:
            print(f"\n... и ещё {len(lines) - 50} строк")
        
        input("\nНажмите Enter для продолжения...")
    
    async def run_game(self, task_id: str):
        """Запуск игры"""
        from state_manager import StateManager
        
        state = self.agent.state_manager.load_state(task_id)
        if not state or not state.current_code:
            print("Код не найден")
            return
        
        print("\nЗапуск игры...")
        result = await self.agent.interface_bridge.execute_code(state.current_code)
        
        print(f"\nРезультат: {'✅ Успешно' if result['success'] else '❌ Ошибка'}")
        if result['output']:
            print(f"Вывод:\n{result['output'][:1000]}")
        
        input("\nНажмите Enter для продолжения...")

async def main():
    """Главная функция CLI"""
    from agent import GameDevAgent
    
    print("Запуск IDLE-Ai-agent CLI...")
    
    try:
        agent = GameDevAgent()
        success = await agent.initialize_modules()
        if not success:
            print("Ошибка инициализации модулей")
            return
        
        cli = CLIInterface(agent)
        await cli.show_main_menu()
        
        print("\nРабота завершена.")
        
    except Exception as e:
        print(f"Ошибка: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())