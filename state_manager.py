# state_manager.py
"""
Управление состоянием задачи разработки игры
"""

import json
import logging
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any, Optional
from datetime import datetime
from pathlib import Path
from enum import Enum

logger = logging.getLogger(__name__)


class TaskStatus(Enum):
    """Статусы задачи"""
    PENDING = "pending"
    PLANNING = "planning"
    CODING = "coding"
    TESTING = "testing"
    FIXING = "fixing"
    COMPLETED = "completed"
    FAILED = "failed"


class ValidationStatus(Enum):
    """Статусы валидации"""
    NOT_STARTED = "not_started"
    PENDING = "pending"
    PASSED = "passed"
    FAILED = "failed"


@dataclass
class CodeChunk:
    """Фрагмент кода с метаданными"""
    subtask: str
    code: str
    timestamp: str
    model_used: str
    rag_context: Optional[List[str]] = None
    errors: List[str] = field(default_factory=list)


@dataclass
class ErrorInfo:
    """Информация об ошибке"""
    type: str
    description: str
    code_context: str
    timestamp: str
    user_feedback: Optional[str] = None
    suggested_fix: Optional[str] = None


@dataclass
class TaskState:
    """
    Полное состояние задачи разработки игры
    
    Сериализуется в JSON для сохранения сессии
    """
    # Основная информация
    task_id: str
    original_task: str
    created_at: str
    updated_at: str
    
    # Статусы
    task_status: TaskStatus = TaskStatus.PENDING
    validation_status: ValidationStatus = ValidationStatus.NOT_STARTED
    
    # Планирование
    subtasks: List[str] = field(default_factory=list)
    current_subtask_index: int = 0
    current_subtask: Optional[str] = None

    metadata: Dict[str, Any] = field(default_factory=dict)
    
    # Код
    code_chunks: List[CodeChunk] = field(default_factory=list)
    generated_code: str = ""
    
    current_code: str = ""
    
    # НОВОЕ: история изменений кода
    code_history: List[Dict[str, Any]] = field(default_factory=list)
    
    # Меняем generated_code на свойство
    @property
    def generated_code(self) -> str:
        return self.current_code
    
    @generated_code.setter
    def generated_code(self, value: str):
        self.current_code = value

    # Ошибки и фиксы
    errors_detected: List[ErrorInfo] = field(default_factory=list)
    user_feedback_history: List[Dict[str, str]] = field(default_factory=list)
    
    # Метаданные
    models_used: List[str] = field(default_factory=list)
    rag_searches: int = 0
    total_executions: int = 0
    successful_executions: int = 0
    
    @property
    def all_code(self) -> str:
        """Весь сгенерированный код"""
        return "\n\n".join([chunk.code for chunk in self.code_chunks])
    
    @property
    def progress_percentage(self) -> float:
        """Процент выполнения задачи"""
        if not self.subtasks:
            return 0.0
        return (self.current_subtask_index / len(self.subtasks)) * 100
    
    def add_code_chunk(self, subtask: str, new_full_code: str, model_used: str):
        """Добавление нового полного кода после модификации"""
        self.code_history.append({
            "timestamp": datetime.now().isoformat(),
            "subtask": subtask,
            "previous_code": self.current_code,
            "new_code": new_full_code,
            "model_used": model_used
        })
        self.current_code = new_full_code
        self.updated_at = datetime.now().isoformat()
        logger.info(f"Код обновлён для подзадачи: {subtask}")
    
    def add_error(
        self,
        error_type: str,
        description: str,
        code_context: str,
        user_feedback: Optional[str] = None
    ):
        """Добавление информации об ошибке"""
        error = ErrorInfo(
            type=error_type,
            description=description,
            code_context=code_context,
            timestamp=datetime.now().isoformat(),
            user_feedback=user_feedback
        )
        self.errors_detected.append(error)
        self.updated_at = datetime.now().isoformat()
        logger.warning(f"Зарегистрирована ошибка: {error_type}")
    
    def add_user_feedback(self, question: str, answer: str):
        """Добавление фидбека пользователя"""
        feedback = {
            "timestamp": datetime.now().isoformat(),
            "question": question,
            "answer": answer
        }
        self.user_feedback_history.append(feedback)
        self.updated_at = datetime.now().isoformat()
        logger.info(f"Добавлен фидбек пользователя: {question[:50]}...")
    
    def move_to_next_subtask(self):
        """Переход к следующей подзадаче"""
        if self.current_subtask_index < len(self.subtasks) - 1:
            self.current_subtask_index += 1
            self.current_subtask = self.subtasks[self.current_subtask_index]
            self.task_status = TaskStatus.CODING
            logger.info(f"Переход к подзадаче {self.current_subtask_index + 1}/{len(self.subtasks)}: {self.current_subtask}")
        else:
            self.task_status = TaskStatus.TESTING
            self.current_subtask = None
            logger.info("Все подзадачи выполнены, переход к тестированию")
    
    def to_dict(self) -> Dict[str, Any]:
        """Сериализация в словарь"""
        return {
            **asdict(self),
            "task_status": self.task_status.value,
            "validation_status": self.validation_status.value,
            "code_chunks": [asdict(chunk) for chunk in self.code_chunks],
            "errors_detected": [asdict(error) for error in self.errors_detected]
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TaskState":
        """Десериализация из словаря"""
        # Восстанавливаем enum значения
        data["task_status"] = TaskStatus(data["task_status"])
        data["validation_status"] = ValidationStatus(data["validation_status"])
        
        # Восстанавливаем списки объектов
        data["code_chunks"] = [CodeChunk(**chunk) for chunk in data.get("code_chunks", [])]
        data["errors_detected"] = [ErrorInfo(**error) for error in data.get("errors_detected", [])]
        
        return cls(**data)


class StateManager:
    """Менеджер для сохранения и загрузки состояний"""
    
    def __init__(self, storage_dir: Path):
        self.storage_dir = storage_dir
        self.storage_dir.mkdir(exist_ok=True)
        logger.info(f"Инициализирован StateManager с директорией: {storage_dir}")
    
    def save_state(self, state: TaskState) -> Path:
        """Сохранение состояния в файл"""
        filepath = self.storage_dir / f"{state.task_id}.json"
        
        state_dict = state.to_dict()
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(state_dict, f, ensure_ascii=False, indent=2)
        
        logger.info(f"Сохранено состояние задачи {state.task_id} в {filepath}")
        return filepath
    
    def load_state(self, task_id: str) -> Optional[TaskState]:
        """Загрузка состояния из файла"""
        filepath = self.storage_dir / f"{task_id}.json"
        
        if not filepath.exists():
            logger.warning(f"Файл состояния не найден: {filepath}")
            return None
        
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                state_dict = json.load(f)
            
            state = TaskState.from_dict(state_dict)
            logger.info(f"Загружено состояние задачи {task_id}")
            return state
            
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            logger.error(f"Ошибка загрузки состояния из {filepath}: {e}")
            return None
    
    def list_saved_states(self) -> List[str]:
        """Список сохранённых состояний"""
        states = []
        for filepath in self.storage_dir.glob("*.json"):
            states.append(filepath.stem)
        return sorted(states)
    
    def create_new_state(self, original_task: str) -> TaskState:
        """Создание нового состояния задачи"""
        from uuid import uuid4
        from datetime import datetime
        
        task_id = f"task_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid4().hex[:8]}"
        
        state = TaskState(
            task_id=task_id,
            original_task=original_task,
            created_at=datetime.now().isoformat(),
            updated_at=datetime.now().isoformat()
        )
        
        logger.info(f"Создано новое состояние задачи: {task_id}")
        return state