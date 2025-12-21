"""
FastRAG менеджер для IDLE-Ai-agent
"""

import json
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
import chromadb
#from chromadb.config import Settings
from sentence_transformers import SentenceTransformer

from config import CHROMA_PERSIST_DIR, EMBEDDING_MODEL, RAG_CATEGORIES, SIMILARITY_TOP_K

logger = logging.getLogger(__name__)

class FastRAG:
    """Быстрый RAG менеджер с ChromaDB"""
    
    def __init__(self):
        logger.info("Инициализация FastRAG...")
        
        # Инициализация эмбеддера
        self.embedder = SentenceTransformer(EMBEDDING_MODEL)
        logger.info(f"Загружен эмбеддер: {EMBEDDING_MODEL}")
        print(f"Размерность эмбеддингов: {self.embedder.get_sentence_embedding_dimension()}")
        
        # Создание директории для ChromaDB
        CHROMA_PERSIST_DIR.mkdir(parents=True, exist_ok=True)
        
        # Инициализация клиента ChromaDB
        self.client = chromadb.PersistentClient(
            path=str(CHROMA_PERSIST_DIR)
        )
        
        self.collection = None
        self._init_collection()
        
        logger.info("FastRAG инициализирован")
    
    def _init_collection(self):
        """Инициализация или создание коллекции"""
        try:
            self.collection = self.client.get_collection("game_templates")
            logger.info("Загружена существующая коллекция RAG")
        except:
            self.collection = self.client.create_collection(
                name="game_templates",
                metadata={
                    "description": "Шаблоны для разработки игр на PyGame",
                    "hnsw:space": "cosine"  # Косинусная метрика
                },
                embedding_function=None
            )
            logger.info("Создана новая коллекция RAG")
            self._load_initial_data()
    
    def _load_initial_data(self):
        """Загрузка начальных данных из JSON файлов"""
        logger.info("Загрузка начальных данных в RAG...")
        
        for category, config in RAG_CATEGORIES.items():
            file_path = config["file"]
            
            if not file_path.exists():
                logger.warning(f"Файл не найден: {file_path}")
                continue
                
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    examples = json.load(f)
                
                added_count = 0
                for example in examples:
                    # Добавляем каждый пример в коллекцию
                    self.add_document(
                        text=example["text"],
                        metadata={
                            "category": category,
                            "tags": ",".join(example["metadata"]["tags"]),
                            "id": example["id"],
                            "type": example["metadata"]["type"]
                        }
                    )
                    added_count += 1
                
                logger.info(f"Загружено {added_count} примеров из {category}")
                
            except Exception as e:
                logger.error(f"Ошибка загрузки {file_path}: {e}")
    
    def add_document(self, text: str, metadata: Dict[str, Any]):
        """Добавление документа в коллекцию"""
        try:
            # Генерация эмбеддинга
            embedding = self.embedder.encode(text).tolist()
            
            # Генерация уникального ID
            doc_id = f"{metadata['category']}_{metadata['id']}"
            
            # Добавление в коллекцию
            self.collection.add(
                embeddings=[embedding],
                documents=[text],
                metadatas=[metadata],
                ids=[doc_id]
            )
            
            logger.debug(f"Добавлен документ: {metadata['id']}")
            
        except Exception as e:
            logger.error(f"Ошибка добавления документа: {e}")
    
    def search(
        self, 
        query: str, 
        category: Optional[str] = None, 
        n_results: int = SIMILARITY_TOP_K
    ) -> List[Dict]:
        """
        Поиск похожих примеров
        
        Args:
            query: Текст запроса
            category: Категория для фильтрации (code_templates, task_plans, error_patterns)
            n_results: Количество возвращаемых результатов
            
        Returns:
            List[Dict]: Список найденных документов
        """
        try:
            # Генерация эмбеддинга для запроса
            query_embedding = self.embedder.encode(query).tolist()
            
            # Фильтр по категории если указана
            where_filter = {"category": category} if category else None
            
            # Поиск в коллекции
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=n_results,
                where=where_filter,
                include=["documents", "metadatas", "distances"]
            )
            
            # Форматирование результатов
            formatted_results = []
            for i in range(len(results["documents"][0])):
                formatted_results.append({
                    "text": results["documents"][0][i],
                    "metadata": results["metadatas"][0][i],
                    "similarity": 1 - results["distances"][0][i],  # Преобразуем расстояние в схожесть
                    "distance": results["distances"][0][i]
                })
            
            logger.debug(f"Поиск RAG: '{query[:50]}...' -> найдено {len(formatted_results)} результатов")
            return formatted_results
            
        except Exception as e:
            logger.error(f"Ошибка поиска в RAG: {e}")
            return []
    
    def get_collection_info(self) -> Dict:
        """Получение информации о коллекции"""
        try:
            count = self.collection.count()
            return {
                "total_documents": count,
                "categories": RAG_CATEGORIES.keys()
            }
        except:
            return {"total_documents": 0, "categories": []}


# Синглтон для удобного доступа
_rag_instance: Optional[FastRAG] = None

def get_rag() -> FastRAG:
    """Получение или создание экземпляра RAG"""
    global _rag_instance
    if _rag_instance is None:
        _rag_instance = FastRAG()
    return _rag_instance


def test_rag():
    """Тестирование RAG системы"""
    print("Тестирование RAG системы...")
    
    rag = get_rag()
    
    # Тест поиска
    test_queries = [
        "создать окно pygame",
        "игровой цикл",
        "обработка событий"
    ]
    
    for query in test_queries:
        print(f"\nПоиск: '{query}'")
        results = rag.search(query, category="code_templates", n_results=2)
        
        if results:
            for i, result in enumerate(results):
                print(f"  Результат {i+1}:")
                print(f"    Категория: {result['metadata']['category']}")
                print(f"    Теги: {result['metadata']['tags']}")
                print(f"    Схожесть: {result['similarity']:.3f}")
                print(f"    Текст: {result['text'][:100]}...")
        else:
            print("  Результатов не найдено")
    
    # Информация о коллекции
    info = rag.get_collection_info()
    print(f"\nИнформация о коллекции:")
    print(f"  Всего документов: {info['total_documents']}")
    print(f"  Категории: {', '.join(info['categories'])}")


if __name__ == "__main__":
    # Тест при прямом запуске
    import logging
    logging.basicConfig(level=logging.INFO)
    test_rag()