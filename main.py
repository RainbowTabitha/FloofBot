#***************************************************************************#
# FloofBot
#***************************************************************************#


import os
import platform
import discord

from cogs.base import Base
from cogs.fun import Fun
from cogs.moderation import Moderation
from cogs.leveling import Leveling
from cogs.activity import Activity
from cogs.birthday import Birthday
from cogs.reference_sheets import ReferenceImages
from cogs.music import Music
from cogs.stats_channels import StatsChannels

from discord.ext import tasks
from discord.ext import commands

#Intents
intents = discord.Intents.all()

#Define Client
bot = commands.Bot(description="FloofBot", command_prefix=commands.when_mentioned_or("/"), intents=intents, activity=discord.Game(name='Fursuit Games'))

@bot.event
async def on_ready():
  memberCount = len(set(bot.get_all_members()))
  serverCount = len(bot.guilds)
  

  print("                                                                ")
  print("################################################################") 
  print(f"Floof Bot                                                      ")
  print("################################################################") 
  print("Running as: " + bot.user.name + "#" + bot.user.discriminator)
  print(f'With Client ID: {bot.user.id}')
  print("\nBuilt With:")
  print("Python " + platform.python_version())
  print("Py-Cord " + discord.__version__)


#Boot Cogs
bot.add_cog(Base(bot))
bot.add_cog(Fun(bot))
bot.add_cog(Moderation(bot))
bot.add_cog(Leveling(bot))
bot.add_cog(Activity(bot))
bot.add_cog(Birthday(bot))
bot.add_cog(ReferenceImages(bot))
bot.add_cog(Music(bot))
bot.add_cog(StatsChannels(bot))

#Run Bot
TOKEN = os.environ.get("FLOOF_TOKEN")
bot.run(TOKEN)