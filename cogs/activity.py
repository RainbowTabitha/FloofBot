#***************************************************************************#
# FloofBot
#***************************************************************************#

import discord
from discord.ext import commands, tasks
import json
import os
import time

# File to store activity logs
ACTIVITY_LOG_FILE = 'activity_log.json'

# Load or initialize activity data
if os.path.exists(ACTIVITY_LOG_FILE):
    with open(ACTIVITY_LOG_FILE, 'r') as f:
        activity_data = json.load(f)
else:
    activity_data = {}

# Function to save activity data
def save_activity():
    with open(ACTIVITY_LOG_FILE, 'w') as f:
        json.dump(activity_data, f, indent=4)

class Activity(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.cleanup_activity.start()  # Start the cleanup task

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot:
            return

        guild_id = str(message.guild.id)
        user_id = str(message.author.id)

        # Initialize guild data if it doesn't exist
        if guild_id not in activity_data:
            activity_data[guild_id] = {}

        # Initialize user data if it doesn't exist
        if user_id not in activity_data[guild_id]:
            activity_data[guild_id][user_id] = []

        # Log the message with a timestamp
        activity_data[guild_id][user_id].append(time.time())

        # Save activity data
        save_activity()

    @commands.slash_command()
    async def activity(self, ctx: discord.ApplicationContext):
        """Check the activity of users in the last 30 days."""
        guild_id = str(ctx.guild.id)
        if guild_id not in activity_data or not activity_data[guild_id]:
            await ctx.respond("No activity logged yet.")
            return

        # Calculate the time threshold for 30 days ago
        time_threshold = time.time() - (30 * 86400)  # 30 days in seconds

        # Count messages in the last 30 days
        activity_count = {}
        for user_id, timestamps in activity_data[guild_id].items():
            # Filter timestamps to only include those within the last 30 days
            recent_messages = [ts for ts in timestamps if ts > time_threshold]
            activity_count[user_id] = len(recent_messages)

        # Sort users by activity count
        sorted_activity = sorted(activity_count.items(), key=lambda x: x[1], reverse=True)

        # Assign ranks
        ranked_activity = []
        current_rank = 1
        previous_count = None

        for index, (user_id, count) in enumerate(sorted_activity):
            if count != previous_count:
                current_rank = index + 1  # Update rank only if the count changes
            ranked_activity.append((user_id, current_rank, count))  # Store user_id, rank, and count
            previous_count = count  # Update previous_count for the next iteration

        # Pagination logic
        page_size = 10
        total_pages = (len(ranked_activity) + page_size - 1) // page_size  # Calculate total pages
        current_page = 0

        # Function to create and send the embed for the current page
        async def send_activity_page(page):
            embed = discord.Embed(title="Most Active Users in the Last 30 Days", color=discord.Color.blue())
            start_index = page * page_size
            end_index = start_index + page_size
            for index, (user_id, rank, count) in enumerate(ranked_activity[start_index:end_index], start=start_index + 1):
                user = ctx.guild.get_member(int(user_id))
                nickname = user.display_name if user else "Unknown User"
                embed.add_field(name=f"{rank}. {nickname}", value=f"{count} messages", inline=False)
            embed.set_footer(text=f"Page {page + 1}/{total_pages}")
            return embed

        # Send the initial message with the leaderboard
        message = await ctx.respond(embed=await send_activity_page(current_page))

        # Add reactions for pagination if there are multiple pages
        if total_pages > 1:
            await message.add_reaction("◀️")  # Previous page
            await message.add_reaction("▶️")  # Next page

        # Reaction handling
        def check(reaction, user):
            return user == ctx.author and str(reaction.emoji) in ["◀️", "▶️"]

        while True:
            try:
                reaction, user = await self.bot.wait_for("reaction_add", timeout=60.0, check=check)
                if str(reaction.emoji) == "◀️" and current_page > 0:
                    current_page -= 1
                    await message.edit(embed=await send_activity_page(current_page))
                elif str(reaction.emoji) == "▶️" and current_page < total_pages - 1:
                    current_page += 1
                    await message.edit(embed=await send_activity_page(current_page))

                # Remove the user's reaction
                await message.remove_reaction(reaction, user)

            except Exception as e:
                print(f"Error during reaction handling: {e}")
                break  # Exit the loop on error

    @tasks.loop(hours=2)  # Run every 2 hours
    async def cleanup_activity(self):
        """Cleanup activity logs older than 30 days and remove users with no activity."""
        for guild_id in list(activity_data.keys()):
            time_threshold = time.time() - (30 * 86400)  # 30 days in seconds

            # Remove old timestamps and users with no messages left
            users_to_remove = []
            for user_id in list(activity_data[guild_id].keys()):
                # Filter timestamps to only include those within the last 30 days
                activity_data[guild_id][user_id] = [ts for ts in activity_data[guild_id][user_id] if ts > time_threshold]
                if not activity_data[guild_id][user_id]:  # If no messages left, mark user for removal
                    users_to_remove.append(user_id)

            # Remove users with no activity
            for user_id in users_to_remove:
                del activity_data[guild_id][user_id]

            # Save cleaned activity data
            save_activity()

    @cleanup_activity.before_loop
    async def before_cleanup_activity(self):
        """Wait until the bot is ready before starting the cleanup task."""
        await self.bot.wait_until_ready()

# Setup function to add the cog to the bot
def setup(bot):
    bot.add_cog(Activity(bot))