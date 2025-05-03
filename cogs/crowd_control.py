import discord
from discord.ext import commands
import json
from datetime import datetime

# Configuration
APPLICATION_CHANNEL_ID = 1361715508805898482
APPLICATION_LOG_CHANNEL_ID = 1361727966861590749
STAFF_ROLE_ID = 1355278431193137395
FURRY_ROLE_ID = 1349842541616562197

class ApplicationModal(discord.ui.Modal):
    def __init__(self):
        super().__init__(title="Fluffy Bakery Application")
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
            label="Describe two rules",
            placeholder="Describe two rules in your own words.",
            style=discord.TextStyle.paragraph,
            required=True
        ))
        self.add_item(discord.ui.TextInput(
            label="Discrimination Promise",
            placeholder="Do you promise not to discriminate against sex, ethnicity, religion, race, or self-identity?",
            style=discord.TextStyle.short,
            required=True
        ))
        self.add_item(discord.ui.TextInput(
            label="Password",
            placeholder="What is the password found in the guidelines?",
            style=discord.TextStyle.short,
            required=True
        ))

    async def callback(self, interaction: discord.Interaction):
        cog = interaction.client.get_cog("CrowdControl")
        if not cog:
            await interaction.response.send_message("Error: CrowdControl cog not found!", ephemeral=True)
            return

        embed = discord.Embed(
            title="New Application",
            description=f"Application from {interaction.user.mention}",
            color=discord.Color.blue(),
            timestamp=datetime.now()
        )
        embed.set_author(name=str(interaction.user), icon_url=interaction.user.display_avatar.url)

        # Add responses to embed
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
    async def accept(self, button: discord.ui.Button, interaction: discord.Interaction):
        await self.handle_moderation(interaction, "accepted")

    @discord.ui.button(label="Deny", style=discord.ButtonStyle.red, custom_id="deny_application")
    async def deny(self, button: discord.ui.Button, interaction: discord.Interaction):
        await self.handle_moderation(interaction, "denied")

    @discord.ui.button(label="Kick", style=discord.ButtonStyle.grey, custom_id="kick_applicant")
    async def kick(self, button: discord.ui.Button, interaction: discord.Interaction):
        await self.handle_moderation(interaction, "kicked")

    @discord.ui.button(label="Ban", style=discord.ButtonStyle.danger, custom_id="ban_applicant")
    async def ban(self, button: discord.ui.Button, interaction: discord.Interaction):
        await self.handle_moderation(interaction, "banned")

    async def handle_moderation(self, interaction: discord.Interaction, action: str):
        if not any(role.id == STAFF_ROLE_ID for role in interaction.user.roles):
            await interaction.response.send_message("You don't have permission to moderate applications!", ephemeral=True)
            return

        applicant = interaction.guild.get_member(self.applicant_id)
        if not applicant:
            await interaction.response.send_message("Applicant not found!", ephemeral=True)
            return

        cog = interaction.client.get_cog("CrowdControl")
        if not cog:
            await interaction.response.send_message("Error: CrowdControl cog not found!", ephemeral=True)
            return

        # Get reason if needed
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

        # Handle the action
        if action == "accepted":
            furry_role = interaction.guild.get_role(FURRY_ROLE_ID)
            if furry_role:
                await applicant.add_roles(furry_role)
                await interaction.followup.send(f"Application accepted! Added {furry_role.name} role to {applicant.mention}")
                try:
                    await applicant.send("Your application has been accepted! Welcome to the server!")
                except:
                    pass
        elif action == "kicked":
            await applicant.kick(reason=reason)
            await interaction.followup.send(f"Kicked {applicant.mention}\nReason: {reason}")
        elif action == "banned":
            await applicant.ban(reason=reason)
            await interaction.followup.send(f"Banned {applicant.mention}\nReason: {reason}")
        else:
            await interaction.followup.send(f"Application {action}!")

        # Disable all buttons
        for child in self.children:
            child.disabled = True
        await interaction.message.edit(view=self)

class ReasonModal(discord.ui.Modal):
    def __init__(self, action: str):
        super().__init__(title=f"Reason for {action.capitalize()}")
        self.reason = discord.ui.TextInput(
            label=f"Reason for {action.capitalize()}",
            style=discord.TextStyle.short,
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
        """Register persistent views when the bot starts"""
        # Use add_view with a custom ID pattern for persistent views
        self.bot.add_view(ApplicationModerationView(0))  # Dummy ID for persistent view
        print("CrowdControl cog is ready!")

def setup(bot):
    bot.add_cog(CrowdControl(bot))