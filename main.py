# main.py
import os
import json
import sys
import io
from datetime import datetime
from openai import OpenAI
from dotenv import load_dotenv
from executor import Executor

# Настройка кодировки
if sys.stdout.encoding != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Системный промпт
system_prompt = system_prompt = system_prompt = """# РОЛЬ: AI-АРХИТЕКТОР ПРОЕКТОВ
Ты - виртуальный Principal Engineer. Твоя задача - ВЫПОЛНЯТЬ ЗАДАЧИ ПО РАЗРАБОТКЕ проекта.

# КРИТИЧЕСКИЕ ПРИНЦИПЫ:

## ПРИНЦИП 1: ВЫПОЛНЯЙ ПОСТАВЛЕННУЮ ЗАДАЧУ
- ВНИМАТЕЛЬНО прочитай задачу пользователя
- Определи КОНКРЕТНО что нужно сделать
- Выполни ИМЕННО то, что просят, а не что-то другое

## ПРИНЦИП 2: ИЗМЕНЯЙ СУЩЕСТВУЮЩИЕ ФАЙЛЫ ПРЕЖДЕ СОЗДАНИЯ НОВЫХ
- Если функциональность может быть добавлена в существующие классы → ИЗМЕНИ существующие файлы
- Создавай новые файлы ТОЛЬКО когда:
  * Нужен совершенно новый компонент
  * Существующие файлы стали слишком большими (>150 строк)
  * Архитектура явно требует разделения

## ПРИНЦИП 3: АНАЛИЗИРУЙ КОНТЕКСТ ЗАДАЧИ
- Если задача про игрока → меняй game/player.py
- Если задача про игру в целом → меняй game/core.py  
- Если задача про уровни → меняй game/level.py
- Создавай новые файлы ТОЛЬКО для принципиально новых сущностей

## ПРИНЦИП 4: СОЗДАВАЙ НЕДОСТАЮЩИЕ КОМПОНЕНТЫ
- Если в процессе выполнения задачи нужен отсутствующий компонент → СОЗДАЙ его
- Если код ссылается на несуществующий модуль → СОЗДАЙ его
- В остальных случаях → ИЗМЕНИ существующие файлы

# ПРОЦЕСС РАБОТЫ:

## ШАГ 1: АНАЛИЗ ЗАДАЧИ
- Что конкретно нужно сделать?
- Какие файлы наиболее релевантны?
- Нужны ли новые компоненты или можно обойтись существующими?

## ШАГ 2: ПЛАНИРОВАНИЕ РЕШЕНИЯ
- Какие изменения нужны в существующих файлах?
- Нужно ли создавать новые файлы? (ТОЛЬКО если необходимо)
- Как обеспечить целостность проекта?

## ШАГ 3: РЕАЛИЗАЦИЯ
- Внеси минимально необходимые изменения
- Сохрани работоспособность проекта
- Убедись что импорты и зависимости работают

# ТИПЫ ЗАДАЧ И ПОДХОДЫ:

## РАЗРАБОТКА НОВЫХ ФУНКЦИЙ
- Добавление механик → изменяй существующие классы
- Новая система → создавай новый файл если необходимо

## РЕФАКТОРИНГ СУЩЕСТВУЮЩЕГО КОДА
- Улучшение архитектуры → изменяй существующие файлы
- Разделение на модули → создавай новые файлы при необходимости

## ИСПРАВЛЕНИЕ ОШИБОК
- Найди коренную причину
- Внеси минимальные исправления
- Восстанови целостность проекта

# ФОРМАТ ОТВЕТА:
{
    "analysis": "ЗАДАЧА: [что нужно сделать] | ПОДХОД: [как буду решать] | ФАЙЛЫ: [почему выбрал эти]",
    "files": {
        "existing_file.py": "код"
    }
}
"""

def get_project_snapshot():
    """Возвращает полный снимок текущего состояния проекта"""
    snapshot = {}
    
    for root, dirs, files in os.walk("."):
        # Пропускаем служебные папки
        if any(skip in root for skip in ['.git', '__pycache__', '.env', 'venv']):
            continue
            
        for file in files:
            if file.endswith(('.py', '.json', '.txt', '.md', '.yml', '.yaml')):
                file_path = os.path.relpath(os.path.join(root, file))
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        snapshot[file_path] = f.read()
                except Exception as e:
                    snapshot[file_path] = f"[ОШИБКА ЧТЕНИЯ: {e}]"
    
    return snapshot

def save_iteration_log(iteration, problem, response, files_changed):
    """Сохраняет историю итераций в файл для отладки"""
    
    log_entry = f"""
=== ИТЕРАЦИЯ {iteration} ===
ВРЕМЯ: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
ЗАДАЧА: {problem}
ОТВЕТ: {json.dumps(response, ensure_ascii=False, indent=2)}
ИЗМЕНЕННЫЕ ФАЙЛЫ: {files_changed}
{'='*50}
"""
    
    try:
        with open('dev_history.log', 'a', encoding='utf-8') as f:
            f.write(log_entry)
        print(f"📝 Лог сохранен: dev_history.log")
    except Exception as e:
        print(f"⚠️ Не удалось сохранить лог: {e}")

def load_recent_context():
    """Загружает краткий контекст последних итераций"""
    try:
        if os.path.exists('dev_history.log'):
            with open('dev_history.log', 'r', encoding='utf-8') as f:
                content = f.read()
                # Берем последние 3 итерации для контекста
                iterations = content.split('=== ИТЕРАЦИЯ ')[-3:]
                context = []
                for iter_text in iterations:
                    if 'ЗАДАЧА:' in iter_text:
                        task = iter_text.split('ЗАДАЧА: ')[1].split('\n')[0]
                        context.append(task)
                return context
    except Exception as e:
        print(f"⚠️ Ошибка загрузки контекста: {e}")
    return []

def ask_ai(problem):
    """Отправляет ИИ текущее состояние проекта и задачу"""
    
    # Получаем актуальное состояние проекта
    current_state = get_project_snapshot()
    
    # УБИРАЕМ загрузку контекста - она только мешает
    # recent_context = load_recent_context()  # ← ЗАКОММЕНТИРОВАТЬ
    
    # Формируем сообщение для ИИ
    user_message = "ТЕКУЩЕЕ СОСТОЯНИЕ ПРОЕКТА:\n\n"
    
    # Добавляем все файлы проекта
    for filename, content in current_state.items():
        user_message += f"--- {filename} ---\n{content}\n\n"
    
    # УБИРАЕМ блок с последними задачами
    # if recent_context:
    #     user_message += "ПОСЛЕДНИЕ ЗАДАЧИ:\n"
    #     for i, task in enumerate(recent_context[-3:], 1):
    #         user_message += f"{i}. {task}\n"
    #     user_message += "\n"
    
    user_message += f"НОВАЯ ЗАДАЧА: {problem}"
    
    # Дальше обычный процесс...
    
    # Только системный промпт и текущее состояние
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_message}
    ]
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            response_format={"type": "json_object"}
        )
        
        return json.loads(response.choices[0].message.content)
        
    except Exception as e:
        print(f"❌ Ошибка API: {e}")
        return None

def run_development_cycle():
    """Запускает цикл разработки"""
    executor = Executor()

    print("🎮 АРХИТЕКТОР ПРОЕКТОВ ЗАПУЩЕН")
    print("=" * 50)
    
    # Проверяем наличие лога
    if os.path.exists('dev_history.log'):
        print("📖 Найден лог предыдущих сессий")
    
    # Проверяем текущее состояние проекта
    current_state = get_project_snapshot()
    if current_state:
        print(f"📁 Найден существующий проект ({len(current_state)} файлов)")
        for filename in current_state.keys():
            print(f"  • {filename}")
    else:
        print("📁 Проект пуст")
    
    # НАЧАЛЬНАЯ ЗАДАЧА - спрашиваем у пользователя
    print(f"\n🎯 Введите начальную задачу:")
    problem = input().strip()
    
    # Если пользователь просто нажал Enter - выходим
    if not problem:
        print("❌ Задача не указана. Завершение работы.")
        return

    iteration = 1
    while True:
        print(f"\n🔄 ИТЕРАЦИЯ {iteration}")
        print(f"Задача: {problem}")
        
        try:
            # Получаем план от ИИ
            plan = ask_ai(problem)
            
            if not plan:
                print("❌ Не удалось получить ответ от ИИ")
                break
                
            print(f"\n📋 АНАЛИЗ: {plan['analysis']}")
            
            # Показываем изменения
            files_to_change = list(plan['files'].keys())
            if files_to_change:
                print(f"📁 ФАЙЛЫ ДЛЯ ИЗМЕНЕНИЯ ({len(files_to_change)}):")
                for filename in files_to_change:
                    action = "🗑️  УДАЛИТЬ" if plan['files'][filename] is None else "📝 ИЗМЕНИТЬ"
                    print(f"  {action}: {filename}")
            else:
                print("📁 Нет изменений в файлах")
            
            # Подтверждение
            print(f"\n💡 Действие: (ok=применить, skip=пропустить, stop=закончить, view=показать код)")
            user_input = input().strip().lower()
            
            if user_input == 'ok':
                # Применяем изменения
                executor.apply_changes(plan['files'])
                
                # Сохраняем в лог
                save_iteration_log(iteration, problem, plan, files_to_change)
                
                print("✅ Изменения применены")
                
                # Новая задача от пользователя
                print(f"\n🎯 Введите следующую задачу (или 'stop' для завершения):")
                problem = input().strip()
                if problem.lower() == 'stop':
                    break
                if not problem:  # Если просто Enter - завершаем
                    break
                    
            elif user_input == 'skip':
                print("⏭️ Итерация пропущена")
                # Сохраняем в лог даже пропущенные итерации
                save_iteration_log(iteration, problem, plan, "ПРОПУЩЕНО")
                
                # Спрашиваем следующую задачу
                print(f"\n🎯 Введите следующую задачу:")
                problem = input().strip()
                if not problem or problem.lower() == 'stop':
                    break
                
            elif user_input == 'view':
                # Показываем код изменяемых файлов
                for filename, content in plan['files'].items():
                    if content is not None:
                        print(f"\n--- {filename} ---")
                        print(content[:500] + "..." if len(content) > 500 else content)
                
                print(f"\n💡 Применить изменения? (ok=да, skip=нет)")
                if input().strip().lower() == 'ok':
                    executor.apply_changes(plan['files'])
                    save_iteration_log(iteration, problem, plan, files_to_change)
                    print("✅ Изменения применены")
                
                print(f"\n🎯 Введите следующую задачу:")
                problem = input().strip()
                if not problem or problem.lower() == 'stop':
                    break
                
            elif user_input == 'stop':
                break
            else:
                print("⏭️ Итерация пропущена (неизвестная команда)")
                print(f"\n🎯 Введите следующую задачу:")
                problem = input().strip()
                if not problem or problem.lower() == 'stop':
                    break
                
            iteration += 1
            
        except Exception as e:
            print(f"❌ Ошибка: {e}")
            print("Введите задачу для исправления:")
            problem = input().strip()
            if not problem:
                break

    print(f"\n🎉 РАБОТА ЗАВЕРШЕНА. Всего итераций: {iteration-1}")

if __name__ == "__main__":
    run_development_cycle()