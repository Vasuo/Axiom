# -*- coding: utf-8 -*-
class Square:
    def __init__(self, x, y, size):
        self.x = x
        self.y = y
        self.size = size

    def draw(self, surface):
        pygame.draw.rect(surface, RED, pygame.Rect(self.x, self.y, self.size, self.size))

    def update_position(self, speed):
        self.x += speed[0]
        self.y += speed[1]


# ===== АВТОМАТИЧЕСКИ СГЕНЕРИРОВАННЫЕ СПРАЙТЫ =====

try:
    character_sprite = pygame.image.load('C:/Users/Vasko/Desktop/Axiom 0.7.4/games/sprites/sd_character_20251221_063740.png').convert_alpha()
    print(f'Загружен спрайт: -*- coding: utf-8 -*...')
except Exception as e:
    print(f'Ошибка загрузки спрайта sd_character_20251221_063740.png: {e}')
    character_sprite = None  # Fallback
