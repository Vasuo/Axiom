import pygame

class JumpSquare(PhysicsEntity):
    def __init__(self, x, y, width, height):
        super().__init__(x, y, width, height)
        self.jump_speed = 10
        self.gravity = 1
    
    def update(self):
        # Управление направлением движения
        if pygame.key.get_pressed()[pygame.K_LEFT]:
            self.x -= self.vel_x
        elif pygame.key.get_pressed()[pygame.K_RIGHT]:
            self.x += self.vel_x
        
        # Управление скоростью объекта
        self.vel_y += self.gravity
        if self.rect.bottom > screen_rect.bottom:
            self.vel_y = 0
    
    def draw(self, surface):
        pygame.draw.rect(surface, (255, 0, 0), (self.x, self.y, self.width, self.height))

pygame.init()
screen_width = 800
screen_height = 600
screen = pygame.display.set_mode((screen_width, screen_height))
clock = pygame.time.Clock()

running = True

# Создание квадрата
x, y = 50, 50
width, height = 100, 100
square = JumpSquare(x, y, width, height)

while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
    
    keys = pygame.key.get_pressed()
    
    # Обновление квадрата
    square.update()
    
    # Отрисовка квадрата
    screen.fill((0, 0, 0))
    square.draw(screen)
    
    pygame.display.flip()
    clock.tick(60)

pygame.quit()