"""
Исполнитель для управления файлами проекта
"""
import os
import shutil
from pathlib import Path
from typing import Dict, Any, Tuple
import traceback
from datetime import datetime  # ДОБАВЛЕНО

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
                
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = self.backup_dir / f"{filepath.name}.{timestamp}.backup"
            
            shutil.copy2(filepath, backup_path)
            return True
        except Exception as e:
            print(f"⚠️ Не удалось создать бэкап {filepath}: {e}")
            return False
    
    def apply_changes(self, file_changes: Dict[str, Any]) -> Dict[str, str]:
        """
        Применяет изменения к файлам проекта
        """
        self.ensure_backup_dir()
        results = {}
        
        for file_path_str, content in file_changes.items():
            file_path = (self.project_root / file_path_str).resolve()
            
            try:
                # Проверяем, что файл находится внутри проекта
                if not str(file_path).startswith(str(self.project_root)):
                    results[file_path_str] = f"ERROR: Файл вне проекта"
                    continue
                
                # Создание директории если нужно
                file_path.parent.mkdir(parents=True, exist_ok=True)
                
                # Удаление файла
                if content is None:
                    if file_path.exists():
                        self.backup_file(file_path)
                        file_path.unlink()
                        results[file_path_str] = "DELETED"
                    else:
                        results[file_path_str] = "SKIP: Файл не существует"
                
                # Создание/изменение файла
                else:
                    # ВАЖНО: Проверяем что content - строка
                    if not isinstance(content, str):
                        results[file_path_str] = f"ERROR: Неподдерживаемый тип {type(content)}"
                        continue
                    
                    self.backup_file(file_path)
                    
                    # Запись с использованием временного файла
                    temp_file = file_path.with_suffix(file_path.suffix + '.tmp')
                    with open(temp_file, 'w', encoding='utf-8', errors='replace') as f:
                        f.write(content)
                        f.flush()
                    
                    # Атомарная замена
                    if file_path.exists():
                        file_path.unlink()
                    temp_file.rename(file_path)
                    
                    results[file_path_str] = f"✅ UPDATED ({len(content)} символов)"
                    
            except PermissionError:
                results[file_path_str] = "ERROR: Нет прав доступа"
            except Exception as e:
                results[file_path_str] = f"ERROR: {str(e)}"
                traceback.print_exc()
        
        return results
    
    def validate_file_changes(self, file_changes: Dict[str, Any]) -> Tuple[bool, str]:
        """Проверяет валидность изменений перед применением"""
        for file_path_str, content in file_changes.items():
            file_path = Path(file_path_str)
            
            # Проверка расширения
            if file_path.suffix and file_path.suffix not in ['.py', '.json', '.txt', '.md', '.yml', '.yaml']:
                return False, f"Неподдерживаемое расширение: {file_path_str}"
            
            # Проверка на опасные пути
            if '..' in file_path_str or file_path_str.startswith('/'):
                return False, f"Опасный путь: {file_path_str}"
            
            # Проверка типа контента
            if content is not None and not isinstance(content, str):
                return False, f"Контент должен быть строкой, а не {type(content)}"
        
        return True, "OK"