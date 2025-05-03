import discord
from discord.ext import commands
import json
from datetime import datetime
import os

# Configuration
APPLICATION_CHANNEL_ID = 1361715508805898482  # Channel where applications are posted
APPLICATION_LOG_CHANNEL_ID = 1361727966861590749  # Channel for logging application actions
STAFF_ROLE_ID = 1355278431193137395  # Role that can moderate applications

class ApplicationModal(discord.ui.Modal, title="FloofBot Application"):
    def __init__(self):
        super().__init__()
        self.add_item(discord.ui.TextInput(
            label="How did you join the server?",
            placeholder="Who invited you? If you joined via Disboard, say Disboard.",
            style=discord.TextStyle.paragraph,
            required=True
        ))
        self.add_item(discord.ui.TextInput(
            label="Tell us about yourself",
            placeholder="Please tell us a bit about yourself and why you want to join.",
            style=discord.TextStyle.paragraph,
            required=True
        ))
        self.add_item(discord.ui.TextInput(
            label="Explain the furry fandom",
            placeholder="Explain the furry fandom in your own words.",
            style=discord.TextStyle.paragraph,
            required=True
        ))
        self.add_item(discord.ui.TextInput(
            label="Rules Agreement",
            placeholder="Did you read the rules thoroughly and agree to them?",
            required=True
        ))
        self.add_item(discord.ui.TextInput(
            label="Describe two rules",
            placeholder="Describe two rules in your own words.",
            style=discord.TextStyle.paragraph,
            required=True
        ))
        self.add_item(discord.ui.TextInput(
            label="Discrimination Promise",
            placeholder="Do you promise not to discriminate against sex, ethnicity, religion, race, or self-identity?",
            required=True
        ))
        self.add_item(discord.ui.TextInput(
            label="Password",
            placeholder="What is the password found in the guidelines?",
            required=True
        ))

    async def on_submit(self, interaction: discord.Interaction):
        # Get the cog instance
        cog = interaction.client.get_cog("CrowdControl")
        if not cog:
            await interaction.response.send_message("Error: CrowdControl cog not found!", ephemeral=True)
            return

        # Create application embed
        embed = discord.Embed(
            title="New Application",
            description=f"Application from {interaction.user.mention}",
            color=discord.Color.blue(),
            timestamp=datetime.now()
        )
        embed.set_author(name=str(interaction.user), icon_url=interaction.user.display_avatar.url)
        
        # Add fields for each question
        for child in self.children:
            embed.add_field(name=child.label, value=child.value, inline=False)

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
            # Add member role or whatever you want to do for accepted applicants
            pass
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

class ReasonModal(discord.ui.Modal, title="Reason for Action"):
    def __init__(self, action: str):
        super().__init__()
        self.reason = discord.ui.TextInput(
            label=f"Reason for {action.capitalize()}",
            placeholder="Enter the reason...",
            style=discord.TextStyle.paragraph,
            required=True
        )
        self.add_item(self.reason)

class CrowdControl(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.applications = {}
        self.load_applications()

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

    @commands.slash_command()
    async def apply(self, ctx):
        """Start the application process"""
        modal = ApplicationModal()
        await ctx.send_modal(modal)

    @commands.Cog.listener()
    async def on_ready(self):
        # Register persistent views
        self.bot.add_view(ApplicationModerationView(0))  # Dummy ID for persistent view

async def setup(bot):
    await bot.add_cog(CrowdControl(bot)) 