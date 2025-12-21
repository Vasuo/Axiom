# -*- coding: utf-8 -*-
import pygame

# Initialize PyGame
pygame.init()
screen = pygame.display.set_mode((640, 480))

# ===== АВТОМАТИЧЕСКИ СГЕНЕРИРОВАННЫЕ СПРАЙТЫ =====

try:
    character_sprite = pygame.image.load('games/sprites/simple_character_20251221_072853.png').convert_alpha()
    print(f'Загружен спрайт: игрок...')
except Exception as e:
    print(f'Ошибка загрузки спрайта simple_character_20251221_072853.png: {e}')
    character_sprite = None  # Fallback

try:
    enemy_sprite = pygame.image.load('games/sprites/simple_enemy_20251221_072856.png').convert_alpha()
    print(f'Загружен спрайт: скелет...')
except Exception as e:
    print(f'Ошибка загрузки спрайта simple_enemy_20251221_072856.png: {e}')
    enemy_sprite = None  # Fallback

try:
    item_sprite = pygame.image.load('games/sprites/simple_item_20251221_072858.png').convert_alpha()
    print(f'Загружен спрайт: меч...')
except Exception as e:
    print(f'Ошибка загрузки спрайта simple_item_20251221_072858.png: {e}')
    item_sprite = None  # Fallback

clock = pygame.time.Clock()

# Define the bird class
class Bird(object):
    def __init__(self, x, y, size, color=(255, 255, 255)):
        self.x = x
        self.y = y
        self.size = size
        self.color = color

    def draw(self):
        pygame.draw.rect(screen, self.color, (self.x, self.y, self.size, self.size))

# Define the platform class
class Platform(object):
    def __init__(self, x, y, width, height):
        self.x = x
        self.y = y
        self.width = width
        self.height = height

    def draw(self):
        pygame.draw.rect(screen, (0, 255, 0), (self.x, self.y, self.width, self.height))

# Initialize the bird and platform objects
bird = Bird(320, 240, 10)
platform = Platform(320, 240, 100, 50)

# Main game loop
running = True
while running:
    # Handle events
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

    # Handle keyboard input
    keys = pygame.key.get_pressed()
    if keys[pygame.K_LEFT]:
        platform.x -= 5
    elif keys[pygame.K_RIGHT]:
        platform.x += 5

    # Update the platform position and clamp it to the screen boundaries
    platform.rect = pygame.Rect(platform.x, platform.y, platform.width, platform.height)
    platform.rect.clamp_ip(screen.get_rect())

    # Check for collisions between bird and platform
    if bird.rect.colliderect(platform.rect):
        # If the bird is on top of the platform, make it jump
        bird.y -= 5

    # Fill the screen with black color
    screen.fill((0, 0, 0))

    # Draw the bird and platform
    bird.draw()
    platform.draw()

    # Update the display
    pygame.display.flip()

    # Limit the game loop to 60 frames per second
    clock.tick(60)

# Quit PyGame
pygame.quit()