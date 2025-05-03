import discord
from discord.ext import commands, tasks
import asyncio

# Configuration: Replace these with your actual channel IDs
MEMBER_COUNT_CHANNEL_ID = 1361718381069205752  # Replace with your member count channel ID
BOT_COUNT_CHANNEL_ID = 1361717535938052176     # Replace with your bot count channel ID
BOOSTS_COUNT_CHANNEL_ID = 1361718731495178431  # Replace with your boosts count channel ID

class StatsChannels(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.update_stats.start()  # Start the birthday check task

    @commands.slash_command()
    @commands.has_role("STAFF")
    async def force_reload_stats(self, ctx):
        """Force reload all stats channels immediately"""
        await ctx.defer()
        await self.update_stats()
        await ctx.respond("Stats channels have been force reloaded!", ephemeral=True)

    @tasks.loop(minutes=5)  # Update every 5 minutes
    async def update_stats(self):
        # Get the guild (server) - adjust the guild ID if needed
        guild = self.bot.get_guild(1349813029809688616)  # Replace with your guild ID
        if not guild:
            return

        # Update member count
        member_count_channel = guild.get_channel(MEMBER_COUNT_CHANNEL_ID)
        if member_count_channel:
            await member_count_channel.edit(name=f"𝗠𝗘𝗠𝗕𝗘𝗥 𝗖𝗢𝗨𝗡𝗧 - {guild.member_count}")

        # Update bot count
        bot_count = sum(1 for member in guild.members if member.bot)
        bot_count_channel = guild.get_channel(BOT_COUNT_CHANNEL_ID)
        if bot_count_channel:
            await bot_count_channel.edit(name=f"𝗕𝗢𝗧 𝗖𝗢𝗨𝗡𝗧 - {bot_count}")

        # Update boosts count
        boosts_count = guild.premium_subscription_count
        boosts_count_channel = guild.get_channel(BOOSTS_COUNT_CHANNEL_ID)
        if boosts_count_channel:
            await boosts_count_channel.edit(name=f"𝗦𝗘𝗥𝗩𝗘𝗥 𝗕𝗢𝗢𝗦𝗧𝗦 - {boosts_count}")

    @update_stats.before_loop
    async def before_update_stats(self):
        await self.bot.wait_until_ready()

def setup(bot):
    bot.add_cog(StatsChannels(bot))