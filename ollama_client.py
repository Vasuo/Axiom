"""
Клиент для взаимодействия с Ollama API
"""
import json
import requests
from typing import Dict, Any, Optional, List
import time

class OllamaClient:
    def __init__(self, 
                 base_url: str = "http://localhost:11434",
                 model: str = "llama3.1:8b"):
        self.base_url = base_url
        self.model = model
        self.timeout = 60  # Увеличиваем для сложных задач
        
    def generate_response(self, 
                         messages: list,
                         format_json: bool = True,
                         temperature: float = 0.1) -> Optional[Any]:
        """
        Отправляет запрос к Ollama
        
        Args:
            messages: Список сообщений
            format_json: Требовать ли JSON ответ
            temperature: Креативность
            
        Returns:
            Ответ (JSON или текст)
        """
        try:
            payload = {
                "model": self.model,
                "messages": messages,
                "stream": False,
                "options": {
                    "temperature": temperature,
                    "num_predict": 4096
                }
            }
            
            if format_json:
                payload["format"] = "json"
            
            print(f"🤖 [{self.model}] Отправка запроса...")
            start_time = time.time()
            
            response = requests.post(
                f"{self.base_url}/api/chat",
                json=payload,
                timeout=self.timeout
            )
            
            elapsed = time.time() - start_time
            print(f"✅ Ответ получен за {elapsed:.2f} секунд")
            
            if response.status_code == 200:
                result = response.json()
                content = result.get("message", {}).get("content", "")
                
                if format_json:
                    try:
                        return json.loads(content)
                    except json.JSONDecodeError:
                        print(f"❌ Не удалось распарсить JSON: {content[:200]}...")
                        return None
                else:
                    return content.strip()
            else:
                print(f"❌ Ошибка API: {response.status_code}")
                return None
                
        except requests.exceptions.Timeout:
            print(f"❌ Таймаут запроса к {self.model}")
            return None
        except Exception as e:
            print(f"❌ Ошибка: {e}")
            return None
    
    def check_connection(self) -> bool:
        """Проверяет подключение к Ollama"""
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=5)
            return response.status_code == 200
        except:
            return False
    
    def list_models(self) -> List[str]:
        """Получает список доступных моделей"""
        try:
            response = requests.get(f"{self.base_url}/api/tags")
            if response.status_code == 200:
                models = response.json().get("models", [])
                return [model["name"] for model in models]
            return []
        except:
            return []