import pygame
import sys
import os

FPS = 50
GRAVITY = 200

pygame.init()
size = WIDTH, HEIGHT = 1000, 500
screen = pygame.display.set_mode(size)
clock = pygame.time.Clock()


def load_image(name, colorkey=None):
    fullname = os.path.join('data', name)
    if not os.path.isfile(fullname):
        print(f"Файл с изображением '{fullname}' не найден")
        sys.exit()
    image = pygame.image.load(fullname)
    if colorkey is not None:
        image = image.convert()
        if colorkey == -1:
            colorkey = image.get_at((0, 0))
        image.set_colorkey(colorkey)
    else:
        image = image.convert_alpha()
    return image


class Entity(pygame.sprite.Sprite):
    def __init__(self, pos):
        super().__init__(player_group, all_sprites)
        self.image = player_image
        self.rect = self.image.get_rect()
        self.rect.bottomleft = pos
        self.pos = list(pos)
        self.start_pos = list(pos)

        self.jump_faze = 0
        self.jump_speed = -200

        self.push_faze = 0
        self.in_pushing = False
        self.push_speed = 500
        self.push_dist = 50
        self.push_acc = self.push_speed ** 2 / (2 * self.push_dist) * -1

    def update(self, time, push=False):
        self.push_faze += time
        if push:
            self.push_faze = 0
            self.in_pushing = True
            self.start_pos[0] = self.pos[0]
        if self.in_pushing:
            self.pos[0] = (self.start_pos[0] + self.push_speed * self.push_faze
                           + (self.push_acc * self.push_faze ** 2) / 2)
            if self.pos[0] - self.start_pos[0] >= self.push_dist - 1:
                self.in_pushing = False

        self.jump_faze += time
        collider = pygame.sprite.spritecollideany(self, platforms_group)
        if collider:
            self.jump_faze = 0
            self.start_pos[1] = collider.rect.topleft[1]

        self.pos[1] = (self.start_pos[1] + self.jump_speed * self.jump_faze +
                       (GRAVITY * self.jump_faze ** 2) / 2)
        self.rect.bottomleft = self.pos


class Platform(pygame.sprite.Sprite):
    def __init__(self, pos):
        super().__init__(platforms_group, all_sprites)
        self.image = pygame.Surface((700, 10))
        pygame.draw.rect(self.image, "gray", (0, 0, 700, 10))
        self.rect = self.image.get_rect()
        self.rect.topleft = pos


all_sprites = pygame.sprite.Group()
player_group = pygame.sprite.Group()
platforms_group = pygame.sprite.Group()

player_image = load_image('player.png')

player = Entity((50, 300))
platform = Platform((40, 490))

timer = pygame.time.Clock()
time = 0
running = True
while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_SPACE:
                player_group.update(time, True)

    screen.fill("black")
    
    all_sprites.draw(screen)
    
    player_group.update(time)
    
    time = timer.tick() / 1000
    pygame.display.flip()