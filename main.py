"""
Главный файл запуска AI-агента разработки игр
"""
import sys
import os
from pathlib import Path

# Добавляем текущую директорию в путь для импортов
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from agent import GameDevAgent

def print_banner():
    """Выводит баннер приложения"""
    banner = """
    ╔═══════════════════════════════════════════════════╗
    ║        🎮 AI-АГЕНТ РАЗРАБОТКИ ИГР PYGAME         ║
    ║            Версия 1.0 - с Ollama 8B              ║
    ╚═══════════════════════════════════════════════════╝
    
    Основные возможности:
    • Автоматическая разработка игр на Pygame
    • Модульная архитектура с разделением по файлам
    • Работа с локальной моделью Ollama 8B
    • Безопасное управление файлами проекта
    • Полная история изменений
    
    Управление:
    • Введите задачу - агент проанализирует и внесет изменения
    • ok - применить изменения
    • skip - пропустить итерацию
    • view - показать код перед применением
    • stop - завершить работу
    """
    print(banner)

def main():
    """Основная функция запуска"""
    print_banner()
    
    # Определяем корень проекта
    if len(sys.argv) > 1:
        project_root = sys.argv[1]
    else:
        project_root = input("Введите путь к проекту (по умолчанию '.'): ").strip() or "."
    
    # Создаем агента
    try:
        agent = GameDevAgent(project_root)
        agent.run_interactive()
    except KeyboardInterrupt:
        print("\n\n👋 Работа завершена пользователем")
    except Exception as e:
        print(f"\n❌ Критическая ошибка: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()