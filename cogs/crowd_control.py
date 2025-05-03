import discord
from discord.ext import commands
import json
from datetime import datetime
import os

# Configuration
APPLICATION_CHANNEL_ID = 1361715508805898482  # Channel where applications are posted
APPLICATION_LOG_CHANNEL_ID = 1361727966861590749  # Channel for logging application actions
STAFF_ROLE_ID = 1355278431193137395  # Role that can moderate applications
FURRY_ROLE_ID = 1349842541616562197  # Role to give when approved

class ApplicationModalPart1(discord.ui.Modal):
    def __init__(self):
        super().__init__(title="Fluffy Bakery Application - Part 1")
        self.add_item(discord.ui.InputText(
            label="How did you join the server?",
            placeholder="Who invited you? If you joined via Disboard, say Disboard.",
            style=discord.TextStyle.long,
            required=True
        ))
        self.add_item(discord.ui.InputText(
            label="Tell us about yourself",
            placeholder="Please tell us a bit about yourself and why you want to join.",
            style=discord.TextStyle.long,
            required=True
        ))
        self.add_item(discord.ui.InputText(
            label="Explain the furry fandom",
            placeholder="Explain the furry fandom in your own words.",
            style=discord.TextStyle.long,
            required=True
        ))
        self.add_item(discord.ui.InputText(
            label="Rules Agreement",
            placeholder="Did you read the rules thoroughly and agree to them?",
            style=discord.TextStyle.short,
            required=True
        ))
        self.add_item(discord.ui.InputText(
            label="Describe two rules",
            placeholder="Describe two rules in your own words.",
            style=discord.TextStyle.long,
            required=True
        ))

    async def callback(self, interaction: discord.Interaction):
        # Store part 1 responses
        responses = [child.value for child in self.children]
        
        # Create and send part 2 modal
        modal = ApplicationModalPart2(responses)
        try:
            await interaction.response.send_modal(modal)
        except Exception as e:
            print(f"Error sending part 2 modal: {e}")
            await interaction.response.send_message("There was an error processing your application. Please try again.", ephemeral=True)

class ApplicationModalPart2(discord.ui.Modal):
    def __init__(self, part1_responses):
        super().__init__(title="Fluffy Bakery Application - Part 2")
        self.part1_responses = part1_responses
        self.add_item(discord.ui.InputText(
            label="Discrimination Promise",
            placeholder="Do you promise not to discriminate against sex, ethnicity, religion, race, or self-identity?",
            style=discord.TextStyle.short,
            required=True
        ))
        self.add_item(discord.ui.InputText(
            label="Password",
            placeholder="What is the password found in the guidelines?",
            style=discord.TextStyle.short,
            required=True
        ))

    async def callback(self, interaction: discord.Interaction):
        try:
            # Get the cog instance
            cog = interaction.client.get_cog("CrowdControl")
            if not cog:
                await interaction.response.send_message("Error: CrowdControl cog not found!", ephemeral=True)
                return

            # Combine all responses
            all_responses = self.part1_responses + [child.value for child in self.children]

            # Create application embed
            embed = discord.Embed(
                title="New Application",
                description=f"Application from {interaction.user.mention}",
                color=discord.Color.blue(),
                timestamp=datetime.now()
            )
            embed.set_author(name=str(interaction.user), icon_url=interaction.user.display_avatar.url)
            
            # Add fields for each question
            questions = [
                "How did you join the server?",
                "Tell us about yourself",
                "Explain the furry fandom",
                "Rules Agreement",
                "Describe two rules",
                "Discrimination Promise",
                "Password"
            ]
            
            for question, response in zip(questions, all_responses):
                embed.add_field(name=question, value=response, inline=False)

            # Create view with moderation buttons
            view = ApplicationModerationView(interaction.user.id)

            # Send to application channel
            channel = interaction.guild.get_channel(APPLICATION_CHANNEL_ID)
            if channel:
                message = await channel.send(embed=embed, view=view)
                cog.applications[str(interaction.user.id)] = {
                    "message_id": message.id,
                    "status": "pending",
                    "timestamp": datetime.now().isoformat()
                }
                cog.save_applications()

            await interaction.response.send_message("Your application has been submitted!", ephemeral=True)
        except Exception as e:
            print(f"Error processing application part 2: {e}")
            await interaction.response.send_message("There was an error processing your application. Please try again.", ephemeral=True)

class ApplicationModerationView(discord.ui.View):
    def __init__(self, applicant_id: int):
        super().__init__(timeout=None)
        self.applicant_id = applicant_id

    @discord.ui.button(label="Accept", style=discord.ButtonStyle.green, custom_id="accept_application")
    async def accept(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.handle_moderation(interaction, "accepted")

    @discord.ui.button(label="Deny", style=discord.ButtonStyle.red, custom_id="deny_application")
    async def deny(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.handle_moderation(interaction, "denied")

    @discord.ui.button(label="Kick", style=discord.ButtonStyle.grey, custom_id="kick_applicant")
    async def kick(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.handle_moderation(interaction, "kicked")

    @discord.ui.button(label="Ban", style=discord.ButtonStyle.danger, custom_id="ban_applicant")
    async def ban(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.handle_moderation(interaction, "banned")

    async def handle_moderation(self, interaction: discord.Interaction, action: str):
        # Get the cog instance
        cog = interaction.client.get_cog("CrowdControl")
        if not cog:
            await interaction.response.send_message("Error: CrowdControl cog not found!", ephemeral=True)
            return

        # Check if user has staff role
        if not any(role.id == STAFF_ROLE_ID for role in interaction.user.roles):
            await interaction.response.send_message("You don't have permission to moderate applications!", ephemeral=True)
            return

        # Get the applicant
        applicant = interaction.guild.get_member(self.applicant_id)
        if not applicant:
            await interaction.response.send_message("Applicant not found!", ephemeral=True)
            return

        # Create modal for reason if needed
        if action in ["denied", "kicked", "banned"]:
            modal = ReasonModal(action)
            await interaction.response.send_modal(modal)
            await modal.wait()
            reason = modal.reason.value
        else:
            reason = None
            await interaction.response.defer()

        # Update application status
        cog.applications[str(self.applicant_id)]["status"] = action
        cog.applications[str(self.applicant_id)]["moderator"] = interaction.user.id
        cog.applications[str(self.applicant_id)]["reason"] = reason
        cog.save_applications()

        # Get current time for embeds
        data = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        # Perform action
        if action == "accepted":
            # Add Furry role to accepted applicant
            furry_role = interaction.guild.get_role(FURRY_ROLE_ID)
            if furry_role:
                try:
                    await applicant.add_roles(furry_role)
                    print(f"Added Furry role to {applicant.name}")
                except discord.Forbidden:
                    print(f"Could not add Furry role to {applicant.name} - missing permissions")
                except Exception as e:
                    print(f"Error adding Furry role: {e}")
            else:
                print(f"Furry role not found! ID: {FURRY_ROLE_ID}")
        elif action == "kicked":
            # Create kick embeds
            server_embed = discord.Embed(
                description="------------------------------------------------------",
                color=0x00ff00
            )
            server_embed.set_author(name="Member Kicked:")
            server_embed.add_field(name="Kicked by: ", value=f"{interaction.user.mention}", inline=False)
            server_embed.add_field(name="Kicked: ", value=f"<@{applicant.id}>", inline=False)
            server_embed.add_field(
                name="Reason: ",
                value=f"{reason}\n------------------------------------------------------",
                inline=False
            )
            server_embed.set_footer(
                text=f"Requested by {interaction.user} \a {data}",
                icon_url=interaction.client.user.avatar.url
            )

            user_embed = discord.Embed(
                description="------------------------------------------------------",
                color=0xff0000
            )
            user_embed.set_author(name="You've been Kicked")
            user_embed.add_field(name="Kicked by: ", value=f"{interaction.user.mention}", inline=False)
            user_embed.add_field(name="Kicked in: ", value=f"{interaction.guild.name}", inline=False)
            user_embed.add_field(
                name="Reason: ",
                value=f"{reason}\n------------------------------------------------------",
                inline=False
            )
            user_embed.set_footer(text=f"Kicked at {data}")

            # Send embeds and perform kick
            await interaction.followup.send(embed=server_embed)
            await applicant.send(embed=user_embed)
            await applicant.kick(reason=reason)

        elif action == "banned":
            # Create ban embeds
            server_embed = discord.Embed(
                description="------------------------------------------------------",
                color=0x00ff00
            )
            server_embed.set_author(name="Member Banned:")
            server_embed.add_field(name="Banned by: ", value=f"{interaction.user.mention}", inline=False)
            server_embed.add_field(name="Banned: ", value=f"<@{applicant.id}>", inline=False)
            server_embed.add_field(
                name="Reason: ",
                value=f"{reason}\n------------------------------------------------------",
                inline=False
            )
            server_embed.set_footer(
                text=f"Requested by {interaction.user} \a {data}",
                icon_url=interaction.client.user.avatar.url
            )

            user_embed = discord.Embed(
                description="------------------------------------------------------",
                color=0xff0000
            )
            user_embed.set_author(name="You've been Banned")
            user_embed.add_field(name="Banned by: ", value=f"{interaction.user.mention}", inline=False)
            user_embed.add_field(name="Banned in: ", value=f"{interaction.guild.name}", inline=False)
            user_embed.add_field(
                name="Reason: ",
                value=f"{reason}\n------------------------------------------------------",
                inline=False
            )
            user_embed.set_footer(text=f"Banned at {data}")

            # Send embeds and perform ban
            await interaction.followup.send(embed=server_embed)
            await applicant.send(embed=user_embed)
            await applicant.ban(reason=reason)

        # Update application embed
        embed = interaction.message.embeds[0]
        embed.color = discord.Color.green() if action == "accepted" else discord.Color.red()
        embed.add_field(name="Status", value=action.capitalize(), inline=False)
        if reason:
            embed.add_field(name="Reason", value=reason, inline=False)
        embed.add_field(name="Moderator", value=interaction.user.mention, inline=False)

        # Log the action
        log_channel = interaction.guild.get_channel(APPLICATION_LOG_CHANNEL_ID)
        if log_channel:
            log_embed = discord.Embed(
                title=f"Application {action.capitalize()}",
                description=f"Application from {applicant.mention} was {action} by {interaction.user.mention}",
                color=embed.color,
                timestamp=datetime.now()
            )
            if reason:
                log_embed.add_field(name="Reason", value=reason, inline=False)
            await log_channel.send(embed=log_embed)

        # Disable all buttons
        for child in self.children:
            child.disabled = True
        await interaction.message.edit(embed=embed, view=self)

        # Notify applicant if not banned
        if action == "accepted":
            try:
                await applicant.send("Your application has been accepted! Welcome to the server!")
            except discord.Forbidden:
                pass

class ReasonModal(discord.ui.Modal):
    def __init__(self, action: str):
        super().__init__(title=f"Reason for {action.capitalize()}")
        self.reason = discord.ui.InputText(
            label=f"Reason for {action.capitalize()}",
            placeholder="Enter the reason...",
            style=discord.InputTextStyle.paragraph,
            required=True
        )
        self.add_item(self.reason)

class CrowdControl(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.applications = {}
        self.load_applications()
        self.setup_done = False

    def load_applications(self):
        try:
            with open('applications.json', 'r') as f:
                self.applications = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            self.applications = {}
            self.save_applications()

    def save_applications(self):
        with open('applications.json', 'w') as f:
            json.dump(self.applications, f, indent=4)

    @commands.Cog.listener()
    async def on_ready(self):
        """Called when the bot is ready"""
        if not self.setup_done:
            print("Bot is ready, setting up crowd control system...")
            await self.setup_application_channel()
            self.setup_done = True

    async def setup_application_channel(self):
        """Set up the application embed in the application channel"""
        print(f"Attempting to setup application channel with ID: {APPLICATION_CHANNEL_ID}")
        channel = self.bot.get_channel(APPLICATION_CHANNEL_ID)
        if not channel:
            print(f"Application channel not found! ID: {APPLICATION_CHANNEL_ID}")
            return
        print(f"Found application channel: {channel.name}")

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

        # Create and send the application embed
        try:
            print("Creating application embed...")
            embed = discord.Embed(
                title="🎫 Server Application",
                description="Want to join our server? Click the button below to start your application!",
                color=discord.Color.blue()
            )
            embed.add_field(
                name="How it works",
                value="1. Click the 'Apply' button\n2. Fill out the application form\n3. Wait for staff to review your application\n4. You'll be notified of the decision!",
                inline=False
            )
            embed.set_footer(text="We'll review your application as soon as possible!")

            view = discord.ui.View()
            view.add_item(ApplyButton())

            print("Sending application embed...")
            await channel.send(embed=embed, view=view)
            print("Application embed posted successfully!")
        except Exception as e:
            print(f"Error posting application embed: {e}")
            print(f"Error type: {type(e)}")
            print(f"Error details: {str(e)}")

    @commands.slash_command()
    async def apply(self, ctx):
        """Start the application process"""
        modal = ApplicationModalPart1()
        await ctx.send_modal(modal)

class ApplyButton(discord.ui.Button):
    def __init__(self):
        super().__init__(
            label="Apply",
            style=discord.ButtonStyle.green,
            emoji="📝"
        )

    async def callback(self, interaction: discord.Interaction):
        modal = ApplicationModalPart1()
        await interaction.response.send_modal(modal)