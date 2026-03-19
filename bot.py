import discord
from discord.ext import commands
from discord import app_commands
from groq import Groq
import os
from dotenv import load_dotenv
import asyncio

load_dotenv()

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
GROQ_API_KEY  = os.getenv("GROQ_API_KEY")

SYSTEM_PROMPT = """Tu es ⚙️・Neptune SHOP, un bot Discord intelligent et professionnel.
Tu parles TOUJOURS en français, avec des phrases courtes et directes.
Tu réponds à tout, tu es utile, rapide et précis.
Jamais de blabla inutile — une réponse courte et efficace, c'est tout."""

conversation_history: dict[int, list] = {}
ping_channels: dict[int, list[int]] = {}

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot         = commands.Bot(command_prefix="!", intents=intents, help_command=None)
groq_client = Groq(api_key=GROQ_API_KEY)

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#   FONCTION IA
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
async def ask_neptune(user_id: int, message: str) -> str:
    if user_id not in conversation_history:
        conversation_history[user_id] = []
    conversation_history[user_id].append({"role": "user", "content": message})
    if len(conversation_history[user_id]) > 20:
        conversation_history[user_id] = conversation_history[user_id][-20:]
    messages = [{"role": "system", "content": SYSTEM_PROMPT}] + conversation_history[user_id]
    loop = asyncio.get_event_loop()
    response = await loop.run_in_executor(
        None,
        lambda: groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=messages,
            max_tokens=500,
            temperature=0.7,
        ),
    )
    reply = response.choices[0].message.content
    conversation_history[user_id].append({"role": "assistant", "content": reply})
    return reply


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#   EVENTS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
@bot.event
async def on_ready():
    synced = await bot.tree.sync()
    await bot.change_presence(
        status=discord.Status.online,
        activity=discord.Activity(
            type=discord.ActivityType.watching,
            name="⚙️ Neptune SHOP"
        )
    )
    print(f"✅ ⚙️・Neptune SHOP en ligne — {bot.user}")
    print(f"✅ {len(synced)} commandes synchronisées")


@bot.event
async def on_message(message: discord.Message):
    if message.author.bot:
        return
    await bot.process_commands(message)
    is_dm        = isinstance(message.channel, discord.DMChannel)
    is_mentioned = bot.user in message.mentions
    if is_dm or is_mentioned:
        content = message.content.replace(f"<@{bot.user.id}>", "").strip()
        if not content:
            return
        async with message.channel.typing():
            reply = await ask_neptune(message.author.id, content)
        await message.reply(reply, mention_author=False)


@bot.event
async def on_member_join(member: discord.Member):
    guild_id = member.guild.id

    if guild_id in ping_channels and ping_channels[guild_id]:
        for ch_id in ping_channels[guild_id]:
            ch = member.guild.get_channel(ch_id)
            if ch:
                msg = await ch.send(content=member.mention)
                await asyncio.sleep(1)
                await msg.delete()
    else:
        channel = discord.utils.get(member.guild.text_channels, name="général") or \
                  discord.utils.get(member.guild.text_channels, name="general")
        if channel:
            msg = await channel.send(content=member.mention)
            await asyncio.sleep(1)
            await msg.delete()


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#   COMMANDE SYNC
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
@bot.command()
@commands.is_owner()
async def sync(ctx):
    await bot.tree.sync()
    await ctx.send("✅ Commandes synchronisées !")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#   /embed
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
@bot.tree.command(name="embed", description="Crée un embed personnalisé")
@app_commands.describe(
    titre="Titre de l'embed",
    description="Contenu de l'embed",
    couleur="Couleur en hex (ex: ff0000 pour rouge)",
    image="URL d'une image (optionnel)",
    miniature="URL d'une miniature (optionnel)",
    footer="Texte en bas de l'embed (optionnel)"
)
@app_commands.checks.has_permissions(manage_messages=True)
async def embed_command(
    interaction: discord.Interaction,
    titre: str,
    description: str,
    couleur: str = "2b2d31",
    image: str = None,
    miniature: str = None,
    footer: str = "⚙️・Neptune SHOP"
):
    await interaction.response.defer(ephemeral=True)
    try:
        color_int = int(couleur.replace("#", ""), 16)
    except ValueError:
        color_int = 0x2b2d31
    embed = discord.Embed(title=titre, description=description, color=color_int)
    if image:
        embed.set_image(url=image)
    if miniature:
        embed.set_thumbnail(url=miniature)
    if footer:
        embed.set_footer(text=footer)
    await interaction.channel.send(embed=embed)
    await interaction.followup.send("✅ Embed envoyé !", ephemeral=True)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#   /reglement
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
@bot.tree.command(name="reglement", description="Affiche le règlement du serveur")
@app_commands.describe(
    titre="Titre du règlement",
    contenu="Contenu (utilise \\n pour sauter une ligne)",
    image="URL d'une bannière (optionnel)",
    couleur="Couleur hex (défaut: rouge)"
)
@app_commands.checks.has_permissions(manage_messages=True)
async def reglement_command(
    interaction: discord.Interaction,
    titre: str = "📜 Règlement du serveur",
    contenu: str = "1. Respectez tous les membres.\\n2. Pas de spam.\\n3. Pas de contenu NSFW hors salons.\\n4. Suivez les directives Discord.\\n5. Bonne ambiance obligatoire.",
    image: str = None,
    couleur: str = "ed4245"
):
    await interaction.response.defer(ephemeral=True)
    try:
        color_int = int(couleur.replace("#", ""), 16)
    except ValueError:
        color_int = 0xed4245
    contenu = contenu.replace("\\n", "\n")
    embed = discord.Embed(title=titre, description=contenu, color=color_int)
    if image:
        embed.set_image(url=image)
    embed.set_footer(text="⚙️・Neptune SHOP • En rejoignant ce serveur, vous acceptez ce règlement.")
    await interaction.channel.send(embed=embed)
    await interaction.followup.send("✅ Règlement publié !", ephemeral=True)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#   /sondage
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
@bot.tree.command(name="sondage", description="Crée un sondage avec réactions")
@app_commands.describe(
    question="La question du sondage",
    choix1="Premier choix (optionnel)",
    choix2="Deuxième choix (optionnel)",
    choix3="Troisième choix (optionnel)",
    choix4="Quatrième choix (optionnel)"
)
async def sondage_command(
    interaction: discord.Interaction,
    question: str,
    choix1: str = None,
    choix2: str = None,
    choix3: str = None,
    choix4: str = None
):
    await interaction.response.defer(ephemeral=True)
    emojis = ["1️⃣", "2️⃣", "3️⃣", "4️⃣"]
    choix = [c for c in [choix1, choix2, choix3, choix4] if c]
    embed = discord.Embed(title=f"📊 {question}", color=0x5865f2)
    if choix:
        embed.description = "\n".join([f"{emojis[i]} {c}" for i, c in enumerate(choix)])
    else:
        embed.description = "👍 Oui  •  👎 Non"
    embed.set_footer(text=f"Sondage par {interaction.user.display_name} • ⚙️・Neptune SHOP")
    msg = await interaction.channel.send(embed=embed)
    if choix:
        for i in range(len(choix)):
            await msg.add_reaction(emojis[i])
    else:
        await msg.add_reaction("👍")
        await msg.add_reaction("👎")
    await interaction.followup.send("✅ Sondage créé !", ephemeral=True)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#   /annonce
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
@bot.tree.command(name="annonce", description="Publie une annonce officielle")
@app_commands.describe(
    titre="Titre de l'annonce",
    contenu="Contenu de l'annonce",
    mention="@everyone ou @here (optionnel)",
    image="URL d'une image (optionnel)"
)
@app_commands.checks.has_permissions(manage_messages=True)
async def annonce_command(
    interaction: discord.Interaction,
    titre: str,
    contenu: str,
    mention: str = None,
    image: str = None
):
    await interaction.response.defer(ephemeral=True)
    contenu = contenu.replace("\\n", "\n")
    embed = discord.Embed(title=f"📢 {titre}", description=contenu, color=0xfee75c)
    if image:
        embed.set_image(url=image)
    embed.set_footer(text=f"Annonce par {interaction.user.display_name} • ⚙️・Neptune SHOP")
    embed.timestamp = discord.utils.utcnow()
    content = mention if mention in ["@everyone", "@here"] else None
    await interaction.channel.send(content=content, embed=embed)
    await interaction.followup.send("✅ Annonce publiée !", ephemeral=True)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#   /clear
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
@bot.tree.command(name="clear", description="Supprime des messages")
@app_commands.describe(nombre="Nombre de messages à supprimer (max 100)")
@app_commands.checks.has_permissions(manage_messages=True)
async def clear_command(interaction: discord.Interaction, nombre: int):
    await interaction.response.defer(ephemeral=True)
    if nombre < 1 or nombre > 100:
        await interaction.followup.send("❌ Entre 1 et 100 messages.", ephemeral=True)
        return
    deleted = await interaction.channel.purge(limit=nombre)
    await interaction.followup.send(f"✅ {len(deleted)} messages supprimés.", ephemeral=True)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#   /userinfo
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
@bot.tree.command(name="userinfo", description="Affiche les infos d'un membre")
@app_commands.describe(membre="Le membre à inspecter")
async def userinfo_command(interaction: discord.Interaction, membre: discord.Member = None):
    await interaction.response.defer()
    membre = membre or interaction.user
    embed = discord.Embed(
        title=f"👤 {membre.display_name}",
        color=membre.color if membre.color.value != 0 else 0x2b2d31
    )
    embed.set_thumbnail(url=membre.display_avatar.url)
    embed.add_field(name="Pseudo", value=str(membre), inline=True)
    embed.add_field(name="ID", value=membre.id, inline=True)
    embed.add_field(name="Compte créé", value=membre.created_at.strftime("%d/%m/%Y"), inline=True)
    embed.add_field(name="A rejoint le", value=membre.joined_at.strftime("%d/%m/%Y"), inline=True)
    roles = [r.mention for r in membre.roles if r.name != "@everyone"]
    embed.add_field(name=f"Rôles ({len(roles)})", value=" ".join(roles) if roles else "Aucun", inline=False)
    embed.set_footer(text="⚙️・Neptune SHOP")
    await interaction.followup.send(embed=embed)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#   /serverinfo
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
@bot.tree.command(name="serverinfo", description="Affiche les infos du serveur")
async def serverinfo_command(interaction: discord.Interaction):
    await interaction.response.defer()
    guild = interaction.guild
    embed = discord.Embed(title=f"🏠 {guild.name}", color=0x2b2d31)
    if guild.icon:
        embed.set_thumbnail(url=guild.icon.url)
    embed.add_field(name="Membres", value=guild.member_count, inline=True)
    embed.add_field(name="Salons", value=len(guild.channels), inline=True)
    embed.add_field(name="Rôles", value=len(guild.roles), inline=True)
    embed.add_field(name="Créé le", value=guild.created_at.strftime("%d/%m/%Y"), inline=True)
    embed.add_field(name="Propriétaire", value=guild.owner.mention, inline=True)
    embed.set_footer(text="⚙️・Neptune SHOP")
    await interaction.followup.send(embed=embed)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#   /setup-ping — jusqu'à 5 salons
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
@bot.tree.command(name="setup-ping", description="Configure jusqu'à 5 salons pour pinger les nouveaux membres")
@app_commands.describe(
    salon1="Salon 1",
    salon2="Salon 2 (optionnel)",
    salon3="Salon 3 (optionnel)",
    salon4="Salon 4 (optionnel)",
    salon5="Salon 5 (optionnel)",
)
@app_commands.checks.has_permissions(administrator=True)
async def setup_ping_command(
    interaction: discord.Interaction,
    salon1: discord.TextChannel,
    salon2: discord.TextChannel = None,
    salon3: discord.TextChannel = None,
    salon4: discord.TextChannel = None,
    salon5: discord.TextChannel = None,
):
    await interaction.response.defer(ephemeral=True)
    salons = [s for s in [salon1, salon2, salon3, salon4, salon5] if s is not None]
    ping_channels[interaction.guild.id] = [s.id for s in salons]
    liste = "\n".join([f"▸ {s.mention}" for s in salons])
    await interaction.followup.send(
        f"✅ Auto-ping configuré dans :\n{liste}\n\nLe ping est supprimé automatiquement après 1 seconde.",
        ephemeral=True
    )


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#   /test-ping
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
@bot.tree.command(name="test-ping", description="Teste le ping de bienvenue sur toi-même")
@app_commands.checks.has_permissions(administrator=True)
async def test_ping_command(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    guild_id = interaction.guild.id
    member   = interaction.user

    if guild_id in ping_channels and ping_channels[guild_id]:
        for ch_id in ping_channels[guild_id]:
            ch = interaction.guild.get_channel(ch_id)
            if ch:
                msg = await ch.send(content=member.mention)
                await asyncio.sleep(1)
                await msg.delete()
        await interaction.followup.send("✅ Test envoyé et supprimé après 1s dans les salons configurés !", ephemeral=True)
    else:
        msg = await interaction.channel.send(content=member.mention)
        await asyncio.sleep(1)
        await msg.delete()
        await interaction.followup.send("✅ Test envoyé ici. Utilise `/setup-ping` pour configurer les salons.", ephemeral=True)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#   /shutdown
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
@bot.tree.command(name="shutdown", description="Éteint le bot (hors-ligne)")
@app_commands.checks.has_permissions(administrator=True)
async def shutdown_command(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    await interaction.followup.send("🔴 Bot en cours d'extinction…", ephemeral=True)
    await bot.change_presence(status=discord.Status.offline)
    await bot.close()


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#   /start
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
@bot.tree.command(name="start", description="Remet le bot en ligne")
@app_commands.checks.has_permissions(administrator=True)
async def start_command(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    await bot.change_presence(
        status=discord.Status.online,
        activity=discord.Activity(
            type=discord.ActivityType.watching,
            name="⚙️ Neptune SHOP"
        )
    )
    await interaction.followup.send("🟢 Bot remis en ligne !", ephemeral=True)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#   /aide
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
@bot.tree.command(name="aide", description="Liste toutes les commandes")
async def aide_command(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    embed = discord.Embed(title="⚙️・Neptune SHOP — Commandes", color=0x2b2d31)
    embed.add_field(
        name="📝 Contenu",
        value="`/embed` `/reglement` `/annonce` `/sondage`",
        inline=False
    )
    embed.add_field(
        name="🛠️ Modération",
        value="`/clear`",
        inline=False
    )
    embed.add_field(
        name="🔔 Ping",
        value="`/setup-ping` `/test-ping`",
        inline=False
    )
    embed.add_field(
        name="ℹ️ Infos",
        value="`/userinfo` `/serverinfo`",
        inline=False
    )
    embed.add_field(
        name="⚙️ Admin",
        value="`/shutdown` `/start`",
        inline=False
    )
    embed.add_field(
        name="🤖 IA",
        value="Mentionne-moi ou envoie-moi un DM !",
        inline=False
    )
    embed.set_footer(text="⚙️・Neptune SHOP")
    await interaction.followup.send(embed=embed, ephemeral=True)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#   GESTION DES ERREURS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
@bot.tree.error
async def on_app_command_error(interaction: discord.Interaction, error):
    msg = "❌ Tu n'as pas la permission." if isinstance(error, app_commands.MissingPermissions) else f"❌ Erreur : {str(error)}"
    try:
        if interaction.response.is_done():
            await interaction.followup.send(msg, ephemeral=True)
        else:
            await interaction.response.send_message(msg, ephemeral=True)
    except Exception:
        pass


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#   LANCEMENT
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
if __name__ == "__main__":
    bot.run(DISCORD_TOKEN)