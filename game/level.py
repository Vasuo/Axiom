import pygame

class Level:
    def __init__(self):
        self.platforms = [
            pygame.Rect(100, 500, 200, 20),
            pygame.Rect(400, 400, 200, 20),
            pygame.Rect(200, 300, 200, 20)
        ]  # Пример инициализации платформ

    def draw(self, surface):
        for platform in self.platforms:
            pygame.draw.rect(surface, (0, 255, 0), platform)  # Рисуем платформы