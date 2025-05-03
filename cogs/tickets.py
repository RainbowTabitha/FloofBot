import discord
from discord.ext import commands
import os
import json
from datetime import datetime
import asyncio
import html
import re

# Configuration
TICKET_CATEGORY_ID = 1367688975828914236
TICKET_LOGS_DIR = "staff-logs/tickets"
TICKET_CHANNEL_ID = 1361717310166929640

class TicketButton(discord.ui.Button):
    def __init__(self):
        super().__init__(
            label="Create Ticket",
            style=discord.ButtonStyle.green,
            emoji="🎫"
        )

    async def callback(self, interaction: discord.Interaction):
        # Create a modal for ticket reason
        modal = TicketModal()
        await interaction.response.send_modal(modal)

class TicketModal(discord.ui.Modal, title="Create a Support Ticket"):
    reason = discord.ui.TextInput(
        label="Reason for ticket",
        placeholder="Please describe why you're creating this ticket...",
        style=discord.TextStyle.paragraph,
        required=True
    )

    async def on_submit(self, interaction: discord.Interaction):
        # Get the cog instance
        cog = interaction.client.get_cog("Tickets")
        if not cog:
            await interaction.response.send_message("Error: Tickets cog not found!", ephemeral=True)
            return

        # Create the ticket
        ctx = await interaction.client.get_context(interaction)
        await cog.ticket(ctx, self.reason.value)

class DeleteTicketButton(discord.ui.Button):
    def __init__(self):
        super().__init__(
            label="Begone, Mods",
            style=discord.ButtonStyle.red,
            emoji="❌"
        )

    async def callback(self, interaction: discord.Interaction):
        # Get the cog instance
        cog = interaction.client.get_cog("Tickets")
        if not cog:
            await interaction.response.send_message("Error: Tickets cog not found!", ephemeral=True)
            return

        # Close the ticket
        ctx = await interaction.client.get_context(interaction)
        await cog.close(ctx)

class Tickets(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.ticket_data = {}
        self.load_ticket_data()
        
        # Create logs directory if it doesn't exist
        os.makedirs(TICKET_LOGS_DIR, exist_ok=True)

    def load_ticket_data(self):
        try:
            with open('tickets.json', 'r') as f:
                self.ticket_data = json.load(f)
        except FileNotFoundError:
            self.ticket_data = {}

    def save_ticket_data(self):
        with open('tickets.json', 'w') as f:
            json.dump(self.ticket_data, f, indent=4)

    @commands.slash_command()
    @commands.has_role("STAFF")
    async def setup_tickets(self, ctx):
        """Set up the ticket creation embed"""
        embed = discord.Embed(
            title="🎫 Support Tickets",
            description="Is some fur is ruining your party? Need help with something?\nClick the button below to create a support ticket!",
            color=discord.Color.blue()
        )
        embed.add_field(
            name="How it works",
            value="1. Click the 'Create Ticket' button\n2. Enter your reason for creating the ticket\n3. A private channel will be created for you and staff\n4. Staff will assist you as soon as possible!",
            inline=False
        )
        embed.set_footer(text="We'll get back to you as soon as we can!")

        view = discord.ui.View()
        view.add_item(TicketButton())

        await ctx.send(embed=embed, view=view)

    @commands.slash_command()
    async def ticket(self, ctx, reason: str):
        """Create a new support ticket"""
        # Check if user already has an open ticket
        if str(ctx.author.id) in self.ticket_data and self.ticket_data[str(ctx.author.id)]["open"]:
            await ctx.respond("You already have an open ticket!", ephemeral=True)
            return

        # Create ticket channel
        category = ctx.guild.get_channel(TICKET_CATEGORY_ID)
        if not category:
            await ctx.respond("Ticket category not found!", ephemeral=True)
            return

        # Create ticket channel
        overwrites = {
            ctx.guild.default_role: discord.PermissionOverwrite(read_messages=False),
            ctx.author: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            ctx.guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            ctx.guild.get_role("STAFF"): discord.PermissionOverwrite(read_messages=True, send_messages=True)
        }

        ticket_channel = await ctx.guild.create_text_channel(
            f"ticket-{ctx.author.name}",
            category=category,
            overwrites=overwrites
        )

        # Store ticket data
        self.ticket_data[str(ctx.author.id)] = {
            "channel_id": ticket_channel.id,
            "open": True,
            "created_at": datetime.now().isoformat(),
            "reason": reason
        }
        self.save_ticket_data()

        # Send initial message with delete button
        embed = discord.Embed(
            title="Ticket Created",
            description=f"Reason: {reason}",
            color=discord.Color.green()
        )
        embed.add_field(name="User", value=ctx.author.mention)
        embed.add_field(name="Created At", value=datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        embed.set_footer(text="Click the button below to close this ticket")

        view = discord.ui.View()
        view.add_item(DeleteTicketButton())

        await ticket_channel.send(embed=embed, view=view)
        await ctx.respond(f"Ticket created! {ticket_channel.mention}", ephemeral=True)

    @commands.slash_command()
    @commands.has_role("STAFF")
    async def close(self, ctx):
        """Close the current ticket"""
        # Find the ticket
        ticket = None
        for user_id, data in self.ticket_data.items():
            if data["channel_id"] == ctx.channel.id and data["open"]:
                ticket = data
                ticket_user_id = user_id
                break

        if not ticket:
            await ctx.respond("This is not a valid ticket channel!", ephemeral=True)
            return

        # Create transcript
        await self.create_transcript(ctx.channel, ticket_user_id, ticket["reason"])

        # Close the ticket
        self.ticket_data[ticket_user_id]["open"] = False
        self.save_ticket_data()

        # Send closing message
        await ctx.respond("Ticket closed! Creating transcript...")
        await asyncio.sleep(2)
        await ctx.channel.delete()

    async def create_transcript(self, channel, user_id, reason):
        # Get all messages
        messages = []
        async for message in channel.history(limit=None, oldest_first=True):
            messages.append(message)

        # Create HTML transcript
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Ticket Transcript - {channel.name}</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                .message {{ margin: 10px 0; padding: 10px; border-radius: 5px; }}
                .user {{ font-weight: bold; }}
                .timestamp {{ color: #666; font-size: 0.8em; }}
                .content {{ margin-top: 5px; }}
                .embed {{ background: #2f3136; padding: 10px; border-radius: 5px; margin: 5px 0; }}
                .embed-title {{ color: #fff; font-weight: bold; }}
                .embed-description {{ color: #dcddde; }}
                .embed-field {{ margin: 5px 0; }}
                .embed-field-name {{ color: #fff; font-weight: bold; }}
                .embed-field-value {{ color: #dcddde; }}
            </style>
        </head>
        <body>
            <h1>Ticket Transcript</h1>
            <p><strong>Channel:</strong> {channel.name}</p>
            <p><strong>User ID:</strong> {user_id}</p>
            <p><strong>Reason:</strong> {reason}</p>
            <p><strong>Created:</strong> {self.ticket_data[user_id]['created_at']}</p>
            <hr>
        """

        for message in messages:
            # Escape HTML in content
            content = html.escape(message.content)
            
            # Convert mentions to readable text
            content = re.sub(r'<@!?(\d+)>', lambda m: f'@{self.bot.get_user(int(m.group(1))).name}', content)
            content = re.sub(r'<#(\d+)>', lambda m: f'#{self.bot.get_channel(int(m.group(1))).name}', content)
            content = re.sub(r'<@&(\d+)>', lambda m: f'@{message.guild.get_role(int(m.group(1))).name}', content)

            html_content += f"""
            <div class="message">
                <div class="user">{message.author.name}</div>
                <div class="timestamp">{message.created_at.strftime('%Y-%m-%d %H:%M:%S')}</div>
                <div class="content">{content}</div>
            """

            # Handle embeds
            for embed in message.embeds:
                html_content += '<div class="embed">'
                if embed.title:
                    html_content += f'<div class="embed-title">{html.escape(embed.title)}</div>'
                if embed.description:
                    html_content += f'<div class="embed-description">{html.escape(embed.description)}</div>'
                for field in embed.fields:
                    html_content += f'''
                    <div class="embed-field">
                        <div class="embed-field-name">{html.escape(field.name)}</div>
                        <div class="embed-field-value">{html.escape(field.value)}</div>
                    </div>
                    '''
                html_content += '</div>'

            # Handle attachments
            for attachment in message.attachments:
                html_content += f'<div class="attachment"><a href="{attachment.url}">{attachment.filename}</a></div>'

            html_content += '</div>'

        html_content += """
        </body>
        </html>
        """

        # Save transcript
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{TICKET_LOGS_DIR}/ticket_{channel.name}_{timestamp}.html"
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(html_content)

        # Post transcript to logs channel
        logs_channel = self.bot.get_channel(1361718840488104157)
        if logs_channel:
            with open(filename, 'rb') as f:
                await logs_channel.send(
                    f"Transcript for ticket {channel.name}",
                    file=discord.File(f, filename=f"transcript_{channel.name}_{timestamp}.html")
                )