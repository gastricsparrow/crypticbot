import yaml
import time
import random
import pathlib
import discord
import asyncio
from typing import List
from redbot.core import commands, checks
from redbot.core.utils.chat_formatting import box, bold, humanize_list
from redbot.core.utils.common_filters import normalize_smartquotes


_SOLVING_SOUND_BITES = [
    "Hmm... that should do it!",
    "Every puzzle has an answer!",
    "?",
    "Any idea what this clue might mean?",
    "OwO what's this?",
    "Can you solve this?",
    "It's not that hard, guys...",
    "Wow, all these puzzlers and no one can solve this?",
    "No takers?",
    "Cryptic clue coming in hot!",
    "Guys, there's still this clue that hasn't been solved..."
]

_STARTING_TEXT = [
    "Here's a brand new cryptic clue:",
    "Feast your brain tongue on this cryptic pop!",
    "OwO what's this clue?",
    "Cryptic clue coming in hot!",
    "Any idea what this clue might be?",
    "Would you care for one of our finest cryptics, sir/madam?",
    "Can you solve this?"
]

class Cryptic(commands.Cog):
    """Duc's custom cog for cryptic clues"""
    def __init__(self):
        super().__init__()
        self._all_clues = self._load_clues()
        # print(self._all_clues)
        self._dead_clues = []
        self._cryptic_being_solved = None

    def _load_clues(self) -> List[pathlib.Path]:
        path = pathlib.Path(__file__).parent.resolve() / "data/cryptics.yaml"
        with path.open(encoding='utf-8') as f:
            clues = yaml.safe_load(f)
        return clues

    @commands.group(invoke_without_command=True)
    @commands.guild_only()
    async def cryptic(self, ctx: commands.Context):
        """
        Get a cryptic crossword clue!
        You must solve one clue before getting the next!
        """
        self.ctx = ctx
        if self._cryptic_being_solved is None:
            if len(self._dead_clues) == len(self._all_clues):
                self._dead_clues = []
            clue = None
            while clue is None or clue in self._dead_clues:
                clue = random.choice(list(self._all_clues.keys()))
            ans = self._all_clues[clue]
            if ' ' in ans:
                ans_len = ', '.join([str(len(a)) for a in ans.split()])
            else:
                ans_len = str(len(ans))
            self._cryptic_being_solved = (clue, ans_len)
            text = random.choice(_STARTING_TEXT)
            await ctx.send(text + "\n\n" + bold(f'{clue} ({ans_len})'))
            self._last_complained = time.time()
            continue_ = await self.wait_for_answer(ans, 2, 900)
        else:
            clue, ans_len = self._cryptic_being_solved
            ans = self._all_clues[clue]
            text = "Everyone is still stuck on this clue:"
            await ctx.send(text + "\n\n" + bold(f'{clue} ({ans_len})'))
    
    async def wait_for_answer(self, answer, delay: float, timeout: float):
        """Wait for a correct answer, and then respond.

        Returns False if waiting was cancelled; this is usually due to the
        session being forcibly stopped.

        Parameters
        ----------
        answer : `str`
            The valid answer to the current cryptic clue.
        delay : float
            How long the bot waits before checking in (in seconds).
        timeout : float
            How long before the bot gets frustrated (seconds).
        Returns
        -------
        bool
            :code:`True` if the session wasn't interrupted.

        """
        while self._cryptic_being_solved is not None:
            clue, ans_len = self._cryptic_being_solved
            try:
                message = await self.ctx.bot.wait_for(
                    "message", check=self.check_answer(answer), timeout=delay
                )
            except asyncio.TimeoutError:
                if time.time() - self._last_complained > timeout:
                    # reply = random.choice(_DERISIVE_TEXT) + '\n\n' + bold(f'{clue} ({ans_len})')
                    # await self.ctx.send(reply)
                    self._last_complained = time.time()
                    continue
            else:
                self._cryptic_being_solved = None
                self._dead_clues += clue,
                await self.ctx.send(f"You got it, {message.author.display_name}! The answer to \n\n" +
                                    bold(f'{clue} ({ans_len})') + '\n'
                                    f"is {answer}!\n\nType ?cryptic to get another clue.")
                return True
        await self.ctx.send("Cryptic was forced to stop. Cryptic is sad.")
        return True

    def check_answer(self, answer):
        answer = answer.upper()
        def _pred(message: discord.Message):
            early_exit = message.channel != self.ctx.channel or message.author == self.ctx.guild.me
            if early_exit:
                return False
            guess = message.content.upper()
            guess = normalize_smartquotes(guess)
            return answer in guess
        return _pred

    @cryptic.command(name="help")
    async def cryptic_help(self, ctx):
        """
        Get an explanation of how the cryptic bot works.
        """
        await ctx.send("Hello, I am the CrypticBot! I will be challenging you with " + bold("cryptic clues") + ".\n\n"

        "A cryptic clue is like a normal crossword clue, except "
        "each one is a puzzle in and of itself, utilising wordplays, ciphers "
        "and trickery to hide the true answer!\n\n"

        """Cryptic clues may employ:
        Double meanings
        Anagrams
        Acronyms
        Homophones
        ...and more!
        """

        "Still unsure? Just look up \"how to solve cryptic clues\" for many useful resources online!\n"

        "\nAre you ready? Type \"?cryptic\" to start!"
        )

    @cryptic.command(name='hack')
    @checks.mod_or_permissions(administrator=True)
    async def cryptic_hack(self, ctx: commands.Context):
        if self._cryptic_being_solved is None:
            await ctx.send(f"""No cryptic clue to hack!""")
            return
        clue, ans_len = self._cryptic_being_solved
        answer = self._all_clues[clue]
        self._cryptic_being_solved = None
        self._dead_clues += clue,
        await ctx.send(f"The answer to the cryptic clue: {clue} ({ans_len}) is:\n\n" + bold(f'||{answer}||'))

    @cryptic.command(name='stop')
    async def cryptic_stop(self, ctx: commands.Context):
        if self._cryptic_being_solved is None:
            await ctx.send(f"""No cryptic clue has been given!""")
            return
        clue, ans_len = self._cryptic_being_solved
        self._cryptic_being_solved = None
        await ctx.send(f"The clue: {clue} ({ans_len}) goes unsolved!")
    