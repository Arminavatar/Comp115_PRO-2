import os
import random

import pygame


pygame.init()
pygame.mixer.init()

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Display
WIDTH, HEIGHT = 1480, 820
GROUND_Y = 800
FPS = 120

# Fonts
font       = pygame.font.Font(None, 50)
big_font   = pygame.font.Font(None, 120)
title_font = pygame.font.Font(None, 90)

# Physics
GRAVITY       = 0.35
JUMP_STRENGTH = -14

# Player
PLAYER_SPEED        = 2
PLAYER_SCALE        = 3
PLAYER_START_X      = 700
PLAYER_START_Y      = 200
SHOOT_COOLDOWN      = 20
INVINCIBILITY_TICKS = 90   # frames of i-frames after being hit

# Arrows
ARROW_SCALE = 2
ARROW_SPEED = 10

# Targets
TARGET_SCALE      = 3.5
MAX_TARGETS       = 5
MIN_TARGET_GAP    = 110
TARGET_SPACING    = 160

# Difficulty
STARTING_TARGET_SPEED  = 1.2
TARGET_SPEED_STEP      = 0.1
SPAWN_DELAY            = 1200   # ms between spawns (starting value)
MIN_SPAWN_DELAY        = 700
SPAWN_DELAY_STEP       = 40
DIFFICULTY_INTERVAL    = 3000   # ms between difficulty ticks

# Game rules
TIME_LIMIT  = 60   # seconds
MAX_HEALTH  = 5

# Paths
ARCHER_BASE_PATH = "pro2/all_colored_archers"

# Colours
WHITE  = (255, 255, 255)
RED    = (220,  30,  30)
GREEN  = ( 60, 200,  80)
GOLD   = (255, 215, 120)
CREAM  = (255, 230, 170)
DARK   = ( 60,  60,  60)

# Window + clock

screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Archer Training")
clock  = pygame.time.Clock()

# ---------------------------------------------------------------------------
# Assets
# ---------------------------------------------------------------------------

# Images
def _scale(img, factor):
    return pygame.transform.scale(img, (int(img.get_width() * factor),
                                        int(img.get_height() * factor)))

background_img = pygame.image.load("pro2/BG.jpg").convert_alpha()

arrow_img = _scale( pygame.image.load("pro2/Arrow/arrow.png").convert_alpha(), ARROW_SCALE,)

target_idle_img = _scale( pygame.image.load("pro2/TrainingDummy/NoArmor/Idle/0.png").convert_alpha(), TARGET_SCALE,)

target_hit_frames = [ _scale( pygame.image.load(f"pro2/TrainingDummy/NoArmor/Hited/{i}.png").convert_alpha(), TARGET_SCALE, ) for i in range(5)]

# Audio
bow_sound        = pygame.mixer.Sound("pro2/sound/bow.mp3")
hit_sound        = pygame.mixer.Sound("pro2/sound/arrow impact.mp3")
player_hit_sound = pygame.mixer.Sound("pro2/sound/hit.mp3")

pygame.mixer.music.load("pro2/sound/BG music.mp3")
pygame.mixer.music.set_volume(0.4)
pygame.mixer.music.play(-1)


# Helper drawing utilities


def draw_background():
    screen.blit(background_img, (0, 0))


def draw_text_centered(text, text_font, color, y, shadow_color=None, shadow_offset=4):
    if shadow_color:
        shadow = text_font.render(text, True, shadow_color)
        screen.blit(shadow, (WIDTH // 2 - shadow.get_width() // 2 + shadow_offset,
                              y + shadow_offset))
    surface = text_font.render(text, True, color)
    screen.blit(surface, (WIDTH // 2 - surface.get_width() // 2, y))


def draw_health_bar(x, y, current, maximum):
    bar_w, bar_h = 220, 26
    fill_w = int(bar_w * current / maximum) if maximum else 0
    pygame.draw.rect(screen, RED,   (x, y, bar_w,  bar_h))
    pygame.draw.rect(screen, GREEN, (x, y, fill_w, bar_h))
    pygame.draw.rect(screen, WHITE, (x, y, bar_w,  bar_h), 3)


# ---------------------------------------------------------------------------
# Archer (player)
# ---------------------------------------------------------------------------

class Archer(pygame.sprite.Sprite):

    # Build options list once at class level (uses module-level ARCHER_BASE_PATH)
    ARCHER_OPTIONS = [
        (name.capitalize(), name)
        for name in sorted(os.listdir(ARCHER_BASE_PATH), key=str.lower)
        if os.path.isdir(os.path.join(ARCHER_BASE_PATH, name))
    ]

    # Action indices
    ACTION_IDLE    = 0
    ACTION_RUN     = 1
    ACTION_SHOOT   = 2
    ANIMATION_TYPES = ["idle", "run", "shooting"]

    ANIMATION_COOLDOWN = 75   # ms per frame

    # ------------------------------------------------------------------ #

    @classmethod
    def _frame_paths(cls, char_type, animation):
        path = os.path.join(ARCHER_BASE_PATH, char_type, animation)
        files = [f for f in os.listdir(path) if f.lower().endswith(".png")]
        return [
            os.path.join(path, f)
            for f in sorted(files, key=lambda f: int(os.path.splitext(f)[0]))
        ]

    @classmethod
    def load_preview_frames(cls, char_type, scale=4):
        return [
            _scale(pygame.image.load(p).convert_alpha(), scale)
            for p in cls._frame_paths(char_type, "idle")
        ]

    # ------------------------------------------------------------------ #

    def __init__(self, char_type, x, y, scale=PLAYER_SCALE, speed=PLAYER_SPEED):
        super().__init__()
        self.char_type = char_type
        self.speed     = speed

        # Load all animation frames
        self.animation_list = [
            [
                _scale(pygame.image.load(p).convert_alpha(), scale)
                for p in self._frame_paths(char_type, anim)
            ]
            for anim in self.ANIMATION_TYPES
        ]

        # State
        self.action       = self.ACTION_IDLE
        self.frame_index  = 0
        self.update_time  = pygame.time.get_ticks()

        self.direction    = 1       # 1 = right, -1 = left
        self.flip         = False
        self.vel_y        = 0
        self.in_air       = True
        self.jump         = False

        self.shoot_cooldown    = 0
        self.shooting          = False
        self.arrow_fired       = False
        self.invincibility     = 0   # countdown ticks

        # Sprite setup
        self.image         = self.animation_list[self.action][self.frame_index]
        self.display_image = self.image
        self.rect          = self.image.get_rect(center=(x, y))
        self.mask          = pygame.mask.from_surface(self.display_image)

    # ------------------------------------------------------------------ #

    def update(self):
        self._update_animation()
        if self.shoot_cooldown > 0:
            self.shoot_cooldown -= 1
        if self.invincibility > 0:
            self.invincibility -= 1

    def move(self, move_left, move_right):
        dx = dy = 0

        if move_left:
            dx = -self.speed
            self.flip      = True
            self.direction = -1
        if move_right:
            dx = self.speed
            self.flip      = False
            self.direction = 1

        if self.jump and not self.in_air:
            self.vel_y  = JUMP_STRENGTH
            self.jump   = False
            self.in_air = True

        self.vel_y = min(self.vel_y + GRAVITY, 10)
        dy += self.vel_y

        if self.rect.bottom + dy > GROUND_Y:
            dy          = GROUND_Y - self.rect.bottom
            self.in_air = False

        self.rect.x += dx
        self.rect.y += dy

    #cool down between shots
    def fire_arrow(self, arrow_group):
        if self.shoot_cooldown > 0:
            return
        self.update_action(self.ACTION_SHOOT)
        self.shooting      = True
        self.shoot_cooldown = SHOOT_COOLDOWN
        self.arrow_fired   = False

    def update_action(self, new_action):
        if new_action != self.action:
            self.action      = new_action
            self.frame_index = 0
            self.update_time = pygame.time.get_ticks()

    def _update_animation(self):
        self.image = self.animation_list[self.action][self.frame_index]

        if pygame.time.get_ticks() - self.update_time > self.ANIMATION_COOLDOWN:
            self.update_time = pygame.time.get_ticks()
            self.frame_index += 1

        if self.frame_index >= len(self.animation_list[self.action]):
            if self.action == self.ACTION_SHOOT:
                self.shooting = False
            self.frame_index = 0

        # Spawn arrow at the last shooting frame
        if (self.action == self.ACTION_SHOOT
            and self.frame_index == len(self.animation_list[self.ACTION_SHOOT]) - 1
            and not self.arrow_fired):
            offset_x = 0.2 * self.rect.width * self.direction
            arrow = Arrow(self.rect.centerx + offset_x, self.rect.centery + 22, self.direction)
            arrow_group.add(arrow)
            bow_sound.play()
            self.arrow_fired = True

        self.display_image = pygame.transform.flip(self.image, self.flip, False)
        self.mask = pygame.mask.from_surface(self.display_image)

    def draw(self):
        # Flicker when invincible
        if self.invincibility == 0 or (self.invincibility // 6) % 2 == 0:
            screen.blit(self.display_image, self.rect)


# ---------------------------------------------------------------------------
# Arrow
# ---------------------------------------------------------------------------

class Arrow(pygame.sprite.Sprite):
    def __init__(self, x, y, direction):
        super().__init__()
        self.direction = direction
        self.image = (pygame.transform.flip(arrow_img, True, False)
                      if direction == -1 else arrow_img)
        self.rect  = self.image.get_rect(center=(x, y))

    def update(self):
        self.rect.x += self.direction * ARROW_SPEED
        if self.rect.right < 0 or self.rect.left > WIDTH:
            self.kill()


# ---------------------------------------------------------------------------
# Target (training dummy)
# ---------------------------------------------------------------------------

class Target(pygame.sprite.Sprite):

    ANIMATION_COOLDOWN = 80

    def __init__(self, x, y, direction, speed):
        super().__init__()
        self.direction   = direction
        self.speed       = speed
        self.hit         = False
        self.frame_index = 0
        self.update_time = pygame.time.get_ticks()

        self.base_image = pygame.transform.flip(target_idle_img, direction == -1, False)
        self.image      = self.base_image
        self.rect       = self.image.get_rect(midbottom=(x, y))
        self.mask       = pygame.mask.from_surface(self.image)

    def update(self):
        if not self.hit:
            self.rect.x += self.direction * self.speed
            off_right = self.direction ==  1 and self.rect.left  > WIDTH
            off_left  = self.direction == -1 and self.rect.right < 0
            if off_right or off_left:
                self.kill()
        else:
            if pygame.time.get_ticks() - self.update_time > self.ANIMATION_COOLDOWN:
                self.update_time  = pygame.time.get_ticks()
                self.frame_index += 1
                if self.frame_index >= len(target_hit_frames):
                    self.kill()
                else:
                    self.image = target_hit_frames[self.frame_index]
                    self.mask  = pygame.mask.from_surface(self.image)


# ---------------------------------------------------------------------------
# Spawning helpers
# ---------------------------------------------------------------------------

def spawn_target(target_group, speed):
    direction      = random.choice((1, -1))
    spawn_padding  = target_idle_img.get_width()
    spacing        = target_idle_img.get_width() + random.randint(
        MIN_TARGET_GAP, TARGET_SPACING + MIN_TARGET_GAP
    )

    live = [t for t in target_group if t.direction == direction and not t.hit]

    if direction == 1:
        anchor = min((t.rect.centerx for t in live), default=None)
        x = (min(-spawn_padding, anchor - spacing) if anchor is not None
             else -spawn_padding - random.randint(MIN_TARGET_GAP, TARGET_SPACING + MIN_TARGET_GAP))
    else:
        anchor = max((t.rect.centerx for t in live), default=None)
        x = (max(WIDTH + spawn_padding, anchor + spacing) if anchor is not None
             else WIDTH + spawn_padding + random.randint(MIN_TARGET_GAP, TARGET_SPACING + MIN_TARGET_GAP))

    target_group.add(Target(x, GROUND_Y, direction, speed))


def fill_targets(target_group, speed):
    while len(target_group) < MAX_TARGETS:
        spawn_target(target_group, speed)


# ---------------------------------------------------------------------------
# Game state
# ---------------------------------------------------------------------------

class GameState:
    def __init__(self):
        self.score           = 0
        self.health          = MAX_HEALTH
        self.game_over       = False
        self.game_started    = False
        self.game_over_reason = ""
        self.start_time      = None

        self.spawn_delay      = SPAWN_DELAY
        self.target_speed     = STARTING_TARGET_SPEED
        self.next_spawn_time  = 0
        self.difficulty_tick  = 0

        # Input flags
        self.move_left        = False
        self.move_right       = False
        self.shoot_requested  = False

        # Menu
        self.selected_archer  = 0
        self.menu_frame       = 0
        self.menu_frame_time  = pygame.time.get_ticks()

    # ------------------------------------------------------------------ #

    def remaining_time(self):
        if self.start_time is None:
            return TIME_LIMIT
        elapsed = (pygame.time.get_ticks() - self.start_time) // 1000
        return max(0, TIME_LIMIT - elapsed)

    def reset(self, player, arrow_group, target_group):
        self.score            = 0
        self.health           = MAX_HEALTH
        self.game_over        = False
        self.game_over_reason = ""
        self.start_time       = pygame.time.get_ticks()
        self.spawn_delay      = SPAWN_DELAY
        self.target_speed     = STARTING_TARGET_SPEED
        self.difficulty_tick  = self.start_time + DIFFICULTY_INTERVAL
        self.next_spawn_time  = self.start_time + self.spawn_delay

        player.rect.center   = (PLAYER_START_X, PLAYER_START_Y)
        player.vel_y         = 0
        player.jump          = False
        player.in_air        = True
        player.flip          = False
        player.direction     = 1
        player.shoot_cooldown = 0
        player.arrow_fired   = False
        player.invincibility = 0
        player.update_action(Archer.ACTION_IDLE)

        arrow_group.empty()
        target_group.empty()
        fill_targets(target_group, self.target_speed)

    def update_difficulty(self, target_group):
        now = pygame.time.get_ticks()
        if self.game_over or now < self.difficulty_tick:
            return
        self.spawn_delay     = max(MIN_SPAWN_DELAY, self.spawn_delay - SPAWN_DELAY_STEP)
        self.target_speed   += TARGET_SPEED_STEP
        self.difficulty_tick = now + DIFFICULTY_INTERVAL
        self.next_spawn_time = min(self.next_spawn_time, now + self.spawn_delay)
        for t in target_group:
            if not t.hit:
                t.speed = self.target_speed

    def take_hit(self, player, target_group, arrow_group):
 
        if player.invincibility > 0:
            return
        self.health -= 1
        player_hit_sound.play()
        player.invincibility = INVINCIBILITY_TICKS
        if self.health <= 0:
            self.health           = 0
            self.game_over        = True
            self.game_over_reason = "YOU WERE OVERRUN!"
            player.update_action(Archer.ACTION_IDLE)
            target_group.empty()
            arrow_group.empty()


# ---------------------------------------------------------------------------
# Menu drawing
# ---------------------------------------------------------------------------

def draw_menu(state, archer_previews):
    draw_background()

    overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 170))
    screen.blit(overlay, (0, 0))

    label, _ = Archer.ARCHER_OPTIONS[state.selected_archer]
    frames   = archer_previews[label]

    now = pygame.time.get_ticks()
    if now - state.menu_frame_time > 140:
        state.menu_frame      = (state.menu_frame + 1) % len(frames)
        state.menu_frame_time = now

    draw_text_centered("ARCHER TRAINING", title_font, GOLD,  110)
    draw_text_centered("Choose your archer with LEFT / RIGHT",font, WHITE, 210)

    preview = frames[state.menu_frame]
    screen.blit(preview, (WIDTH // 2 - preview.get_width() // 2, 250))

    draw_text_centered(f"<  {label} Archer  >",                             font, CREAM, 500)
    draw_text_centered("Shoot the training dummies before time runs out.",   font, WHITE, 560)
    draw_text_centered("A / D   Move",                                       font, WHITE,620)
    draw_text_centered("W       Jump",                                       font, WHITE, 670)
    draw_text_centered("SPACE   Shoot",                                      font, WHITE, 720)
    draw_text_centered("Press ENTER to start",                               font, WHITE, 770)


# ---------------------------------------------------------------------------
# Pre-load archer preview frames
# ---------------------------------------------------------------------------

archer_previews = { label: Archer.load_preview_frames(char_type) for label, char_type in Archer.ARCHER_OPTIONS}

# ---------------------------------------------------------------------------
# Bootstrap
# ---------------------------------------------------------------------------

gs          = GameState()
arrow_group  = pygame.sprite.Group()
target_group = pygame.sprite.Group()
player       = Archer(Archer.ARCHER_OPTIONS[gs.selected_archer][1],
                      PLAYER_START_X, PLAYER_START_Y)

# ---------------------------------------------------------------------------
# Main loop
# ---------------------------------------------------------------------------

running = True
while running:
    clock.tick(FPS)
    now = pygame.time.get_ticks()

    # ------------------------------------------------------------------ #
    # Events
    # ------------------------------------------------------------------ #
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

        elif event.type == pygame.KEYDOWN:

            if event.key == pygame.K_ESCAPE:
                running = False

            # --- Menu ---
            elif not gs.game_started:
                if event.key == pygame.K_LEFT:
                    gs.selected_archer  = (gs.selected_archer - 1) % len(Archer.ARCHER_OPTIONS)
                    gs.menu_frame       = 0
                    gs.menu_frame_time  = now
                    player = Archer(Archer.ARCHER_OPTIONS[gs.selected_archer][1],
                                    PLAYER_START_X, PLAYER_START_Y)
                elif event.key == pygame.K_RIGHT:
                    gs.selected_archer  = (gs.selected_archer + 1) % len(Archer.ARCHER_OPTIONS)
                    gs.menu_frame       = 0
                    gs.menu_frame_time  = now
                    player = Archer(Archer.ARCHER_OPTIONS[gs.selected_archer][1],
                                    PLAYER_START_X, PLAYER_START_Y)
                elif event.key == pygame.K_RETURN:
                    gs.game_started    = True
                    gs.move_left       = False
                    gs.move_right      = False
                    gs.shoot_requested = False
                    gs.reset(player, arrow_group, target_group)

            # --- Game over ---
            elif gs.game_over:
                if event.key == pygame.K_r:
                    gs.move_left       = False
                    gs.move_right      = False
                    gs.shoot_requested = False
                    gs.reset(player, arrow_group, target_group)

            # --- In-game ---
            else:
                if event.key == pygame.K_a:
                    gs.move_left = True
                elif event.key == pygame.K_d:
                    gs.move_right = True
                elif event.key == pygame.K_w:
                    player.jump = True
                elif event.key == pygame.K_SPACE:
                    gs.shoot_requested = True

        elif event.type == pygame.KEYUP:
            if event.key == pygame.K_a:
                gs.move_left = False
            elif event.key == pygame.K_d:
                gs.move_right = False

    # ------------------------------------------------------------------ #
    # Draw / update
    # ------------------------------------------------------------------ #
    if not gs.game_started:
        draw_menu(gs, archer_previews)

    else:
        draw_background()

        # --- Update ---
        player.update()
        arrow_group.update()
        target_group.update()

        # --- Arrow ↔ target collisions ---
        for arrow in list(arrow_group):
            targets_hit = pygame.sprite.spritecollide(
                arrow, target_group, False, pygame.sprite.collide_mask
            )
            if targets_hit:
                arrow.kill()
                for target in targets_hit:
                    if not target.hit:
                        gs.score += 100
                        hit_sound.play()
                        target.hit         = True
                        target.frame_index = 0

        # --- Player ↔ target collisions ---
        if not gs.game_over:
            for target in pygame.sprite.spritecollide(
                player, target_group, False, pygame.sprite.collide_mask
            ):
                if not target.hit:
                    target.kill()
                    gs.take_hit(player, target_group, arrow_group)
                    if gs.game_over:
                        break

        # --- Difficulty + spawning ---
        gs.update_difficulty(target_group)

        if not gs.game_over and len(target_group) < MAX_TARGETS and now >= gs.next_spawn_time:
            spawn_target(target_group, gs.target_speed)
            gs.next_spawn_time = now + gs.spawn_delay

        # --- Player action ---
        if not gs.game_over:
            if player.action == Archer.ACTION_SHOOT and player.shooting:
                pass   # let shooting animation finish
            elif gs.shoot_requested:
                player.fire_arrow(arrow_group)
                gs.shoot_requested = False
            elif gs.move_left or gs.move_right:
                player.update_action(Archer.ACTION_RUN)
            else:
                player.update_action(Archer.ACTION_IDLE)

        player.move(gs.move_left, gs.move_right)

        # --- Draw sprites ---
        target_group.draw(screen)
        arrow_group.draw(screen)
        player.draw()

        # --- HUD ---
        remaining = gs.remaining_time()
        draw_health_bar(40, 28, gs.health, MAX_HEALTH)
        screen.blit(font.render(f"Score: {gs.score}", True, WHITE),
                    (WIDTH - 250, 20))
        timer_surf = font.render(f"Time: {remaining}", True, WHITE)
        screen.blit(timer_surf, (WIDTH // 2 - timer_surf.get_width() // 2, 20))

        # --- Time-up check ---
        if remaining == 0 and not gs.game_over:
            gs.game_over        = True
            gs.game_over_reason = "TIME'S UP!"
            player.update_action(Archer.ACTION_IDLE)
            target_group.empty()
            arrow_group.empty()

        # --- Game-over overlay ---
        if gs.game_over:
            draw_text_centered(gs.game_over_reason,              big_font, RED,   HEIGHT // 2 - 100, (0, 0, 0))
            draw_text_centered(f"Final score: {gs.score}",       font,     WHITE, HEIGHT // 2 + 20,  (0, 0, 0), 3)
            draw_text_centered("Press R to restart  |  ESC to quit", font, WHITE, HEIGHT // 2 + 70,  (0, 0, 0), 3)

    pygame.display.flip()

pygame.quit()