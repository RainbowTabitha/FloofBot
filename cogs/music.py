import discord
from discord.ext import commands
import yt_dlp
import asyncio
from collections import deque

class Music(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.queues = {}  # Server ID -> Queue of songs
        self.now_playing = {}  # Server ID -> Current song
        self.voice_clients = {}  # Server ID -> Voice client
        self.song_owners = {}  # Server ID -> User ID of who added the song
        self.music_channels = {}  # Server ID -> Channel ID for music messages

    def get_queue(self, guild_id):
        if guild_id not in self.queues:
            self.queues[guild_id] = deque()
        return self.queues[guild_id]

    def has_dj_role(self, member):
        """Check if a member has the DJ role"""
        return any(role.name.lower() == 'dj' for role in member.roles)

    @commands.slash_command()
    async def play(self, ctx, query: str):
        """Play a song from YouTube URL or search query"""
        if not ctx.author.voice:
            embed = discord.Embed(title="Error", description="You need to be in a voice channel!", color=discord.Color.red())
            await ctx.respond(embed=embed)
            return

        # Store the channel where the command was used
        self.music_channels[ctx.guild.id] = ctx.channel.id

        # Get or create voice client
        if ctx.guild.id not in self.voice_clients:
            self.voice_clients[ctx.guild.id] = await ctx.author.voice.channel.connect()
        elif not self.voice_clients[ctx.guild.id].is_connected():
            self.voice_clients[ctx.guild.id] = await ctx.author.voice.channel.connect()

        # Configure yt-dlp options
        ydl_opts = {
            'format': 'bestaudio/best',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
        }

        embed = discord.Embed(title="Searching", description="Looking for your song...", color=discord.Color.blue())
        message = await ctx.respond(embed=embed)

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                # Search for videos
                search_results = ydl.extract_info(f"ytsearch5:{query}", download=False)['entries']
                
                if not search_results:
                    embed = discord.Embed(title="Error", description="No results found!", color=discord.Color.red())
                    await message.edit_original_response(embed=embed)
                    return

                # Create select menu options
                options = []
                for i, result in enumerate(search_results, 1):
                    title = result['title']
                    duration = result.get('duration', 'Unknown')
                    if isinstance(duration, int):
                        minutes = duration // 60
                        seconds = duration % 60
                        duration = f"{minutes}:{seconds:02d}"
                    options.append(discord.SelectOption(
                        label=f"{i}. {title[:100]}",  # Discord has a 100 char limit for labels
                        value=str(i-1),
                        description=f"Duration: {duration}"
                    ))

                # Create select menu
                select = discord.ui.Select(
                    placeholder="Choose a song",
                    options=options
                )

                # Create view
                view = discord.ui.View()
                view.add_item(select)

                # Update message with select menu
                embed = discord.Embed(title="Search Results", description="Please select a song:", color=discord.Color.blue())
                await message.edit_original_response(embed=embed, view=view)

                # Wait for selection
                def check(interaction):
                    return interaction.user == ctx.author and interaction.data['component_type'] == 3

                try:
                    interaction = await self.bot.wait_for("interaction", check=check, timeout=60.0)
                    selected_index = int(interaction.data['values'][0])
                    selected_video = search_results[selected_index]
                    
                    # Get the video URL
                    info = ydl.extract_info(selected_video['id'], download=False)
                    title = info['title']
                    url2 = info['url']

                    # Add to queue
                    queue = self.get_queue(ctx.guild.id)
                    queue.append((title, url2))
                    # Store who added the song
                    if ctx.guild.id not in self.song_owners:
                        self.song_owners[ctx.guild.id] = []
                    self.song_owners[ctx.guild.id].append(ctx.author.id)

                    if len(queue) == 1:  # If this is the first song
                        embed = discord.Embed(title="Added to Queue", description=f"Added {title} and starting playback!", color=discord.Color.green())
                        await message.edit_original_response(embed=embed, view=None)
                        await self.play_next(ctx.guild)
                    else:
                        embed = discord.Embed(title="Added to Queue", description=title, color=discord.Color.green())
                        await message.edit_original_response(embed=embed, view=None)

                except asyncio.TimeoutError:
                    embed = discord.Embed(title="Timeout", description="You took too long to select a song!", color=discord.Color.red())
                    await message.edit_original_response(embed=embed, view=None)
                    return

        except Exception as e:
            embed = discord.Embed(title="Error", description=str(e), color=discord.Color.red())
            await message.edit_original_response(embed=embed, view=None)

    async def play_next(self, guild):
        queue = self.get_queue(guild.id)
        if not queue:
            return

        title, url = queue[0]
        self.now_playing[guild.id] = title

        try:
            self.voice_clients[guild.id].play(
                discord.FFmpegPCMAudio(url),
                after=lambda e: asyncio.run_coroutine_threadsafe(
                    self.play_next(guild), self.bot.loop
                )
            )
            if guild.id in self.music_channels:
                channel = guild.get_channel(self.music_channels[guild.id])
                if channel:
                    embed = discord.Embed(title="Now Playing", description=title, color=discord.Color.blue())
                    await channel.send(embed=embed)
        except Exception as e:
            if guild.id in self.music_channels:
                channel = guild.get_channel(self.music_channels[guild.id])
                if channel:
                    embed = discord.Embed(title="Error", description=f"Error playing song: {str(e)}", color=discord.Color.red())
                    await channel.send(embed=embed)
            queue.popleft()
            if guild.id in self.song_owners and self.song_owners[guild.id]:
                self.song_owners[guild.id].pop(0)
            await self.play_next(guild)

    @commands.slash_command()
    async def skip(self, ctx):
        """Skip the current song"""
        if not ctx.guild.id in self.voice_clients or not self.voice_clients[ctx.guild.id].is_playing():
            embed = discord.Embed(title="Error", description="Nothing is playing!", color=discord.Color.red())
            await ctx.respond(embed=embed)
            return

        # Check if user has DJ role or is the song owner
        if not self.has_dj_role(ctx.author):
            if ctx.guild.id not in self.song_owners or not self.song_owners[ctx.guild.id]:
                embed = discord.Embed(title="Permission Denied", description="You need the DJ role to skip songs!", color=discord.Color.red())
                await ctx.respond(embed=embed)
                return
            if self.song_owners[ctx.guild.id][0] != ctx.author.id:
                embed = discord.Embed(title="Permission Denied", description="You can only skip your own songs unless you have the DJ role!", color=discord.Color.red())
                await ctx.respond(embed=embed)
                return

        self.voice_clients[ctx.guild.id].stop()
        if ctx.guild.id in self.song_owners and self.song_owners[ctx.guild.id]:
            self.song_owners[ctx.guild.id].pop(0)
            embed = discord.Embed(title="Skipped", description="Current song has been skipped!", color=discord.Color.green())
            await ctx.respond(embed=embed)

    @commands.slash_command()
    async def stop(self, ctx):
        """Stop playing and clear the queue"""
        if not self.has_dj_role(ctx.author):
            embed = discord.Embed(title="Permission Denied", description="You need the DJ role to stop playback!", color=discord.Color.red())
            await ctx.respond(embed=embed)
            return

        if ctx.guild.id in self.voice_clients:
            self.voice_clients[ctx.guild.id].stop()
            self.queues[ctx.guild.id] = deque()
            self.song_owners[ctx.guild.id] = []
            embed = discord.Embed(title="Stopped", description="Playback stopped and queue cleared!", color=discord.Color.green())
            await ctx.respond(embed=embed)
        else:
            embed = discord.Embed(title="Error", description="Nothing is playing!", color=discord.Color.red())
            await ctx.respond(embed=embed)

    @commands.slash_command()
    async def queue(self, ctx):
        """Show the current queue"""
        queue = self.get_queue(ctx.guild.id)
        if not queue:
            embed = discord.Embed(title="Queue", description="The queue is empty!", color=discord.Color.blue())
            await ctx.respond(embed=embed)
            return

        embed = discord.Embed(title="Music Queue", color=discord.Color.blue())
        for i, (title, _) in enumerate(queue, 1):
            embed.add_field(name=f"{i}.", value=title, inline=False)

        await ctx.respond(embed=embed)

    @commands.slash_command()
    async def leave(self, ctx):
        """Make the bot leave the voice channel"""
        if not self.has_dj_role(ctx.author):
            embed = discord.Embed(title="Permission Denied", description="You need the DJ role to make the bot leave!", color=discord.Color.red())
            await ctx.respond(embed=embed)
            return

        if ctx.guild.id in self.voice_clients:
            await self.voice_clients[ctx.guild.id].disconnect()
            del self.voice_clients[ctx.guild.id]
            if ctx.guild.id in self.song_owners:
                del self.song_owners[ctx.guild.id]
            embed = discord.Embed(title="Left Channel", description="I've left the voice channel!", color=discord.Color.green())
            await ctx.respond(embed=embed)
        else:
            embed = discord.Embed(title="Error", description="I'm not in a voice channel!", color=discord.Color.red())
            await ctx.respond(embed=embed)

async def setup(bot):
    await bot.add_cog(Music(bot)) 