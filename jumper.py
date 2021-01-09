import pygame
import sys
import os
from random import randrange, getrandbits

FPS = 50
GRAVITY = 300

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


class Camera:
    def __init__(self, target=None, limit=500):
        self.x = 0
        self.set_target(target, limit)

    def apply(self, group, k=1):
        for sprite in group:
            if sprite != self.target:
                sprite.rect.x = sprite.start_pos[0] + (self.x - sprite.camera_delta) * k

    def set_target(self, target, limit):
        self.target = target
        self.limit = limit

    def set_position(self, pos):
        if pos[0] > self.limit:
            self.x = -pos[0] + self.limit
        else:
            self.target.rect.x = pos[0]
        self.target.rect.bottom = pos[1]


class Sprite(pygame.sprite.Sprite):
    def __init__(self, pos, *groups, randflip=False):
        super().__init__(*groups)

        self.death = False

        self.frames = {}
        self.cur_frame = 0
        self.anim_name = None
        self.anim_delay = 0
        self.anim_phase = 0
        self.flipped = getrandbits(1) if randflip else 0
        self.prev_name = None

        self.start_pos = list(pos)
        self.camera_delta = camera.x

    def update(self, time):
        if self.rect.right < 0 or self.rect.top > HEIGHT:
            self.kill()

        self.anim_phase += time
        if self.anim_name and self.anim_phase > self.anim_delay:
            self.anim_phase = 0
            if self.cur_frame + 1 < len(self.frames[self.anim_name]):
                self.cur_frame += 1
                self.image = pygame.transform.flip(
                    self.frames[self.anim_name][self.cur_frame],
                    self.flipped, 0)
                new_pos = self.rect.midbottom
                self.rect = self.image.get_rect()
                self.rect.midbottom = new_pos
            else:
                self.prev_name = self.anim_name
                self.anim_name = None

    def cut_sheet(self, sheet, name, columns, rows):
        self.rect = pygame.Rect(0, 0, sheet.get_width() // columns,
                                sheet.get_height() // rows)
        for j in range(rows):
            for i in range(columns):
                frame_location = (self.rect.w * i, self.rect.h * j)
                self.frames.setdefault(name, [])
                self.frames[name].append(sheet.subsurface(pygame.Rect(
                    frame_location, self.rect.size)))

    def start_anim(self, name, delay):
        self.anim_name = name
        self.anim_delay = delay
        self.cur_frame = 0

    def is_playing(self):
        return bool(self.anim_name)


class Background(Sprite):
    def __init__(self, image, x, group):
        super().__init__((x, 0), group, all_backs_group, all_sprites)
        self.image = image
        self.rect = self.image.get_rect()
        self.rect.left = x


class Player(Sprite):
    def __init__(self, pos, jump_speed):
        super().__init__(pos, player_group, all_sprites)
        self.cut_sheet(player_jump_sheet, "jump", 6, 1)
        self.cut_sheet(player_landing_sheet, "landing", 6, 1)
        self.cut_sheet(player_die_sheet, "die", 15, 1)
        self.image = self.frames["jump"][0]
        self.rect = self.image.get_rect()
        self.rect.bottomleft = pos
        self.pos = list(pos)
        self.move_pos = list(pos)

        self.m = 1

        self.push_phase = 0
        self.in_pushing = False
        self.push_speed = 500
        self.push_dist = 80
        self.push_acc = self.push_speed ** 2 / (2 * self.push_dist) * -1

        self.is_jump = True
        self.jump_phase = 0
        self.jump_speed = jump_speed

        self.start_anim("jump", 0.15)


    def update(self, time, push=False):
        super().update(time)
        self.push_phase += time
        self.jump_phase += time
        if push and not self.death:
            self.push_phase = 0
            self.in_pushing = True
            self.move_pos[0] = self.pos[0]

        collider = pygame.sprite.spritecollideany(self, platforms_group)
        enemy = pygame.sprite.spritecollideany(self, enemies_group)
        if self.in_pushing and not collider:
            self.pos[0] = (self.move_pos[0] + self.push_speed * self.push_phase
                           + (self.push_acc * self.push_phase ** 2) / 2)
            if self.pos[0] - self.move_pos[0] >= self.push_dist - 1:
                self.in_pushing = False

        if collider:
            if self.rect.bottom - collider.rect.top < 5:
                self.is_jump = False
                self.jump_phase = 0
                self.move_pos[1] = collider.rect.topleft[1]
                if not self.is_playing() and self.prev_name != "landing":
                    self.start_anim("landing", 0.01)
                    self.is_jump = True
            else:
                self.in_pushing = False

        if self.is_jump:
            if not self.is_playing() and self.prev_name != "jump":
                self.start_anim("jump", 0.15)

            self.pos[1] = (self.move_pos[1] - self.jump_speed * self.jump_phase +
                           (GRAVITY * self.jump_phase ** 2) / 2)

        if not self.death and enemy and sum([bool(
                self.rect.collidepoint(x, y))
            for x, y in (enemy.rect.topleft,
                         enemy.rect.midtop,
                         enemy.rect.topright)]) == 2:
            enemy.kill()

        camera.set_position(self.pos)

        if self.death:
            if self.anim_name != "die" and self.prev_name != "die":
                self.start_anim("die", 0.05)
                self.jump_phase = 0
                self.jump_speed = 0
                self.move_pos[1] = self.pos[1]
            if self.prev_name == "die":
                super().kill()

    def kill(self):
        self.death = True


class Enemy(Sprite):
    def __init__(self, pos, jump_speed):
        super().__init__(pos, enemies_group, all_sprites, randflip=True)
        self.cut_sheet(enemy_jump_sheet, "jump", 13, 1)
        self.cut_sheet(enemy_landing_sheet, "landing", 5, 1)
        self.cut_sheet(enemy_die_sheet, "die", 15, 1)
        self.image = self.frames["jump"][0]
        self.rect = self.image.get_rect()
        self.rect.bottomleft = pos
        self.pos = list(pos)
        self.move_pos = list(pos)

        self.is_jump = True
        self.jump_phase = 0
        self.jump_speed = jump_speed

        self.in_pushing = False
        self.push_phase = 0
        self.push_speed = 0
        self.push_acc = 0

    def update(self, time):
        super().update(time)
        self.jump_phase += time
        self.push_phase += time

        collider = pygame.sprite.spritecollideany(self, platforms_group)
        if collider:
            if self.rect.bottom - collider.rect.top < 5:
                self.is_jump = False
                self.jump_phase = 0
                self.move_pos[1] = collider.rect.topleft[1]
                if not self.is_playing() and self.prev_name != "landing":
                    self.start_anim("landing", 0.01)
                    self.is_jump = True

        if self.is_jump:
            if not self.is_playing() and self.prev_name != "jump":
                self.start_anim("jump", 0.1)

            self.pos[1] = (self.move_pos[1] - self.jump_speed * self.jump_phase +
                           (GRAVITY * self.jump_phase ** 2) / 2)

        player = pygame.sprite.spritecollideany(self, player_group)
        enemy = pygame.sprite.spritecollideany(self, enemies_group)
        if (player or enemy != self) and not self.death:
            self.pos[0] += 5

        if not self.death and player and sum([bool(
                self.rect.collidepoint(x, y))
            for x, y in (player.rect.topleft,
                         player.rect.midtop,
                         player.rect.topright)]) == 2:
            player.kill()

        self.start_pos[0] = self.pos[0]
        self.rect.bottom = self.pos[1]

        if self.death:
            if self.anim_name != "die" and self.prev_name != "die":
                self.start_anim("die", 0.05)
                self.jump_phase = 0
                self.jump_speed = 0
                self.move_pos[1] = self.pos[1]
            if self.prev_name == "die":
                super().kill()

    def kill(self):
        self.death = True


class Bomb(Sprite):
    def __init__(self, pos):
        super().__init__(pos, bombs_group, all_sprites)
        self.cut_sheet(fire_sheet, "fire", 7, 1)
        self.cut_sheet(boom_sheet, "boom", 6, 1)
        self.image = self.frames["fire"][0]
        self.rect = self.image.get_rect()
        self.rect.bottom = pos[1]
        self.radius = 150

        self.player = None

    def update(self, time):
        super().update(time)
        player = pygame.sprite.spritecollideany(self, player_group)
        if player and not self.is_playing() and self.prev_name != "fire":
            self.start_anim("fire", 0.3)
        if not self.is_playing() and self.prev_name == "fire":
            for entity in (enemies_group.sprites() +
                           player_group.sprites()):
                if pygame.sprite.collide_circle(self, entity):
                    entity.kill()
            self.start_anim("boom", 0.15)
        if self.prev_name == "boom":
            self.kill()


class Platform(Sprite):
    def __init__(self, x, height, length):
        super().__init__((x, HEIGHT - height), platforms_group, all_sprites)
        self.image = pygame.Surface((length, height))
        pygame.draw.rect(self.image, "#7A2029", (0, 0, length, height))
        self.rect = self.image.get_rect()
        self.rect.bottomleft = (x, HEIGHT)


all_sprites = pygame.sprite.Group()

all_backs_group = pygame.sprite.Group()
sky_group = pygame.sprite.Group()
bg_group = pygame.sprite.Group()
middle_group = pygame.sprite.Group()
fg_group = pygame.sprite.Group()
grass_group = pygame.sprite.Group()

player_group = pygame.sprite.Group()
enemies_group = pygame.sprite.Group()
bombs_group = pygame.sprite.Group()
platforms_group = pygame.sprite.Group()

sky_image = load_image("sky.png")
bg_image = load_image("bg.png")
middle_image = load_image("middle.png")
fg_image = load_image("fg.png")
grass_image = load_image("grass.png")

player_jump_sheet = load_image("player_jump.png")
player_landing_sheet = load_image("player_landing.png")
player_die_sheet = load_image("player_die.png")
enemy_jump_sheet = load_image("enemy_jump.png")
enemy_landing_sheet = load_image("enemy_landing.png")
enemy_die_sheet = load_image("enemy_die.png")
fire_sheet = load_image("fire.png")
boom_sheet = load_image("boom.png")


camera = Camera()

last_sky = Background(sky_image, 0, sky_group)
last_bg = Background(bg_image, 0, bg_group)
last_middle = Background(middle_image, 0, middle_group)
last_fg = Background(fg_image, 0, fg_group)
last_grass = Background(grass_image, 0, grass_group)

last_platform = Platform(30, 100, 500)
last_enemy = Enemy((350, 400), 250)
last_bomb = Bomb((300, 400))
player = Player((50, 300), 300)

camera.set_target(player, 600)

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

    if last_sky.rect.right < 2 * WIDTH:
        last_sky = Background(sky_image, last_sky.rect.right, sky_group)
    if last_bg.rect.right < 2 * WIDTH:
        last_bg = Background(bg_image, last_bg.rect.right, bg_group)
    if last_middle.rect.right < 2 * WIDTH:
        last_middle = Background(middle_image, last_middle.rect.right, middle_group)
    if last_fg.rect.right < 2 * WIDTH:
        last_fg = Background(fg_image, last_fg.rect.right, fg_group)
    if last_grass.rect.right < 2 * WIDTH:
        last_grass = Background(grass_image, last_grass.rect.right - 5, grass_group)

    if last_platform.rect.right < 2 * WIDTH:
        new_x = last_platform.rect.right + randrange(150, 300)
        height = randrange(40, 95)
        length = randrange(150, 500)

        last_platform = Platform(new_x, height, length)

        for _ in range(randrange(0, 3)):
            enem_x = randrange(new_x, new_x + length - last_enemy.rect.width)
            jump_speed = randrange(200, 350)
            last_enemy = Enemy((enem_x, HEIGHT - height - last_enemy.rect.height), jump_speed)

        if randrange(0, 101) < 20:
            bomb_x = randrange(new_x, new_x + length - last_bomb.rect.width)
            last_bomb = Bomb((bomb_x, HEIGHT - height))

    sky_group.draw(screen)
    bg_group.draw(screen)
    middle_group.draw(screen)
    fg_group.draw(screen)

    platforms_group.draw(screen)
    bombs_group.draw(screen)
    player_group.draw(screen)
    enemies_group.draw(screen)

    grass_group.draw(screen)

    camera.apply(sky_group, 0.1)
    camera.apply(bg_group, 0.3)
    camera.apply(middle_group, 0.5)
    camera.apply(fg_group, 0.8)
    camera.apply(grass_group, 1.5)

    camera.apply(platforms_group)
    camera.apply(enemies_group)
    camera.apply(bombs_group)

    all_backs_group.update(time)

    player_group.update(time)
    enemies_group.update(time)
    bombs_group.update(time)
    platforms_group.update(time)

    time = timer.tick() / 1000
    pygame.display.flip()