"""
Исполнитель для управления файлами проекта
"""
import os
import shutil
from pathlib import Path
from typing import Dict, Any
import traceback

class Executor:
    def __init__(self, project_root: str = "."):
        self.project_root = Path(project_root).resolve()
        self.backup_dir = self.project_root / ".agent_backups"
        
    def ensure_backup_dir(self):
        """Создает директорию для бэкапов"""
        self.backup_dir.mkdir(exist_ok=True)
    
    def backup_file(self, filepath: Path) -> bool:
        """Создает бэкап файла"""
        try:
            if not filepath.exists():
                return True
                
            backup_path = self.backup_dir / f"{filepath.name}.backup"
            # Сохраняем до 5 бэкапов
            if backup_path.exists():
                for i in range(4, 0, -1):
                    old_backup = self.backup_dir / f"{filepath.name}.backup.{i}"
                    new_backup = self.backup_dir / f"{filepath.name}.backup.{i+1}"
                    if old_backup.exists():
                        shutil.copy2(old_backup, new_backup)
                shutil.copy2(backup_path, self.backup_dir / f"{filepath.name}.backup.1")
            
            shutil.copy2(filepath, backup_path)
            return True
        except Exception as e:
            print(f"⚠️ Не удалось создать бэкап {filepath}: {e}")
            return False
    
    def apply_changes(self, file_changes: Dict[str, Any]) -> Dict[str, str]:
        """
        Применяет изменения к файлам проекта
        
        Args:
            file_changes: Словарь {путь_к_файлу: содержимое_или_None}
            
        Returns:
            Словарь с результатами операций
        """
        self.ensure_backup_dir()
        results = {}
        
        for file_path_str, content in file_changes.items():
            file_path = (self.project_root / file_path_str).resolve()
            
            try:
                # Проверяем, что файл находится внутри проекта
                if not str(file_path).startswith(str(self.project_root)):
                    results[file_path_str] = f"ERROR: Файл вне проекта: {file_path}"
                    continue
                
                # Создание директории если нужно
                file_path.parent.mkdir(parents=True, exist_ok=True)
                
                # Удаление файла
                if content is None:
                    if file_path.exists():
                        self.backup_file(file_path)
                        file_path.unlink()
                        results[file_path_str] = "DELETED"
                        print(f"🗑️  Удален файл: {file_path_str}")
                    else:
                        results[file_path_str] = "SKIP: Файл не существует"
                        print(f"⚠️  Файл не существует: {file_path_str}")
                
                # Создание/изменение файла
                else:
                    self.backup_file(file_path)
                    
                    # Запись с использованием временного файла
                    temp_file = file_path.with_suffix(file_path.suffix + '.tmp')
                    with open(temp_file, 'w', encoding='utf-8') as f:
                        f.write(content)
                        f.flush()
                    
                    # Атомарная замена
                    if file_path.exists():
                        file_path.unlink()
                    temp_file.rename(file_path)
                    
                    results[file_path_str] = "UPDATED"
                    print(f"✅ Обновлен файл: {file_path_str} ({len(content)} символов)")
                    
            except PermissionError:
                results[file_path_str] = "ERROR: Нет прав доступа"
                print(f"❌ Нет прав доступа: {file_path_str}")
            except Exception as e:
                results[file_path_str] = f"ERROR: {str(e)}"
                print(f"❌ Ошибка файла {file_path_str}: {e}")
                traceback.print_exc()
        
        return results
    
    def validate_file_changes(self, file_changes: Dict[str, Any]) -> tuple[bool, str]:
        """Проверяет валидность изменений перед применением"""
        for file_path_str in file_changes.keys():
            file_path = Path(file_path_str)
            
            # Проверка расширения
            if file_path.suffix not in ['.py', '.json', '.txt', '.md', '.yml', '.yaml', '']:
                return False, f"Неподдерживаемое расширение: {file_path_str}"
            
            # Проверка на опасные пути
            if '..' in file_path_str or file_path_str.startswith('/'):
                return False, f"Опасный путь: {file_path_str}"
        
        return True, "OK"