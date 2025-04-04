import discord
from discord.ext import commands
import random
import asyncio

# Game constants
WIDTH = 15
HEIGHT = 10
PACMAN = '😃'
GHOST = '👻'
WALL = '🟦'
PELLET = '⚪'
EMPTY = '⬛'

# Movement reactions
MOVEMENTS = {
    '⬆️': (0, -1),
    '⬇️': (0, 1),
    '⬅️': (-1, 0),
    '➡️': (1, 0)
}

# Additional reactions
RESTART = '🔄'
CANCEL = '🚫'

class GameState:
    def __init__(self):
        self.board = None
        self.player_position = None
        self.ghost_position = None
        self.score = 0
        self.message = None
        self.is_active = True
        self.level = 1
        self.pellets_collected = 0
        self.total_pellets = 0
        self.ghost_move_counter = 0
        self.ghost_original_cell = EMPTY

    def create_board(self):
        self.board = [[EMPTY for _ in range(WIDTH)] for _ in range(HEIGHT)]

        # Add outer walls
        for i in range(WIDTH):
            self.board[0][i] = WALL
            self.board[HEIGHT - 1][i] = WALL
        for i in range(HEIGHT):
            self.board[i][0] = WALL
            self.board[i][WIDTH - 1] = WALL

        # Add inner walls for levels 2 and above
        if self.level >= 2:
            self.add_inner_walls()

        # Calculate the number of pellets for this level
        self.total_pellets = 10 + (self.level - 1) * 5

        # Add pellets
        pellets_added = 0
        while pellets_added < self.total_pellets:
            x, y = random.randint(1, WIDTH - 2), random.randint(1, HEIGHT - 2)
            if self.board[y][x] == EMPTY:
                self.board[y][x] = PELLET
                pellets_added += 1

    def add_inner_walls(self):
        num_walls = min(self.level, 5)  # Cap at 5 additional walls
        for _ in range(num_walls):
            wall_length = random.randint(2, 4)
            start_x = random.randint(2, WIDTH - 3)
            start_y = random.randint(2, HEIGHT - 3)
            direction = random.choice(['horizontal', 'vertical'])

            for i in range(wall_length):
                if direction == 'horizontal' and start_x + i < WIDTH - 1:
                    self.board[start_y][start_x + i] = WALL
                elif direction == 'vertical' and start_y + i < HEIGHT - 1:
                    self.board[start_y + i][start_x] = WALL

    def place_character(self, char):
        attempts = 0
        while attempts < 100:  # Limit attempts to prevent infinite loop
            x, y = random.randint(1, WIDTH - 2), random.randint(1, HEIGHT - 2)
            if self.board[y][x] == EMPTY or (char == PACMAN and self.board[y][x] == PELLET):
                if char == GHOST:
                    # Store the original content of the cell
                    self.ghost_original_cell = self.board[y][x]
                self.board[y][x] = char
                return x, y
            attempts += 1
        raise Exception("Unable to place character after 100 attempts")

    def move_character(self, x, y, dx, dy):
        new_x, new_y = x + dx, y + dy
        if 0 <= new_x < WIDTH and 0 <= new_y < HEIGHT and self.board[new_y][new_x] != WALL:
            return new_x, new_y
        return x, y

    def move_ghost(self):
        px, py = self.player_position
        gx, gy = self.ghost_position

        # Calculate direction to move towards the player
        dx = 1 if px > gx else -1 if px < gx else 0
        dy = 1 if py > gy else -1 if py < gy else 0

        # Try to move in the calculated direction
        new_x, new_y = self.move_character(gx, gy, dx, dy)

        # If can't move in the ideal direction, try other directions
        if (new_x, new_y) == (gx, gy):
            possible_moves = [(1, 0), (-1, 0), (0, 1), (0, -1)]
            random.shuffle(possible_moves)
            for dx, dy in possible_moves:
                new_x, new_y = self.move_character(gx, gy, dx, dy)
                if (new_x, new_y) != (gx, gy):
                    break

        # Restore the original cell content and update ghost position
        self.board[gy][gx] = self.ghost_original_cell
        self.ghost_original_cell = self.board[new_y][new_x]
        self.board[new_y][new_x] = GHOST
        self.ghost_position = (new_x, new_y)

    def update_game_state(self):
        if not self.is_active:
            return False

        # Move ghost every 3 seconds
        self.ghost_move_counter += 1
        if self.ghost_move_counter >= 3:
            self.move_ghost()
            self.ghost_move_counter = 0

        # Check if Pac-Man is caught
        if self.player_position == self.ghost_position:
            return False

        # Check if all pellets are collected
        if self.pellets_collected >= self.total_pellets:
            if self.level < 10:
                self.level += 1
                self.pellets_collected = 0
                self.create_board()
                self.player_position = self.place_character(PACMAN)
                self.ghost_position = self.place_character(GHOST)
            else:
                return False  # Game won

        return True

    def render_game(self):
        board_str = '\n'.join([''.join(row) for row in self.board])
        return f"{board_str}\nLevel: {self.level}\nScore: {self.score}\nPellets: {self.pellets_collected}/{self.total_pellets}"

class Pacman(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.game_states = {}

    @commands.command(name='pacman')
    async def start_pacman(self, ctx):
        await self.start_game(ctx)

    async def start_game(self, ctx):
        game_state = GameState()
        self.game_states[ctx.channel.id] = game_state

        game_state.create_board()
        game_state.player_position = game_state.place_character(PACMAN)
        game_state.ghost_position = game_state.place_character(GHOST)

        game_state.message = await ctx.send(game_state.render_game())

        for emoji in list(MOVEMENTS.keys()) + [RESTART, CANCEL]:
            await game_state.message.add_reaction(emoji)

        while game_state.update_game_state():
            await game_state.message.edit(content=game_state.render_game())
            await asyncio.sleep(1)

        if game_state.is_active:
            if game_state.level == 10 and game_state.pellets_collected >= game_state.total_pellets:
                await game_state.message.edit(content=f'{game_state.render_game()}\nCongratulations! You won the game!')
            else:
                await game_state.message.edit(content=f'{game_state.render_game()}\nGame Over!')
        del self.game_states[ctx.channel.id]

    @commands.Cog.listener()
    async def on_reaction_add(self, reaction, user):
        if user == self.bot.user:
            return

        channel_id = reaction.message.channel.id
        if channel_id not in self.game_states:
            return

        game_state = self.game_states[channel_id]
        if reaction.message.id != game_state.message.id:
            return

        if str(reaction.emoji) in MOVEMENTS:
            dx, dy = MOVEMENTS[str(reaction.emoji)]
            x, y = game_state.player_position
            new_x, new_y = game_state.move_character(x, y, dx, dy)

            if game_state.board[new_y][new_x] == PELLET:
                game_state.score += 10
                game_state.pellets_collected += 1

            game_state.board[y][x] = EMPTY
            game_state.board[new_y][new_x] = PACMAN
            game_state.player_position = (new_x, new_y)

        elif str(reaction.emoji) == RESTART:
            game_state.is_active = False
            await reaction.message.channel.send("Restarting the game...")
            await self.start_game(reaction.message.channel)

        elif str(reaction.emoji) == CANCEL:
            game_state.is_active = False
            await reaction.message.edit(content=f'{game_state.render_game()}\nGame Cancelled!')
            del self.game_states[channel_id]

        await reaction.remove(user)

async def setup(bot):
    await bot.add_cog(Pacman(bot))