#***************************************************************************#
# FloofBot
#***************************************************************************#

import discord
from discord.ext import commands, tasks
import json
import os
from datetime import datetime
import pytz  # Import pytz for timezone handling
import asyncio
import requests
import io

# File to store reference image data
REFERENCE_FILE = 'reference_images.json'

# Load or initialize reference image data
if os.path.exists(REFERENCE_FILE):
    with open(REFERENCE_FILE, 'r') as f:
        reference_data = json.load(f)
else:
    reference_data = {}

# Function to save reference image data
def save_references():
    with open(REFERENCE_FILE, 'w') as f:
        json.dump(reference_data, f, indent=4)

# Replace hardcoded API key with loading from local file
try:
    with open('imgbb.key', 'r') as f:
        IMGBB_API_KEY = f.read().strip()
except FileNotFoundError:
    IMGBB_API_KEY = 'YOUR_IMGBB_API_KEY'  # Fallback if file not found

class ReferenceImages(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.slash_command()
    async def set_ref(self, ctx, character_name: str = "default"):
        """Set a reference image for a character. Upload an image in DM."""
        await ctx.author.send("Please upload an image for your reference.")
        def check(message):
            return message.author == ctx.author and message.channel == ctx.author.dm_channel and len(message.attachments) > 0
        try:
            message = await self.bot.wait_for("message", check=check, timeout=60.0)
            image_url = message.attachments[0].url
            # Download the image
            response = requests.get(image_url)
            if response.status_code != 200:
                await ctx.author.send("Failed to download the image.")
                return
            image_data = response.content
            # Upload to imgbb
            files = {'image': ('image.png', io.BytesIO(image_data))}
            payload = {'key': IMGBB_API_KEY}
            r = requests.post('https://api.imgbb.com/1/upload', files=files, data=payload)
            if r.status_code != 200:
                await ctx.author.send("Failed to upload the image to imgbb.")
                return
            imgbb_url = r.json()['data']['url']
            # Store the URL in the JSON file
            user_id = str(ctx.author.id)
            if user_id not in reference_data:
                reference_data[user_id] = {}
            reference_data[user_id][character_name] = imgbb_url
            save_references()
            await ctx.author.send(f"Reference image for {character_name} has been set!")
        except Exception as e:
            await ctx.author.send(f"An error occurred: {e}")

    @commands.slash_command()
    async def ref(self, ctx, character_name: str = "default"):
        """Retrieve the reference image for a character."""
        user_id = str(ctx.author.id)
        if user_id in reference_data and character_name in reference_data[user_id]:
            img_url = reference_data[user_id][character_name]
            embed = discord.Embed(title=f"Reference for {character_name}", color=discord.Color.blue())
            embed.set_image(url=img_url)
            await ctx.respond(embed=embed)
        else:
            await ctx.respond(f"No reference image found for {character_name}.")

# Add the cog to the bot
async def setup(bot):
    await bot.add_cog(ReferenceImages(bot))