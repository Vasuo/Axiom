import pygame

class Player:
    def __init__(self):
        self.x = 100
        self.y = 100
        self.width = 50
        self.height = 60
        self.vel = 5
        self.gravity = 0.5  # Сила гравитации
        self.vel_y = 0  # Вертикальная скорость
        self.is_jumping = False  # Проверка на прыжок
        self.rect = pygame.Rect(self.x, self.y, self.width, self.height)

    def update(self, platforms):
        keys = pygame.key.get_pressed()
        if keys[pygame.K_LEFT]:
            self.rect.x -= self.vel
        if keys[pygame.K_RIGHT]:
            self.rect.x += self.vel
        if keys[pygame.K_SPACE] and not self.is_jumping:
            self.vel_y = -10  # Начальная скорость прыжка
            self.is_jumping = True

        self.vel_y += self.gravity  # Применяем гравитацию
        self.rect.y += self.vel_y  # Обновляем вертикальную позицию

        # Проверка на столкновение с платформами
        for platform in platforms:
            if self.rect.colliderect(platform):
                self.rect.y = platform.top - self.height  # Ставим игрока на платформу
                self.vel_y = 0  # Обнуляем вертикальную скорость
                self.is_jumping = False  # Возвращаем состояние прыжка к False

    def draw(self, surface):
        pygame.draw.rect(surface, (255, 0, 0), self.rect)  # Рисуем игрока красным