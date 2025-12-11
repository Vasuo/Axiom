import pygame
import sys
from player import Player
from level import Level  # Исправлено: правильный импорт класса Level

class Game:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((800, 600))
        self.clock = pygame.time.Clock()
        self.player = Player()
        self.level = Level()  # Инициализируем Level

    def run(self):
        while True:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()
            self.player.update(self.level.platforms)  # Передаем платформы в метод обновления игрока
            self.screen.fill((0, 0, 0))  # Заполнение фона черным
            self.level.draw(self.screen)  # Рисуем уровень
            self.player.draw(self.screen)  # Рисуем игрока
            pygame.display.flip()
            self.clock.tick(60)  # Ограничение до 60 FPS

if __name__ == '__main__':
    game = Game()
    game.run()