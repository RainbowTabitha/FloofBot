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
    async def set_birthday(self, ctx):
        """Set your birthday using dropdowns for month and day."""
        # Create month options
        month_options = [discord.SelectOption(label=month, value=str(index + 1)) for index, month in enumerate([
            "January", "February", "March", "April", "May", "June",
            "July", "August", "September", "October", "November", "December"
        ])]

        # Create day options
        day_options = [discord.SelectOption(label=str(day), value=str(day)) for day in range(1, 32)]

        # Create dropdowns
        month_select = discord.ui.Select(placeholder="Select your birth month", options=month_options)
        day_select = discord.ui.Select(placeholder="Select your birth day", options=day_options)

        # Create a view to hold the dropdowns
        view = discord.ui.View()
        view.add_item(month_select)
        view.add_item(day_select)

        # Send the dropdowns to the user
        await ctx.respond("Please select your birthday:", view=view)

        # Wait for the user to select both month and day
        def check(interaction):
            return interaction.user == ctx.author and interaction.data['component_type'] == 3  # 3 is the type for Select

        # Wait for the user to select a month and day
        try:
            interaction = await self.bot.wait_for("interaction", check=check, timeout=60.0)
            month = month_select.values[0]
            day = day_select.values[0]

            # Format the birthday as YYYY-MM-DD
            birthday = f"2023-{month.zfill(2)}-{day.zfill(2)}"  # Using a fixed year for simplicity
            user_id = str(ctx.author.id)
            birthday_data[user_id] = birthday
            save_birthdays()
            await interaction.response.send_message(f"Your birthday has been set to {birthday}!")

        except Exception as e:
            await ctx.respond("You took too long to respond or an error occurred.")

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