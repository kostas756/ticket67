import discord
from discord.ext import commands
from discord import app_commands
import os
import json
from dotenv import load_dotenv
from flask import Flask
from threading import Thread

# ========== KEEP ALIVE ==========
app = Flask(__name__)

@app.route("/")
def home():
    return "Bot is running"

def run():
    app.run(host="0.0.0.0", port=8080)

Thread(target=run).start()

# ========== ENV ==========
load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")

# ========== DATA ==========
DATA_FILE = "ticket_data.json"

# ========== INTENTS ==========
intents = discord.Intents.default()
intents.guilds = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

# ========== DATA HANDLING ==========
def load_data():
    if not os.path.exists(DATA_FILE):
        return {
            "ticket_count": 0,
            "support_role": None
        }
    with open(DATA_FILE, "r") as f:
        return json.load(f)

def save_data():
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=4)

data = load_data()

# ========== READY ==========
@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f"✅ Logged in as {bot.user}")

# ========== TICKET ==========
class TicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Create Ticket", emoji="🎫", style=discord.ButtonStyle.green)
    async def create_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        guild = interaction.guild
        user = interaction.user

        data["ticket_count"] += 1
        save_data()

        category = discord.utils.get(guild.categories, name="Tickets")
        if not category:
            category = await guild.create_category("Tickets")

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            user: discord.PermissionOverwrite(view_channel=True),
            guild.me: discord.PermissionOverwrite(view_channel=True)
        }

        channel = await guild.create_text_channel(
            f"ticket-{data['ticket_count']}",
            category=category,
            overwrites=overwrites
        )

        await channel.send(f"{user.mention} Ticket created.")
        await interaction.response.send_message("✅ Ticket created!", ephemeral=True)

# ========== COMMAND ==========
@bot.tree.command(name="ticket_setup")
@app_commands.checks.has_permissions(administrator=True)
async def ticket_setup(interaction: discord.Interaction, channel: discord.TextChannel):
    await channel.send("Click to create a ticket", view=TicketView())
    await interaction.response.send_message("✅ Panel sent", ephemeral=True)

# ========== RUN ==========
bot.run(TOKEN)
