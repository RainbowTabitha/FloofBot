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
STAFF_ROLE_ID = 1355278431193137395
TICKET_LOG_CHANNEL = 1361718840488104157
TICKET_CHANNEL_ID = 1361717310166929640
STAFF_NOTIFICATION_CHANNEL = 1361694388346163360

class TicketButton(discord.ui.Button):
    def __init__(self):
        super().__init__(
            label="Create Ticket",
            style=discord.ButtonStyle.green,
            emoji="🎫"
        )

    async def callback(self, interaction: discord.Interaction):
        # Get the cog instance
        cog = interaction.client.get_cog("Tickets")
        if not cog:
            await interaction.response.send_message("Error: Tickets cog not found!", ephemeral=True)
            return

        # Check if user already has an open ticket
        user_id = str(interaction.user.id)
        if user_id in cog.ticket_data:
            ticket = cog.ticket_data[user_id]
            if ticket.get("open", False):
                # Verify the channel still exists
                channel = interaction.guild.get_channel(ticket["channel_id"])
                if channel:
                    await interaction.response.send_message("You already have an open ticket!", ephemeral=True)
                    return
                else:
                    # Channel doesn't exist, clean up the data
                    del cog.ticket_data[user_id]
                    cog.save_ticket_data()

        # Create ticket channel
        category = interaction.guild.get_channel(TICKET_CATEGORY_ID)
        if not category:
            await interaction.response.send_message("Ticket category not found!", ephemeral=True)
            return

        # Get staff role
        staff_role = interaction.guild.get_role(STAFF_ROLE_ID)
        if not staff_role:
            await interaction.response.send_message("Staff role not found!", ephemeral=True)
            return

        # Create ticket channel
        overwrites = {
            interaction.guild.default_role: discord.PermissionOverwrite(read_messages=False),
            interaction.user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            interaction.guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            staff_role: discord.PermissionOverwrite(read_messages=True, send_messages=True)
        }

        ticket_channel = await interaction.guild.create_text_channel(
            f"ticket-{interaction.user.name}",
            category=category,
            overwrites=overwrites
        )

        # Store ticket data
        cog.ticket_data[user_id] = {
            "channel_id": ticket_channel.id,
            "open": True,
            "created_at": datetime.now().isoformat(),
            "reason": "Created via button"
        }
        cog.save_ticket_data()

        # Send initial message with delete button
        embed = discord.Embed(
            title="Ticket Created",
            description="Please describe your issue in this channel. Staff will assist you shortly!",
            color=discord.Color.green()
        )
        embed.add_field(name="User", value=interaction.user.mention)
        embed.add_field(name="Created At", value=datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        embed.set_footer(text="Click the button below to close this ticket")

        view = discord.ui.View()
        view.add_item(DeleteTicketButton())

        await ticket_channel.send(embed=embed, view=view)
        await interaction.response.send_message(f"Ticket created! {ticket_channel.mention}", ephemeral=True)

        # Ping staff in notification channel
        notification_channel = interaction.guild.get_channel(STAFF_NOTIFICATION_CHANNEL)
        if notification_channel:
            staff_ping = f"{staff_role.mention} New ticket created by {interaction.user.mention} in {ticket_channel.mention}"
            await notification_channel.send(staff_ping)

class DeleteTicketButton(discord.ui.Button):
    def __init__(self):
        super().__init__(
            label="Begone, Mods",
            style=discord.ButtonStyle.red,
            emoji="❌",
            custom_id="delete_ticket_button"
        )

    async def callback(self, interaction: discord.Interaction):
        # Get the cog instance
        cog = interaction.client.get_cog("Tickets")
        if not cog:
            await interaction.response.send_message("Error: Tickets cog not found!", ephemeral=True)
            return

        # Create a context from the interaction
        ctx = await interaction.client.get_context(interaction.message)
        ctx.author = interaction.user
        ctx.channel = interaction.channel

        # Close the ticket
        await cog.close(ctx)

class TicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(DeleteTicketButton())

class Tickets(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.ticket_data = {}
        self.load_ticket_data()
        self.setup_done = False
        
        # Create logs directory if it doesn't exist
        os.makedirs(TICKET_LOGS_DIR, exist_ok=True)
        print("Tickets cog initialized!")

    @commands.Cog.listener()
    async def on_ready(self):
        """Called when the bot is ready"""
        if not self.setup_done:
            print("Bot is ready, setting up ticket system...")
            self.bot.add_view(TicketView())
            await self.cleanup_stale_tickets()
            await self.setup_ticket_channel()
            self.setup_done = True

    async def cleanup_stale_tickets(self):
        """Clean up any stale ticket data where channels no longer exist"""
        stale_tickets = []
        for user_id, data in self.ticket_data.items():
            if data.get("open", False):
                # Get the guild and channel
                for guild in self.bot.guilds:
                    channel = guild.get_channel(data["channel_id"])
                    if not channel:
                        stale_tickets.append(user_id)
                        break

        # Remove stale tickets
        for user_id in stale_tickets:
            del self.ticket_data[user_id]
        
        if stale_tickets:
            self.save_ticket_data()
            print(f"Cleaned up {len(stale_tickets)} stale tickets")

    def load_ticket_data(self):
        try:
            with open('tickets.json', 'r') as f:
                self.ticket_data = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            self.ticket_data = {}
            self.save_ticket_data()  # Create the file if it doesn't exist

    def save_ticket_data(self):
        with open('tickets.json', 'w') as f:
            json.dump(self.ticket_data, f, indent=4)

    async def setup_ticket_channel(self):
        """Set up the ticket creation embed in the ticket channel"""
        print(f"Attempting to setup ticket channel with ID: {TICKET_CHANNEL_ID}")
        channel = self.bot.get_channel(TICKET_CHANNEL_ID)
        if not channel:
            print(f"Ticket channel not found! ID: {TICKET_CHANNEL_ID}")
            return
        print(f"Found ticket channel: {channel.name}")

        # Delete any existing messages in the channel
        try:
            messages = [message async for message in channel.history(limit=None)]
            if messages:  # Only try to delete if there are messages
                print(f"Found {len(messages)} messages to clear")
                await channel.purge(limit=None)
                print(f"Cleared {len(messages)} messages from application channel")
            else:
                print("No messages to clear in application channel")
        except discord.Forbidden:
            print("No permission to delete messages in application channel!")
            return
        except Exception as e:
            print(f"Error clearing messages: {e}")
            # Continue anyway, we'll try to post the embed

        # Create and send the ticket creation embed
        try:
            print("Creating ticket creation embed...")
            embed = discord.Embed(
                title="🎫 Support Tickets",
                description="Is some fur is ruining your party? Need help with something?\nClick the button below to create a support ticket!",
                color=discord.Color.blue()
            )
            embed.add_field(
                name="How it works",
                value="1. Click the 'Create Ticket' button\n2. A private channel will be created for you and staff\n3. Describe your issue in the channel\n4. Staff will assist you as soon as possible!",
                inline=False
            )
            embed.set_footer(text="We'll get back to you as soon as we can!")

            view = discord.ui.View(timeout=None)
            view.add_item(TicketButton())

            print("Sending ticket creation embed...")
            await channel.send(embed=embed, view=view)
            print("Ticket creation embed posted successfully!")
        except Exception as e:
            print(f"Error posting ticket embed: {e}")
            print(f"Error type: {type(e)}")
            print(f"Error details: {str(e)}")

    @commands.command()
    @commands.has_role("STAFF")
    async def close(self, ctx_or_interaction):
        """Close the current ticket"""
        # Handle both command and interaction contexts
        if isinstance(ctx_or_interaction, discord.Interaction):
            channel = ctx_or_interaction.channel
            user = ctx_or_interaction.user
            send_message = ctx_or_interaction.response.send_message
        else:
            channel = ctx_or_interaction.channel
            user = ctx_or_interaction.author
            send_message = ctx_or_interaction.send

        # Find the ticket
        ticket = None
        for user_id, data in self.ticket_data.items():
            if data["channel_id"] == channel.id and data["open"]:
                ticket = data
                ticket_user_id = user_id
                break

        if not ticket:
            await send_message("This is not a valid ticket channel!", ephemeral=True)
            return

        # Create transcript
        transcript_path = await self.create_transcript(channel, ticket_user_id, ticket["reason"])

        # Close the ticket
        self.ticket_data[ticket_user_id]["open"] = False
        self.save_ticket_data()

        # Send closing message
        await send_message("Ticket closed! Creating transcript...")

        # Send transcript to log channel
        log_channel = self.bot.get_channel(TICKET_LOG_CHANNEL)
        if log_channel:
            with open(transcript_path, 'rb') as f:
                await log_channel.send(
                    f"Transcript for ticket {channel.name}",
                    file=discord.File(f, filename=f"transcript_{channel.name}.html")
                )

        # Send transcript to user
        ticket_user = self.bot.get_user(int(ticket_user_id))
        if ticket_user:
            try:
                with open(transcript_path, 'rb') as f:
                    await ticket_user.send(
                        "Here's the transcript of your ticket. Please open it in a web browser to view it properly.",
                        file=discord.File(f, filename=f"transcript_{channel.name}.html")
                    )
            except discord.Forbidden:
                await log_channel.send(f"Could not DM transcript to user {ticket_user.mention} (DMs are closed).")

        await asyncio.sleep(2)
        await channel.delete()

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

        return filename