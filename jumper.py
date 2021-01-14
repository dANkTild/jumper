import pygame
import pygame_gui
import sys
import os
import csv, json
from random import randrange, getrandbits, uniform

WIDTH, HEIGHT = 1000, 500
GRAVITY = 300

MENU_MUSIC_VOLUME = 0.2
GAME_MUSIC_VOLUME = 0.25
PAUSE_MUSIC_VOLUME = 0.2
PLAYER_LANDING_VOLUME = 0.8
PLAYER_PUSH_VOLUME = 0.4
PLAYER_DIE_VOLUME = 1
ENEMY_LANDING_VOLUME = 0.5
ENEMY_DIE_VOLUME = 0.6
BOOM_VOLUME = 0.4

GOD_MODE = 0
SHOW_FPS_IN_GAME = 1


def load_image(name, size=None, colorkey=None):
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
    if size:
        prev_w, prev_h = image.get_size()
        if abs(size[0] / prev_w) > abs(size[1] / prev_h):
            image = pygame.transform.smoothscale(image, (size[0], prev_h * size[0] // prev_w))
        else:
            image = pygame.transform.smoothscale(image,
                                                 (prev_w * size[1] // prev_h,
                                                  size[1]))
    return image


def load_sound(name):
    fullname = os.path.join('data', name)
    if not os.path.isfile(fullname):
        print(f"Файл звука '{fullname}' не найден")
        sys.exit()
    return pygame.mixer.Sound(fullname)


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

    def move_from(self, x):
        if self.target.pos[0] > self.limit:
            self.x = -self.target.pos[0] + self.limit + x
        else:
            self.x = x


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
        self.camera_delta = game.camera.x

    def update(self, time):
        if self.rect.right < -game.width:
            self.destruct()
        if self.rect.top > game.height:
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

    def on_map(self):
        return 0 < self.rect.right < game.width + self.rect.width

    def destruct(self):
        super().kill()


class Text(Sprite):
    def __init__(self, text, pos, size, color, font=None,
                 bg_color=(0, 0, 0, 0), padding=5, align_left=True):
        super().__init__(pos, game.texts_group, game.all_sprites)
        self.pos = pos
        self.color = color
        self.bg_color = bg_color
        self.padding = padding
        self.align_left = align_left
        self.font = pygame.font.Font(font, size)
        self.set(text)

    def set(self, text):
        if text:
            text_surf = self.font.render(str(text), 1, self.color)
            w, h = text_surf.get_size()
            background = pygame.Surface((w + self.padding * 2,
                                         h + self.padding * 2),
                                        pygame.SRCALPHA)
            background.fill(self.bg_color)
            background.blit(text_surf, (self.padding, self.padding))
            self.image = background
            self.rect = self.image.get_rect()
            if self.align_left:
                self.rect.topleft = self.pos
            else:
                self.rect.topright = self.pos


class Background(Sprite):
    def __init__(self, image, x, group):
        super().__init__((x, 0), group, game.all_backs_group, game.all_sprites)
        self.image = image
        self.rect = self.image.get_rect()
        self.rect.bottomleft = x, game.height


class Player(Sprite):
    def __init__(self, pos, jump_speed):
        super().__init__(pos, game.player_group, game.all_sprites)
        self.cut_sheet(player_jump_sheet, "jump", 6, 1)
        self.cut_sheet(player_landing_sheet, "landing", 6, 1)
        self.cut_sheet(player_die_sheet, "die", 15, 1)
        self.image = self.frames["jump"][0]
        self.rect = self.image.get_rect()
        self.rect.bottomleft = pos
        self.pos = list(pos)
        self.move_pos = list(pos)

        self.push_sound = push_sound
        self.landing_sound = landing_sound
        self.die_sound = player_die_sound

        self.level = 0
        self.last_level = None

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
            if self.on_map():
                self.push_sound.play()
            self.push_phase = 0
            self.in_pushing = True
            self.move_pos[0] = self.pos[0]
        platform = pygame.sprite.spritecollideany(self, game.platforms_group)
        enemy = pygame.sprite.spritecollideany(self, game.enemies_group)
        if self.in_pushing and not platform:
            self.pos[0] = (self.move_pos[0] + self.push_speed * self.push_phase
                           + (self.push_acc * self.push_phase ** 2) / 2)
            if self.pos[0] - self.move_pos[0] >= self.push_dist - 1:
                self.in_pushing = False

        if platform and pygame.sprite.collide_mask(self, platform):
            if (self.pos[1] - platform.rect.top <= 10 or
                    platform.rect.left < self.rect.left <
                    platform.rect.right - self.rect.width):
                self.is_jump = False
                self.jump_phase = 0
                self.move_pos[1] = platform.rect.topleft[1]
                if not self.is_playing() and self.prev_name != "landing":
                    if self.on_map():
                        self.start_anim("landing", 0.01)
                    self.landing_sound.play()
                    self.is_jump = True
            elif self.rect.right > platform.rect.right:
                self.pos[0] += 2
            elif self.rect.left < platform.rect.left:
                self.pos[0] -= 2
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

        game.camera.set_position(self.pos)

        for platform in game.platforms_group.sprites():
            proj = platform.rect.copy()
            proj.y = 0
            proj.height = game.height
            if self.rect.colliderect(proj) and hash(platform) != self.last_level:
                self.level += 1
                self.last_level = hash(platform)

        if self.death:
            if self.anim_name != "die" and self.prev_name != "die":
                self.start_anim("die", 0.05)
                self.die_sound.play()
                self.jump_phase = 0
                self.jump_speed = 0
                self.move_pos[1] = self.pos[1]
            if self.prev_name == "die":
                super().kill()

    def kill(self):
        self.death = True if not GOD_MODE else False


class Enemy(Sprite):
    def __init__(self, pos, jump_speed):
        super().__init__(pos, game.enemies_group, game.all_sprites, randflip=True)
        self.cut_sheet(enemy_jump_sheet, "jump", 13, 1)
        self.cut_sheet(enemy_landing_sheet, "landing", 5, 1)
        self.cut_sheet(enemy_die_sheet, "die", 15, 1)
        self.image = self.frames["jump"][0]
        self.rect = self.image.get_rect()
        self.rect.bottomleft = pos
        self.pos = list(pos)
        self.move_pos = list(pos)

        self.landing_sound = landing_sound
        self.die_sound = enemy_die_sound

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

        platform = pygame.sprite.spritecollideany(self, game.platforms_group)
        if platform and pygame.sprite.collide_mask(self, platform):
            if (self.pos[1] - platform.rect.top <= 10 or
                    platform.rect.left < self.rect.left <
                    platform.rect.right - self.rect.width):
                self.is_jump = False
                self.jump_phase = 0
                self.move_pos[1] = platform.rect.topleft[1]
                if not self.is_playing() and self.prev_name != "landing":
                    self.start_anim("landing", 0.01)
                    if self.on_map():
                        self.landing_sound.play()
                    self.is_jump = True

        if self.is_jump:
            if not self.is_playing() and self.prev_name != "jump":
                self.start_anim("jump", 0.1)

            self.pos[1] = (self.move_pos[1] - self.jump_speed * self.jump_phase +
                           (GRAVITY * self.jump_phase ** 2) / 2)

        player = pygame.sprite.spritecollideany(self, game.player_group)
        if not self.death and player and sum([bool(
                self.rect.collidepoint(x, y))
            for x, y in (player.rect.topleft,
                         player.rect.midtop,
                         player.rect.topright)]) == 2:
            player.kill()

        if not self.death:
            enemy = pygame.sprite.spritecollideany(self, game.enemies_group)
            if player and (player.rect.x < self.rect.left or
                           player.rect.x > self.rect.left):
                delta = self.rect.x - player.rect.x
                self.pos[0] += delta / 4
            if enemy and enemy != self and enemy.rect.x < self.rect.left:
                self.pos[0] += 3

        self.start_pos[0] = self.pos[0]
        self.rect.bottom = self.pos[1]

        if self.death:
            if self.anim_name != "die" and self.prev_name != "die":
                self.start_anim("die", 0.05)
                if self.on_map():
                    self.die_sound.play()
                self.jump_phase = 0
                self.jump_speed = 0
                self.move_pos[1] = self.pos[1]
            if self.prev_name == "die":
                super().kill()

    def kill(self):
        self.death = True


class Bomb(Sprite):
    def __init__(self, pos):
        super().__init__(pos, game.bombs_group, game.all_sprites)
        self.cut_sheet(fire_sheet, "fire", 7, 1)
        self.cut_sheet(boom_sheet, "boom", 6, 1)
        self.image = self.frames["fire"][0]
        self.rect = self.image.get_rect()
        self.rect.bottom = pos[1]
        self.radius = 200

        self.boom_sound = boom_sound

        self.player = None

    def update(self, time):
        super().update(time)
        player_collision = pygame.sprite.collide_mask(self, game.player)
        if player_collision and not self.is_playing() and self.prev_name != "fire":
            self.start_anim("fire", 0.3)
        if not self.is_playing() and self.prev_name == "fire":
            for entity in (game.enemies_group.sprites() +
                           game.player_group.sprites()):
                if pygame.sprite.collide_circle(self, entity):
                    entity.kill()
            self.start_anim("boom", 0.15)
            self.boom_sound.play()
        if self.prev_name == "boom":
            self.kill()


class Platform(Sprite):
    def __init__(self, x, height, length):
        super().__init__((x, game.height - height), game.platforms_group, game.all_sprites)
        self.image = pygame.Surface((length, height))
        pygame.draw.rect(self.image, "#7A2029", (0, 0, length, height))
        self.rect = self.image.get_rect()
        self.rect.bottomleft = (x, game.height)


class Form:
    def __init__(self, screen):
        self.screen = screen
        self.width, self.height = self.screen.get_size()
        self.is_visible = False


class Start(Form):
    def __init__(self, screen):
        super().__init__(screen)
        self.is_visible = True

        self.manager = pygame_gui.UIManager((self.width, self.height))

        self.background = menu_bg_image
        buttons_rect = pygame.Rect((0, 0), (300, 50))
        buttons_rect.center = self.width // 2, self.height // 2 - buttons_rect.height - 5
        self.logo_text = pygame_gui.elements.UILabel(relative_rect=buttons_rect,
                                                     text='Jumper',
                                                     manager=self.manager)
        buttons_rect.centery += buttons_rect.height + 5
        self.play_button = pygame_gui.elements.UIButton(relative_rect=buttons_rect,
                                                        text='Play',
                                                        manager=self.manager)
        buttons_rect.centery += buttons_rect.height + 5
        self.records_button = pygame_gui.elements.UIButton(relative_rect=buttons_rect,
                                                           text='Records',
                                                           manager=self.manager)
        buttons_rect.centery += buttons_rect.height + 5
        buttons_rect.width //= 2
        buttons_rect.width -= 2.5
        self.settings_button = pygame_gui.elements.UIButton(relative_rect=buttons_rect,
                                                            text='Settings',
                                                            manager=self.manager)
        buttons_rect.centerx += buttons_rect.width + 5
        self.exit_button = pygame_gui.elements.UIButton(relative_rect=buttons_rect,
                                                        text='Exit',
                                                        manager=self.manager)

        self.music = menu_music
        self.channel = None

    def main(self, events, timer):
        time_delta = timer.tick() / 1000.0
        if not self.channel:
            self.channel = self.music.play(-1)
        for event in events:
            if (event.type == pygame.USEREVENT and
                    event.user_type == pygame_gui.UI_BUTTON_PRESSED):
                if event.ui_element == self.exit_button:
                    sys.exit()
                if event.ui_element == self.play_button:
                    self.channel = self.music.stop()
                    game.restart_game()
                    self.is_visible = False
                    game.is_visible = True
                if event.ui_element == self.settings_button:
                    self.is_visible = False
                    settings_form.prev_form = self
                    settings_form.is_visible = True

            self.manager.process_events(event)

        self.manager.update(time_delta)

        self.screen.blit(self.background, (0, 0))
        self.manager.draw_ui(self.screen)

        pygame.display.update()


class Settings(Form):
    def __init__(self, screen):
        super().__init__(screen)

        self.prev_form = None
        self.load_settings()

        self.manager = pygame_gui.UIManager((self.width, self.height))

        self.background = menu_bg_image
        rect = pygame.Rect((0, 0), (300, 30))

        rect.center = self.width // 2, self.height // 2 - (rect.height - 5) * 5
        pygame_gui.elements.UILabel(relative_rect=rect,
                                    text='Master Volume',
                                    manager=self.manager)
        rect.centery += rect.height + 5
        self.master_volume = pygame_gui.elements.UIHorizontalSlider(relative_rect=rect,
                                                                    start_value=self.settings["master_vol"],
                                                                    value_range=(0.0, 1.0),
                                                                    manager=self.manager)
        rect.centery += (rect.height + 5) * 2
        pygame_gui.elements.UILabel(relative_rect=rect,
                                    text='Music Volume',
                                    manager=self.manager)
        rect.centery += rect.height + 5
        self.music_volume = pygame_gui.elements.UIHorizontalSlider(relative_rect=rect,
                                                                   start_value=self.settings["music_vol"],
                                                                   value_range=(0.0, 1.0),
                                                                   manager=self.manager)
        rect.centery += rect.height + 5
        pygame_gui.elements.UILabel(relative_rect=rect,
                                    text='Effects Volume',
                                    manager=self.manager)
        rect.centery += rect.height + 5
        self.effects_volume = pygame_gui.elements.UIHorizontalSlider(relative_rect=rect,
                                                                     start_value=self.settings["effects_vol"],
                                                                     value_range=(0.0, 1.0),
                                                                     manager=self.manager)
        rect.centery += rect.height + 5
        rect.width //= 2
        rect.centerx += rect.width + 2.5
        self.exit_button = pygame_gui.elements.UIButton(relative_rect=rect,
                                                        text='ok',
                                                        manager=self.manager)

    def load_settings(self):
        self.settings = json.loads(open("settings.json").read())
        self.set_volumes()

    def update_settings(self):
        open("settings.json", "w").write(json.dumps(self.settings))

    def set_volumes(self):
        start_form.music.set_volume(MENU_MUSIC_VOLUME *
                                    self.settings["master_vol"] *
                                    self.settings["music_vol"])
        game.music.set_volume(GAME_MUSIC_VOLUME *
                              self.settings["master_vol"] *
                              self.settings["music_vol"])
        pause.music.set_volume(PAUSE_MUSIC_VOLUME *
                               self.settings["master_vol"] *
                               self.settings["music_vol"])

        player = game.player
        if player:
            player.push_sound.set_volume(PLAYER_PUSH_VOLUME *
                                         self.settings["master_vol"] *
                                         self.settings["effects_vol"])
            player.landing_sound.set_volume(PLAYER_LANDING_VOLUME *
                                            self.settings["master_vol"] *
                                            self.settings["effects_vol"])
            player.die_sound.set_volume(PLAYER_DIE_VOLUME *
                                        self.settings["master_vol"] *
                                        self.settings["effects_vol"])
        for enemy in game.enemies_group.sprites():
            enemy.landing_sound.set_volume(ENEMY_LANDING_VOLUME *
                                           self.settings["master_vol"] *
                                           self.settings["effects_vol"])
            enemy.die_sound.set_volume(ENEMY_DIE_VOLUME *
                                       self.settings["master_vol"] *
                                       self.settings["effects_vol"])
        for bomb in game.bombs_group.sprites():
            bomb.boom_sound.set_volume(BOOM_VOLUME *
                                       self.settings["master_vol"] *
                                       self.settings["effects_vol"])

    def main(self, events, timer):
        time_delta = timer.tick() / 1000.0

        for event in events:
            if event.type == pygame.USEREVENT:
                if event.user_type == pygame_gui.UI_BUTTON_PRESSED:
                    if event.ui_element == self.exit_button:
                        self.update_settings()
                        self.is_visible = False
                        self.prev_form.is_visible = True
                if event.user_type == pygame_gui.UI_HORIZONTAL_SLIDER_MOVED:
                    self.settings["master_vol"] = self.master_volume.get_current_value()
                    self.settings["music_vol"] = self.music_volume.get_current_value()
                    self.settings["effects_vol"] = self.effects_volume.get_current_value()
                    self.set_volumes()

            self.manager.process_events(event)

        self.manager.update(time_delta)

        self.screen.blit(self.background, (0, 0))
        self.manager.draw_ui(self.screen)

        pygame.display.update()


class Game(Form):
    def __init__(self, screen):
        super().__init__(screen)

        self.all_sprites = pygame.sprite.Group()

        self.all_backs_group = pygame.sprite.Group()
        self.sky_group = pygame.sprite.Group()
        self.bg_group = pygame.sprite.Group()
        self.middle_group = pygame.sprite.Group()
        self.fg_group = pygame.sprite.Group()
        self.grass_group = pygame.sprite.Group()

        self.texts_group = pygame.sprite.Group()
        self.player_group = pygame.sprite.Group()
        self.enemies_group = pygame.sprite.Group()
        self.bombs_group = pygame.sprite.Group()
        self.platforms_group = pygame.sprite.Group()

        self.player = None

        self.music = game_music
        self.music.set_volume(GAME_MUSIC_VOLUME)

    def restart_game(self):
        for sprite in self.all_sprites.sprites():
            sprite.destruct()

        self.camera = Camera()

        self.last_sky = Background(sky_image, 0, self.sky_group)
        self.last_bg = Background(bg_image, 0, self.bg_group)
        self.last_middle = Background(middle_image, 0, self.middle_group)
        self.last_fg = Background(fg_image, 0, self.fg_group)
        self.last_grass = Background(grass_image, 0, self.grass_group)

        self.last_platform = Platform(30, 100, 500)
        self.last_enemy = Enemy((-100, 400), 0)
        self.last_bomb = Bomb((-150, 400))
        self.player = Player((50, 300), 300)

        self.camera.set_target(self.player, 600)

        self.time_text = Text("0", (0, 0), 50, "green", bg_color=(0, 0, 0, 190))
        self.level_text = Text("0", (self.width, 0), 50, "red", bg_color=(0, 0, 0, 190), align_left=False)
        self.fps_text = Text("0", (self.width, 480), 20, "white", bg_color=(0, 0, 0, 255), align_left=False,
                             padding=1)
        if not SHOW_FPS_IN_GAME:
            self.fps_text.kill()
        self.game_over = False
        self.on_pause = False
        self.end_phase = 0
        self.round_time = 0

        self.music.stop()
        self.channel = self.music.play(-1)

    def main(self, events, timer):
        time = timer.tick() / 1000.0
        for event in events:
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_SPACE:
                    if not self.game_over:
                        self.player_group.update(time, True)
                    else:
                        self.restart_game()
                if event.key == pygame.K_ESCAPE:
                    if not self.player.death:
                        self.on_pause = not self.on_pause
                        pause.is_visible = self.on_pause
                        if not self.on_pause:
                            pause.channel = pause.music.stop()

        self.sky_group.draw(self.screen)
        self.bg_group.draw(self.screen)
        self.middle_group.draw(self.screen)
        self.fg_group.draw(self.screen)

        self.platforms_group.draw(self.screen)
        self.bombs_group.draw(self.screen)
        self.player_group.draw(self.screen)
        self.enemies_group.draw(self.screen)

        self.grass_group.draw(self.screen)

        if self.player not in self.player_group:
            self.end_phase += time
            if self.end_phase > uniform(0.1, 3.0):
                self.end_phase = 0
                self.camera.move_from(randrange(-20, 20))
            if not self.game_over:
                self.game_over = True
                go_text = Text("GAME OVER", (0, 200), 100, "white",
                               bg_color=(0, 0, 0, 220), padding=20)
                Text("Press space to restart", (0, go_text.rect.bottom + 5),
                     50, "white", bg_color=(0, 0, 0, 220), padding=10)

            self.screen.blit(end_image, (0, 0))

        self.texts_group.draw(self.screen)

        if self.on_pause:
            self.channel.pause()
            return False

        self.channel.unpause()

        self.round_time += time if not self.player.death else 0

        if self.last_sky.rect.right < 2 * self.width:
            self.last_sky = Background(sky_image, self.last_sky.rect.right - 5, self.sky_group)
        if self.last_bg.rect.right < 2 * self.width:
            self.last_bg = Background(bg_image, self.last_bg.rect.right - 5, self.bg_group)
        if self.last_middle.rect.right < 2 * self.width:
            self.last_middle = Background(middle_image, self.last_middle.rect.right - 5, self.middle_group)
        if self.last_fg.rect.right < 2 * self.width:
            self.last_fg = Background(fg_image, self.last_fg.rect.right - 5, self.fg_group)
        if self.last_grass.rect.right < 2 * self.width:
            self.last_grass = Background(grass_image, self.last_grass.rect.right - 5, self.grass_group)

        if self.last_platform.rect.right < 2 * self.width:
            new_x = self.last_platform.rect.right + randrange(150, 300)
            height = randrange(45, 110)
            length = randrange(150, 500)

            self.last_platform = Platform(new_x, height, length)

            for _ in range(randrange(0, 3)):
                enem_x = randrange(new_x, new_x + length - self.last_enemy.rect.width)
                jump_speed = randrange(200, 350)
                self.last_enemy = Enemy((enem_x, self.height - height - self.last_enemy.rect.height), jump_speed)

            if randrange(0, 101) < 20:
                bomb_x = randrange(new_x, new_x + length - self.last_bomb.rect.width)
                self.last_bomb = Bomb((bomb_x, self.height - height))

        self.camera.apply(self.sky_group, 0.1)
        self.camera.apply(self.bg_group, 0.3)
        self.camera.apply(self.middle_group, 0.5)
        self.camera.apply(self.fg_group, 0.8)
        self.camera.apply(self.grass_group, 1.5)

        self.camera.apply(self.platforms_group)
        self.camera.apply(self.enemies_group)
        self.camera.apply(self.bombs_group)

        self.all_backs_group.update(time)

        self.player_group.update(time)
        self.enemies_group.update(time)
        self.bombs_group.update(time)
        self.platforms_group.update(time)

        self.level_text.set(self.player.level)
        self.time_text.set(int(self.round_time))
        self.fps_text.set("{:0.0f}".format(timer.get_fps()))

        pygame.display.flip()


class Pause(Form):
    def __init__(self, screen):
        super().__init__(screen)

        self.manager = pygame_gui.UIManager((self.width, self.height))

        self.background = pygame.Surface((self.width, self.height),
                                         pygame.SRCALPHA)
        self.background.fill((0, 0, 0, 150))
        buttons_rect = pygame.Rect((0, 0), (300, 50))
        buttons_rect.center = (self.width // 2,
                               self.height // 2 - buttons_rect.height - 5)
        self.paused_text = pygame_gui.elements.UILabel(relative_rect=buttons_rect,
                                                       text='Paused',
                                                       manager=self.manager)
        buttons_rect.centery += buttons_rect.height + 5
        self.resume_button = pygame_gui.elements.UIButton(relative_rect=buttons_rect,
                                                          text='Resume',
                                                          manager=self.manager)
        buttons_rect.centery += buttons_rect.height + 5
        buttons_rect.width //= 2
        buttons_rect.width -= 2.5
        self.settings_button = pygame_gui.elements.UIButton(relative_rect=buttons_rect,
                                                            text='Setting',
                                                            manager=self.manager)
        buttons_rect.centerx += buttons_rect.width + 5
        self.exit_button = pygame_gui.elements.UIButton(relative_rect=buttons_rect,
                                                        text='Exit',
                                                        manager=self.manager)

        self.music = pause_music
        self.channel = None

    def main(self, events, timer):
        time_delta = timer.tick() / 1000.0

        if not self.channel:
            self.channel = self.music.play(-1)
        for event in events:
            if (event.type == pygame.USEREVENT and
                    event.user_type == pygame_gui.UI_BUTTON_PRESSED):
                if event.ui_element == self.exit_button:
                    self.is_visible = False
                    game.is_visible = False
                    start_form.is_visible = True
                    self.channel = self.music.stop()
                if event.ui_element == self.resume_button:
                    self.channel = self.music.stop()
                    self.is_visible = False
                    game.on_pause = False
                if event.ui_element == self.settings_button:
                    self.is_visible = False
                    settings_form.prev_form = self
                    settings_form.is_visible = True

            self.manager.process_events(event)

        self.manager.update(time_delta)

        self.screen.blit(self.background, (0, 0))
        self.manager.draw_ui(self.screen)

        pygame.display.update()


pygame.init()
pygame.mixer.init()
screen = pygame.display.set_mode((WIDTH, HEIGHT))
timer = pygame.time.Clock()

menu_bg_image = load_image("menu_bg.jpg", (WIDTH, HEIGHT))

sky_image = load_image("sky.png", (WIDTH, HEIGHT))
bg_image = load_image("bg.png", (WIDTH, HEIGHT))
middle_image = load_image("middle.png", (WIDTH, HEIGHT))
fg_image = load_image("fg.png", (WIDTH, HEIGHT))
grass_image = load_image("grass.png")
end_image = load_image("glitch.png", (WIDTH, HEIGHT))

player_jump_sheet = load_image("player_jump.png")
player_landing_sheet = load_image("player_landing.png")
player_die_sheet = load_image("player_die.png")
enemy_jump_sheet = load_image("enemy_jump.png")
enemy_landing_sheet = load_image("enemy_landing.png")
enemy_die_sheet = load_image("enemy_die.png")
fire_sheet = load_image("fire.png")
boom_sheet = load_image("boom.png")

menu_music = load_sound("menu.mp3")
game_music = load_sound("game.mp3")
pause_music = load_sound("pause.mp3")
landing_sound = load_sound("landing.wav")
push_sound = load_sound("push.wav")
boom_sound = load_sound("boom.wav")
player_die_sound = load_sound("player_die.ogg")
enemy_die_sound = load_sound("enemy_die.wav")

if __name__ == '__main__':
    start_form = Start(screen)
    game = Game(screen)
    pause = Pause(screen)
    settings_form = Settings(screen)

    running = True
    while running:
        events = pygame.event.get()
        for event in events:
            if event.type == pygame.QUIT:
                running = False

        if settings_form.is_visible:
            settings_form.main(events, timer)
        if start_form.is_visible:
            start_form.main(events, timer)
        if game.is_visible:
            game.main(events, timer)
        if pause.is_visible:
            pause.main(events, timer)
