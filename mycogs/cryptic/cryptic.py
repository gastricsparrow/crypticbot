from redbot.core import commands

class Cryptic(commands.Cog):
    """My custom cog"""

    @commands.command()
    async def cryptic(self, ctx):
        """This does stuff!"""
        # Your code will go here
        await ctx.send("I am supposed to send you a cryptic!")