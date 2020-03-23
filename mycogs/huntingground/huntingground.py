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


class HuntingGround(commands.Cog):
    """UTS Puzzle Society's custom cog for puzzle hunting on Discord"""
    def __init__(self):
        super().__init__()
        self.load_hunt_data()

    def _load_hunt_data(self) -> List[pathlib.Path]:
        path = pathlib.Path(__file__).parent.resolve() / "data/hunt.yaml"
        with path.open(encoding='utf-8') as f:
            hunt_info = yaml.safe_load(f)
        self.hunt_info = hunt_info

    @commands.group(invoke_without_command=True)
    @commands.guild_only()
    async def hunt(self, ctx: commands.Context):
        """
        Core hunt command group
        """
        ending_time = datetime.strptime(self.hunt_info['End time'], "%Y/%m/%d %H:%M:%S")
        await ctx.send("Current puzzle hunt: " + bold(self.hunt_info['Name']) +
        "\nTime left: " + bold(datetime.strftime(ending_time - datetime.now(), "%d days, %H hours, %M minutes and %S seconds")) +
        "\n(Ends on " + self.hunt_info['End time'] + " AEDT)"
        "\n\nIf you haven't started, use \"?hunt join\" to start or join a team channel. "
        "Or use \"?hunt help\" for a tutorial (sent to your DM).")
    
    async def wait_for_answer(self, answer, delay: float, timeout: float):
        """Wait for a correct answer, and then respond.

        Returns False if waiting was cancelled; this is usually due to the
        session being forcibly stopped.

        Parameters
        ----------
        answer : `str`
            The valid answer to the current huntingground clue.
        delay : float
            How long the bot waits before checking in (in seconds).
        timeout : float
            How long before the bot gets frustrated (seconds).
        Returns
        -------
        bool
            :code:`True` if the session wasn't interrupted.

        """
        while self._huntingground_being_solved is not None:
            clue, ans_len = self._huntingground_being_solved
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
                self._huntingground_being_solved = None
                self._dead_clues += clue,
                await self.ctx.send(f"You got it, {message.author.display_name}! The answer to \n\n" +
                                    bold(f'{clue} ({ans_len})') + '\n'
                                    f"is {answer}!\n\nType ?huntingground to get another clue.")
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

    @hunt.command(name="help")
    async def help(self, ctx):
        """
        Get an explanation of how the huntingground bot works.
        """
        await ctx.send("Hello, I am the CrypticBot, and welcome to " + bold(self.hunt_info['Name']) + ".\n\n"

        "This is a puzzle hunt about " + self.hunt_info['Theme'] + ","
        " created by " + self.hunt_info['Author'] + ". You can"
        " join now by sending \"?hunt join\"! You will be messaged"
        " by me about setting up or joining a team.\n\n"

        """To 
        """

        "Still unsure? Just look up \"how to solve huntingground clues\" for many useful resources online!\n"

        "\nAre you ready? Type \"?hunt join\" to start!"
        )

    @hunt.command(name="puzzles")
    async def list_puzzles(self, ctx):
        await.

    @hunt.command(name="join")
    async def join_team(self, ctx):
        await.

    @hunt.command(name='hack')
    @checks.mod_or_permissions(administrator=True)
    async def huntingground_hack(self, ctx: commands.Context):
        if self._huntingground_being_solved is None:
            await ctx.send(f"""No huntingground clue to hack!""")
            return
        clue, ans_len = self._huntingground_being_solved
        answer = self._all_clues[clue]
        self._huntingground_being_solved = None
        self._dead_clues += clue,
        await ctx.send(f"The answer to the huntingground clue: {clue} ({ans_len}) is:\n\n" + bold(f'||{answer}||'))
