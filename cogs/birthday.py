import discord
from discord.ext import commands, tasks
import json
import os
from datetime import datetime

# File to store birthday data
BIRTHDAY_FILE = 'birthdays.json'

# Load or initialize birthday data
if os.path.exists(BIRTHDAY_FILE):
    with open(BIRTHDAY_FILE, 'r') as f:
        birthday_data = json.load(f)
else:
    birthday_data = {}

# Function to save birthday data
def save_birthdays():
    with open(BIRTHDAY_FILE, 'w') as f:
        json.dump(birthday_data, f, indent=4)

class Birthday(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.check_birthdays.start()  # Start the birthday check task

    @commands.slash_command()
    async def set_birthday(self, ctx, birthday: str):
        """Set your birthday in the format YYYY-MM-DD."""
        user_id = str(ctx.author.id)
        birthday_data[user_id] = birthday
        save_birthdays()
        await ctx.respond(f"Your birthday has been set to {birthday}!")

    @tasks.loop(hours=24)  # Check every 24 hours
    async def check_birthdays(self):
        today = datetime.now().strftime("%Y-%m-%d")
        for user_id, birthday in birthday_data.items():
            if birthday == today:
                user = self.bot.get_user(int(user_id))
                if user:
                    channel = self.bot.get_channel(1361514241865158687)
                    await channel.send(f"🎉 Happy Birthday {user.mention}! 🎉")

    @check_birthdays.before_loop
    async def before_check_birthdays(self):
        await self.bot.wait_until_ready()