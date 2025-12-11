"""
Клиент для взаимодействия с Ollama API
"""
import json
import requests
from typing import Dict, Any, Optional
from config import AgentConfig
import time

class OllamaClient:
    def __init__(self, base_url: str = "http://localhost:11434"):
        self.base_url = base_url
        self.model = AgentConfig.MODEL_NAME
        self.timeout = 30
        
    def check_connection(self) -> bool:
        """Проверяет подключение к Ollama"""
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=5)
            return response.status_code == 200
        except requests.exceptions.ConnectionError:
            return False
    
    def generate_response(self, messages: list) -> Optional[Dict[str, Any]]:
        """
        Отправляет запрос к Ollama и получает ответ
        
        Args:
            messages: Список сообщений в формате [{"role": "system/user", "content": "..."}]
        
        Returns:
            Ответ в формате JSON или None в случае ошибки
        """
        try:
            payload = {
                "model": self.model,
                "messages": messages,
                "stream": False,
                "format": "json",  # Форсируем JSON ответ
                "options": {
                    "temperature": AgentConfig.TEMPERATURE,
                    "num_predict": AgentConfig.MAX_TOKENS
                }
            }
            
            print(f"🤖 Отправка запроса к модели {self.model}...")
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
                content = result.get("message", {}).get("content", "{}")
                
                try:
                    return json.loads(content)
                except json.JSONDecodeError as e:
                    print(f"❌ Ошибка парсинга JSON: {e}")
                    print(f"Ответ: {content[:200]}...")
                    return None
            else:
                print(f"❌ Ошибка API: {response.status_code}")
                print(response.text)
                return None
                
        except requests.exceptions.Timeout:
            print("❌ Таймаут запроса к Ollama")
            return None
        except requests.exceptions.ConnectionError:
            print("❌ Не удалось подключиться к Ollama")
            print(f"Убедитесь, что Ollama запущен на {self.base_url}")
            return None
        except Exception as e:
            print(f"❌ Неожиданная ошибка: {e}")
            return None
    
    def list_models(self) -> list:
        """Получает список доступных моделей"""
        try:
            response = requests.get(f"{self.base_url}/api/tags")
            if response.status_code == 200:
                models = response.json().get("models", [])
                return [model["name"] for model in models]
            return []
        except:
            return []