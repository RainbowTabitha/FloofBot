#***************************************************************************#
# FloofBot
#***************************************************************************#

import aiohttp
import discord
import random
import requests
import time

from dadjokes import Dadjoke
from discord.ext import commands
from discord import emoji, SlashCommandGroup

class Fun(commands.Cog):

    """Cog for Fun commands"""

    def __init__(self, bot):
        self.bot = bot

    #Roll Command
    @commands.slash_command(aliases=["party"])
    async def roll(self, ctx, min: int, max:int, count:int):
        
        """Roll a dice, default is rolling 1d6. (minNumber, maxNumber, diceCount)"""
        if count <= 20:
            for _ in range(count):
                await ctx.respond(random.randint(min, max))
        if count > 20:
            await ctx.respond('Invalid number of rolls')

    #Dadjoke Command
    @commands.slash_command(aliases=["dadjoke"])
    async def dadjoke(self, ctx):
        """Sends a dadjoke."""
        await ctx.respond(Dadjoke().joke)
    
    #Coin Flip Command
    @commands.slash_command(aliases=["flip"])
    async def toss(self, ctx):
        """Flip a coin, heads or tails, your fate"""
        ch = ["Heads", "Tails"]
        rch = random.choice(ch)
        await ctx.respond(f"You got **{rch}**")


    #Reverse Text Command
    @commands.slash_command()
    async def reverse(self, ctx, *, text):
        """Reverse the given text"""
        await ctx.respond("".join(list(reversed(str(text)))))

def setup(bot):
    bot.add_cog(Fun(bot))