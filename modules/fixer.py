"""
Модуль анализа и исправления ошибок с user-in-the-loop
"""

import subprocess
import tempfile
import os
import logging
from typing import Dict, Any, Optional, Tuple, List
from rag_manager import get_rag
from config import MODELS, MAX_CODE_EXECUTION_TIME

logger = logging.getLogger(__name__)

class FixerDetector:
    """Детектор ошибок с интерактивным исправлением"""
    
    def __init__(self, ollama_client):
        self.ollama = ollama_client
        self.rag = get_rag()
        logger.info("FixerDetector инициализирован")
    
    async def analyze_code(self, code: str, task_description: str) -> Dict[str, Any]:
        """
        Полный анализ кода: запуск + анализ + исправление
        """
        logger.info("Запуск анализа кода...")
        
        results = {
            "code": code,
            "original_code": code,
            "execution_success": False,
            "errors_detected": [],
            "user_feedback": None,
            "fixed_code": code,
            "fix_applied": False
        }
        
        # 1. Статический анализ
        static_issues = await self._static_analysis(code)
        if static_issues:
            results["errors_detected"].extend(static_issues)
        
        # 2. Динамический анализ (запуск кода)
        execution_result = await self._execute_code_safe(code)
        results["execution_result"] = execution_result
        results["execution_success"] = execution_result["success"]
        
        if not execution_result["success"]:
            # 3. Анализ ошибок выполнения
            runtime_issues = await self._analyze_runtime_error(
                code, 
                execution_result,
                task_description
            )
            results["errors_detected"].extend(runtime_issues)
        
        # 4. User-in-the-loop: запрос фидбека
        if results["errors_detected"] or not results["execution_success"]:
            user_feedback = await self._get_user_feedback(results)
            results["user_feedback"] = user_feedback
            
            # 5. Попытка исправления
            if user_feedback != "skip":
                fixed_code = await self._generate_fix(
                    code,
                    results["errors_detected"],
                    user_feedback,
                    task_description
                )
                results["fixed_code"] = fixed_code
                results["fix_applied"] = fixed_code != code
        
        return results
    
    async def _static_analysis(self, code: str) -> List[Dict[str, str]]:
        """Статический анализ кода на типовые ошибки"""
        issues = []
        
        # Проверка encoding declaration
        if not code.startswith('# -*- coding: utf-8 -*-'):
            issues.append({
                "type": "encoding_error",
                "description": "Missing encoding declaration",
                "severity": "critical"
            })
        
        # Проверка импортов
        if "import pygame" not in code:
            issues.append({
                "type": "missing_import",
                "description": "Missing pygame import",
                "severity": "critical"
            })
        
        # Проверка инициализации
        if "pygame.init()" not in code:
            issues.append({
                "type": "missing_init",
                "description": "Missing pygame.init()",
                "severity": "critical"
            })
        
        # Проверка игрового цикла
        if "while" not in code or "pygame.event.get()" not in code:
            issues.append({
                "type": "missing_game_loop",
                "description": "No main game loop found",
                "severity": "high"
            })
        
        # Проверка обновления экрана
        if "pygame.display.flip()" not in code and "pygame.display.update()" not in code:
            issues.append({
                "type": "missing_display_update",
                "description": "No screen update found",
                "severity": "high"
            })
        
        # Проверка на не-ASCII символы
        if any(ord(c) > 127 for c in code):
            issues.append({
                "type": "non_ascii_chars",
                "description": "Code contains non-ASCII characters",
                "severity": "critical"
            })
        
        return issues
    
    async def _execute_code_safe(self, code: str) -> Dict[str, Any]:
        """Безопасный запуск кода с таймаутом"""
        try:
            # Предварительная очистка кода
            code = self._sanitize_code(code)
            
            # Создаем временный файл
            with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False, encoding='utf-8') as f:
                f.write(code)
                temp_file = f.name
            
            # Запускаем код
            result = subprocess.run(
                ['python', temp_file],
                capture_output=True,
                text=True,
                timeout=MAX_CODE_EXECUTION_TIME,
                encoding='utf-8'
            )
            
            # Удаляем временный файл
            os.unlink(temp_file)
            
            return {
                "success": result.returncode == 0,
                "return_code": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "output": result.stderr if result.stderr else result.stdout
            }
            
        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "return_code": -1,
                "output": f"Timeout: Program ran for more than {MAX_CODE_EXECUTION_TIME} seconds"
            }
        except Exception as e:
            return {
                "success": False,
                "return_code": -1,
                "output": f"Execution error: {str(e)}"
            }
    
    def _sanitize_code(self, code: str) -> str:
        """Полная санитарная очистка кода"""
        if not code:
            return ""
        
        # 1. Убедимся, что есть encoding declaration
        if not code.startswith('# -*- coding: utf-8 -*-'):
            code = '# -*- coding: utf-8 -*-\n' + code
        
        # 2. Удаляем все не-ASCII символы
        sanitized = []
        for char in code:
            if 32 <= ord(char) <= 126 or char in '\n\t\r':
                sanitized.append(char)
            else:
                sanitized.append(' ')  # Заменяем не-ASCII на пробел
        
        code = ''.join(sanitized)
        
        # 3. Удаляем повторяющиеся encoding declarations
        lines = code.split('\n')
        cleaned_lines = []
        encoding_added = False
        for line in lines:
            if '# -*- coding: utf-8 -*-' in line:
                if not encoding_added:
                    cleaned_lines.append(line)
                    encoding_added = True
            else:
                cleaned_lines.append(line)
        
        # 4. Убедимся, что encoding declaration в начале
        if encoding_added and '# -*- coding: utf-8 -*-' not in cleaned_lines[0]:
            for i, line in enumerate(cleaned_lines):
                if '# -*- coding: utf-8 -*-' in line:
                    cleaned_lines.pop(i)
                    cleaned_lines.insert(0, line)
                    break
        
        return '\n'.join(cleaned_lines)
    
    async def _analyze_runtime_error(
        self, 
        code: str, 
        execution_result: Dict[str, Any],
        task_description: str
    ) -> List[Dict[str, str]]:
        """Анализ ошибок выполнения с помощью RAG"""
        error_output = execution_result["output"]
        
        # Поиск похожих ошибок в RAG
        similar_errors = self.rag.search(
            query=error_output[:100] if error_output else "runtime error",
            category="error_patterns",
            n_results=3
        )
        
        issues = []
        
        # Детекция кодировочных ошибок (самая важная!)
        if "Non-UTF-8 code" in error_output or "encoding declared" in error_output:
            issues.append({
                "type": "encoding_error",
                "description": "Encoding problem (file not UTF-8)",
                "severity": "critical",
                "rag_context": self._extract_rag_context(similar_errors, "encoding_error")
            })
        
        # Базовый анализ по ключевым словам
        if "ImportError" in error_output:
            issues.append({
                "type": "import_error",
                "description": "Module import error",
                "severity": "critical",
                "rag_context": self._extract_rag_context(similar_errors, "import_error")
            })
        
        if "NameError" in error_output:
            issues.append({
                "type": "name_error",
                "description": "Undefined variable or function",
                "severity": "high",
                "rag_context": self._extract_rag_context(similar_errors, "name_error")
            })
        
        if "SyntaxError" in error_output or "IndentationError" in error_output:
            issues.append({
                "type": "syntax_error",
                "description": "Syntax or indentation error",
                "severity": "critical",
                "rag_context": self._extract_rag_context(similar_errors, "syntax_error")
            })
        
        if "AttributeError" in error_output:
            issues.append({
                "type": "attribute_error",
                "description": "Object attribute error",
                "severity": "high",
                "rag_context": self._extract_rag_context(similar_errors, "attribute_error")
            })
        
        # Черный экран или таймаут
        if not error_output.strip() or "ТАЙМАУТ" in error_output or "Timeout" in error_output:
            issues.append({
                "type": "black_screen_or_timeout",
                "description": "Black screen or infinite loop",
                "severity": "high",
                "rag_context": self._extract_rag_context(similar_errors, "black_screen")
            })
        
        return issues
    
    def _extract_rag_context(self, similar_errors: List, error_type: str) -> str:
        """Извлечение контекста из RAG для конкретного типа ошибки"""
        for error in similar_errors:
            if error_type in error['metadata'].get('type', ''):
                # Очищаем текст от не-ASCII
                text = error['text']
                cleaned = ''.join(c for c in text if ord(c) < 128 or c in '\n\t\r')
                return cleaned[:300]
        return ""
    
    async def _get_user_feedback(self, analysis_results: Dict) -> str:
        """Интерактивный диалог с пользователем"""
        errors = analysis_results["errors_detected"]
        exec_result = analysis_results.get("execution_result", {})
        
        print(f"\n{'='*60}")
        print("CODE ANALYSIS COMPLETE")
        print(f"{'='*60}")
        
        if analysis_results["execution_success"]:
            print("✅ Code executes successfully!")
            if exec_result.get('stdout'):
                print(f"Output: {exec_result['stdout'][:100]}...")
            return "success"
        else:
            print("⚠️ Issues detected:")
            
            for i, error in enumerate(errors):
                print(f"\n{i+1}. {error['type'].upper()} ({error['severity']}):")
                print(f"   {error['description']}")
            
            if exec_result.get('output'):
                print(f"\nError output: {exec_result['output'][:200]}...")
            
            print(f"\n{'='*60}")
            print("OPTIONS:")
            print("1. Try to fix automatically")
            print("2. Show full code for manual editing")
            print("3. Skip fix (continue)")
            print("4. Cancel task")
            print(f"{'='*60}")
            
            try:
                choice = input("\nChoose option (1-4): ").strip()
                if choice == "1":
                    return "auto_fix"
                elif choice == "2":
                    print(f"\n{'='*60}")
                    print("FULL CODE:")
                    print(f"{'='*60}")
                    print(analysis_results["code"])
                    print(f"{'='*60}")
                    return "manual_review"
                elif choice == "3":
                    return "skip"
                elif choice == "4":
                    return "cancel"
                else:
                    return "auto_fix"
            except:
                return "auto_fix"
    
    async def _generate_fix(
        self, 
        code: str,
        errors: List[Dict],
        user_feedback: str,
        task_description: str
    ) -> str:
        """Генерация исправленного кода"""
        if user_feedback == "skip" or not errors:
            return self._sanitize_code(code)
        
        # 1. Сначала применяем простые автоматические исправления
        fixed_code = self._sanitize_code(code)
        
        for error in errors:
            if error["type"] == "encoding_error":
                # Уже исправлено в _sanitize_code
                pass
            
            if error["type"] == "missing_init" and "pygame.init()" not in fixed_code:
                # Добавляем pygame.init() после импортов
                lines = fixed_code.split('\n')
                new_lines = []
                for line in lines:
                    new_lines.append(line)
                    if 'import pygame' in line and 'pygame.init()' not in '\n'.join(new_lines):
                        new_lines.append('pygame.init()')
                fixed_code = '\n'.join(new_lines)
        
        # 2. Если после простых исправлений всё ещё есть критические ошибки, используем модель
        if any(e["severity"] == "critical" for e in errors) and user_feedback == "auto_fix":
            # Собираем информацию об ошибках для промпта
            error_summary = "\n".join([
                f"- {error['type']}: {error['description']}"
                for error in errors[:3]
            ])
            
            # Поиск решений в RAG
            solutions = []
            for error in errors[:2]:
                rag_solutions = self.rag.search(
                    query=error['type'],
                    category="error_patterns",
                    n_results=1
                )
                if rag_solutions:
                    solutions.append(rag_solutions[0]['text'])
            
            rag_context = "\n\n".join(solutions) if solutions else ""
            
            # Системный промпт на английском
            system_prompt = f"""You are a PyGame error fixing expert.

TASK: {task_description}

DETECTED ERRORS:
{error_summary}

{rag_context if rag_context else "Use standard PyGame error fixing patterns."}

INSTRUCTIONS:
1. Analyze the code below
2. Fix ALL detected errors
3. Keep working functionality
4. Return COMPLETE fixed code
5. Code must compile and run
6. Use ONLY ASCII characters (English only)
7. Add '# -*- coding: utf-8 -*-' at the top

Return only the fixed Python code without explanations."""
            
            try:
                response = await self.ollama.generate(
                    model=MODELS["fixer"],
                    prompt=f"Fix errors in code:\n```python\n{code}\n```",
                    system=system_prompt,
                    temperature=0.3,
                    max_tokens=1500
                )
                
                fixed_code = response.response.strip()
                
                # Извлечение кода из markdown
                if '```python' in fixed_code:
                    parts = fixed_code.split('```python')
                    if len(parts) > 1:
                        fixed_code = parts[1].split('```')[0].strip()
                
                # Санитарная очистка
                fixed_code = self._sanitize_code(fixed_code)
                
                logger.info(f"Generated fixed code ({len(fixed_code)} chars)")
                return fixed_code
                
            except Exception as e:
                logger.error(f"Error generating fix: {e}")
                return self._sanitize_code(code)  # Возвращаем очищенный исходный код
        
        return fixed_code