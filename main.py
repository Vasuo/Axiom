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
    ║           Многоуровневая архитектура             ║
    ║         Аналитик + Исполнитель + Ollama          ║
    ╚═══════════════════════════════════════════════════╝
    
    Архитектура проекта:
    • agent.py - Главный координатор
    • analyzer.py - Аналитик-планировщик
    • implementer.py - Программист-исполнитель
    • executor.py - Менеджер файлов
    • ollama_client.py - Клиент Ollama
    • config.py - Конфигурация
    • main.py - Точка входа
    
    Преимущества новой архитектуры:
    • Более точное планирование
    • Последовательное выполнение
    • Минимальные конфликты в коде
    • Лучший контроль над процессом
    """
    print(banner)

def main():
    """Основная функция запуска"""
    print_banner()
    
    # Определяем корень проекта
    if len(sys.argv) > 1:
        project_root = sys.argv[1]
    else:
        # ИСПРАВЛЕННАЯ СТРОКА - закрытая кавычка
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