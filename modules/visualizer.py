"""
modules/visualizer.py
Улучшенный визуализатор с RAG для SD промптов
"""

import aiohttp
import asyncio
import logging
import base64
from pathlib import Path
from datetime import datetime
from PIL import Image, ImageDraw
import random

logger = logging.getLogger(__name__)

class VisualGenerator:
    """Улучшенный визуализатор с RAG для простых объектов"""
    
    def __init__(self, rag_manager=None):
        self.base_url = "http://localhost:7860"
        self.connected = False
        self.session = None
        self.rag = rag_manager
        self.sprites_dir = Path("games/sprites")
        self.sprites_dir.mkdir(parents=True, exist_ok=True)
        logger.info("VisualGenerator инициализирован")
    
    async def ensure_sd_ready(self) -> bool:
        """Проверка доступности SD"""
        if self.connected:
            return True
        
        try:
            if self.session is None:
                timeout = aiohttp.ClientTimeout(total=10)
                self.session = aiohttp.ClientSession(timeout=timeout)
            
            async with self.session.get(f"{self.base_url}/sdapi/v1/sd-models", timeout=5) as response:
                if response.status == 200:
                    self.connected = True
                    logger.info("SD подключен")
                    return True
                    
        except Exception as e:
            logger.warning(f"SD не доступен: {e}")
        
        return False
    
    async def generate_sprite(self, description: str, sprite_type: str = "item"):
        """
        Генерация спрайта с использованием RAG для промптов
        
        Args:
            description: Описание на русском (бочка, скелет, меч)
            sprite_type: Тип спрайта (enemy, item, weapon)
        """
        logger.info(f"Генерация спрайта: {description} ({sprite_type})")
        
        # 1. Ищем похожий промпт в RAG
        rag_prompt = None
        if self.rag:
            try:
                results = self.rag.search(
                    query=description,
                    category="sd_prompts",
                    n_results=3
                )
                
                if results:
                    rag_prompt = results[0]['text']
                    logger.info(f"Найден RAG промпт: {rag_prompt[:50]}...")
            except:
                pass
        
        # 2. Формируем финальный промпт
        if not rag_prompt:
            # Fallback: простые промпты для конкретных объектов
            prompt_map = {
                "скелет": "skeleton, bones, monster, white bones on black background",
                "бочка": "wooden barrel, brown, simple cylinder, game asset",
                "меч": "sword, weapon, silver blade, simple shape",
                "зелье": "potion bottle, green liquid, glass bottle, simple shape",
                "сундук": "treasure chest, wooden box, simple rectangle",
                "слизь": "slime monster, green blob, simple round shape",
                "ключ": "key, metal, simple shape, golden",
                "призрак": "ghost, white, simple round shape with wavy bottom",
                "монета": "coin, gold, simple circle, shiny",
                "сердце": "heart, red, health item, simple heart shape"
            }
            
            description_lower = description.lower()
            for key, prompt in prompt_map.items():
                if key in description_lower:
                    rag_prompt = prompt
                    break
        
        if not rag_prompt:
            rag_prompt = f"{description}, simple shape, front view, clean lines, game asset, cartoon style"
        
        final_prompt = f"{rag_prompt}, 2D game sprite, front view, centered, white background, clean lines, no details, cartoon style, simple"
        logger.info(f"Финальный промпт: {final_prompt}")
        
        # 3. Пытаемся сгенерировать через SD
        if await self.ensure_sd_ready():
            try:
                return await self._generate_with_sd(final_prompt, description, sprite_type)
            except Exception as e:
                logger.error(f"Ошибка SD генерации: {e}")
        
        # 4. Fallback: простая генерация через Pillow
        return await self._generate_simple_sprite(description, sprite_type)
    
    async def _generate_with_sd(self, prompt: str, description: str, sprite_type: str):
        """Генерация через Stable Diffusion"""
        try:
            negative_prompt = "pixel art, detailed, realistic, blurry, low quality, text, watermark, signature, background, landscape, portrait"
            
            payload = {
                "prompt": prompt,
                "negative_prompt": negative_prompt,
                "steps": 20,
                "cfg_scale": 7,
                "width": 256,
                "height": 256,
                "sampler_index": "Euler a",
                "batch_size": 1,
                "restore_faces": False
            }
            
            logger.info(f"Отправка запроса в SD: {prompt[:50]}...")
            
            async with self.session.post(
                f"{self.base_url}/sdapi/v1/txt2img",
                json=payload,
                timeout=60
            ) as response:
                
                if response.status == 200:
                    result = await response.json()
                    
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    filename = f"sd_{sprite_type}_{timestamp}.png"
                    filepath = self.sprites_dir / filename
                    
                    with open(filepath, "wb") as f:
                        f.write(base64.b64decode(result["images"][0]))
                    
                    logger.info(f"SD спрайт создан: {filename}")
                    
                    return {
                        "success": True,
                        "images": [{
                            "path": str(filepath),
                            "filename": filename,
                            "description": description,
                            "type": sprite_type,
                            "prompt": prompt,
                            "method": "stable_diffusion"
                        }]
                    }
                else:
                    error = await response.text()
                    logger.error(f"Ошибка SD API: {error[:200]}")
                    raise Exception("SD API error")
                    
        except Exception as e:
            logger.error(f"Ошибка генерации через SD: {e}")
            raise
    
    async def _generate_simple_sprite(self, description: str, sprite_type: str):
        """Простая генерация спрайта через Pillow"""
        size = 128
        img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        
        colors = {
            "enemy": (255, 50, 50, 255),
            "item": (255, 200, 50, 255),
            "weapon": (200, 200, 200, 255),
            "character": (50, 150, 255, 255)
        }
        
        color = colors.get(sprite_type, (150, 150, 150, 255))
        
        description_lower = description.lower()
        
        if any(word in description_lower for word in ["скелет", "кости", "кост", "skeleton"]):
            draw.ellipse([30, 30, 98, 98], fill=color)
            draw.rectangle([50, 80, 78, 110], fill=color)
            draw.line([40, 80, 50, 100], fill=color, width=4)
            draw.line([88, 80, 78, 100], fill=color, width=4)
            draw.line([50, 110, 45, 120], fill=color, width=4)
            draw.line([78, 110, 83, 120], fill=color, width=4)
            
        elif any(word in description_lower for word in ["бочка", "barrel"]):
            draw.ellipse([30, 40, 98, 88], fill=color)
            draw.rectangle([30, 64, 98, 68], fill=(100, 50, 0, 255))
            
        elif any(word in description_lower for word in ["меч", "sword"]):
            draw.rectangle([58, 30, 68, 90], fill=color)
            draw.rectangle([52, 90, 74, 100], fill=(100, 50, 0, 255))
            
        elif any(word in description_lower for word in ["зелье", "potion", "бутылка"]):
            draw.rectangle([50, 60, 78, 98], fill=(50, 200, 50, 255))
            draw.rectangle([48, 40, 80, 60], fill=color)
            draw.ellipse([48, 35, 80, 45], fill=color)
            
        else:
            draw.ellipse([30, 30, 98, 98], fill=color)
            
            if description:
                try:
                    from PIL import ImageFont
                    font = ImageFont.load_default()
                    text = description[0].upper()
                    text_bbox = draw.textbbox((0, 0), text, font=font)
                    text_width = text_bbox[2] - text_bbox[0]
                    text_height = text_bbox[3] - text_bbox[1]
                    x = (size - text_width) // 2
                    y = (size - text_height) // 2
                    draw.text((x, y), text, fill=(255, 255, 255, 255), font=font)
                except:
                    pass
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"simple_{sprite_type}_{timestamp}.png"
        filepath = self.sprites_dir / filename
        img.save(filepath, "PNG")
        
        logger.info(f"Простой спрайт создан: {filename}")
        
        return {
            "success": True,
            "images": [{
                "path": str(filepath),
                "filename": filename,
                "description": description,
                "type": sprite_type,
                "method": "simple_pillow"
            }]
        }
    
    async def analyze_code_for_sprites(self, code: str):
        """Анализ кода для поиска объектов"""
        sprites = []
        
        simple_objects = {
            "скелет": "enemy",
            "бочка": "item", 
            "меч": "weapon",
            "зелье": "item",
            "сундук": "item",
            "слизь": "enemy",
            "ключ": "item",
            "призрак": "enemy",
            "монета": "item",
            "сердце": "item",
            "игрок": "character",
            "враг": "enemy",
            "предмет": "item"
        }
        
        lines = code.split('\n')
        for line in lines:
            line_lower = line.lower()
            
            if '#' in line:
                comment = line.split('#')[1].strip()
                if len(comment) > 3:
                    for obj_word, obj_type in simple_objects.items():
                        if obj_word in comment.lower():
                            sprites.append({
                                "type": obj_type,
                                "description": obj_word
                            })
                            break
            
            if any(keyword in line_lower for keyword in ["sprite", "image", "draw", "рисуй", "спрайт"]):
                for obj_word, obj_type in simple_objects.items():
                    if obj_word in line_lower:
                        sprites.append({
                            "type": obj_type,
                            "description": obj_word
                        })
                        break
        
        if not sprites:
            sprites = [
                {"type": "character", "description": "игрок"},
                {"type": "enemy", "description": "скелет"},
                {"type": "item", "description": "меч"}
            ]
        
        unique_sprites = []
        seen = set()
        for sprite in sprites:
            key = f"{sprite['type']}_{sprite['description']}"
            if key not in seen:
                seen.add(key)
                unique_sprites.append(sprite)
        
        return unique_sprites[:3]
    
    async def close(self):
        if self.session:
            await self.session.close()

# СИНГЛТОН ДЛЯ ИМПОРТА
_visualizer_instance = None

async def get_visualizer():
    """Функция для импорта из agent.py"""
    global _visualizer_instance
    if _visualizer_instance is None:
        _visualizer_instance = VisualGenerator()
    return _visualizer_instance