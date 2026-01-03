import discord
from discord.ext import commands
from discord import app_commands
import json
import os
from dotenv import load_dotenv
from flask import Flask
from threading import Thread

# ================= KEEP ALIVE =================
app = Flask(__name__)

@app.route("/")
def home():
    return "Ticket bot is running"

def run():
    app.run(host="0.0.0.0", port=8080)

Thread(target=run).start()

# ================= ENV =================
load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")

# ================= CONFIG =================
DATA_FILE = "ticket_data.json"

# ================= INTENTS =================
intents = discord.Intents.default()
intents.guilds = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

# ================= DATA HANDLING =================
def load_data():
    if not os.path.exists(DATA_FILE):
        return {
            "ticket_count": 0,
            "support_role": None,
            "panel_channel_id": None,
            "panel_message_id": None
        }
    with open(DATA_FILE, "r") as f:
        return json.load(f)

def save_data():
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=4)

data = load_data()

# ================= READY =================
@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f"✅ Logged in as {bot.user}")

# ================= CREATE TICKET VIEW =================
class TicketCreateView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Create Ticket", emoji="🎫", style=discord.ButtonStyle.green)
    async def create_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        guild = interaction.guild
        user = interaction.user

        data["ticket_count"] += 1
        ticket_number = str(data["ticket_count"]).zfill(4)
        save_data()

        category = discord.utils.get(guild.categories, name="Tickets")
        if category is None:
            category = await guild.create_category("Tickets")

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            user: discord.PermissionOverwrite(view_channel=True, send_messages=True),
            guild.me: discord.PermissionOverwrite(view_channel=True)
        }

        if data["support_role"]:
            role = guild.get_role(data["support_role"])
            if role:
                overwrites[role] = discord.PermissionOverwrite(view_channel=True, send_messages=True)

        channel = await guild.create_text_channel(
            name=f"ticket-{ticket_number}",
            category=category,
            overwrites=overwrites
        )

        embed = discord.Embed(
            title=f"🎟 Ticket #{ticket_number}",
            description=f"{user.mention}, please describe your issue.",
            color=discord.Color.blue()
        )

        await channel.send(content=user.mention, embed=embed, view=TicketCloseView(user.id))
        await interaction.response.send_message(f"✅ Ticket created: {channel.mention}", ephemeral=True)

# ================= CLOSE VIEW =================
class TicketCloseView(discord.ui.View):
    def __init__(self, owner_id):
        super().__init__(timeout=None)
        self.owner_id = owner_id

    @discord.ui.button(label="Close Ticket", emoji="🔒", style=discord.ButtonStyle.red)
    async def close_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        support_role_id = data.get("support_role")
        has_support = support_role_id and discord.utils.get(interaction.user.roles, id=support_role_id)

        if interaction.user.id != self.owner_id and not has_support:
            await interaction.response.send_message("❌ No permission.", ephemeral=True)
            return

        await interaction.response.send_message("🔒 Closing ticket...")
        await interaction.channel.delete()

# ================= COMMANDS =================
@bot.tree.command(name="ticket_setup", description="Send ticket panel")
@app_commands.checks.has_permissions(administrator=True)
async def ticket_setup(interaction: discord.Interaction, channel: discord.TextChannel):
    embed = discord.Embed(
        title="🎫 Support Tickets",
        description="Click the button below to create a ticket.",
        color=discord.Color.green()
    )
    message = await channel.send(embed=embed, view=TicketCreateView())
    data["panel_channel_id"] = channel.id
    data["panel_message_id"] = message.id
    save_data()
    await interaction.response.send_message("✅ Panel sent.", ephemeral=True)

@bot.tree.command(name="ticket_role", description="Set support role")
@app_commands.checks.has_permissions(administrator=True)
async def ticket_role(interaction: discord.Interaction, role: discord.Role):
    data["support_role"] = role.id
    save_data()
    await interaction.response.send_message(f"✅ Role set to {role.name}", ephemeral=True)

# ================= RUN =================
bot.run(TOKEN)
