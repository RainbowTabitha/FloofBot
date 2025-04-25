#***************************************************************************#
# FloofBot
#***************************************************************************#


import discord
from PIL import Image
from datetime import datetime
from discord.ext import commands
import aiohttp
import io

class Moderation(commands.Cog):

    """Cog for Base commands"""

    def __init__(self, bot):
        self.bot = bot

    @commands.slash_command(pass_context=True)
    @commands.has_role("STAFF")
    async def ban(self, ctx, user: discord.Member, message):
        author = ctx.author
        reason = message
        server = ctx.guild.name
        data = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        embed = discord.Embed(
            description="------------------------------------------------------",
            color=0x00ff00)
        embed.set_author(name="Member Banned:")
        embed.add_field(
            name="Banned by: ", value="{}".format(author.mention), inline=False)
        embed.add_field(
            name="Banned: ", value="<@{}>".format(user.id), inline=False)
        embed.add_field(
            name="Reason: ",
            value="{}\n------------------------------------------------------".
            format(message),
            inline=False)
        embed.set_footer(
            text="Requested by {} \a {}".format(author, data),
            icon_url=self.bot.user.avatar.url)
        await ctx.respond(embed=embed)
        embed = discord.Embed(
            description="------------------------------------------------------",
            color=0xff0000)
        embed.set_author(name="You've been Banned")
        embed.add_field(
            name="Banned by: ", value="{}".format(author.mention), inline=False)
        embed.add_field(
            name="Banned in: ", value="{}".format(server), inline=False)
        embed.add_field(
            name="Reason: ",
            value="{}\n------------------------------------------------------".
            format(message),
            inline=False)
        embed.set_footer(text="Banned at {}".format(data))
        await user.send(embed=embed)
        await ctx.guild.ban(user, reason=reason)
    
    @commands.slash_command(pass_context=True)
    @commands.has_role("STAFF")
    async def kick(self, ctx, user: discord.Member, message):
        author = ctx.author
        reason = message
        server = ctx.guild.name
        data = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        embed = discord.Embed(
            description="------------------------------------------------------",
            color=0x00ff00)
        embed.set_author(name="Member Kicked:")
        embed.add_field(
            name="Kicked by: ", value="{}".format(author.mention), inline=False)
        embed.add_field(
            name="Kicked: ", value="<@{}>".format(user.id), inline=False)
        embed.add_field(
            name="Kicked: ",
            value="{}\n------------------------------------------------------".
            format(message),
            inline=False)
        embed.set_footer(
            text="Requested by {} \a {}".format(author, data),
            icon_url=self.bot.user.avatar.url)
        await ctx.respond(embed=embed)
        embed = discord.Embed(
            description="------------------------------------------------------",
            color=0xff0000)
        embed.set_author(name="You've been Kicked")
        embed.add_field(
            name="Kicked by: ", value="{}".format(author.mention), inline=False)
        embed.add_field(
            name="Kicked in: ", value="{}".format(server), inline=False)
        embed.add_field(
            name="Reason: ",
            value="{}\n------------------------------------------------------".
            format(message),
            inline=False)
        embed.set_footer(text="Kicked at {}".format(data))
        await user.send(embed=embed)
        await ctx.guild.kick(user, reason=reason)

    @commands.slash_command()
    @commands.has_role("STAFF")
    async def lock(self, ctx):
        """Locks the current channel to prevent messages."""
        channel = ctx.channel
        await channel.set_permissions(ctx.guild.default_role, send_messages=False)

        embed = discord.Embed(
            title="Channel Locked",
            description="This channel has been locked to prevent further messages.",
            color=0xff0000
        )
        await ctx.respond(embed=embed)

    @commands.slash_command()
    @commands.has_role("STAFF")
    async def unlock(self, ctx):
        """Unlocks the current channel to allow messages."""
        channel = ctx.channel
        await channel.set_permissions(ctx.guild.default_role, send_messages=True)
        embed = discord.Embed(
            title="Channel Unlocked",
            description="This channel has been unlocked and messages can be sent again.",
            color=0x00ff00
        )
        await ctx.respond(embed=embed)

def setup(bot):
    bot.add_cog(Moderation(bot))