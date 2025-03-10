import sys
import time
from entities.player import Player
from entities.enemy import Enemy
from map import Map
from search.searchAlgorithms import *

# pygame init
pygame.init()


class App:
    """Game class"""

    def __init__(self):
        """Game initialization"""
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        self.clock = pygame.time.Clock()

        if GAME_SEED is not None:
            np.random.seed(GAME_SEED)

        # time of game starting
        self.play_time = None

        # generated on restart
        self.running = None
        self.won = None
        self.state = None
        self.frame = None
        self.map = None
        self.coins_spawned = None
        self.coins_collected = None
        self.player = None
        self.enemies = None

        self._generate()

        # autopilot search
        self.search_type = "A*"
        self.search_heuristic = "Manhattan"
        self.search_time = 0

        # where LMB was pressed on grid
        self.grid_pos_mouse = pygame.math.Vector2(0, 0)
        # where RMB was pressed on grid
        self.grid_pos_mouse4 = []
        # saves last path to draw it on screen
        self._debug_draw_path = []

    def _generate(self):
        # state
        self.running = True
        self.won = False
        self.state = "start"

        # map
        self.map = Map()

        # % score of player's performance during game
        self.coins_spawned = self.map.coins.sum()
        self.coins_collected = 0

        # spawn player
        self.player = Player(self, START_POS, PLAYER_COLOR, PLAYER_LIVES)

        # spawn enemies
        self.enemies = []
        # spawn enemies-random
        for i in range(ENEMY_RANDOM):
            while True:
                # generate x ,y
                x = np.random.randint(0, self.map.shape[0])
                y = np.random.randint(0, self.map.shape[1])
                if self.map.walls[x][y] == 0 \
                        and (x - self.player.grid_pos[0]) + (y - self.player.grid_pos[1]) > 5:
                    self.enemies.append(Enemy(self, (x, y), MENU_BLUE, "random"))
                    break
        # spawn enemies-chaser
        for i in range(ENEMY_CHASER):
            while True:
                # generate x ,y
                x = np.random.randint(0, self.map.shape[0])
                y = np.random.randint(0, self.map.shape[1])
                if self.map.walls[x][y] == 0 \
                        and (x - self.player.grid_pos[0]) + (y - self.player.grid_pos[1]) > 5:
                    self.enemies.append(Enemy(self, (x, y), RED, "chaser"))
                    break

    def run(self):
        """Main game cycle"""
        while self.running:
            if self.state == "start":
                self.start_events()
                self.start_draw()
            elif self.state == "play":
                self.play_events()
                self.play_update()
                self.play_draw()
            elif self.state == "end":
                self.end_events()
                self.end_draw()
            pygame.display.update()
            if LOCK_FPS:
                self.clock.tick(FPS)
        pygame.quit()
        sys.exit()

    # START MENU FUNCTIONS

    def start_events(self):
        """Managing events during start menu"""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            if event.type == pygame.KEYDOWN and event.key == pygame.K_SPACE:
                self.state = "play"
                self.play_time = time.time()

    def start_draw(self):
        """Drawing the start menu"""
        # fill background
        self.screen.fill(BLACK)

        # menu
        self.draw_text("PACMAN",
                       [WIDTH_BACKGROUND // 2, HEIGHT // 2 - LOGO_TEXT_SIZE],
                       LOGO_TEXT_SIZE, MENU_ORANGE, DEFAULT_FONT, True, True)
        self.draw_text("Dmytro Geleshko",
                       [WIDTH_BACKGROUND // 2, HEIGHT // 2 - SMALL_TEXT_SIZE],
                       SMALL_TEXT_SIZE, MENU_BLUE, DEFAULT_FONT, True, True)
        self.draw_text("IP-91",
                       [WIDTH_BACKGROUND // 2, HEIGHT // 2],
                       SMALL_TEXT_SIZE, MENU_BLUE, DEFAULT_FONT, True, True)
        self.draw_text("PRESS SPACE TO PLAY",
                       [WIDTH_BACKGROUND // 2, HEIGHT // 2 + BIG_TEXT_SIZE * 2],
                       BIG_TEXT_SIZE, MENU_ORANGE, DEFAULT_FONT, True, True)
        self.draw_info()

    # PLAY FUNCTIONS

    def play_events(self):
        """Managing events that happen during the game itself"""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False

            if event.type == pygame.KEYDOWN:
                # movement
                if event.key == pygame.K_LEFT:
                    self.player.input_direction(pygame.math.Vector2(-1, 0))
                if event.key == pygame.K_RIGHT:
                    self.player.input_direction(pygame.math.Vector2(1, 0))
                if event.key == pygame.K_UP:
                    self.player.input_direction(pygame.math.Vector2(0, -1))
                if event.key == pygame.K_DOWN:
                    self.player.input_direction(pygame.math.Vector2(0, 1))
                # remove one life
                if event.key == pygame.K_ESCAPE:
                    self.player.lives -= 1
                if event.key == pygame.K_BACKQUOTE:
                    self.console_command()
                # start search for all coins
                if event.key == pygame.K_q:
                    self.player.autopilot_type = 3
                    self.player.autopilot_has_path = False
                # change search algorithm
                if event.key == pygame.K_s:
                    if self.search_type == "A*":
                        self.search_type = "A*g"
                    elif self.search_type == "A*g":
                        self.search_type = "A*c"
                    elif self.search_type == "A*c":
                        self.search_type = "BFS"
                        self.search_heuristic = "None"
                    elif self.search_type == "BFS":
                        self.search_type = "UNI COST"
                    elif self.search_type == "UNI COST":
                        self.search_type = "DFS"
                    elif self.search_type == "DFS":
                        self.search_type = "DFS+"
                    else:
                        self.search_type = "A*"
                        self.search_heuristic = "Manhattan"
                # change search heuristic
                if event.key == pygame.K_a:
                    if self.search_heuristic == "Manhattan":
                        self.search_heuristic = "Euclidean"
                    elif self.search_heuristic == "Euclidean":
                        self.search_heuristic = "Pow2"
                    elif self.search_heuristic == "Pow2":
                        self.search_heuristic = "Manhattan"

            if event.type == pygame.MOUSEBUTTONDOWN and not self.mouse_on_wall():
                # LMB
                if event.button == 1:
                    self.grid_pos_mouse = self.get_mouse_grid_pos()
                    self.player.autopilot_type = 1
                    self.player.autopilot_has_path = False
                # RMB
                elif event.button == 3:
                    # append next target
                    self.grid_pos_mouse4.append(self.get_mouse_grid_pos())
                    # if has 4 targets
                    if len(self.grid_pos_mouse4) == 4:
                        self.player.autopilot_type = 2
                        self.player.autopilot_has_path = False

    def play_update(self):
        """Updating game state"""
        # if won
        if self.map.coins.sum() == 0:
            self.won = True
            self.state = "end"
            # game stats
            self.end_stats()
        # if lost
        elif self.player.lives == 0:
            self.state = "end"
            # game stats
            self.end_stats()
        # game
        else:
            # update player
            self.player.update()
            # update enemy movement
            for enemy in self.enemies:
                enemy.update()

            self.on_coin()
            self.on_enemy()

    def play_draw(self):
        """Drawing the game"""
        # refresh
        self.screen.fill(BLACK)

        # draw grid
        self.draw_grid()

        # draw walls above grid
        self.draw_walls()

        # draw coins
        self.draw_coins()

        # draw player
        self.player.draw()

        # draw enemies
        for enemy in self.enemies:
            enemy.draw()

        # draw score/search info
        self.draw_info()

        # draw selected targets
        self.draw_selected_rmb_targets()

        if self.player.autopilot_has_path:
            self.draw_player_path()

        if DEBUG:
            # grids
            self.player.draw_grid()
            for enemy in self.enemies:
                enemy.draw_grid()

    # END FUNCTIONS

    def end_events(self):
        """Managing events during end screen"""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_SPACE:
                    self._generate()
                if event.key == pygame.K_ESCAPE:
                    self.running = False

    def end_draw(self):
        """Drawing the end screen"""
        self.screen.fill(BLACK)
        if self.won:
            self.draw_text("YOU WON",
                           [WIDTH_BACKGROUND // 2, HEIGHT // 2 - LOGO_TEXT_SIZE],
                           LOGO_TEXT_SIZE, MENU_ORANGE, DEFAULT_FONT, True, True)
        else:
            self.draw_text("YOU DIED",
                           [WIDTH_BACKGROUND // 2, HEIGHT // 2 - LOGO_TEXT_SIZE],
                           LOGO_TEXT_SIZE, MENU_ORANGE, DEFAULT_FONT, True, True)

        self.draw_text("PRESS ESC TO CLOSE",
                       [WIDTH_BACKGROUND // 2, HEIGHT // 2 + BIG_TEXT_SIZE * 2],
                       BIG_TEXT_SIZE, MENU_ORANGE, DEFAULT_FONT, True, True)
        self.draw_text("PRESS SPACE TO RESTART",
                       [WIDTH_BACKGROUND // 2, HEIGHT // 2 + BIG_TEXT_SIZE * 3],
                       BIG_TEXT_SIZE, MENU_ORANGE, DEFAULT_FONT, True, True)
        self.draw_info()

    def end_stats(self):
        with open("score.txt", "a") as scoreboard:
            scoreboard.write(str(int(self.won)) + ","
                             + str(self.coins_collected * 100 / self.coins_spawned) + ","
                             + str(self.player.lives) + ","
                             + str(time.time() - self.play_time) + "\n")

    # SUPPORT FUNCTIONS

    def console_command(self):
        pygame.draw.rect(self.screen, RED,
                         pygame.Rect(0, 0, WIDTH, HEIGHT), 10)
        pygame.display.update()
        try:
            command = input().split()

            if command[0] == "help":
                print("""
tgm - toggle god mode
tcl - toggle player collision
set speed [target] [value] - multiplies the speed of target
set lives [value] - sets new # of lives
game quit - ends game
game restart - restarts game
game win - win game
game lose - lose game
                """)

            if command[0] == "tgm":
                self.player.god_mode = not self.player.god_mode
                print("God mode:", self.player.god_mode)

            elif command[0] == "tcl":
                self.player.collision = not self.player.collision
                print("Collision:", self.player.collision)

            elif command[0] == "game":
                if command[1] == "quit":
                    self.running = False
                elif command[1] == "restart":
                    self._generate()
                elif command[1] == "win":
                    self.map.coins.fill(0)
                    self.coins_collected = self.coins_spawned
                elif command[1] == "lose":
                    self.player.lives = 0

            elif command[0] == "set":
                if command[1] == "speed":
                    if command[2] == "player":
                        self.player.speed = int(command[3])
                        print("Player speed:", self.player.speed)
                    elif command[2] == "enemies":
                        for enemy in self.enemies:
                            enemy.speed = int(command[3])
                        print("Enemies speed:", self.enemies[0].speed)
                elif command[1] == "lives":
                    self.player.lives = int(command[2])
                    print("Player lives:", self.player.lives)
        except:
            pass

    def can_move(self, pos, direction):
        """Checks whether it is possible to move from given position in given direction"""
        if self.map.walls[int(pos[0] + direction[0])][int(pos[1] + direction[1])] == 1:
            return False
        return True

    def draw_coins(self):
        """Draws coins on game map"""
        for i in range(self.map.shape[0]):
            for j in range(self.map.shape[1]):
                if self.map.coins[i][j] == 1:
                    pygame.draw.circle(self.screen, MENU_ORANGE,
                                       (i * CELL_PIXEL_SIZE + CELL_PIXEL_SIZE // 2,
                                        j * CELL_PIXEL_SIZE + CELL_PIXEL_SIZE // 2),
                                       CELL_PIXEL_SIZE // 5)

    def on_coin(self):
        if self.map.coins[int(self.player.grid_pos[0])][int(self.player.grid_pos[1])] == 1:
            self.map.coins[int(self.player.grid_pos[0])][int(self.player.grid_pos[1])] = 0
            self.coins_collected += 1

    def on_enemy(self):
        for enemy in self.enemies:
            if self.player.collision \
                    and abs(enemy.pix_pos[0] - self.player.pix_pos[0]) <= int(CELL_PIXEL_SIZE * 0.8) \
                    and abs(enemy.pix_pos[1] - self.player.pix_pos[1]) <= int(CELL_PIXEL_SIZE * 0.8):
                if not self.player.god_mode:
                    self.player.lives -= 1
                while True:
                    # generate x ,y
                    x = np.random.randint(0, self.map.shape[0])
                    y = np.random.randint(0, self.map.shape[1])
                    if self.map.walls[x][y] == 0:
                        enemy.respawn(x, y)
                        break

    def draw_text(self, text, pos, size, color, font_name, make_centered_w=False, make_centered_h=False):
        """Helper function to draw text on screen"""
        # define font
        font = pygame.font.SysFont(font_name, size)
        # render font
        on_screen_text = font.render(text, False, color)
        # place at pos
        if make_centered_w:
            pos[0] = pos[0] - on_screen_text.get_size()[0] // 2
        if make_centered_h:
            pos[1] = pos[1] - on_screen_text.get_size()[1] // 2
        self.screen.blit(on_screen_text, pos)

    def draw_grid(self):
        """Helper function for debugging: draws map grid and player position on it"""
        # Grid top-bottom
        for i in range(1, self.map.shape[0]):
            pygame.draw.line(self.screen, GRAY,
                             (i * CELL_PIXEL_SIZE, 0),
                             (i * CELL_PIXEL_SIZE, HEIGHT_BACKGROUND))
        # Grid left-right
        for i in range(1, self.map.shape[1]):
            pygame.draw.line(self.screen, GRAY,
                             (0, i * CELL_PIXEL_SIZE),
                             (WIDTH_BACKGROUND, i * CELL_PIXEL_SIZE))

    def draw_walls(self):
        for i in range(self.map.shape[0]):
            for j in range(self.map.shape[1]):
                if self.map.walls[i][j] == 1:
                    pygame.draw.rect(self.screen, MAP_BLUE,
                                     pygame.Rect(i * CELL_PIXEL_SIZE, j * CELL_PIXEL_SIZE,
                                                 CELL_PIXEL_SIZE, CELL_PIXEL_SIZE))

    def draw_player_path(self):
        """Draws autopilot path as circles on grid whenever it is True"""
        if self.player.autopilot_type != 0:
            color = pygame.Vector3(PLAYER_COLOR[0] // 2,
                                   PLAYER_COLOR[1] // 2,
                                   PLAYER_COLOR[2] // 2)

            color_step = color // (1.5 * len(self._debug_draw_path))
            for pos in self._debug_draw_path:
                pygame.draw.circle(self.screen, color,
                                   (pos[0] * CELL_PIXEL_SIZE + CELL_PIXEL_SIZE // 2,
                                    pos[1] * CELL_PIXEL_SIZE + CELL_PIXEL_SIZE // 2),
                                   CELL_PIXEL_SIZE // 2.2, 2)
                color = color + color_step

    def draw_info(self):
        """Draws the information about game to the right of game map"""
        # screen split
        pygame.draw.line(self.screen, WHITE,
                         (WIDTH_BACKGROUND + 1, 0),
                         (WIDTH_BACKGROUND + 1, HEIGHT_BACKGROUND), 1)

        pygame.draw.line(self.screen, WHITE,
                         (WIDTH_BACKGROUND + 4, 0),
                         (WIDTH_BACKGROUND + 4, HEIGHT_BACKGROUND), 3)
        pygame.draw.line(self.screen, WHITE,
                         (WIDTH_BACKGROUND + 7, 0),
                         (WIDTH_BACKGROUND + 7, HEIGHT_BACKGROUND), 1)

        # high score
        self.draw_text("HIGH SCORE",
                       [(WIDTH - WIDTH_BACKGROUND) // 2 + WIDTH_BACKGROUND, 0],
                       MID_TEXT_SIZE, WHITE, DEFAULT_FONT, True, False)
        self.draw_text(str("¯\_(-_-)_/¯"),
                       [(WIDTH - WIDTH_BACKGROUND) // 2 + WIDTH_BACKGROUND, MID_TEXT_SIZE + 10],
                       SMALL_TEXT_SIZE, YELLOW, DEFAULT_FONT, True, False)

        # cur score
        self.draw_text("CURRENT SCORE",
                       [(WIDTH - WIDTH_BACKGROUND) // 2 + WIDTH_BACKGROUND, MID_TEXT_SIZE * 3],
                       MID_TEXT_SIZE, WHITE, DEFAULT_FONT, True, False)
        self.draw_text("{:.2f}%".format(round(self.coins_collected * 100 / self.coins_spawned, 2)),
                       [(WIDTH - WIDTH_BACKGROUND) // 2 + WIDTH_BACKGROUND, MID_TEXT_SIZE * 4],
                       MID_TEXT_SIZE, YELLOW, DEFAULT_FONT, True, False)

        # lives
        self.draw_text("LIVES",
                       [(WIDTH - WIDTH_BACKGROUND) // 2 + WIDTH_BACKGROUND, MID_TEXT_SIZE * 6],
                       MID_TEXT_SIZE, WHITE, DEFAULT_FONT, True, False)
        self.draw_text(str(self.player.lives),
                       [(WIDTH - WIDTH_BACKGROUND) // 2 + WIDTH_BACKGROUND, MID_TEXT_SIZE * 7],
                       MID_TEXT_SIZE, YELLOW, DEFAULT_FONT, True, False)

        # type of search
        self.draw_text("SEARCH",
                       [(WIDTH - WIDTH_BACKGROUND) // 2 + WIDTH_BACKGROUND, MID_TEXT_SIZE * 9],
                       MID_TEXT_SIZE, WHITE, DEFAULT_FONT, True, False)
        self.draw_text(self.search_type,
                       [(WIDTH - WIDTH_BACKGROUND) // 2 + WIDTH_BACKGROUND, MID_TEXT_SIZE * 10],
                       MID_TEXT_SIZE, YELLOW, DEFAULT_FONT, True, False)

        # heuristic
        self.draw_text("HEURISTIC",
                       [(WIDTH - WIDTH_BACKGROUND) // 2 + WIDTH_BACKGROUND, MID_TEXT_SIZE * 12],
                       MID_TEXT_SIZE, WHITE, DEFAULT_FONT, True, False)
        self.draw_text(self.search_heuristic,
                       [(WIDTH - WIDTH_BACKGROUND) // 2 + WIDTH_BACKGROUND, MID_TEXT_SIZE * 13],
                       MID_TEXT_SIZE, RED, DEFAULT_FONT, True, False)

        # time of search
        self.draw_text("SEARCH TIME",
                       [(WIDTH - WIDTH_BACKGROUND) // 2 + WIDTH_BACKGROUND, MID_TEXT_SIZE * 15],
                       MID_TEXT_SIZE, WHITE, DEFAULT_FONT, True, False)
        self.draw_text("{:.3f}ms".format(round(self.search_time * 1000, 3)),
                       [(WIDTH - WIDTH_BACKGROUND) // 2 + WIDTH_BACKGROUND, MID_TEXT_SIZE * 16],
                       MID_TEXT_SIZE, RED, DEFAULT_FONT, True, False)

    def mouse_on_wall(self):
        x, y = pygame.mouse.get_pos()
        x = x // CELL_PIXEL_SIZE
        y = y // CELL_PIXEL_SIZE
        if self.map.walls[x][y] == 1:
            return True
        return False

    def get_mouse_grid_pos(self):
        """Finds mouse pos after mouse click for autopilot engagement"""
        x, y = pygame.mouse.get_pos()
        x = x // CELL_PIXEL_SIZE
        y = y // CELL_PIXEL_SIZE
        return pygame.math.Vector2(x, y)

    def draw_selected_rmb_targets(self):
        for pos in self.grid_pos_mouse4:
            pygame.draw.rect(self.screen, RED,
                             pygame.Rect(pos[0] * CELL_PIXEL_SIZE,
                                         pos[1] * CELL_PIXEL_SIZE,
                                         CELL_PIXEL_SIZE, CELL_PIXEL_SIZE), 2)

    # SEARCH
    def path_stats(self, path):
        print("Cost:", len(path))
        print("Path:", path)
        # drawing path in-game
        self._debug_draw_path = []
        pos = pygame.math.Vector2(self.player.grid_pos)
        for dir_ in path:
            pos = pos + dir_
            self._debug_draw_path.append(pos)

    def search(self, start, end):
        """Search function that calls the selected algorithm"""
        time_start = time.time()

        path = []

        if self.search_type == "A*":
            path = A_star(self, start, end, self.search_heuristic)
        elif self.search_type == "A*g":
            path = A_star(self, start, end, self.search_heuristic, _greedy=True)
        elif self.search_type == "A*c":
            path = A_star(self, start, end, self.search_heuristic, _count_coin=True)
        elif self.search_type == "BFS":
            path = bfs(self, start, end)
        elif self.search_type == "UNI COST":
            path = uni_cost(self, start, end)
        elif self.search_type == "DFS":
            path = dfs(self, start, end)
        elif self.search_type == "DFS+":
            path = dfs_full(self, start, end)

        time_end = time.time()
        self.search_time = time_end - time_start

        if DEBUG:
            self.path_stats(path)
        return path

    def search4(self, start):
        time_sum = 0
        total_path = []
        best_next_path = []
        best_next_index = 0
        while len(self.grid_pos_mouse4) > 0:
            for i in range(len(self.grid_pos_mouse4)):
                this_path = self.search(start, self.grid_pos_mouse4[i])
                time_sum += self.search_time
                if i == 0 or len(this_path) < len(best_next_path):
                    best_next_path = this_path
                    best_next_index = i
            total_path = total_path + best_next_path
            start = self.grid_pos_mouse4.pop(best_next_index)

        if DEBUG:
            self.path_stats(total_path)
        self.search_time = time_sum
        return total_path

    def search_all(self, start):
        time_sum = 0
        total_path = []
        targets = []
        # find pos where coin is not collected
        for i in range(self.map.coins.shape[0]):
            for j in range(self.map.coins.shape[1]):
                if self.map.coins[i, j] == 1:
                    targets.append(pygame.math.Vector2(i, j))
        while True:
            targets.sort(key=lambda pos: heuristic.manhattan(pos, start))

            next = targets.pop(0)

            path = self.search(start, next)
            total_path = total_path + path
            time_sum += self.search_time

            visited = start
            for i in range(len(path)):
                visited = visited + path[i]
                if visited in targets:
                    targets.remove(visited)

            if len(targets) == 0:
                break
            else:
                start = next

        if DEBUG:
            self.path_stats(total_path)
        self.search_time = time_sum
        return total_path
