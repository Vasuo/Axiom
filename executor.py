# executor.py
import os

class Executor:
    """
    Исполнитель для управления файлами проекта.
    """
    
    @staticmethod
    def apply_changes(file_changes):
        """
        Применяет изменения к файлам проекта.
        file_changes = {
            "main.py": "новый код",
            "old_file.py": None  # удалить файл
        }
        """
        for filename, content in file_changes.items():
            if content is None:
                # Удаление файла
                Executor.delete_file(filename)
            else:
                # Создание/перезапись файла
                Executor.write_file(filename, content)
    
    @staticmethod
    def write_file(filename, content):
        """Создает или перезаписывает файл с гарантированной записью"""
        try:
            os.makedirs(os.path.dirname(filename) or '.', exist_ok=True)
            
            # Вариант 1: Используем временный файл
            temp_file = filename + '.tmp'
            with open(temp_file, 'w', encoding='utf-8') as f:
                f.write(content)
                f.flush()
                os.fsync(f.fileno())
            
            # Заменяем оригинальный файл
            if os.path.exists(filename):
                os.remove(filename)
            os.rename(temp_file, filename)
            
            print(f"✅ Файл обновлен: {filename}")
            return True
            
        except Exception as e:
            print(f"❌ Ошибка файла {filename}: {e}")
            return False

    @staticmethod
    def delete_file(filename):
        """Удаляет файл"""
        try:
            if os.path.exists(filename):
                os.remove(filename)
                print(f"🗑️ Файл удален: {filename}")
                return True
            print(f"⚠️ Файл не найден: {filename}")
            return False
        except Exception as e:
            print(f"❌ Ошибка удаления {filename}: {e}")
            return False