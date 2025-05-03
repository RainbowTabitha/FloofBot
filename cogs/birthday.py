import discord
from discord.ext import commands, tasks
import json
import os
from datetime import datetime
import asyncio
import pytz

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
        """Set your birthday using a dropdown for month and input for day."""
        # Create month options
        month_options = [discord.SelectOption(label=month, value=str(index + 1)) for index, month in enumerate([
            "January", "February", "March", "April", "May", "June",
            "July", "August", "September", "October", "November", "December"
        ])]

        # Create dropdown for month
        month_select = discord.ui.Select(placeholder="Select your birth month", options=month_options)

        # Create a view to hold the month dropdown
        view = discord.ui.View()
        view.add_item(month_select)

        # Send the month dropdown to the user in DMs
        await ctx.author.send("Please select your birth month:", view=view)

        # Wait for the user to select a month
        def check_month(interaction):
            return interaction.user == ctx.author and interaction.data['component_type'] == 3  # 3 is the type for Select

        try:
            month_interaction = await self.bot.wait_for("interaction", check=check_month, timeout=60.0)
            month = int(month_select.values[0])  # Get the selected month

            # Acknowledge the month selection with an ephemeral message
            await month_interaction.response.send_message(f"You selected: {month_options[month - 1].label}. Please type your birth day (1-31):", ephemeral=True)

            # Wait for the user to respond with the day
            def check_day(message):
                return message.author == ctx.author and message.channel == ctx.author.dm_channel

            day_message = await self.bot.wait_for("message", check=check_day, timeout=60.0)
            day = day_message.content.strip()

            # Validate the day input
            if not day.isdigit() or not (1 <= int(day) <= 31):
                await ctx.author.send("Please enter a valid day between 1 and 31.")
                return

            # Format the birthday as YYYY-MM-DD
            birthday = f"2023-{month:02}-{int(day):02}"  # Using a fixed year for simplicity

            # Extract month name for the DM response
            month_name = ["January", "February", "March", "April", "May", "June",
                          "July", "August", "September", "October", "November", "December"][month - 1]
            formatted_birthday = f"{month_name} {int(day)}"

            user_id = str(ctx.author.id)
            birthday_data[user_id] = birthday
            save_birthdays()

            # Send the confirmation message in a DM
            await ctx.author.send(f"Your birthday has been set to {formatted_birthday}!")

        except Exception as e:
            # Handle the error gracefully
            if isinstance(e, discord.errors.NotFound):
                await ctx.author.send("An error occurred while processing your request. Please try again.")
            else:
                await ctx.author.send("You took too long to respond or an error occurred.")

    @tasks.loop(hours=24)  # Check every 24 hours
    async def check_birthdays(self):
        # Get the current time in EST
        est = pytz.timezone('America/New_York')
        now = datetime.now(est)

        # Check if it's 12 AM
        if now.hour == 0 and now.minute == 0:
            today = now.strftime("%Y-%m-%d")
            for user_id, birthday in birthday_data.items():
                if birthday == today:
                    user = self.bot.get_user(int(user_id))
                    if user:
                        channel = self.bot.get_channel(1361514241865158687)
                        await channel.send(f"🎉 Happy Birthday {user.mention}! 🎉")
        else:
            await asyncio.sleep(60)

    @check_birthdays.before_loop
    async def before_check_birthdays(self):
        await self.bot.wait_until_ready()