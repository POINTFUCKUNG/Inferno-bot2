import discord
from discord.ext import commands
from discord import app_commands
from datetime import timedelta
import sqlite3
from discord.ui import View, Button, Select, Modal, TextInput
import discord


# -----------------------------
# INTENTS
# -----------------------------
intents = discord.Intents.default()
intents.members = True
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

# -----------------------------
# DATABASE (WARN SYSTEM)
# -----------------------------
db = sqlite3.connect("warnings.db")
cursor = db.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS warnings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    moderator_id INTEGER,
    reason TEXT
)
""")
db.commit()


# ==================================================
#                 TICKET SYSTEM
# ==================================================

SUPPORT_ROLE_ID = 1515701293174362193  # <-- HIER deine Support Rollen ID einfügen
CATEGORY_NAME = "📨 Tickets"


# -------------------------
# CLOSE BUTTON
# -------------------------
class CloseTicketView(View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="🔒 Ticket schließen", style=discord.ButtonStyle.red)
    async def close_ticket(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_message("Ticket wird geschlossen...", ephemeral=True)
        await interaction.channel.delete()


# -------------------------
# MODAL (FORMULAR)
# -------------------------
class TicketModal(Modal):

    def __init__(self, ticket_type):
        super().__init__(title=f"{ticket_type} Ticket")
        self.ticket_type = ticket_type

        self.frage1 = TextInput(
            label="Beschreibe dein Anliegen",
            style=discord.TextStyle.paragraph,
            required=True,
            max_length=500
        )

        self.frage2 = TextInput(
            label="Weitere Informationen",
            style=discord.TextStyle.paragraph,
            required=False,
            max_length=500
        )

        self.add_item(self.frage1)
        self.add_item(self.frage2)

    async def on_submit(self, interaction: discord.Interaction):

        guild = interaction.guild
        user = interaction.user

        # Kategorie holen oder erstellen
        category = discord.utils.get(guild.categories, name=CATEGORY_NAME)
        if category is None:
            category = await guild.create_category(CATEGORY_NAME)

        support_role = guild.get_role(SUPPORT_ROLE_ID)

        # Nur 1 Ticket pro User pro Typ
        for channel in category.channels:
            if channel.name == f"{self.ticket_type.lower()}-{user.id}":
                await interaction.response.send_message("Du hast bereits ein Ticket offen!", ephemeral=True)
                return

        # Channel erstellen
        channel = await guild.create_text_channel(
            name=f"{self.ticket_type.lower()}-{user.id}",
            category=category
        )

        await channel.set_permissions(guild.default_role, read_messages=False)
        await channel.set_permissions(user, read_messages=True, send_messages=True)
        await channel.set_permissions(support_role, read_messages=True, send_messages=True)

        embed = discord.Embed(
            title=f"{self.ticket_type} Ticket",
            color=discord.Color.green()
        )

        embed.add_field(name="Von", value=user.mention, inline=False)
        embed.add_field(name="Anliegen", value=self.frage1.value, inline=False)
        embed.add_field(name="Details", value=self.frage2.value or "Keine weiteren Angaben", inline=False)

        await channel.send(content=f"{user.mention} {support_role.mention}", embed=embed, view=CloseTicketView())
        await interaction.response.send_message(f"✅ Ticket erstellt: {channel.mention}", ephemeral=True)


# -------------------------
# DROPDOWN
# -------------------------
class TicketSelect(Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="🐞 Bug melden", description="Melde technische Fehler"),
            discord.SelectOption(label="📋 Team Bewerbung", description="Bewirb dich für das Team"),
            discord.SelectOption(label="🔓 Entbannungsantrag", description="Stelle einen Antrag auf Entbannung"),
        ]

        super().__init__(
            placeholder="Wähle eine Ticket-Kategorie...",
            options=options
        )

    async def callback(self, interaction: discord.Interaction):

        if self.values[0] == "🐞 Bug melden":
            await interaction.response.send_modal(TicketModal("Bug"))

        elif self.values[0] == "📋 Team Bewerbung":
            await interaction.response.send_modal(TicketModal("Bewerbung"))

        elif self.values[0] == "🔓 Entbannungsantrag":
            await interaction.response.send_modal(TicketModal("Entbannung"))


# -------------------------
# VIEW
# -------------------------
class TicketView(View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(TicketSelect())

# -----------------------------
# EVENTS
# -----------------------------

@bot.event
async def on_ready():
    bot.add_view(TicketView())
    bot.add_view(CloseTicketView())

    await bot.tree.sync()
    print(f"Eingeloggt als {bot.user}")


@bot.event
async def on_error(event, *args, **kwargs):
    logging.exception(f"Fehler bei Event: {event}")


# -----------------------------
# SLASH COMMANDS
# -----------------------------

@bot.tree.command(name="ticketpanel", description="Öffnet das Ticket Panel")
async def ticketpanel(interaction: discord.Interaction):

    embed = discord.Embed(
        title="🎫 Support Ticket System",
        description="""
🐞 **Bug melden**
→ Technische Fehler melden

📋 **Team Bewerbung**
→ Bewirb dich für das Team

🔓 **Entbannungsantrag**
→ Antrag auf Entbannung stellen
""",
        color=discord.Color.blue()
    )

    await interaction.response.send_message(embed=embed, view=TicketView())


# -----------------------------
# MODERATION
# -----------------------------
@bot.tree.command(name="kick")
@app_commands.checks.has_permissions(kick_members=True)
async def kick(interaction: discord.Interaction, member: discord.Member, reason: str = "Kein Grund"):
    await member.kick(reason=reason)
    await interaction.response.send_message(f"{member} wurde gekickt.")


@bot.tree.command(name="ban")
@app_commands.checks.has_permissions(ban_members=True)
async def ban(interaction: discord.Interaction, member: discord.Member, reason: str = "Kein Grund"):
    await member.ban(reason=reason)
    await interaction.response.send_message(f"{member} wurde gebannt.")


@bot.tree.command(name="timeout")
@app_commands.checks.has_permissions(moderate_members=True)
async def timeout(interaction: discord.Interaction, member: discord.Member, minuten: int, reason: str = "Kein Grund"):

    await member.timeout(
        timedelta(minutes=minuten),
        reason=reason
    )

    await interaction.response.send_message(f"{member} wurde getimeoutet.")


@bot.tree.command(name="clear")
@app_commands.checks.has_permissions(manage_messages=True)
async def clear(interaction: discord.Interaction, amount: int):

    await interaction.response.defer(ephemeral=True)
    await interaction.channel.purge(limit=amount)

    await interaction.followup.send(f"{amount} Nachrichten gelöscht.", ephemeral=True)


# -----------------------------
# WARN SYSTEM
# -----------------------------
@bot.tree.command(name="warn")
@app_commands.checks.has_permissions(moderate_members=True)
async def warn(interaction: discord.Interaction, member: discord.Member, reason: str):

    cursor.execute(
        "INSERT INTO warnings (user_id, moderator_id, reason) VALUES (?, ?, ?)",
        (member.id, interaction.user.id, reason)
    )
    db.commit()

    cursor.execute("SELECT COUNT(*) FROM warnings WHERE user_id = ?", (member.id,))
    count = cursor.fetchone()[0]

    await interaction.response.send_message(
        f"⚠️ {member.mention} verwarnt ({count} Warns). Grund: {reason}"
    )


@bot.tree.command(name="warnings")
@app_commands.checks.has_permissions(moderate_members=True)
async def warnings(interaction: discord.Interaction, member: discord.Member):

    cursor.execute("SELECT id, reason FROM warnings WHERE user_id = ?", (member.id,))
    rows = cursor.fetchall()

    if not rows:
        await interaction.response.send_message("Keine Warnungen.")
        return

    embed = discord.Embed(
        title=f"Warnungen von {member}",
        color=discord.Color.orange()
    )

    for wid, reason in rows:
        embed.add_field(name=f"Warn #{wid}", value=reason, inline=False)

    await interaction.response.send_message(embed=embed)


@bot.tree.command(name="unwarn")
@app_commands.checks.has_permissions(moderate_members=True)
async def unwarn(interaction: discord.Interaction, warn_id: int):

    cursor.execute("DELETE FROM warnings WHERE id = ?", (warn_id,))
    db.commit()

    await interaction.response.send_message(f"Warn #{warn_id} entfernt.")


# -----------------------------
# BOT START
# -----------------------------
import os
bot.run(os.environ["TOKEN"])

# -----------------------------
# INTENTS
# -----------------------------
intents = discord.Intents.default()
intents.members = True
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

# -----------------------------
# DATABASE (WARN SYSTEM)
# -----------------------------
db = sqlite3.connect("warnings.db")
cursor = db.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS warnings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    moderator_id INTEGER,
    reason TEXT
)
""")
db.commit()


# -----------------------------
# TICKET SYSTEM
# -----------------------------
class CloseTicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="🔒 Ticket schließen",
        style=discord.ButtonStyle.red,
        custom_id="close_ticket"
    )
    async def close_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("Ticket wird geschlossen...", ephemeral=True)
        await interaction.channel.delete()


class TicketSelect(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="Support", emoji="🎧"),
            discord.SelectOption(label="Bewerbung", emoji="📝"),
            discord.SelectOption(label="Entbannung", emoji="🔓"),
        ]

        super().__init__(
            placeholder="Wähle eine Ticket-Kategorie",
            options=options,
            custom_id="ticket_select"
        )

    async def callback(self, interaction: discord.Interaction):
        guild = interaction.guild
        user = interaction.user
        category_name = "Tickets"

        category = discord.utils.get(guild.categories, name=category_name)
        if category is None:
            category = await guild.create_category(category_name)

        channel = await guild.create_text_channel(
            name=f"{self.values[0].lower()}-{user.name}",
            category=category
        )

        await channel.set_permissions(guild.default_role, read_messages=False)
        await channel.set_permissions(user, read_messages=True, send_messages=True)

        embed = discord.Embed(
            title=f"{self.values[0]} Ticket",
            description="Beschreibe dein Anliegen.",
            color=discord.Color.green()
        )

        await channel.send(embed=embed, view=CloseTicketView())

        await interaction.response.send_message(
            f"Ticket erstellt: {channel.mention}",
            ephemeral=True
        )


class TicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(TicketSelect())


# -----------------------------
# EVENTS
# -----------------------------
@bot.event
async def on_ready():
    bot.add_view(TicketView())
    bot.add_view(CloseTicketView())

    await bot.tree.sync()
    print(f"Eingeloggt als {bot.user}")


# -----------------------------
# TICKET PANEL COMMAND
# -----------------------------
@bot.tree.command(name="ticketpanel", description="Erstellt das Ticket Panel")
@app_commands.checks.has_permissions(administrator=True)
async def ticketpanel(interaction: discord.Interaction):

    embed = discord.Embed(
        title="🎫 Ticketsystem",
        description="Wähle unten eine Kategorie.",
        color=discord.Color.blurple()
    )

    await interaction.channel.send(embed=embed, view=TicketView())

    await interaction.response.send_message("Ticket Panel erstellt.", ephemeral=True)


# -----------------------------
# MODERATION
# -----------------------------
@bot.tree.command(name="kick")
@app_commands.checks.has_permissions(kick_members=True)
async def kick(interaction: discord.Interaction, member: discord.Member, reason: str = "Kein Grund"):
    await member.kick(reason=reason)
    await interaction.response.send_message(f"{member} wurde gekickt.")


@bot.tree.command(name="ban")
@app_commands.checks.has_permissions(ban_members=True)
async def ban(interaction: discord.Interaction, member: discord.Member, reason: str = "Kein Grund"):
    await member.ban(reason=reason)
    await interaction.response.send_message(f"{member} wurde gebannt.")


@bot.tree.command(name="timeout")
@app_commands.checks.has_permissions(moderate_members=True)
async def timeout(interaction: discord.Interaction, member: discord.Member, minuten: int, reason: str = "Kein Grund"):

    await member.timeout(
        timedelta(minutes=minuten),
        reason=reason
    )

    await interaction.response.send_message(f"{member} wurde getimeoutet.")


@bot.tree.command(name="clear")
@app_commands.checks.has_permissions(manage_messages=True)
async def clear(interaction: discord.Interaction, amount: int):

    await interaction.response.defer(ephemeral=True)
    await interaction.channel.purge(limit=amount)

    await interaction.followup.send(f"{amount} Nachrichten gelöscht.", ephemeral=True)


# -----------------------------
# WARN SYSTEM
# -----------------------------
@bot.tree.command(name="warn")
@app_commands.checks.has_permissions(moderate_members=True)
async def warn(interaction: discord.Interaction, member: discord.Member, reason: str):

    cursor.execute(
        "INSERT INTO warnings (user_id, moderator_id, reason) VALUES (?, ?, ?)",
        (member.id, interaction.user.id, reason)
    )
    db.commit()

    cursor.execute("SELECT COUNT(*) FROM warnings WHERE user_id = ?", (member.id,))
    count = cursor.fetchone()[0]

    await interaction.response.send_message(
        f"⚠️ {member.mention} verwarnt ({count} Warns). Grund: {reason}"
    )


@bot.tree.command(name="warnings")
@app_commands.checks.has_permissions(moderate_members=True)
async def warnings(interaction: discord.Interaction, member: discord.Member):

    cursor.execute("SELECT id, reason FROM warnings WHERE user_id = ?", (member.id,))
    rows = cursor.fetchall()

    if not rows:
        await interaction.response.send_message("Keine Warnungen.")
        return

    embed = discord.Embed(
        title=f"Warnungen von {member}",
        color=discord.Color.orange()
    )

    for wid, reason in rows:
        embed.add_field(name=f"Warn #{wid}", value=reason, inline=False)

    await interaction.response.send_message(embed=embed)


@bot.tree.command(name="unwarn")
@app_commands.checks.has_permissions(moderate_members=True)
async def unwarn(interaction: discord.Interaction, warn_id: int):

    cursor.execute("DELETE FROM warnings WHERE id = ?", (warn_id,))
    db.commit()

    await interaction.response.send_message(f"Warn #{warn_id} entfernt.")


# -----------------------------
# BOT START
# -----------------------------
import os
bot.run(os.environ["TOKEN"])