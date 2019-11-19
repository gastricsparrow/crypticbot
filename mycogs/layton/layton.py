import yaml
import time
import random
import requests
import pathlib
import discord
import asyncio
from html.parser import HTMLParser
from bs4 import BeautifulSoup
from typing import List
from redbot.core import commands, checks
from redbot.core.utils.chat_formatting import box, bold, humanize_list
from redbot.core.utils.common_filters import normalize_smartquotes


_SUCCESS_SOUNDBITES = [
    "Hmm... that should do it!",
    "Every puzzle has an answer!",
    "Critical thinking is the key to success!",
    "A true gentleman leaves no puzzle unsolved!",
    "I love the thrill of a good solution!"
]

_START_SOUNDBITES = [
    "That reminds me of a puzzle...",
    "Speaking of, have you heard of this puzzle?",
    "Tell me, have you heard this one before?",
    "Oh my, a puzzle!",
    "Think good and hard before you answer.",
    "Speaking of, I've got just the puzzle for you!",
    "Why not try your hand at this puzzle?",
    "Please take a look at this puzzle.",
    "Why don't you give this puzzle a go?",
    "You just reminded me of a splendid puzzle!"
]

HINT_TEXT = """I'm out of hints. Just think really hard?\n
You could also use \"?layton solve <puzzleID>\""""


def get_puzzle_text(puzzle_dict):
    text = '"' + random.choice(_START_SOUNDBITES) + \
        "\"\n\n**" + puzzle_dict['title'] + \
        "**\n" + puzzle_dict['puzzle'] + \
        (puzzle_dict['image'] if puzzle_dict['image'] else '=' * 12 + '**The image may be missing.**' + '=' * 12) + \
        "\n" + f"*This is puzzle {puzzle_dict['number']} from {puzzle_dict['game']}.\nPuzzle ID: {puzzle_dict['id']}*"
    return text

class Layton(commands.Cog):
    """
    Professor Layton extension for Red-DiscordBot.
    Thanks to the layton.fandom.com community for the compiled puzzles.
    """
    def __init__(self):
        super().__init__()
        self._puzzles = self._load_puzzles()
        self._current_puzzle = None

    def _load_puzzles(self):
        path = pathlib.Path(__file__).parent.resolve() / "data/puzzles.yaml"
        with path.open(encoding='utf-8') as f:
            puzzles = yaml.safe_load(f)
        return puzzles

    @commands.group(invoke_without_command=True)
    @commands.guild_only()
    async def layton(self, ctx: commands.Context):
        """
        Get a random puzzle from Professor Layton!
        TODO: Give out Picarats.
        """
        self.ctx = ctx
        if self._current_puzzle is None or 'set_answer' not in self._current_puzzle:
            id_ = random.choice(list(self._puzzles.keys()))
            answers = [ans for ans in self._puzzles[id_] if ans not in ('', None)]
            self._current_puzzle = grab_puzzle(id_)
            if not self._current_puzzle:
                await ctx.send("I've failed to retrieve a puzzle. Please try again.")
                return
            await ctx.send(get_puzzle_text(self._current_puzzle))
            text = ''
            if self._current_puzzle['hints']:
                text = "There are hints available for this puzzle. Type \"?layton hint\" to see one.\n"
            if answers:
                self._current_puzzle['set_answer'] = True
                await ctx.send(text + "If you answer correctly below, you'll get {} Picarats!".format(self._current_puzzle['picarats']))
                continue_ = await self.wait_for_answer(ctx, answers, 1, 900)
            else:
                text += f"This puzzle is not interactive (yet?). Type \"?layton solve\" to check your answer!"
                await ctx.send(text)
                # await ctx.send(f"This puzzle does not have an interactive solution. Type \"?layton solve {self._current_puzzle['id']}\" to check your answer!")
        else:
            clue, ans_len = self._current_puzzle
            ans = self._all_clues[clue]
            text = "You have one puzzle in progress: **" + self._current_puzzle['id'] + "**. Stuck? Type \"?layton hint\" for a hint, or \"?layton solve\" to get the solution!"
            await ctx.send(text + "\n\n" + self._current_puzzle['puzzle'] + "\n" + self._current_puzzle['image'])
    
    async def wait_for_answer(self, ctx, answers, delay: float, timeout: float):
        """Wait for a correct answer, and then respond.

        Returns False if waiting was cancelled; this is usually due to the
        session being forcibly stopped.

        Parameters
        ----------
        answers : `list`
            The valid answers to the current cryptic clue.
        delay : float
            How long the bot waits before checking in (in seconds).
        timeout : float
            How long before the bot gets frustrated (seconds).
        Returns
        -------
        bool
            :code:`True` if the session wasn't interrupted.
        """
        while self._current_puzzle is not None:
            try:
                message = await self.ctx.bot.wait_for(
                    "message", check=self.check_answer(answers), timeout=delay
                )
            except asyncio.TimeoutError:
                continue
            else:
                puzzle = self._current_puzzle
                solution = puzzle['solution']
                title = puzzle['title']
                sol_imgs = puzzle['solution_images']
                await ctx.send(f"\"{random.choice(_SUCCESS_SOUNDBITES)}\"\n\n**{title} - Solution**\n{solution}!\n" + '\n'.join(sol_imgs))
                await ctx.send(f"You got it, {message.author.display_name}! For solving " + puzzle['id'] +
                                    f", you have earned {puzzle['picarats']} picarats!")
                self._current_puzzle = None
                return True
        # await self.ctx.send("Layton's wait-for-answer function was force-stopped.")
        return True

    def check_answer(self, answers):
        answers = [str(ans).lower() for ans in answers]
        def _pred(message: discord.Message):
            early_exit = message.channel != self.ctx.channel or message.author == self.ctx.guild.me
            if early_exit:
                return False
            guess = message.content.lower()
            guess = normalize_smartquotes(guess)
            return any([guess == ans for ans in answers])
        return _pred

    @layton.command(name="help")
    async def layton_help(self, ctx):
        """
        Get an explanation of how the Layton puzzle cog works.
        """
        await ctx.send("Every puzzle has an answer!\n\n"

        "Type ?layton and I will give you a puzzle from the Professor Layton franchise."
        " If the puzzle has its answer already set, you can gain Picarats by answering correctly.\n\n"

        "Type \"?layton hint <puzzleID>\" and you'll receive a hint for the puzzle if one's available."
        "Type \"?layton solve <puzzleID>\" to read the solution of a puzzle."
        )

    @layton.command(name='modview')
    @checks.mod_or_permissions(administrator=True)
    async def layton_modview(self, ctx: commands.Context, *puzzle_id: str):
        """
        Admin only: ?layton modview <puzzleid>
        Get puzzle by ID.
        """
        try:
            puzzle_id = puzzle_id[0]
            puzzle = grab_puzzle(puzzle_id)
        except:
            await ctx.send("Wrong command. Pass in a Puzzle ID!")
        if not puzzle:
            await ctx.send("Failed to retrieve puzzle!")
        else:
            await ctx.send(get_puzzle_text(puzzle))
        

    @layton.group(name='solve', invoke_without_command=True)
    async def layton_solve(self, ctx: commands.Context, *puzzle_id : str):
        """Get the solution to the last puzzle, or by puzzle ID."""
        print(puzzle_id)
        if self._current_puzzle is None and not puzzle_id:
            await ctx.send("I'm not sure which puzzle you mean. Add the Puzzle ID?")
            return
        if not puzzle_id:
            puzzle = self._current_puzzle
        else:
            if puzzle_id[0] not in self._puzzles.keys():
                await ctx.send("Invalid puzzle ID.")
                return
            puzzle = grab_puzzle(puzzle_id[0])
            if not puzzle:
                await ctx.send("Error, maybe invalid puzzle ID.")
                return
        if puzzle == self._current_puzzle and 'set_answer' in puzzle:
            await ctx.send("A gentleman should not give the answer away when there are picarats on the line!")
            return
        solution = puzzle['solution']
        title = puzzle['title']
        sol_imgs = puzzle['solution_images']
        await ctx.send(f"\"{random.choice(_SUCCESS_SOUNDBITES)}\"\n\n**{title} - Solution**\n{solution}!\n" + '\n'.join(sol_imgs))

    
    @layton.command(name='hint')
    async def layton_hint(self, ctx: commands.Context):
        """Get available hints to the current puzzle one by one."""
        if self._current_puzzle is None:
            await ctx.send("I'm not sure which puzzle you want to get the hint for.")
            return
        if not self._current_puzzle['hints']:
            await ctx.send("I'm fresh out of hints to give. Looks like you're on your own.")
            return
        hint_no, hint = self._current_puzzle['hints'].pop(0)
        title = self._current_puzzle['title']
        text = '\nThere are no more hints.'
        if self._current_puzzle['hints']:
            text = '\nMore hints are available.'
        await ctx.send(f"**{title} - Hint {hint_no}**\n{hint}!" + text)

    @layton.command(name='setanswer')
    @checks.mod_or_permissions(administrator=True)
    async def layton_setanswer(self, ctx: commands.Context, *args: str):
        """
        Admin only: Set an interactive answer to a puzzle.
        """
        if len(args) < 2:
            await ctx.send("Invalid arguments!")
            return
        puzzle_id = args[0]
        answer = ' '.join(args[1:])
        if puzzle_id not in self._puzzles:
            await ctx.send("Invalid Puzzle ID!")
            return
        self._puzzles[puzzle_id] = answer
        path = pathlib.Path(__file__).parent.resolve() / "data/puzzles.yaml"
        with path.open('w', encoding='utf-8') as f:
            puzzles = yaml.safe_dump(self._puzzles, f)
        await ctx.send(f"Successfully set the interactive answer of {puzzle_id}!")

    # async def update_picarats(self, picarats):
    #     """Update the leaderboard with the given picarats.

    #     Parameters
    #     ----------
    #     picarats: Number of picarats to give out

    #     """
    #     max_score = session.settings["max_score"]
    #     for member, score in session.scores.items():
    #         if member.id == session.ctx.bot.user.id:
    #             continue
    #         stats = await self.conf.member(member).all()
    #         if score == max_score:
    #             stats["wins"] += 1
    #         stats["total_score"] += score
    #         stats["games"] += 1
    #         await self.conf.member(member).set(stats)


class MyHTMLParser(HTMLParser):
    raw_data = None
    start_attrs = None
    def handle_starttag(self, tag, attrs):
        self.start_attrs = attrs
    def handle_data(self, x):
        if x.strip() != '':
            self.raw_data = x

parser = MyHTMLParser()

def grab_puzzle(puzzle_id):
    puzzle_dict = {
        'id': puzzle_id,
        'URL': "https://layton.fandom.com/wiki/Puzzle:" + puzzle_id
    }
    puzzle_html = requests.get(puzzle_dict['URL'])
    puzzle_soup = BeautifulSoup(
        puzzle_html.content, 'html.parser')
    print(puzzle_dict['URL'])
    image = puzzle_soup.find('img', class_='pi-image-thumbnail')
    try:
        puzzle_dict['image'] = image['src']
    except:
        puzzle_dict['image'] = ""

    # Game
    try:
        parser.feed(str(puzzle_soup.select("div[data-source='game']")[0]))
        for attr in parser.start_attrs:
            if attr[0] == 'title':
                game = attr[1]
    except:
        game = 'Professor Layton'
    
    # Number
    parser.reset()
    try:
        parser.feed(str(puzzle_soup.select("div[data-source='number']")[0]))
        number = parser.raw_data
    except:
        number = 'xxx'

    # Picarats
    parser.reset()
    try:
        parser.feed(str(puzzle_soup.select("div[data-source='picarats']")[0]))
        picarats = parser.raw_data
    except:
        picarats = '10'

    puzzle_dict['game'] = game
    puzzle_dict['number'] = number
    puzzle_dict['picarats'] = picarats
    
    # Get Puzzle text
    puzzle_text_span = puzzle_soup.find('span', id='Puzzle')
    puzzle_span = puzzle_text_span.parent.parent
    puzzle_txts = []
    s = time.time()
    cur = puzzle_text_span
    while time.time() - s < 0.1:
        t = cur.find_next(['p', 'h2', 'li', 'dt'])
        if t is None:
            break
        txt = t.get_text()
        if 'Hints' in txt:
            break
        else:
            puzzle_txts += txt,
        cur = t
    else:
        return False

    # Get solutions
    puz_txt = '\n'.join(puzzle_txts)
    if 'US Version' in puz_txt:
        puz_txt = puz_txt.split('UK Version\n')[0]
    puzzle_dict['puzzle'] = puz_txt

    # Get puzzle title
    title = puzzle_span.find('h2', class_='pi-title')
    puzzle_dict['title'] = title.get_text()

    correct = puzzle_span.find('span', id='Correct')
    end_table = correct.find_next('table')
    cur = correct
    sol_txts = []
    start = time.time()
    while time.time() - start < 0.5:
        if cur.find_next('table') != end_table:
            break
        p = cur.find_next(['p', 'dt'])
        if p is None:
            break
        sol_txts += p.get_text(),
        cur = p
    else:
        return False
    
    solution_txt = '\n'.join(sol_txts).split('A big thanks to')[0]
    if 'US Version' in solution_txt:
        solution_txt = solution_txt.split('UK Version')[0]
    puzzle_dict['solution'] = solution_txt

    # Get solution image
    cur = correct
    sol_imgs = []
    start = time.time()
    while time.time() - start < 0.5:
        if cur.find_next('table') != end_table:
            break
        i = cur.find_next('img')
        try:
            iurl = i['src']
            if 'http' in iurl:
                sol_imgs += iurl,
            cur = i
        except:
            break
            continue
    else:
        return False
    puzzle_dict['solution_images'] = sol_imgs

    # Get hints
    hints = puzzle_span.find_all('div', class_='tabbertab')
    hints = [hint.get_text().strip() for hint in hints if 'Hint' in hint['title']]
    hint_list = []
    for i, hint in enumerate(hints):
        if 'US Version' in hint:
            hint = hint.split('US Version\n')[1].split('UK Version\n')[0]
        hint_list += (i + 1, hint),
    puzzle_dict['hints'] = hint_list
    return puzzle_dict