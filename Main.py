import discord
import json
import os
import difflib
from discord import app_commands

FILE = os.path.join(os.path.dirname(__file__), "player_data.json")
BG_FILE = os.path.join(os.path.dirname(__file__), "backgrounds.json")
SHOP_FILE = os.path.join(os.path.dirname(__file__), "item_shop.json")
ERROR_CATEGORY = "Downtime"
ERROR_CHANNEL = "seraphi-error-reports"
CATEGORY_TO_TABLE = {
    "hailey's table": "hailey table",
    "alijah's table": "alijah table",
    "spencer's table": "spencer table",
    "joseph's table": "joseph table",
    "rotation table": "rotation table"
}
CLASS_LIST = [
    "warlock",  
    "sorcerer", 
    "bard", 
    "paladin", 
    "fighter", 
    "rogue", 
    "marshal", 
    "oracle", 
    "psion", 
    "roboticist",
    "scientist",
    "adept",
    "vanguard",
    "plainshifter",
    "survivalist"
]

# ---------------- JSON HELPERS ----------------
def load_data():
    try:
        with open(FILE, "r") as f:
            return json.load(f)

    except FileNotFoundError:
        return {
            "players": {}
        }

def save_data(data):
    with open(FILE, "w") as f:
        json.dump(
            data,
            f,
            indent=4
        )

def load_backgrounds():
    try:
        with open(BG_FILE, "r") as f:
            return json.load(f)

    except FileNotFoundError:
        return {
            "backgrounds": {}
        }

def load_shop():
    try:
        with open(SHOP_FILE, "r") as f:
            return json.load(f)

    except FileNotFoundError:
        return {}

def save_shop(shop):
    with open(SHOP_FILE, "w") as f:
        json.dump(
            shop,
            f,
            indent=4
        )

# ---------------- BID RAISE AMOUNT BY LEVEL ----------------
def get_bid_raise_amount(level: int) -> int:
    if 1 <= level <= 4:
        return 100
    elif 5 <= level <= 8:
        return 200
    elif 9 <= level <= 12:
        return 300
    elif 13 <= level <= 16:
        return 500
    elif 17 <= level <= 20:
        return 700
    else:
        raise ValueError("Level must be between 1 and 20")

# ---------------- ITEM AMOUNT ERROR CALL FUNCTION ----------
async def item_amount_error(guild: discord.Guild, username: str, item: str, reason: str):
    """
    Global error logger for item/magic item issues.
    Can be used by ANY command.
    """

    try:
        if not guild:
            return

        category = discord.utils.get(guild.categories, name=ERROR_CATEGORY)
        if not category:
            return

        channel = discord.utils.get(category.channels, name=ERROR_CHANNEL)
        if not channel:
            return

        embed = discord.Embed(
            title="🚨 Item System Error Report",
            color=discord.Color.red()
        )

        embed.add_field(name="Player", value=username, inline=False)
        embed.add_field(name="Item", value=item, inline=False)
        embed.add_field(name="Issue", value=reason, inline=False)

        await channel.send(embed=embed)

    except Exception:
        # never crash bot due to logging failure
        pass

# ---------------- GET TABLES FROM INTERCATION --------------
def get_table_from_interaction(interaction: discord.Interaction):
    if not interaction.channel or not interaction.channel.category:
        return None

    category_name = interaction.channel.category.name.lower().strip()
    category_name = category_name.replace("’", "'")

    for key, value in CATEGORY_TO_TABLE.items():
        if key in category_name:
            return value

    return None

# ---------------- BOT CLASS ----------------
class Client(discord.Client):
    def __init__(self, *, intents):
        super().__init__(intents=intents)
        self.tree = discord.app_commands.CommandTree(self)

    async def on_ready(self):
        await self.tree.sync()
        print("Slash commands synced!")
        print(f"Logged on as {self.user}")

    async def on_message(self, message):

        # ignore bot messages (important to prevent loops)
        if message.author.bot:
            return

        content = message.content.lower().strip()

        if content == "hello seraphi":
            await message.channel.send(f"Hello {message.author.name} 👋")


# ---------------- INTENTS ----------------
intents = discord.Intents.default()
intents.message_content = True

client = Client(intents=intents)

# =========================================================
# SLASH COMMAND: list players (admin only)
# =========================================================
@client.tree.command(
    name="listplayers",
    description="List all registered players"
)
async def listplayers(interaction: discord.Interaction):

    # =========================================================
    # PERMISSION CHECK
    # =========================================================

    is_admin = interaction.user.guild_permissions.administrator

    has_dm_role = any(
        role.name.lower() == "dm"
        for role in interaction.user.roles
    )

    has_tech_role = any(
        role.name.lower() == "tech"
        for role in interaction.user.roles
    )

    if not (is_admin or has_dm_role or has_tech_role):
        await interaction.response.send_message(
            "❌ You do not have permission to use this command.",
            ephemeral=True
        )
        return

    # =========================================================
    # LOAD DATA
    # =========================================================

    data = load_data()

    players = data.get("players", {})

    if not players:
        await interaction.response.send_message(
            "❌ There are currently no registered players.",
            ephemeral=True
        )
        return

    # =========================================================
    # BUILD PLAYER ENTRIES
    # =========================================================

    player_list = []

    for username, player_data in players.items():

        # Player structure:
        # [0] Name
        # [1] Character
        # [2] Background
        # [3] Credits
        # [4] Normal Items
        # [5] Magic Items
        # [6] Class

        name = (
            player_data[0]
            if len(player_data) > 0
            else "Unknown"
        )

        character = (
            player_data[1]
            if len(player_data) > 1
            else "Unknown"
        )

        player_list.append(
            f"👤 **Username:** {username}\n"
            f"   **Name:** {name}\n"
            f"   **Character:** {character}"
        )

    # =========================================================
    # SORT PLAYERS ALPHABETICALLY BY USERNAME
    # =========================================================

    player_list.sort(key=lambda x: x.lower())

    # =========================================================
    # SPLIT INTO DISCORD-SAFE MESSAGES
    # =========================================================

    header = "📋 **REGISTERED PLAYERS**\n\n"

    messages = []
    current_message = header

    # Keep well below Discord's 2,000 character limit
    max_length = 1900

    for player in player_list:

        player_entry = player + "\n\n"

        # If adding this player would exceed the limit,
        # start a new message.
        if len(current_message) + len(player_entry) > max_length:

            messages.append(current_message.rstrip())

            current_message = player_entry

        else:

            current_message += player_entry

    # Add the final message
    if current_message.strip():
        messages.append(current_message.rstrip())

    # =========================================================
    # SEND MESSAGES
    # =========================================================

    await interaction.response.send_message(
        messages[0],
        ephemeral=True
    )

    # Send additional chunks as follow-up messages
    for message in messages[1:]:

        await interaction.followup.send(
            message,
            ephemeral=True
        )

# =========================================================
# SLASH COMMAND: ADD PLAYER
# =========================================================
@client.tree.command(
    name="addplayer",
    description="Add a player using name, character, and background"
)
@discord.app_commands.describe(
    name="Player name",
    character="Player character name",
    background="Background (from backgrounds.json)",
    class_type="Player class",
    item="Optional: Add an item to the player's inventory"
)
async def addplayer(
    interaction: discord.Interaction,
    name: str,
    character: str,
    background: str,
    class_type: str,
    item: str = None
):

    data = load_data()

    if "players" not in data:
        data["players"] = {}

    user_key = interaction.user.name.lower()

    name = name.lower()
    character = character.lower()
    background = background.lower()
    class_type = class_type.lower()

    # =========================================================
    # PLAYER ALREADY EXISTS CHECK
    # =========================================================
    if user_key in data["players"]:
        await interaction.response.send_message(
            "❌ You already have a player!",
            ephemeral=True
        )
        return

    # =========================================================
    # CLASS VALIDATION
    # =========================================================
    if class_type not in CLASS_LIST:

        matches = difflib.get_close_matches(
            class_type,
            CLASS_LIST,
            n=1,
            cutoff=0.6
        )

        if matches:
            await interaction.response.send_message(
                "❌ Invalid class type.\n\n"
                f"🔎 Did you mean **{matches[0]}**?",
                ephemeral=True
            )
        else:
            await interaction.response.send_message(
                "❌ Invalid class type.\n\n"
                f"Valid classes are:\n`{', '.join(CLASS_LIST)}`",
                ephemeral=True
            )
        return

    # =========================================================
    # LOAD BACKGROUNDS
    # =========================================================
    bg_data = load_backgrounds()
    backgrounds = bg_data.get("backgrounds", {})

    # =========================================================
    # EXACT BACKGROUND MATCH
    # =========================================================
    if background in backgrounds:

        base_credits = backgrounds[background][0]

        # Make a copy so we don't modify backgrounds.json data
        items = backgrounds[background][1].copy()

        # =========================================================
        # ADD OPTIONAL STARTING ITEM
        # =========================================================
        if item:
            items.append(item.lower())

        total_credits = 5000 + base_credits

        data["players"][user_key] = [
            name,             # 0
            character,        # 1
            background,       # 2
            total_credits,    # 3
            items,            # 4 Normal inventory
            {},               # 5 Magic items
            class_type        # 6 Class
        ]

        save_data(data)

        await interaction.response.send_message(
            f"✅ Player created!\n"
            f"👤 Name: {name}\n"
            f"⚔️ Character: {character}\n"
            f"📜 Background: {background}\n"
            f"🧬 Class: {class_type}\n"
            f"💰 Credits: {total_credits}\n"
            f"🎒 Items received: {len(items)}",
            ephemeral=True
        )
        return

    # =========================================================
    # FUZZY BACKGROUND MATCH
    # =========================================================
    matches = difflib.get_close_matches(
        background,
        backgrounds.keys(),
        n=1,
        cutoff=0.6
    )

    if matches:
        suggested = matches[0]

        await interaction.response.send_message(
            "❌ Background not found.\n\n"
            f"🔎 Did you mean **{suggested}**?\n\n"
            f"👉 Try again with:\n"
            f"```/addplayer {name} {character} {suggested} {class_type}```",
            ephemeral=True
        )
    else:
        await interaction.response.send_message(
            "❌ Background not found and no close match exists.",
            ephemeral=True
        )


# =========================================================
# DELETE PLAYER (ADMIN ONLY)
# =========================================================
@client.tree.command(
    name="deleteplayer",
    description="Delete a player (admin only)"
)
async def deleteplayer(interaction: discord.Interaction, username: str):

    # =========================================================
    # PERMISSION CHECK
    # =========================================================
    
    is_admin = interaction.user.guild_permissions.administrator
    
    has_dm_role = any(
        role.name.lower() == "dm"
        for role in interaction.user.roles
    )
    
    has_tech_role = any(
        role.name.lower() == "tech"
        for role in interaction.user.roles
    )
    
    if not (is_admin or has_dm_role or has_tech_role):
        await interaction.response.send_message(
            "❌ You do not have permission to use this command.",
            ephemeral=True
            )
        return

    data = load_data()

    username = username.lower()
    players = data.get("players", {})

    # ---------------- EXACT MATCH ----------------
    if username in players:
        del players[username]
        save_data(data)

        await interaction.response.send_message(
            f"🗑️ Player '{username}' has been deleted.",
            ephemeral=True
        )
        return

    # ---------------- FUZZY MATCH ----------------
    matches = difflib.get_close_matches(username, players.keys(), n=1, cutoff=0.6)

    if matches:
        suggested = matches[0]

        await interaction.response.send_message(
            "❌ Player not found.\n\n"
            f"🔎 Did you mean **{suggested}**?\n\n"
            f"👉 To delete them, use:\n"
            f"```/deleteplayer {suggested}```",
            ephemeral=True
        )
    else:
        await interaction.response.send_message(
            "❌ Player not found and no close match exists.",
            ephemeral=True
        )


# =========================================================
# ADD CREDITS (ADMIN ONLY)
# =========================================================
@client.tree.command(
    name="addcredits",
    description="Add credits to a player (admin only)"
)
async def addcredits(interaction: discord.Interaction, username: str, amount: int):

    # =========================================================
    # PERMISSION CHECK
    # =========================================================
    
    is_admin = interaction.user.guild_permissions.administrator
    
    has_dm_role = any(
        role.name.lower() == "dm"
        for role in interaction.user.roles
    )
    
    has_tech_role = any(
        role.name.lower() == "tech"
        for role in interaction.user.roles
    )
    
    if not (is_admin or has_dm_role or has_tech_role):
        await interaction.response.send_message(
            "❌ You do not have permission to use this command.",
            ephemeral=True
            )
        return

    data = load_data()

    username = username.lower()
    players = data.get("players", {})

    # ---------------- EXACT MATCH ----------------
    if username in players:
        players[username][3] += amount
        save_data(data)

        await interaction.response.send_message(
            f"✅ Added {amount} credits. New balance: {players[username][3]}",
            ephemeral=True
        )
        return

    # ---------------- FUZZY MATCH ----------------
    matches = difflib.get_close_matches(username, players.keys(), n=1, cutoff=0.6)

    if matches:
        suggested = matches[0]

        await interaction.response.send_message(
            "❌ Player not found.\n\n"
            f"🔎 Did you mean **{suggested}**?\n\n"
            f"👉 Try again with:\n"
            f"```/addcredits {suggested} {amount}```",
            ephemeral=True
        )
    else:
        await interaction.response.send_message(
            "❌ Player not found and no close match exists.",
            ephemeral=True
        )


# =========================================================
# REMOVE CREDITS (ADMIN ONLY)
# =========================================================
@client.tree.command(
    name="removecredits",
    description="Remove credits from a player (admin only)"
)
async def removecredits(interaction: discord.Interaction, username: str, amount: int):

    # =========================================================
    # PERMISSION CHECK
    # =========================================================
    
    is_admin = interaction.user.guild_permissions.administrator
    
    has_dm_role = any(
        role.name.lower() == "dm"
        for role in interaction.user.roles
    )
    
    has_tech_role = any(
        role.name.lower() == "tech"
        for role in interaction.user.roles
    )
    
    if not (is_admin or has_dm_role or has_tech_role):
        await interaction.response.send_message(
            "❌ You do not have permission to use this command.",
            ephemeral=True
            )
        return

    data = load_data()

    username = username.lower()
    players = data.get("players", {})

    # ---------------- EXACT MATCH ----------------
    if username in players:
        current_balance = players[username][3]

        if current_balance < amount:
            await interaction.response.send_message(
                f"❌ Insufficient funds. Current balance: {current_balance}",
                ephemeral=True
            )
            return

        players[username][3] = current_balance - amount
        save_data(data)

        await interaction.response.send_message(
            f"🪙 Removed {amount}. New balance: {players[username][3]}",
            ephemeral=True
        )
        return

    # ---------------- FUZZY MATCH ----------------
    matches = difflib.get_close_matches(username, players.keys(), n=1, cutoff=0.6)

    if matches:
        suggested = matches[0]

        await interaction.response.send_message(
            "❌ Player not found.\n\n"
            f"🔎 Did you mean **{suggested}**?\n\n"
            f"👉 Try again with:\n"
            f"```/removecredits {suggested} {amount}```",
            ephemeral=True
        )
    else:
        await interaction.response.send_message(
            "❌ Player not found and no close match exists.",
            ephemeral=True
        )


# =========================================================
# GET CREDITS 
# =========================================================
@client.tree.command(
    name="getcredits",
    description="Check a player's credit balance"
)
async def getcredits(interaction: discord.Interaction, username: str):

    data = load_data()

    username = username.lower()
    user_key = interaction.user.name.lower()
    players = data.get("players", {})

    # =========================================================
    # PERMISSION CHECK
    # =========================================================

    is_admin = interaction.user.guild_permissions.administrator

    has_dm_role = any(
        role.name.lower() == "dm"
        for role in interaction.user.roles
    )

    has_tech_role = any(
        role.name.lower() == "tech"
        for role in interaction.user.roles
    )

    # The player can view their own credits
    is_self = user_key == username

    # Admin, DM, Tech, or the player themselves can use this
    if not (
        is_admin
        or has_dm_role
        or has_tech_role
        or is_self
    ):
        await interaction.response.send_message(
            "❌ You can only view your own balance.",
            ephemeral=True
        )
        return

    # =========================================================
    # EXACT MATCH
    # =========================================================

    if username in players:

        player = players[username]

        # Safety check for credit slot
        if len(player) <= 3:
            await interaction.response.send_message(
                "❌ This player's credit data is missing. "
                "Please contact a DM or Tech.",
                ephemeral=True
            )
            return

        balance = player[3]

        await interaction.response.send_message(
            f"💰 **{username}** has **{balance} credits**.",
            ephemeral=True
        )
        return

    # =========================================================
    # FUZZY MATCH
    # =========================================================

    matches = difflib.get_close_matches(
        username,
        players.keys(),
        n=1,
        cutoff=0.6
    )

    if matches:

        suggested = matches[0]

        await interaction.response.send_message(
            "❌ Player not found.\n\n"
            f"🔎 Did you mean **{suggested}**?\n\n"
            f"👉 Try again with:\n"
            f"```/getcredits {suggested}```",
            ephemeral=True
        )

    else:

        await interaction.response.send_message(
            "❌ Player not found and no close match exists.",
            ephemeral=True
        )

# =========================================================
# Add Custom Item (Admin Only)
# =========================================================
@client.tree.command(
    name="additem",
    description="Add non magic items to a player that are not from item shop. Add item worth if needed (admin only)"
)
async def additem(interaction: discord.Interaction, username: str, item: str):

    # =========================================================
    # PERMISSION CHECK
    # =========================================================
    
    is_admin = interaction.user.guild_permissions.administrator
    
    has_dm_role = any(
        role.name.lower() == "dm"
        for role in interaction.user.roles
    )
    
    has_tech_role = any(
        role.name.lower() == "tech"
        for role in interaction.user.roles
    )
    
    if not (is_admin or has_dm_role or has_tech_role):
        await interaction.response.send_message(
            "❌ You do not have permission to use this command.",
            ephemeral=True
            )
        return

    data = load_data()

    username = username.lower()
    item = item.lower()
    players = data.get("players", {})

    # ---------------- EXACT MATCH ----------------
    if username in players:

        player = players[username]

        # ensure item list exists
        if len(player) < 5 or player[4] is None:
            player.append([])

        player[4].append(item)
        save_data(data)

        await interaction.response.send_message(
            f"🎒 Added **{item}** to {username}'s inventory.",
            ephemeral=True
        )
        return

    # ---------------- FUZZY MATCH ----------------
    matches = difflib.get_close_matches(username, players.keys(), n=1, cutoff=0.6)

    if matches:
        suggested = matches[0]

        await interaction.response.send_message(
            "❌ Player not found.\n\n"
            f"🔎 Did you mean **{suggested}**?\n\n"
            f"👉 Try again with:\n"
            f"```/additem {suggested} {item}```",
            ephemeral=True
        )
    else:
        await interaction.response.send_message(
            "❌ Player not found and no close match exists.",
            ephemeral=True
        )

# =========================================================
# Add Magic Item (Admin Only)
# =========================================================
@client.tree.command(
    name="addmagicitem",
    description="(ADMIN ONLY) Add a magic item to a player. You MUST provide an item name AND description."
)
@discord.app_commands.describe(
    username="Player name",
    item="Magic item name",
    description="Item description (required for magic item effects / details)"
)
async def addmagicitem(
    interaction: discord.Interaction,
    username: str,
    item: str,
    description: str
):

    # =========================================================
    # PERMISSION CHECK
    # =========================================================
    
    is_admin = interaction.user.guild_permissions.administrator
    
    has_dm_role = any(
        role.name.lower() == "dm"
        for role in interaction.user.roles
    )
    
    has_tech_role = any(
        role.name.lower() == "tech"
        for role in interaction.user.roles
    )
    
    if not (is_admin or has_dm_role or has_tech_role):
        await interaction.response.send_message(
            "❌ You do not have permission to use this command.",
            ephemeral=True
            )
        return

    data = load_data()

    username = username.lower()
    item = item.lower()

    players = data.get("players", {})

    # ---------------- FUZZY USERNAME MATCH ----------------
    if username not in players:
        matches = difflib.get_close_matches(username, players.keys(), n=1, cutoff=0.6)

        if matches:
            suggested = matches[0]

            await interaction.response.send_message(
                "❌ Player not found.\n\n"
                f"🔎 Did you mean **{suggested}**?\n\n"
                f"👉 Try again with:\n"
                f"```/addmagicitem {suggested} {item} \"{description}\"```",
                ephemeral=True
            )
        else:
            await interaction.response.send_message(
                "❌ Player not found and no close match exists.",
                ephemeral=True
            )
        return

    # ---------------- GET PLAYER ----------------
    player = players[username]

    # ensure magic item dict exists
    if len(player) < 6:
        player.append({})

    magic_items = player[5]

    # ---------------- ADD MAGIC ITEM ----------------
    if item in magic_items:
        magic_items[item]["amount"] += 1
    else:
        magic_items[item] = {
            "description": description,
            "amount": 1
        }

    save_data(data)

    await interaction.response.send_message(
        f"✨ Added magic item **{item}** to {username}.\n"
        f"📜 Description: {description}",
        ephemeral=True
    )

# =========================================================
# Add Shop Item (Admin Only)
# =========================================================
@client.tree.command(
    name="addshopitem",
    description="Add a shop item to a player's inventory (admin only)"
)
async def addshopitem(interaction: discord.Interaction, username: str, item: str):

    # =========================================================
    # PERMISSION CHECK
    # =========================================================
    
    is_admin = interaction.user.guild_permissions.administrator
    
    has_dm_role = any(
        role.name.lower() == "dm"
        for role in interaction.user.roles
    )
    
    has_tech_role = any(
        role.name.lower() == "tech"
        for role in interaction.user.roles
    )
    
    if not (is_admin or has_dm_role or has_tech_role):
        await interaction.response.send_message(
            "❌ You do not have permission to use this command.",
            ephemeral=True
            )
        return

    data = load_data()
    shop = load_shop()

    username = username.lower()
    item = item.lower()
    players = data.get("players", {})

    # ---------------- USERNAME FUZZY MATCH ----------------
    if username not in players:
        user_matches = difflib.get_close_matches(
            username,
            players.keys(),
            n=1,
            cutoff=0.6
        )

        if user_matches:
            suggested_user = user_matches[0]

            await interaction.response.send_message(
                "❌ Player not found.\n\n"
                f"🔎 Did you mean **{suggested_user}**?\n\n"
                f"👉 Try again with:\n"
                f"```/addshopitem {suggested_user} {item}```",
                ephemeral=True
            )
        else:
            await interaction.response.send_message(
                "❌ Player not found and no close match exists.",
                ephemeral=True
            )
        return

    # ---------------- ITEM FUZZY MATCH ----------------
    if item not in shop:
        item_matches = difflib.get_close_matches(
            item,
            shop.keys(),
            n=5,
            cutoff=0.5
        )

        if item_matches:
            suggestions = "\n".join([f"• {match}" for match in item_matches])

            await interaction.response.send_message(
                "❌ Shop item not found.\n\n"
                "🔎 Did you mean:\n"
                f"{suggestions}\n\n"
                "👉 Try again with the exact name.",
                ephemeral=True
            )
        else:
            await interaction.response.send_message(
                "❌ Shop item not found and no similar items exist.",
                ephemeral=True
            )
        return

    # ---------------- PLAYER SETUP ----------------
    player = players[username]

    if len(player) < 5:
        player.append([])

    if len(player) < 6:
        player.append({})

    inventory = player[4]
    magic_items = player[5]

    item_data = shop[item]

    # ---------------- CONTAINER ITEM ----------------
    if "contains" in item_data:

        added_items = []
        added_magic = []

        for contained_item in item_data["contains"]:
            contained_item = contained_item.lower()

            if contained_item in shop and shop[contained_item].get("magic", False):

                desc = shop[contained_item].get(
                    "description",
                    "No description provided."
                )

                if contained_item in magic_items:
                    magic_items[contained_item]["amount"] += 1
                else:
                    magic_items[contained_item] = {
                        "description": desc,
                        "amount": 1
                    }

                added_magic.append(contained_item)

            else:
                inventory.append(contained_item)
                added_items.append(contained_item)

        message = (
            f"📦 Added contents of **{item}** to {username}.\n"
            f"🎒 Normal items: {len(added_items)}\n"
            f"✨ Magic items: {len(added_magic)}"
        )

    # ---------------- MAGIC ITEM ----------------
    elif item_data.get("magic", False):

        desc = item_data.get("description", "No description provided.")

        if item in magic_items:
            magic_items[item]["amount"] += 1
        else:
            magic_items[item] = {
                "description": desc,
                "amount": 1
            }

        message = (
            f"✨ Added magic item **{item}** to {username}'s magic inventory."
        )

    # ---------------- NORMAL ITEM ----------------
    else:
        inventory.append(item)

        message = (
            f"🎒 Added **{item}** to {username}'s inventory."
        )

    # ---------------- SAVE ----------------
    save_data(data)

    await interaction.response.send_message(
        message,
        ephemeral=True
    )

# =========================================================
# Get Player Items
# =========================================================
@client.tree.command(
    name="getitems",
    description="View a player's inventory"
)
async def getitems(interaction: discord.Interaction, username: str):

    data = load_data()

    username = username.lower().strip()
    user_key = interaction.user.name.lower()
    players = data.get("players", {})

    # =========================================================
    # EXACT MATCH
    # =========================================================

    if username in players:

        # =====================================================
        # PERMISSION CHECK
        # =====================================================

        is_admin = interaction.user.guild_permissions.administrator

        has_dm_role = any(
            role.name.lower() == "dm"
            for role in interaction.user.roles
        )

        has_tech_role = any(
            role.name.lower() == "tech"
            for role in interaction.user.roles
        )

        is_self = user_key == username

        if not (
            is_admin
            or has_dm_role
            or has_tech_role
            or is_self
        ):
            await interaction.response.send_message(
                "❌ You can only view your own items.",
                ephemeral=True
            )
            return

        player = players[username]

        # =====================================================
        # SAFETY CHECKS
        # =====================================================

        inventory = (
            player[4]
            if len(player) > 4 and isinstance(player[4], list)
            else []
        )

        magic_items = (
            player[5]
            if len(player) > 5 and isinstance(player[5], dict)
            else {}
        )

        # =====================================================
        # SORT NORMAL INVENTORY ALPHABETICALLY
        # =====================================================

        inventory.sort(
            key=lambda item: str(item).lower()
        )

        player[4] = inventory

        # =====================================================
        # SORT MAGIC ITEMS ALPHABETICALLY
        # =====================================================

        magic_items = dict(
            sorted(
                magic_items.items(),
                key=lambda item: str(item[0]).lower()
            )
        )

        player[5] = magic_items

        # =====================================================
        # SAVE SORTED INVENTORY
        # =====================================================

        save_data(data)

        # =====================================================
        # EMPTY CHECK
        # =====================================================

        if not inventory and not magic_items:

            await interaction.response.send_message(
                f"🎒 **{username}** has no items.",
                ephemeral=True
            )

            return

        # =====================================================
        # BUILD INVENTORY LINES
        # =====================================================

        inventory_lines = []

        for item in inventory:

            inventory_lines.append(
                f"• {item}"
            )

        # =====================================================
        # BUILD MAGIC ITEM LINES
        # =====================================================

        magic_lines = []

        for name, item_data in magic_items.items():

            # =================================================
            # ERROR SAFETY CHECK
            # =================================================

            if not isinstance(item_data, dict):

                await item_amount_error(
                    interaction.guild,
                    username,
                    name,
                    f"Invalid magic item structure: {item_data}"
                )

                magic_lines.append(
                    f"• {name} (x1): {str(item_data)}"
                )

                continue

            amount = item_data.get(
                "amount",
                1
            )

            desc = item_data.get(
                "description",
                "No description"
            )

            # =================================================
            # INVALID AMOUNT CHECK
            # =================================================

            if not isinstance(amount, int) or amount <= 0:

                await item_amount_error(
                    interaction.guild,
                    username,
                    name,
                    f"Invalid magic item amount: {amount}"
                )

                amount = 1

            magic_lines.append(
                f"• {name} (x{amount}): {desc}"
            )

        # =====================================================
        # BUILD SECTIONS
        # =====================================================

        normal_header = "📦 **Items:**"
        magic_header = "✨ **Magic Items:**"

        # =====================================================
        # CREATE MESSAGE CHUNKS
        # =====================================================

        chunks = []

        current_chunk = (
            f"🎒 **{username}'s Inventory:**\n\n"
        )

        # -----------------------------------------------------
        # NORMAL ITEMS
        # -----------------------------------------------------

        if inventory_lines:

            current_chunk += normal_header + "\n"

            for line in inventory_lines:

                # Check whether adding this line would exceed
                # Discord's 2,000 character message limit.

                test_chunk = (
                    current_chunk
                    + line
                    + "\n"
                )

                if len(test_chunk) > 1900:

                    chunks.append(
                        current_chunk.rstrip()
                    )

                    current_chunk = (
                        f"🎒 **{username}'s Inventory "
                        f"(continued):**\n\n"
                        f"{line}\n"
                    )

                else:

                    current_chunk = test_chunk

        else:

            current_chunk += (
                normal_header
                + "\n• None\n"
            )

        # -----------------------------------------------------
        # MAGIC ITEMS
        # -----------------------------------------------------

        # Add spacing before magic items.

        if magic_lines:

            magic_header_text = (
                "\n"
                + magic_header
                + "\n"
            )

            test_chunk = (
                current_chunk
                + magic_header_text
            )

            if len(test_chunk) > 1900:

                chunks.append(
                    current_chunk.rstrip()
                )

                current_chunk = (
                    f"🎒 **{username}'s Inventory "
                    f"(continued):**\n"
                    f"{magic_header}\n"
                )

            else:

                current_chunk = test_chunk

            # Add magic items one at a time.

            for line in magic_lines:

                test_chunk = (
                    current_chunk
                    + line
                    + "\n"
                )

                if len(test_chunk) > 1900:

                    chunks.append(
                        current_chunk.rstrip()
                    )

                    current_chunk = (
                        f"🎒 **{username}'s Inventory "
                        f"(continued):**\n\n"
                        f"{line}\n"
                    )

                else:

                    current_chunk = test_chunk

        else:

            test_chunk = (
                current_chunk
                + "\n"
                + magic_header
                + "\n• None\n"
            )

            if len(test_chunk) > 1900:

                chunks.append(
                    current_chunk.rstrip()
                )

                current_chunk = (
                    f"🎒 **{username}'s Inventory "
                    f"(continued):**\n\n"
                    f"{magic_header}\n"
                    f"• None\n"
                )

            else:

                current_chunk = test_chunk

        # =====================================================
        # ADD FINAL CHUNK
        # =====================================================

        if current_chunk.strip():

            chunks.append(
                current_chunk.rstrip()
            )

        # =====================================================
        # SEND FIRST MESSAGE
        # =====================================================

        if chunks:

            await interaction.response.send_message(
                chunks[0],
                ephemeral=True
            )

        # =====================================================
        # SEND REMAINING MESSAGES
        # =====================================================

        for chunk in chunks[1:]:

            await interaction.followup.send(
                chunk,
                ephemeral=True
            )

        return

    # =========================================================
    # FUZZY MATCH
    # =========================================================

    matches = difflib.get_close_matches(
        username,
        players.keys(),
        n=1,
        cutoff=0.6
    )

    if matches:

        suggested = matches[0]

        await interaction.response.send_message(
            "❌ Player not found.\n\n"
            f"🔎 Did you mean **{suggested}**?\n\n"
            f"👉 Try again with:\n"
            f"```/getitems {suggested}```",
            ephemeral=True
        )

    else:

        await interaction.response.send_message(
            "❌ Player not found and no close match exists.",
            ephemeral=True
        )

# =========================================================
# Remove Item
# =========================================================
@client.tree.command(
    name="removeitem",
    description="Remove an item (normal or magic) from a player's inventory"
)
async def removeitem(interaction: discord.Interaction, username: str, item: str):

    data = load_data()

    username = username.lower()
    item = item.lower()
    user_key = interaction.user.name.lower()
    players = data.get("players", {})

    # =========================================================
    # 1. USERNAME RESOLUTION (EXACT + FUZZY)
    # =========================================================
    if username not in players:
        matches = difflib.get_close_matches(username, players.keys(), n=1, cutoff=0.6)

        if matches:
            suggested = matches[0]
            await interaction.response.send_message(
                "❌ Player not found.\n\n"
                f"🔎 Did you mean **{suggested}**?\n\n"
                f"👉 Try again with:\n"
                f"```/removeitem {suggested} {item}```",
                ephemeral=True
            )
        else:
            await interaction.response.send_message(
                "❌ Player not found and no close match exists.",
                ephemeral=True
            )
        return

    resolved_user = username

    # =========================================================
    # 2. PERMISSION CHECK
    # =========================================================
    is_admin = interaction.user.guild_permissions.administrator

    has_dm_role = any(
        role.name.lower() == "dm"
        for role in interaction.user.roles
    )

    has_tech_role = any(
        role.name.lower() == "tech"
        for role in interaction.user.roles
    )

    is_self = user_key == resolved_user

    if not (is_admin or has_dm_role or has_tech_role or is_self):
        await interaction.response.send_message(
            "❌ You can only remove your own items unless you are "
            "an administrator, DM, or Tech.",
            ephemeral=True
        )
        return

    player = players[resolved_user]

    # =========================================================
    # 3. SAFE STRUCTURE SETUP
    # =========================================================
    if len(player) < 5 or player[4] is None:
        player[4] = []

    if len(player) < 6 or player[5] is None:
        player[5] = {}

    inventory = player[4]
    magic_items = player[5]

    # =========================================================
    # 4. NORMAL ITEM CHECK
    # =========================================================
    if item in inventory:
        inventory.remove(item)
        save_data(data)

        await interaction.response.send_message(
            f"🗑️ Removed **{item}** from {resolved_user}'s inventory.",
            ephemeral=True
        )
        return

    normal_matches = difflib.get_close_matches(item, inventory, n=1, cutoff=0.6)

    if normal_matches:
        suggested = normal_matches[0]

        await interaction.response.send_message(
            "❌ Item not found exactly.\n\n"
            f"🔎 Did you mean **{suggested}**?\n\n"
            f"👉 Try again with:\n"
            f"```/removeitem {resolved_user} {suggested}```",
            ephemeral=True
        )
        return

    # =========================================================
    # 5. MAGIC ITEM CHECK (UPDATED STACK SYSTEM)
    # =========================================================
    if item in magic_items:

        item_data = magic_items[item]

        # ensure structure safety
        if not isinstance(item_data, dict):
            await interaction.response.send_message(
                "❌ Corrupted magic item data detected.",
                ephemeral=True
            )
            return

        amount = item_data.get("amount", 1)

        # CASE 1: MORE THAN 1 → decrement
        if amount > 1:
            item_data["amount"] = amount - 1
            save_data(data)

            await interaction.response.send_message(
                f"✨ Removed 1 stack of **{item}** from {resolved_user}. (Remaining: {item_data['amount']})",
                ephemeral=True
            )
            return

        # CASE 2: 1 or less → ERROR + LOG
        error_msg = (
            f"🚨 MAGIC ITEM ERROR 🚨\n"
            f"User: {resolved_user}\n"
            f"Item: {item}\n"
            f"Issue: Attempted to reduce amount below 1.\n"
            f"Action required: please resolve this issue."
        )

        await interaction.response.send_message(
            "❌ Cannot remove item. Error has been reported to admins.",
            ephemeral=True
        )

        # send to downtime channel
        try:
            channel = None

            for guild in interaction.client.guilds:
                for cat in guild.categories:
                    if cat.name.lower() == "downtime":
                        for ch in cat.channels:
                            if ch.name == "seraphi-error-reports":
                                channel = ch
                                break

            if channel:
                await channel.send(error_msg)

        except Exception as e:
            print(f"Error logging to downtime channel: {e}")

        return

    # =========================================================
    # 6. MAGIC ITEM FUZZY MATCH
    # =========================================================
    magic_matches = difflib.get_close_matches(item, magic_items.keys(), n=1, cutoff=0.6)

    if magic_matches:
        suggested = magic_matches[0]

        await interaction.response.send_message(
            "❌ Magic item not found exactly.\n\n"
            f"🔎 Did you mean **{suggested}**?\n\n"
            f"👉 Try again with:\n"
            f"```/removeitem {resolved_user} {suggested}```",
            ephemeral=True
        )
        return

    # =========================================================
    # 7. NOT FOUND
    # =========================================================
    await interaction.response.send_message(
        "❌ Item not found in normal inventory or magic items.",
        ephemeral=True
    )

# =========================================================
# Buy Item
# =========================================================
@client.tree.command(
    name="buyitem",
    description="Buy an item from the shop"
)
async def buyitem(interaction: discord.Interaction, item: str):

    data = load_data()
    shop = load_shop()

    username = interaction.user.name.lower()
    item = item.lower()

    # =========================================================
    # PLAYER CHECK
    # =========================================================

    if username not in data.get("players", {}):
        await interaction.response.send_message(
            "❌ You are not registered as a player.",
            ephemeral=True
        )
        return

    player = data["players"][username]

    # =========================================================
    # ENSURE PLAYER DATA STRUCTURE
    # =========================================================

    # Slot 4 = normal inventory
    if len(player) < 5 or player[4] is None:
        while len(player) < 5:
            player.append([])

    # Slot 5 = magic inventory
    if len(player) < 6 or player[5] is None:
        while len(player) < 6:
            player.append({})

    # Slot 6 = class
    if len(player) < 7 or player[6] is None:
        await interaction.response.send_message(
            "❌ Your character class is missing from the player database. "
            "Please contact a DM.",
            ephemeral=True
        )
        return

    # Slot 7 = discount tracking
    if len(player) < 8 or player[7] is None:
        while len(player) < 8:
            player.append({})

    # Make sure slot 7 is a dictionary
    if not isinstance(player[7], dict):
        player[7] = {}

    inventory = player[4]
    magic_items = player[5]
    discount_data = player[7]

    # =========================================================
    # PLAYER INFORMATION
    # =========================================================

    credits = player[3]

    background = (
        str(player[2]).lower().strip()
        if len(player) > 2
        else ""
    )

    class_type = (
        str(player[6]).lower().strip()
        if len(player) > 6
        else ""
    )

    # =========================================================
    # ITEM LOOKUP
    # =========================================================

    if item in shop:

        item_data = shop[item]

    else:

        matches = difflib.get_close_matches(
            item,
            shop.keys(),
            n=5,
            cutoff=0.5
        )

        if matches:

            suggestions = "\n".join(
                [f"• {match}" for match in matches]
            )

            await interaction.response.send_message(
                "❌ Item not found.\n\n"
                "🔎 Did you mean:\n"
                f"{suggestions}\n\n"
                "👉 Try again with the exact name.",
                ephemeral=True
            )

        else:

            await interaction.response.send_message(
                "❌ Item not found and no similar items exist.",
                ephemeral=True
            )

        return

    # =========================================================
    # PRICE CHECK
    # =========================================================

    original_price = item_data.get("price", 0)

    if (
        not isinstance(original_price, (int, float))
        or original_price <= 0
    ):

        await item_amount_error(
            interaction.guild,
            username,
            item,
            f"Invalid item price: {original_price}"
        )

        await interaction.response.send_message(
            "❌ This item has an invalid price. "
            "Admins have been notified.",
            ephemeral=True
        )
        return

    price = original_price

    # =========================================================
    # SESSION 0
    # =========================================================

    session_zero = data.get("session 0", False)

    # =========================================================
    # ITEM TYPES
    # =========================================================

    is_cyberware = item_data.get("cyberware", False)
    is_bioware = item_data.get("bioware", False)
    is_mageware = item_data.get("mageware", False)

    # =========================================================
    # DETERMINE WARE TYPE
    # =========================================================

    ware_types = []

    if is_cyberware:
        ware_types.append("cyberware")

    if is_bioware:
        ware_types.append("bioware")

    if is_mageware:
        ware_types.append("mageware")

    # An item should normally only have one ware type.
    if len(ware_types) > 1:

        await item_amount_error(
            interaction.guild,
            username,
            item,
            f"Item has multiple ware types: {ware_types}"
        )

        await interaction.response.send_message(
            "❌ This item has an invalid ware configuration. "
            "Admins have been notified.",
            ephemeral=True
        )
        return

    ware_type = ware_types[0] if ware_types else None

    # =========================================================
    # DISCOUNT ELIGIBILITY
    # =========================================================

    # ---------------------------------------------------------
    # CYBERWARE CLASSES
    # ---------------------------------------------------------

    cyberware_classes = {
        "psion",
        "roboticist",
        "scientist",
        "vanguard",
        "fighter",
        "rogue"
    }

    cyberware_backgrounds = set()

    # ---------------------------------------------------------
    # BIOWARE CLASSES
    # ---------------------------------------------------------

    bioware_classes = {
        "adept",
        "fighter",
        "psion",
        "survivalist"
    }

    bioware_backgrounds = {
        "fugitive"
    }

    # ---------------------------------------------------------
    # MAGEWARE CLASSES
    # ---------------------------------------------------------

    mageware_classes = {
        "bard",
        "oracle",
        "sorcerer"
    }

    mageware_backgrounds = {
        "occultist"
    }

    # =========================================================
    # DISCOUNT STATUS
    # =========================================================

    discounted = False
    discount_reason = None

    # These are only saved after the purchase succeeds.
    new_test_subject_choice = None
    new_plainshifter_choice = None

    # =========================================================
    # DETERMINE EXISTING UNLIMITED DISCOUNTS
    # =========================================================
    #
    # This is primarily used for Test Subject.
    #
    # Example:
    #
    # Psion:
    #   Cyberware = half price
    #   Bioware   = half price
    #
    # Therefore Test Subject automatically chooses:
    #   Mageware
    #
    # =========================================================

    existing_unlimited_discounts = set()

    # ---------------------------------------------------------
    # CLASS DISCOUNTS
    # ---------------------------------------------------------

    if class_type in cyberware_classes:
        existing_unlimited_discounts.add("cyberware")

    if class_type in bioware_classes:
        existing_unlimited_discounts.add("bioware")

    if class_type in mageware_classes:
        existing_unlimited_discounts.add("mageware")

    # ---------------------------------------------------------
    # BACKGROUND DISCOUNTS
    # ---------------------------------------------------------

    if background in cyberware_backgrounds:
        existing_unlimited_discounts.add("cyberware")

    if background in bioware_backgrounds:
        existing_unlimited_discounts.add("bioware")

    if background in mageware_backgrounds:
        existing_unlimited_discounts.add("mageware")

    # =========================================================
    # TEST SUBJECT
    # =========================================================
    #
    # Test Subject receives unlimited half-price ware of ONE
    # category:
    #
    #   Cyberware
    #   Bioware
    #   Mageware
    #
    # If the character already receives unlimited discounts for
    # one or more categories through their class/background,
    # Test Subject automatically chooses a category they do NOT
    # already receive.
    #
    # Example:
    #
    # Psion + Test Subject
    #
    # Psion already gives:
    #   Cyberware
    #   Bioware
    #
    # Therefore Test Subject automatically chooses:
    #   Mageware
    #
    # =========================================================

    if session_zero and background == "test subject":

        test_subject_choice = discount_data.get(
            "test_subject_choice"
        )

        # -----------------------------------------------------
        # AUTOMATICALLY SELECT A USEFUL CATEGORY
        # -----------------------------------------------------

        if not test_subject_choice:

            available_test_subject_types = [
                "cyberware",
                "bioware",
                "mageware"
            ]

            for possible_type in available_test_subject_types:

                if possible_type not in existing_unlimited_discounts:

                    test_subject_choice = possible_type

                    new_test_subject_choice = possible_type

                    break

        # -----------------------------------------------------
        # APPLY TEST SUBJECT DISCOUNT
        # -----------------------------------------------------

        if (
            ware_type
            and test_subject_choice
            and ware_type == test_subject_choice
        ):

            discounted = True

            discount_reason = (
                f"Test Subject {ware_type} discount"
            )

    # =========================================================
    # NORMAL CLASS/BACKGROUND DISCOUNTS
    # =========================================================

    if session_zero and ware_type:

        # =====================================================
        # CYBERWARE CLASS
        # =====================================================

        if (
            ware_type == "cyberware"
            and class_type in cyberware_classes
        ):

            discounted = True

            discount_reason = (
                f"{class_type.title()} cyberware discount"
            )

        # =====================================================
        # BIOWARE CLASS
        # =====================================================

        elif (
            ware_type == "bioware"
            and class_type in bioware_classes
        ):

            discounted = True

            discount_reason = (
                f"{class_type.title()} bioware discount"
            )

        # =====================================================
        # MAGEWARE CLASS
        # =====================================================

        elif (
            ware_type == "mageware"
            and class_type in mageware_classes
        ):

            discounted = True

            discount_reason = (
                f"{class_type.title()} mageware discount"
            )

        # =====================================================
        # CYBERWARE BACKGROUND
        # =====================================================

        elif (
            ware_type == "cyberware"
            and background in cyberware_backgrounds
        ):

            discounted = True

            discount_reason = (
                f"{background.title()} cyberware discount"
            )

        # =====================================================
        # BIOWARE BACKGROUND
        # =====================================================

        elif (
            ware_type == "bioware"
            and background in bioware_backgrounds
        ):

            discounted = True

            discount_reason = (
                f"{background.title()} bioware discount"
            )

        # =====================================================
        # MAGEWARE BACKGROUND
        # =====================================================

        elif (
            ware_type == "mageware"
            and background in mageware_backgrounds
        ):

            discounted = True

            discount_reason = (
                f"{background.title()} mageware discount"
            )

    # =========================================================
    # PLAINSHIFTER
    # =========================================================
    #
    # Plainshifter receives unlimited half-price:
    #
    #   Bioware OR Mageware
    #
    # Once they purchase one type, that type is locked in.
    #
    # =========================================================

    if session_zero and class_type == "plainshifter":

        plainshifter_choice = discount_data.get(
            "plainshifter_choice"
        )

        if ware_type in {
            "bioware",
            "mageware"
        }:

            # -------------------------------------------------
            # No choice yet
            # -------------------------------------------------

            if not plainshifter_choice:

                discounted = True

                new_plainshifter_choice = ware_type

                discount_reason = (
                    f"Plainshifter {ware_type} discount"
                )

            # -------------------------------------------------
            # Already chose this type
            # -------------------------------------------------

            elif plainshifter_choice == ware_type:

                discounted = True

                discount_reason = (
                    f"Plainshifter {ware_type} discount"
                )

    # =========================================================
    # SOLDIER
    # =========================================================
    #
    # Soldier receives ONE total half-price Cyberware OR
    # Bioware purchase.
    #
    # =========================================================

    if (
        session_zero
        and background == "soldier"
    ):

        soldier_used = discount_data.get(
            "soldier_used",
            False
        )

        if (
            not soldier_used
            and ware_type in {
                "cyberware",
                "bioware"
            }
        ):

            discounted = True

            discount_reason = (
                f"Soldier one-time {ware_type} discount"
            )

    # =========================================================
    # NATURALIST
    # =========================================================
    #
    # Naturalist receives one half-price Bioware purchase.
    #
    # =========================================================

    if (
        session_zero
        and background == "naturalist"
        and ware_type == "bioware"
    ):

        naturalist_used = discount_data.get(
            "naturalist_used",
            False
        )

        if not naturalist_used:

            discounted = True

            discount_reason = (
                "Naturalist one-time bioware discount"
            )

    # =========================================================
    # APPLY HALF PRICE
    # =========================================================

    if discounted:

        price = original_price // 2

    # =========================================================
    # FINAL CREDIT CHECK
    # =========================================================

    if credits < price:

        await interaction.response.send_message(
            f"❌ You need **{price}** credits but only have "
            f"**{credits}**.",
            ephemeral=True
        )

        # IMPORTANT:
        # No Test Subject or Plainshifter choice is saved
        # here because the purchase failed.

        return

    # =========================================================
    # SAVE TEST SUBJECT CHOICE
    # =========================================================

    if new_test_subject_choice:

        discount_data["test_subject_choice"] = (
            new_test_subject_choice
        )

    # =========================================================
    # SAVE PLAINSHIFTER CHOICE
    # =========================================================

    if new_plainshifter_choice:

        discount_data["plainshifter_choice"] = (
            new_plainshifter_choice
        )

    # =========================================================
    # SAVE SOLDIER USAGE
    # =========================================================

    if (
        discounted
        and background == "soldier"
        and ware_type in {
            "cyberware",
            "bioware"
        }
    ):

        discount_data["soldier_used"] = True

    # =========================================================
    # SAVE NATURALIST USAGE
    # =========================================================

    if (
        discounted
        and background == "naturalist"
        and ware_type == "bioware"
    ):

        discount_data["naturalist_used"] = True

    # =========================================================
    # DEDUCT CREDITS
    # =========================================================

    player[3] -= price

    # =========================================================
    # CONTAINER ITEM
    # =========================================================

    if "contains" in item_data:

        for contained_item in item_data["contains"]:

            contained_item = contained_item.lower()

            # -------------------------------------------------
            # MAGIC ITEM INSIDE CONTAINER
            # -------------------------------------------------

            if (
                contained_item in shop
                and shop[contained_item].get("magic", False)
            ):

                desc = shop[contained_item].get(
                    "description",
                    "No description provided."
                )

                if contained_item in magic_items:

                    existing = magic_items[contained_item]

                    if isinstance(existing, dict):

                        existing["amount"] = (
                            existing.get("amount", 0) + 1
                        )

                    else:

                        magic_items[contained_item] = {
                            "description": desc,
                            "amount": 1
                        }

                else:

                    magic_items[contained_item] = {
                        "description": desc,
                        "amount": 1
                    }

            # -------------------------------------------------
            # NORMAL ITEM INSIDE CONTAINER
            # -------------------------------------------------

            else:

                inventory.append(contained_item)

        message = (
            f"🛒 You bought **{item}** for "
            f"**{price}** credits.\n"
            f"📦 It contained "
            f"{len(item_data['contains'])} items."
        )

    # =========================================================
    # MAGIC ITEM
    # =========================================================

    elif item_data.get("magic", False):

        desc = item_data.get(
            "description",
            "No description provided."
        )

        if item in magic_items:

            existing = magic_items[item]

            if not isinstance(existing, dict):

                existing = {
                    "description": desc,
                    "amount": 0
                }

            amount = existing.get("amount", 0) + 1

            # -------------------------------------------------
            # SAFETY CHECK
            # -------------------------------------------------

            if (
                not isinstance(amount, int)
                or amount <= 0
            ):

                await item_amount_error(
                    interaction.guild,
                    username,
                    item,
                    f"Magic item reached invalid amount: {amount}"
                )

                await interaction.response.send_message(
                    "❌ Magic item is in an invalid state. "
                    "Admins have been notified.",
                    ephemeral=True
                )

                return

            magic_items[item] = {
                "description": desc,
                "amount": amount
            }

        else:

            magic_items[item] = {
                "description": desc,
                "amount": 1
            }

        message = (
            f"✨ You bought **{item}** for "
            f"**{price}** credits.\n"
            f"📜 Added to magic inventory."
        )

    # =========================================================
    # NORMAL ITEM
    # =========================================================

    else:

        inventory.append(item)

        message = (
            f"🛒 You bought **{item}** for "
            f"**{price}** credits."
        )

    # =========================================================
    # DISCOUNT MESSAGE
    # =========================================================

    if discounted:

        message += (
            f"\n🏷️ **Half price applied!**"
            f"\n📜 Reason: {discount_reason}"
            f"\n💰 Original price: **{original_price}**"
            f"\n💰 Discounted price: **{price}**"
        )

    # =========================================================
    # SAVE DATA
    # =========================================================

    save_data(data)

    # =========================================================
    # RESPONSE
    # =========================================================

    await interaction.response.send_message(
        message,
        ephemeral=True
    )

# =========================================================
# Get Item Price
# =========================================================
@client.tree.command(
    name="getitemprice",
    description="Get the price of an item"
)
async def getitemprice(interaction: discord.Interaction, item: str):

    shop = load_shop()
    item = item.lower()

    # ---------------- EXACT MATCH ----------------
    if item in shop:
        item_data = shop[item]
        price = item_data.get("price", 0)

        await interaction.response.send_message(
            f"💰 **{item}** costs {price} cc.",
            ephemeral=True
        )
        return

    # ---------------- FUZZY MATCH ----------------
    matches = difflib.get_close_matches(item, shop.keys(), n=5, cutoff=0.5)

    if matches:
        suggestions = "\n".join([f"• {m}" for m in matches])

        await interaction.response.send_message(
            "❌ Item not found.\n\n"
            "🔎 Did you mean:\n"
            f"{suggestions}\n\n"
            "👉 Try again with the exact name.",
            ephemeral=True
        )
    else:
        await interaction.response.send_message(
            "❌ Item not found and no similar items exist.",
            ephemeral=True
        )

# =========================================================
# Set Level
# =========================================================
@client.tree.command(
    name="setlevel",
    description="Set the global level value (admin only)"
)
async def setlevel(interaction: discord.Interaction, level: int):

    # =========================================================
    # PERMISSION CHECK
    # =========================================================
        
    is_admin = interaction.user.guild_permissions.administrator
    
    has_dm_role = any(
        role.name.lower() == "dm"
        for role in interaction.user.roles
    )
        
    has_tech_role = any(
        role.name.lower() == "tech"
        for role in interaction.user.roles
    )
        
    if not (is_admin or has_dm_role or has_tech_role):
        await interaction.response.send_message(
            "❌ You do not have permission to use this command.",
            ephemeral=True
            )
        return

    # ---------------- VALIDATE LEVEL RANGE ----------------
    if level < 1 or level > 20:
        await interaction.response.send_message(
            "❌ That is not a valid level. Level must be between 0 and 20.",
            ephemeral=True
        )
        return

    data = load_data()

    # ---------------- SET LEVEL ----------------
    data["level"] = level
    save_data(data)

    # ---------------- CONFIRMATION ----------------
    await interaction.response.send_message(
        f"📊 Level has been set to **{level}**.",
        ephemeral=True
    )

# =========================================================
# Add to Table (Admin Only)
# =========================================================
@client.tree.command(
    name="addtable",
    description="Add a player to the table based on the current category (admin only)"
)
async def addtable(interaction: discord.Interaction, username: str):

    # =========================================================
    # PERMISSION CHECK
    # =========================================================
        
    is_admin = interaction.user.guild_permissions.administrator
    
    has_dm_role = any(
        role.name.lower() == "dm"
        for role in interaction.user.roles
    )
        
    has_tech_role = any(
        role.name.lower() == "tech"
        for role in interaction.user.roles
    )
        
    if not (is_admin or has_dm_role or has_tech_role):
        await interaction.response.send_message(
            "❌ You do not have permission to use this command.",
            ephemeral=True
            )
        return

    data = load_data()

    # =========================================================
    # GET TABLE FROM CATEGORY (NEW CLEAN METHOD)
    # =========================================================
    table_name = get_table_from_interaction(interaction)

    if not table_name:
        await interaction.response.send_message(
            "❌ This is not a valid table category.",
            ephemeral=True
        )
        return

    # =========================================================
    # ENSURE TABLE EXISTS
    # =========================================================
    if "tables" not in data:
        data["tables"] = {}

    if table_name not in data["tables"]:
        data["tables"][table_name] = {
            "players": {},
            "loot": {
                "money": 0,
                "items": {}
            }
        }

    # =========================================================
    # GLOBAL PLAYER DATABASE
    # =========================================================
    players_db = data.get("players", {})
    username = username.lower()

    # =========================================================
    # FUZZY MATCH (GLOBAL PLAYERS ONLY)
    # =========================================================
    if username not in players_db:
        matches = difflib.get_close_matches(
            username,
            players_db.keys(),
            n=1,
            cutoff=0.6
        )

        if matches:
            suggested = matches[0]

            await interaction.response.send_message(
                f"❌ Player not found.\n\n"
                f"🔎 Did you mean **{suggested}**?\n\n"
                f"👉 Try again with:\n"
                f"```/addtable {suggested}```",
                ephemeral=True
            )
        else:
            await interaction.response.send_message(
                "❌ Player does not exist in player database.",
                ephemeral=True
            )
        return

    # =========================================================
    # CHECK IF PLAYER IS ALREADY IN ANY TABLE
    # =========================================================
    for table, table_data in data["tables"].items():
        if username in table_data.get("players", {}):
            await interaction.response.send_message(
                f"❌ {username} is already in **{table}**.",
                ephemeral=True
            )
            return

    # =========================================================
    # ADD PLAYER TO TABLE
    # =========================================================
    data["tables"][table_name]["players"][username] = {
        "bids": {},
        "total_bids": 0,
        "claimed": False
    }

    save_data(data)

    # =========================================================
    # CONFIRMATION
    # =========================================================
    await interaction.response.send_message(
        f"✅ Added **{username}** to **{table_name}**.",
        ephemeral=True
    )

# =========================================================
# Remove from Table (Admin Only)
# =========================================================
@client.tree.command(
    name="removetable",
    description="Remove a player from the table based on the current category (admin only)"
)
async def removetable(interaction: discord.Interaction, username: str):

    # =========================================================
    # PERMISSION CHECK
    # =========================================================
        
    is_admin = interaction.user.guild_permissions.administrator
    
    has_dm_role = any(
        role.name.lower() == "dm"
        for role in interaction.user.roles
    )
        
    has_tech_role = any(
        role.name.lower() == "tech"
        for role in interaction.user.roles
    )
        
    if not (is_admin or has_dm_role or has_tech_role):
        await interaction.response.send_message(
            "❌ You do not have permission to use this command.",
            ephemeral=True
            )
        return

    data = load_data()

    # =========================================================
    # GET TABLE FROM CATEGORY (NEW SYSTEM)
    # =========================================================
    table_name = get_table_from_interaction(interaction)

    if not table_name:
        await interaction.response.send_message(
            "❌ This is not a valid table category.",
            ephemeral=True
        )
        return

    # =========================================================
    # ENSURE TABLE EXISTS
    # =========================================================
    if "tables" not in data or table_name not in data["tables"]:
        await interaction.response.send_message(
            "❌ This table does not exist.",
            ephemeral=True
        )
        return

    table_players = data["tables"][table_name].get("players", {})

    username = username.lower()

    # =========================================================
    # EXACT MATCH REMOVE
    # =========================================================
    if username in table_players:
        del table_players[username]
        save_data(data)

        await interaction.response.send_message(
            f"🗑️ Removed **{username}** from **{table_name}**.",
            ephemeral=True
        )
        return

    # =========================================================
    # FUZZY MATCH (WITHIN TABLE ONLY)
    # =========================================================
    matches = difflib.get_close_matches(
        username,
        table_players.keys(),
        n=1,
        cutoff=0.6
    )

    if matches:
        suggested = matches[0]

        await interaction.response.send_message(
            f"❌ Player not found in this table.\n\n"
            f"🔎 Did you mean **{suggested}**?\n\n"
            f"👉 Try again with:\n"
            f"```/removetable {suggested}```",
            ephemeral=True
        )
        return

    # =========================================================
    # NOT FOUND
    # =========================================================
    await interaction.response.send_message(
        "❌ Player not found in this table.",
        ephemeral=True
    )

# =========================================================
# Clear Table Players (Admin Only)
# =========================================================
@client.tree.command(
    name="cleartableplayers",
    description="Clear all players from the current table (admin only)"
)
async def cleartableplayers(interaction: discord.Interaction):

    # =========================================================
    # PERMISSION CHECK
    # =========================================================
        
    is_admin = interaction.user.guild_permissions.administrator
    
    has_dm_role = any(
        role.name.lower() == "dm"
        for role in interaction.user.roles
    )
        
    has_tech_role = any(
        role.name.lower() == "tech"
        for role in interaction.user.roles
    )
        
    if not (is_admin or has_dm_role or has_tech_role):
        await interaction.response.send_message(
            "❌ You do not have permission to use this command.",
            ephemeral=True
            )
        return

    # =========================================================
    # LOAD DATA
    # =========================================================

    data = load_data()

    # =========================================================
    # GET TABLE FROM CATEGORY (NEW SYSTEM)
    # =========================================================
    table_name = get_table_from_interaction(interaction)

    if not table_name:
        await interaction.response.send_message(
            "❌ This is not a valid table category.",
            ephemeral=True
        )
        return

    # =========================================================
    # ENSURE TABLE EXISTS
    # =========================================================
    if "tables" not in data or table_name not in data["tables"]:
        await interaction.response.send_message(
            "❌ This table does not exist.",
            ephemeral=True
        )
        return

    # =========================================================
    # CLEAR PLAYERS ONLY
    # =========================================================
    data["tables"][table_name]["players"] = {}

    save_data(data)

    # =========================================================
    # CONFIRMATION
    # =========================================================
    await interaction.response.send_message(
        f"🧹 All players have been removed from **{table_name}**.",
        ephemeral=True
    )

# =========================================================
# Get Table List
# =========================================================
@client.tree.command(
    name="gettable",
    description="View all players in the current table"
)
async def gettable(interaction: discord.Interaction):

    data = load_data()

    # =========================================================
    # GET TABLE FROM CATEGORY (NEW SYSTEM)
    # =========================================================
    table_name = get_table_from_interaction(interaction)

    if not table_name:
        await interaction.response.send_message(
            "❌ This command must be used inside a table category channel.",
            ephemeral=True
        )
        return

    # =========================================================
    # CHECK TABLE EXISTS
    # =========================================================
    if "tables" not in data or table_name not in data["tables"]:
        await interaction.response.send_message(
            "❌ This table does not exist.",
            ephemeral=True
        )
        return

    players = data["tables"][table_name].get("players", {})

    # =========================================================
    # EMPTY TABLE CHECK
    # =========================================================
    if not players:
        await interaction.response.send_message(
            f"📭 **{table_name}** currently has no players.",
            ephemeral=True
        )
        return

    # =========================================================
    # FORMAT PLAYER LIST
    # =========================================================
    player_list = "\n".join(
        [f"• {player}" for player in players.keys()]
    )

    # =========================================================
    # RESPONSE
    # =========================================================
    await interaction.response.send_message(
        f"📋 **Players in {table_name}:**\n\n{player_list}",
        ephemeral=True
    )

# =========================================================
# Set Table Money (Admin Only)present
# =========================================================
@client.tree.command(
    name="settablemoney",
    description="Set the loot money for the current table (admin only)"
)
async def settablemoney(interaction: discord.Interaction, amount: int):

    # =========================================================
    # PERMISSION CHECK
    # =========================================================
        
    is_admin = interaction.user.guild_permissions.administrator
    
    has_dm_role = any(
        role.name.lower() == "dm"
        for role in interaction.user.roles
    )
        
    has_tech_role = any(
        role.name.lower() == "tech"
        for role in interaction.user.roles
    )
        
    if not (is_admin or has_dm_role or has_tech_role):
        await interaction.response.send_message(
            "❌ You do not have permission to use this command.",
            ephemeral=True
            )
        return

    # =========================================================
    # VALIDATE INPUT
    # =========================================================
    if amount < 0:
        await interaction.response.send_message(
            "❌ Amount must be a positive whole number.",
            ephemeral=True
        )
        return

    data = load_data()

    # =========================================================
    # GET TABLE FROM CATEGORY (NEW SYSTEM)
    # =========================================================
    table_name = get_table_from_interaction(interaction)

    if not table_name:
        await interaction.response.send_message(
            "❌ This command must be used inside a table category channel.",
            ephemeral=True
        )
        return

    # =========================================================
    # ENSURE TABLE EXISTS
    # =========================================================
    if "tables" not in data or table_name not in data["tables"]:
        await interaction.response.send_message(
            "❌ This table does not exist.",
            ephemeral=True
        )
        return

    # =========================================================
    # SET LOOT MONEY
    # =========================================================
    data["tables"][table_name]["loot"]["money"] = amount

    save_data(data)

    # =========================================================
    # CONFIRMATION
    # =========================================================
    await interaction.response.send_message(
        f"💰 Set **{table_name}** loot money to **{amount}**cc.",
        ephemeral=True
    )

# =========================================================
# Reset Table Money (ADMIN ONLY)
# =========================================================
@client.tree.command(
    name="resettablemoney",
    description="Reset the loot money for the current table (admin only)"
)
async def resettablemoney(interaction: discord.Interaction):

    # =========================================================
    # PERMISSION CHECK
    # =========================================================
        
    is_admin = interaction.user.guild_permissions.administrator
    
    has_dm_role = any(
        role.name.lower() == "dm"
        for role in interaction.user.roles
    )
        
    has_tech_role = any(
        role.name.lower() == "tech"
        for role in interaction.user.roles
    )
        
    if not (is_admin or has_dm_role or has_tech_role):
        await interaction.response.send_message(
            "❌ You do not have permission to use this command.",
            ephemeral=True
            )
        return

    data = load_data()

    # =========================================================
    # TABLE RESOLVE (UPDATED)
    # =========================================================
    table_name = get_table_from_interaction(interaction)

    if not table_name:
        await interaction.response.send_message(
            "❌ This command must be used inside a table category channel.",
            ephemeral=True
        )
        return

    # =========================================================
    # ENSURE TABLE EXISTS
    # =========================================================
    if "tables" not in data or table_name not in data["tables"]:
        await interaction.response.send_message(
            "❌ This table does not exist.",
            ephemeral=True
        )
        return

    # =========================================================
    # RESET MONEY
    # =========================================================
    data["tables"][table_name]["loot"]["money"] = 0

    save_data(data)

    # =========================================================
    # CONFIRMATION
    # =========================================================
    await interaction.response.send_message(
        f"🧹 Reset loot money for **{table_name}** to **0**cc.",
        ephemeral=True
    )

# =========================================================
# Get Table Money
# =========================================================
@client.tree.command(
    name="gettablemoney",
    description="View the current loot money for this table"
)
async def gettablemoney(interaction: discord.Interaction):

    data = load_data()

    # =========================================================
    # TABLE RESOLVE (UPDATED)
    # =========================================================
    table_name = get_table_from_interaction(interaction)

    if not table_name:
        await interaction.response.send_message(
            "❌ This command must be used inside a table category channel.",
            ephemeral=True
        )
        return

    # =========================================================
    # CHECK TABLE EXISTS
    # =========================================================
    if "tables" not in data or table_name not in data["tables"]:
        await interaction.response.send_message(
            "❌ This table does not exist.",
            ephemeral=True
        )
        return

    # =========================================================
    # GET MONEY VALUE
    # =========================================================
    money = data["tables"][table_name]["loot"].get("money", 0)

    # =========================================================
    # RESPONSE
    # =========================================================
    await interaction.response.send_message(
        f"💰 **{table_name} loot money:** {money}cc",
        ephemeral=True
    )

# =========================================================
# Add Table Item (Admin Only)
# =========================================================
@client.tree.command(
    name="addtableitem",
    description="Add a loot item to the current table (admin only)"
)
async def addtableitem(
    interaction: discord.Interaction,
    item_name: str,
    description: str,
    is_magic: bool
):

    # =========================================================
    # PERMISSION CHECK
    # =========================================================
        
    is_admin = interaction.user.guild_permissions.administrator
    
    has_dm_role = any(
        role.name.lower() == "dm"
        for role in interaction.user.roles
    )
        
    has_tech_role = any(
        role.name.lower() == "tech"
        for role in interaction.user.roles
    )
        
    if not (is_admin or has_dm_role or has_tech_role):
        await interaction.response.send_message(
            "❌ You do not have permission to use this command.",
            ephemeral=True
            )
        return

    data = load_data()

    # =========================================================
    # TABLE RESOLVE
    # =========================================================
    table_name = get_table_from_interaction(interaction)

    if not table_name:
        await interaction.response.send_message(
            "❌ This command must be used inside a table category channel.",
            ephemeral=True
        )
        return

    # =========================================================
    # ENSURE TABLE EXISTS
    # =========================================================
    if "tables" not in data:
        data["tables"] = {}

    if table_name not in data["tables"]:
        data["tables"][table_name] = {
            "players": {},
            "loot": {
                "money": 0,
                "items": {}
            }
        }

    table = data["tables"][table_name]

    # =========================================================
    # ENSURE LOOT STRUCTURE EXISTS
    # =========================================================
    table.setdefault("loot", {})
    table["loot"].setdefault("items", {})

    loot_items = table["loot"]["items"]

    # =========================================================
    # NORMALIZE ITEM NAME
    # =========================================================
    item_name = item_name.lower()

    # =========================================================
    # ITEM ALREADY EXISTS
    # =========================================================
    if item_name in loot_items:
        loot_items[item_name]["amount"] = loot_items[item_name].get("amount", 1) + 1

        save_data(data)

        await interaction.response.send_message(
            f"📦 Increased **{item_name}** quantity to **{loot_items[item_name]['amount']}**.",
            ephemeral=True
        )
        return

    # =========================================================
    # CREATE NEW ITEM
    # =========================================================
    loot_items[item_name] = {
        "description": description,
        "amount": 1,
        "claimed": [],
        "magic": is_magic,
        "bids": []
    }

    save_data(data)

    # =========================================================
    # CONFIRMATION
    # =========================================================
    await interaction.response.send_message(
        f"📦 Added **{item_name}** to **{table_name}** loot.\n"
        f"📦 Quantity: **1**\n"
        f"✨ Magic: {is_magic}\n"
        f"📜 Description: {description}",
        ephemeral=True
    )

# =========================================================
# Remove Table Item (ADMIN ONLY)
# =========================================================
@client.tree.command(
    name="removetableitem",
    description="Remove a loot item from the current table (admin only)"
)
async def removetableitem(interaction: discord.Interaction, item_name: str):

    # =========================================================
    # PERMISSION CHECK
    # =========================================================
        
    is_admin = interaction.user.guild_permissions.administrator
    
    has_dm_role = any(
        role.name.lower() == "dm"
        for role in interaction.user.roles
    )
        
    has_tech_role = any(
        role.name.lower() == "tech"
        for role in interaction.user.roles
    )
        
    if not (is_admin or has_dm_role or has_tech_role):
        await interaction.response.send_message(
            "❌ You do not have permission to use this command.",
            ephemeral=True
            )
        return

    data = load_data()

    # =========================================================
    # GET TABLE FROM INTERACTION (HELPER)
    # =========================================================
    table_name = get_table_from_interaction(interaction)

    if not table_name:
        await interaction.response.send_message(
            "❌ This command must be used inside a valid table category channel.",
            ephemeral=True
        )
        return

    # =========================================================
    # ENSURE TABLE EXISTS
    # =========================================================
    if "tables" not in data or table_name not in data["tables"]:
        await interaction.response.send_message(
            "❌ This table does not exist.",
            ephemeral=True
        )
        return

    # =========================================================
    # GET LOOT ITEMS
    # =========================================================
    loot_items = data["tables"][table_name].get("loot", {}).get("items", {})

    if not loot_items:
        await interaction.response.send_message(
            "❌ There are no items in this table.",
            ephemeral=True
        )
        return

    item_name = item_name.lower()

    # =========================================================
    # EXACT MATCH REMOVE
    # =========================================================
    if item_name in loot_items:
        del loot_items[item_name]
        save_data(data)

        await interaction.response.send_message(
            f"🗑️ Removed **{item_name}** from **{table_name}** loot.",
            ephemeral=True
        )
        return

    # =========================================================
    # FUZZY MATCH (LOOT ITEMS ONLY)
    # =========================================================
    matches = difflib.get_close_matches(
        item_name,
        loot_items.keys(),
        n=1,
        cutoff=0.6
    )

    if matches:
        suggested = matches[0]

        await interaction.response.send_message(
            f"❌ Item not found.\n\n"
            f"🔎 Did you mean **{suggested}**?\n\n"
            f"👉 Try again with:\n"
            f"```/removetableitem {suggested}```",
            ephemeral=True
        )
        return

    # =========================================================
    # NOT FOUND
    # =========================================================
    await interaction.response.send_message(
        "❌ Item not found in table loot.",
        ephemeral=True
    )

# =========================================================
# Clear Table Item (ADMIN ONLY)
# =========================================================
@client.tree.command(
    name="cleartableitem",
    description="Clear all loot items from the current table (admin only)"
)
async def cleartableitem(interaction: discord.Interaction):

    # =========================================================
    # PERMISSION CHECK
    # =========================================================
        
    is_admin = interaction.user.guild_permissions.administrator
    
    has_dm_role = any(
        role.name.lower() == "dm"
        for role in interaction.user.roles
    )
        
    has_tech_role = any(
        role.name.lower() == "tech"
        for role in interaction.user.roles
    )
        
    if not (is_admin or has_dm_role or has_tech_role):
        await interaction.response.send_message(
            "❌ You do not have permission to use this command.",
            ephemeral=True
            )
        return

    data = load_data()

    # =========================================================
    # GET TABLE FROM INTERACTION (HELPER)
    # =========================================================
    table_name = get_table_from_interaction(interaction)

    if not table_name:
        await interaction.response.send_message(
            "❌ This command must be used inside a valid table category channel.",
            ephemeral=True
        )
        return

    # =========================================================
    # CHECK TABLE EXISTS
    # =========================================================
    if "tables" not in data or table_name not in data["tables"]:
        await interaction.response.send_message(
            "❌ This table does not exist.",
            ephemeral=True
        )
        return

    # =========================================================
    # CLEAR LOOT ITEMS ONLY
    # =========================================================
    data["tables"][table_name]["loot"]["items"] = {}

    save_data(data)

    # =========================================================
    # CONFIRMATION
    # =========================================================
    await interaction.response.send_message(
        f"🧹 All loot items have been cleared from **{table_name}**.",
        ephemeral=True
    )

# =========================================================
# Get Table Item
# =========================================================
@client.tree.command(
    name="gettableitem",
    description="View all loot items in the current table"
)
async def gettableitem(interaction: discord.Interaction):

    data = load_data()

    # =========================================================
    # GET TABLE FROM INTERACTION (HELPER)
    # =========================================================
    table_name = get_table_from_interaction(interaction)

    if not table_name:
        await interaction.response.send_message(
            "❌ This command must be used inside a valid table category channel.",
            ephemeral=True
        )
        return

    # =========================================================
    # CHECK TABLE EXISTS
    # =========================================================
    if "tables" not in data or table_name not in data["tables"]:
        await interaction.response.send_message(
            "❌ This table does not exist.",
            ephemeral=True
        )
        return

    loot_items = data["tables"][table_name].get(
        "loot", {}
    ).get(
        "items",
        {}
    )

    # =========================================================
    # EMPTY CHECK
    # =========================================================
    if not loot_items:
        await interaction.response.send_message(
            f"📭 **{table_name}** has no loot items.",
            ephemeral=True
        )
        return

    # =========================================================
    # FORMAT ITEMS (NEW CLAIM LIST SYSTEM)
    # =========================================================
    formatted_items = []

    for name, item in loot_items.items():

        desc = item.get(
            "description",
            "No description"
        )

        magic = item.get(
            "magic",
            False
        )

        claimed_list = item.get(
            "claimed",
            []
        )

        amount = item.get(
            "amount",
            1
        )

        # Safety check for amount
        if not isinstance(amount, int) or amount < 1:
            amount = 1

        # Safety check for claimed list
        if not isinstance(claimed_list, list):
            claimed_list = []

        for i in range(amount):

            if i < len(claimed_list):
                claimed_by = claimed_list[i]
            else:
                claimed_by = "Not claimed yet"

            item_text = (
                f"📦 **{name}**\n"
                f"   📜 {desc}\n"
                f"   ✨ Magic: {magic}\n"
                f"   👤 Claimed By: {claimed_by}"
            )

            formatted_items.append(item_text)

    # =========================================================
    # SPLIT INTO DISCORD-SAFE MESSAGES
    # =========================================================
    #
    # Discord allows a maximum of 2,000 characters per message.
    # We use 1,900 as the practical limit to leave a safety margin.
    #
    header = f"📦 **Loot Items in {table_name}:**\n\n"

    max_message_length = 1900

    messages = []
    current_message = header

    for item_text in formatted_items:

        item_with_spacing = item_text + "\n\n"

        # -----------------------------------------------------
        # NORMAL CASE
        # -----------------------------------------------------
        if len(current_message) + len(item_with_spacing) <= max_message_length:

            current_message += item_with_spacing

        # -----------------------------------------------------
        # ITEM DOES NOT FIT
        # -----------------------------------------------------
        else:

            # Save current message if it has content
            if current_message.strip():
                messages.append(
                    current_message.rstrip()
                )

            # Start a new message with this item
            current_message = item_with_spacing

    # =========================================================
    # ADD FINAL MESSAGE
    # =========================================================
    if current_message.strip():
        messages.append(
            current_message.rstrip()
        )

    # =========================================================
    # SEND FIRST MESSAGE
    # =========================================================
    await interaction.response.send_message(
        messages[0],
        ephemeral=True
    )

    # =========================================================
    # SEND REMAINING MESSAGES
    # =========================================================
    for message in messages[1:]:

        await interaction.followup.send(
            message,
            ephemeral=True
        )

# =========================================================
# Present Table Loot
# =========================================================
@client.tree.command(
    name="presenttableloot",
    description="Present loot for the current table (admin only)"
)
async def presenttableloot(interaction: discord.Interaction):
    # Check permissions
    is_admin = interaction.user.guild_permissions.administrator
    has_dm_role = any(
        role.name.lower() == "dm"
        for role in interaction.user.roles
    )
    has_tech_role = any(
        role.name.lower() == "tech"
        for role in interaction.user.roles
    )

    if not (is_admin or has_dm_role or has_tech_role):
        await interaction.response.send_message(
            "❌ You do not have permission to use this command.",
            ephemeral=True
        )
        return

    # Load data
    data = load_data()

    # Get the current table
    table_name = get_table_from_interaction(interaction)

    if not table_name:
        await interaction.response.send_message(
            "❌ This channel is not assigned to a valid table.",
            ephemeral=True
        )
        return

    if table_name not in data.get("tables", {}):
        await interaction.response.send_message(
            f"❌ Table **{table_name}** could not be found.",
            ephemeral=True
        )
        return

    table = data["tables"][table_name]

    # Table to loot channel mapping
    category_to_channel = {
        "hailey table": "haileys-loot",
        "alijah table": "alijahs-loot",
        "spencer table": "spencers-loot",
        "joseph table": "josephs-loot",
        "rotation table": "rotation-loot"
    }

    channel_name = category_to_channel.get(table_name.lower())

    if not channel_name:
        await interaction.response.send_message(
            f"❌ No loot channel is configured for **{table_name}**.",
            ephemeral=True
        )
        return

    # Find the loot channel
    loot_channel = discord.utils.get(
        interaction.guild.text_channels,
        name=channel_name
    )

    if not loot_channel:
        await interaction.response.send_message(
            f"❌ Could not find the loot channel **#{channel_name}**.",
            ephemeral=True
        )
        return

    # Make sure loot exists
    loot = table.get("loot", {})
    loot_items = loot.get("items", {})
    money = loot.get("money", 0)

    # Start bidding
    table["bid active"] = True

    # Reset player bidding/claiming information
    players = table.get("players", {})

    for username, player in players.items():
        player["claimed"] = False
        player["total bids"] = 0
        player["bids"] = []
        player["total_bids"] = 0
        player["_old_bid_total"] = 0

    # Build the player list
    player_lines = []

    for username, player in players.items():
        character_name = player.get("character", username)

        if isinstance(player, list):
            character_name = (
                player[1]
                if len(player) > 1
                else username
            )

        player_lines.append(
            f"• **{character_name}**"
        )

    if player_lines:
        player_text = "\n".join(player_lines)
    else:
        player_text = "No players currently assigned to this table."

    # Build the item list
    item_lines = []

    for item_name, item_data in loot_items.items():
        if not isinstance(item_data, dict):
            continue

        amount = item_data.get("amount", 1)

        try:
            amount = int(amount)
        except (ValueError, TypeError):
            amount = 1

        if amount < 1:
            amount = 1

        description = item_data.get(
            "description",
            "No description provided."
        )

        claimed = item_data.get("claimed", [])

        if not isinstance(claimed, list):
            claimed = []

        # Create one entry for each copy
        for copy_number in range(1, amount + 1):
            if copy_number <= len(claimed):
                claimed_by = claimed[copy_number - 1]

                item_lines.append(
                    f"**{item_name}** #{copy_number}\n"
                    f"{description}\n"
                    f"🔒 **Claimed by:** {claimed_by}"
                )
            else:
                item_lines.append(
                    f"**{item_name}** #{copy_number}\n"
                    f"{description}\n"
                    f"🟢 **Available**"
                )

    # Build the header
    header = (
        f"## 🎁 {table_name.title()} Loot\n\n"
        f"💰 **Money:** {money:,} credits\n"
        f"📋 **Players:**\n{player_text}\n\n"
        f"**Items:**\n"
    )

    # Split the presentation into messages under Discord's limit
    max_message_length = 1900
    messages = []

    current_message = header

    for item_line in item_lines:
        item_text = item_line + "\n\n"

        # Normal case
        if len(current_message) + len(item_text) <= max_message_length:
            current_message += item_text

        # Current message would be too long
        else:
            if current_message.strip():
                messages.append(current_message.rstrip())

            current_message = item_text

            # Safety check for an unusually large individual item
            if len(current_message) > max_message_length:
                # Split the oversized item into smaller chunks
                while len(current_message) > max_message_length:
                    messages.append(
                        current_message[:max_message_length]
                    )
                    current_message = current_message[max_message_length:]

    # Add status message
    status_text = "📊 **Status:** Bidding is now ACTIVE"

    if len(current_message) + len(status_text) + 2 <= max_message_length:
        current_message += "\n" + status_text
        messages.append(current_message.rstrip())
    else:
        if current_message.strip():
            messages.append(current_message.rstrip())

        messages.append(status_text)

    # Get IDs of previous loot presentation messages
    old_message_ids = table.get("loot message ids", [])

    if not isinstance(old_message_ids, list):
        old_message_ids = []

    # Backwards compatibility with the old single-message system
    if not old_message_ids and table.get("loot message id"):
        old_message_ids = [table["loot message id"]]

    # Delete old presentation messages
    for message_id in old_message_ids:
        try:
            old_message = await loot_channel.fetch_message(message_id)
            await old_message.delete()

        except discord.NotFound:
            pass

        except discord.HTTPException:
            pass

    # Send the new presentation messages
    sent_messages = []

    for message in messages:
        sent_message = await loot_channel.send(message)
        sent_messages.append(sent_message)

    # Save all message IDs
    table["loot message ids"] = [
        message.id
        for message in sent_messages
    ]

    # Keep the first message ID for backwards compatibility
    if sent_messages:
        table["loot message id"] = sent_messages[0].id

    # Save the loot channel ID
    table["loot channel id"] = loot_channel.id

    # Save all changes
    save_data(data)

    # Confirm to the person who ran the command
    await interaction.response.send_message(
        f"✅ Loot for **{table_name.title()}** has been presented in "
        f"#{loot_channel.name}.\n"
        f"📨 Sent {len(sent_messages)} message(s).\n"
        f"📊 Bidding is now **ACTIVE**.",
        ephemeral=True
    )

# =========================================================
# Claim Table Item
# =========================================================
@client.tree.command(
    name="claimtableitem",
    description="Claim a loot item from the current table"
)
async def claimtableitem(
    interaction: discord.Interaction,
    item_name: str
):

    data = load_data()

    # =========================================================
    # GET TABLE FROM INTERACTION
    # =========================================================

    table_name = get_table_from_interaction(interaction)

    if not table_name:
        await interaction.response.send_message(
            "❌ Must be used inside a valid table category.",
            ephemeral=True
        )
        return

    table = data.get(
        "tables",
        {}
    ).get(
        table_name
    )

    if not table:
        await interaction.response.send_message(
            "❌ Table does not exist.",
            ephemeral=True
        )
        return

    # =========================================================
    # CHECK BID ACTIVE
    # =========================================================

    if not table.get("bid active", False):
        await interaction.response.send_message(
            "❌ Loot claiming is not active.",
            ephemeral=True
        )
        return

    username = interaction.user.name.lower()

    players = table.get(
        "players",
        {}
    )

    # =========================================================
    # CHECK PLAYER IN TABLE
    # =========================================================

    if username not in players:
        await interaction.response.send_message(
            "❌ You are not assigned to this table.",
            ephemeral=True
        )
        return

    # =========================================================
    # CHECK PLAYER ROUND LIMIT
    # =========================================================

    if players[username].get(
        "claimed",
        False
    ):

        await interaction.response.send_message(
            "❌ You have already claimed an item this round.",
            ephemeral=True
        )
        return

    # =========================================================
    # GET LOOT ITEMS
    # =========================================================

    loot_items = table.get(
        "loot",
        {}
    ).get(
        "items",
        {}
    )

    if not loot_items:
        await interaction.response.send_message(
            "❌ There are no loot items available.",
            ephemeral=True
        )
        return

    # =========================================================
    # CASE-INSENSITIVE ITEM LOOKUP
    # =========================================================

    item_name_lower = item_name.lower()

    matched_item_name = None

    for stored_item_name in loot_items.keys():

        if stored_item_name.lower() == item_name_lower:

            matched_item_name = stored_item_name
            break

    # =========================================================
    # ITEM NOT FOUND
    # =========================================================

    if matched_item_name is None:

        item_names_lower = [
            name.lower()
            for name in loot_items.keys()
        ]

        suggestions = difflib.get_close_matches(
            item_name_lower,
            item_names_lower,
            n=3,
            cutoff=0.6
        )

        if suggestions:

            display_suggestions = []

            for suggestion in suggestions:

                for original_name in loot_items.keys():

                    if original_name.lower() == suggestion:

                        display_suggestions.append(
                            original_name
                        )

                        break

            await interaction.response.send_message(
                f"❌ Item not found.\n"
                f"Did you mean: "
                f"**{', '.join(display_suggestions)}**?",
                ephemeral=True
            )

        else:

            await interaction.response.send_message(
                "❌ Item not found.",
                ephemeral=True
            )

        return

    # =========================================================
    # GET ACTUAL ITEM
    # =========================================================

    item = loot_items[
        matched_item_name
    ]

    # =========================================================
    # INIT CLAIM LIST + SLOT CHECK
    # =========================================================

    item.setdefault(
        "claimed",
        []
    )

    if not isinstance(
        item["claimed"],
        list
    ):

        item["claimed"] = []

    amount = item.get(
        "amount",
        1
    )

    if not isinstance(
        amount,
        int
    ) or amount < 1:

        amount = 1

    # =========================================================
    # CHECK IF FULLY CLAIMED
    # =========================================================

    if len(item["claimed"]) >= amount:

        await interaction.response.send_message(
            "❌ This item is fully claimed.",
            ephemeral=True
        )
        return

    # =========================================================
    # PREVENT DOUBLE CLAIM BY SAME USER
    # =========================================================

    if username in item["claimed"]:

        await interaction.response.send_message(
            "❌ You already claimed this item.",
            ephemeral=True
        )
        return

    # =========================================================
    # APPLY CLAIM
    #
    # IMPORTANT:
    # This does NOT give the item to the player's inventory.
    #
    # The item is only marked as claimed here.
    # /finalizebids will actually give the item.
    # =========================================================

    item["claimed"].append(
        username
    )

    players[username]["claimed"] = True

    # =========================================================
    # LOOT CHANNEL MAP
    # =========================================================

    category_to_channel = {
        "hailey table": "haileys-loot",
        "alijah table": "alijahs-loot",
        "spencer table": "spencers-loot",
        "joseph table": "josephs-loot",
        "rotation table": "rotation-loot"
    }

    channel_name = category_to_channel.get(
        table_name
    )

    loot_channel = discord.utils.get(
        interaction.guild.text_channels,
        name=channel_name
    )

    # =========================================================
    # REBUILD LOOT PRESENTATION
    # =========================================================

    if loot_channel:

        # -----------------------------------------------------
        # GET ALL EXISTING MESSAGE IDS
        # -----------------------------------------------------

        message_ids = table.get(
            "loot message ids",
            []
        )

        if not isinstance(
            message_ids,
            list
        ):

            message_ids = []

        # Backwards compatibility with older tables
        if not message_ids and table.get(
            "loot message id"
        ):

            message_ids = [
                table["loot message id"]
            ]

        # -----------------------------------------------------
        # GET LOOT MONEY
        # -----------------------------------------------------

        money = table.get(
            "loot",
            {}
        ).get(
            "money",
            0
        )

        # -----------------------------------------------------
        # BUILD UPDATED ITEM LIST
        # -----------------------------------------------------

        updated_items = []

        for name, it in loot_items.items():

            amount_i = it.get(
                "amount",
                1
            )

            claimed_list = it.get(
                "claimed",
                []
            )

            if not isinstance(
                amount_i,
                int
            ) or amount_i < 1:

                amount_i = 1

            if not isinstance(
                claimed_list,
                list
            ):

                claimed_list = []

            icon = (
                "✨"
                if it.get("magic", False)
                else "📦"
            )

            # Build one entry for every copy
            for i in range(amount_i):

                if i < len(claimed_list):

                    status = (
                        f"CLAIMED "
                        f"({claimed_list[i]})"
                    )

                else:

                    status = "UNCLAIMED"

                line = (
                    f"{icon} **{name} #{i + 1}** - "
                    f"{status}\n"
                    f"   📜 "
                    f"{it.get('description', '')}"
                )

                updated_items.append(
                    line
                )

        if not updated_items:

            updated_items.append(
                "No loot items."
            )

        # -----------------------------------------------------
        # PLAYER LIST
        # -----------------------------------------------------

        player_list = (
            "\n".join(
                f"• {player}"
                for player in players.keys()
            )
            if players
            else
            "No players"
        )

        # -----------------------------------------------------
        # HEADER
        # -----------------------------------------------------

        header = (
            f"🎲 **LOOT PRESENTATION - "
            f"{table_name.upper()}**\n\n"
            f"👥 **Players:**\n"
            f"{player_list}\n\n"
            f"💰 **Loot Money:** {money}cc\n"
            f"💸 **Money will be distributed when "
            f"bids are finalized.**\n\n"
            f"📦 **Items:**\n"
        )

        # -----------------------------------------------------
        # SPLIT INTO DISCORD-SAFE MESSAGES
        # -----------------------------------------------------

        max_message_length = 1900

        messages = []

        current_message = header

        for item_line in updated_items:

            item_text = item_line + "\n\n"

            if (
                len(current_message)
                + len(item_text)
                <= max_message_length
            ):

                current_message += item_text

            else:

                if current_message.strip():

                    messages.append(
                        current_message.rstrip()
                    )

                current_message = item_text

        # -----------------------------------------------------
        # ADD STATUS
        # -----------------------------------------------------

        status_text = (
            "📊 **Status:** LIVE CLAIMS ACTIVE"
        )

        if (
            len(current_message)
            + len(status_text)
            + 2
            <= max_message_length
        ):

            current_message += status_text

            messages.append(
                current_message.rstrip()
            )

        else:

            if current_message.strip():

                messages.append(
                    current_message.rstrip()
                )

            messages.append(
                status_text
            )

        # -----------------------------------------------------
        # FETCH EXISTING MESSAGES
        # -----------------------------------------------------

        existing_messages = []

        for message_id in message_ids:

            try:

                msg = await loot_channel.fetch_message(
                    message_id
                )

                existing_messages.append(
                    msg
                )

            except discord.NotFound:
                pass

            except discord.HTTPException:
                pass

        # -----------------------------------------------------
        # EDIT EXISTING / SEND NEW MESSAGES
        # -----------------------------------------------------

        new_message_ids = []

        for i, content in enumerate(messages):

            if i < len(existing_messages):

                try:

                    await existing_messages[i].edit(
                        content=content
                    )

                    new_message_ids.append(
                        existing_messages[i].id
                    )

                except discord.NotFound:

                    new_msg = await loot_channel.send(
                        content
                    )

                    new_message_ids.append(
                        new_msg.id
                    )

            else:

                new_msg = await loot_channel.send(
                    content
                )

                new_message_ids.append(
                    new_msg.id
                )

        # -----------------------------------------------------
        # DELETE EXTRA OLD MESSAGES
        # -----------------------------------------------------

        if len(existing_messages) > len(messages):

            for extra_message in existing_messages[
                len(messages):
            ]:

                try:

                    await extra_message.delete()

                except discord.NotFound:
                    pass

                except discord.HTTPException:
                    pass

        # -----------------------------------------------------
        # SAVE ALL MESSAGE IDS
        # -----------------------------------------------------

        table["loot message ids"] = (
            new_message_ids
        )

        # Keep the original field for compatibility
        if new_message_ids:

            table["loot message id"] = (
                new_message_ids[0]
            )

        table["loot channel id"] = (
            loot_channel.id
        )

    # =========================================================
    # SAVE DATA
    # =========================================================

    save_data(data)

    # =========================================================
    # RESPONSE
    # =========================================================

    await interaction.response.send_message(
        f"✅ You claimed **{matched_item_name}**. "
        f"The item will be added to your inventory when "
        f"the bids are finalized.",
        ephemeral=True
    )

# =========================================================
# Stop Bid (ADMIN ONLY)
# =========================================================
@client.tree.command(
    name="stopbid",
    description="Stop active loot bidding and remove the loot presentation message"
)
async def stopbid(interaction: discord.Interaction):

        # =========================================================
    # PERMISSION CHECK
    # =========================================================
        
    is_admin = interaction.user.guild_permissions.administrator
    
    has_dm_role = any(
        role.name.lower() == "dm"
        for role in interaction.user.roles
    )
        
    has_tech_role = any(
        role.name.lower() == "tech"
        for role in interaction.user.roles
    )
        
    if not (is_admin or has_dm_role or has_tech_role):
        await interaction.response.send_message(
            "❌ You do not have permission to use this command.",
            ephemeral=True
            )
        return

    data = load_data()

    # =========================================================
    # GET TABLE FROM INTERACTION (HELPER)
    # =========================================================
    table_name = get_table_from_interaction(interaction)

    if not table_name:
        await interaction.response.send_message(
            "❌ Must be used inside a valid table category.",
            ephemeral=True
        )
        return

    # =========================================================
    # LOOT CHANNEL MAP
    # =========================================================
    category_to_channel = {
        "hailey table": "haileys-loot",
        "alijah table": "alijahs-loot",
        "spencer table": "spencers-loot",
        "joseph table": "josephs-loot",
        "rotation table": "rotation-loot"
    }

    # =========================================================
    # ENSURE TABLE EXISTS
    # =========================================================
    if "tables" not in data or table_name not in data["tables"]:
        await interaction.response.send_message(
            "❌ Table does not exist.",
            ephemeral=True
        )
        return

    table = data["tables"][table_name]

    # =========================================================
    # TURN BID OFF
    # =========================================================
    table["bid active"] = False

    # =========================================================
    # DELETE LOOT MESSAGE
    # =========================================================
    channel_name = category_to_channel.get(table_name)

    loot_channel = discord.utils.get(
        interaction.guild.text_channels,
        name=channel_name
    )

    deleted = False

    if loot_channel and table.get("loot message id"):
        try:
            msg = await loot_channel.fetch_message(
                table["loot message id"]
            )

            await msg.delete()
            deleted = True

        except discord.NotFound:
            pass

    # =========================================================
    # REMOVE STORED MESSAGE REFERENCES
    # =========================================================
    table.pop("loot message id", None)
    table.pop("loot channel id", None)

    save_data(data)

    # =========================================================
    # RESPONSE
    # =========================================================
    if deleted:
        await interaction.response.send_message(
            f"✅ Loot bidding stopped for **{table_name}** and presentation removed.",
            ephemeral=True
        )
    else:
        await interaction.response.send_message(
            f"✅ Loot bidding stopped for **{table_name}**.",
            ephemeral=True
        )

# =========================================================
# BID COMMAND
# =========================================================
@client.tree.command(
    name="bid",
    description="Place bids on table loot items"
)
async def bid(
    interaction: discord.Interaction,
    item_name: str,
    amount: int
):

    data = load_data()

    # =========================================================
    # TABLE RESOLUTION
    # =========================================================

    table_name = get_table_from_interaction(interaction)

    if not table_name:
        await interaction.response.send_message(
            "❌ Must be used inside a valid table category.",
            ephemeral=True
        )
        return

    table = data.get("tables", {}).get(table_name)

    if not table:
        await interaction.response.send_message(
            "❌ Table does not exist.",
            ephemeral=True
        )
        return

    # =========================================================
    # BID ACTIVE CHECK
    # =========================================================

    if not table.get("bid active", False):
        await interaction.response.send_message(
            "❌ Bidding is not currently active.",
            ephemeral=True
        )
        return

    # =========================================================
    # PLAYER CHECK
    # =========================================================

    username = interaction.user.name.lower()

    players = table.get("players", {})

    if username not in players:
        await interaction.response.send_message(
            "❌ You are not at this table.",
            ephemeral=True
        )
        return

    player_entry = players[username]

    # Make sure bids is a dictionary
    if not isinstance(player_entry.get("bids"), dict):
        player_entry["bids"] = {}

    player_bids = player_entry["bids"]

    # =========================================================
    # ITEM CHECK
    # =========================================================

    loot = table.get("loot", {})
    loot_items = loot.get("items", {})

    if not loot_items:
        await interaction.response.send_message(
            "❌ There are no loot items available.",
            ephemeral=True
        )
        return

    # =========================================================
    # CASE-INSENSITIVE ITEM LOOKUP
    # =========================================================

    item_name_input = item_name.strip()
    item_name_lower = item_name_input.lower()

    matched_item_name = None

    for stored_item_name in loot_items.keys():

        if stored_item_name.lower() == item_name_lower:
            matched_item_name = stored_item_name
            break

    # =========================================================
    # ITEM NOT FOUND
    # =========================================================

    if matched_item_name is None:

        item_names_lower = [
            name.lower()
            for name in loot_items.keys()
        ]

        matches = difflib.get_close_matches(
            item_name_lower,
            item_names_lower,
            n=3,
            cutoff=0.6
        )

        if matches:

            display_matches = []

            for match in matches:

                for original_name in loot_items.keys():

                    if original_name.lower() == match:

                        display_matches.append(
                            original_name
                        )

                        break

            await interaction.response.send_message(
                f"❌ Item not found.\n\n"
                f"🔎 Did you mean "
                f"**{', '.join(display_matches)}**?",
                ephemeral=True
            )

        else:

            await interaction.response.send_message(
                "❌ Item does not exist.",
                ephemeral=True
            )

        return

    # Use the actual stored item name
    item_name = matched_item_name

    # =========================================================
    # CHECK BID AMOUNT
    # =========================================================

    if amount < 0:
        await interaction.response.send_message(
            "❌ Bid amount cannot be negative.",
            ephemeral=True
        )
        return

    # =========================================================
    # PLAYER DATABASE
    # =========================================================

    players_db = data.get("players", {})

    player_data = players_db.get(username)

    if not player_data:
        await interaction.response.send_message(
            "❌ Player not found in database.",
            ephemeral=True
        )
        return

    # =========================================================
    # PLAYER DATA FORMAT CHECK
    # =========================================================

    if not isinstance(player_data, list):
        await interaction.response.send_message(
            "❌ Player data is in an invalid format.",
            ephemeral=True
        )
        return

    if len(player_data) <= 3:
        await interaction.response.send_message(
            "❌ Player credit data is missing.",
            ephemeral=True
        )
        return

    # =========================================================
    # GET CREDITS
    # =========================================================

    try:
        credits = int(player_data[3])

    except (ValueError, TypeError):
        await interaction.response.send_message(
            "❌ Your credit balance is invalid.",
            ephemeral=True
        )
        return

    # =========================================================
    # GET PLAYER LEVEL
    # =========================================================
    #
    # Current player_data structure:
    #
    # [0] player name
    # [1] character name
    # [2] background
    # [3] credits
    # [4] inventory
    # [5] magic inventory
    # [6] class
    # [7] discount tracking
    #
    # There is currently no level stored here.
    #
    # Using [6] would incorrectly use the player's CLASS
    # as their level.
    #
    # Until you add a proper level field, level defaults to 1.
    #

    level = 1

    # =========================================================
    # GET BID COST
    # =========================================================

    try:
        bid_cost = get_bid_raise_amount(level)

    except Exception:
        await interaction.response.send_message(
            "❌ Could not determine the bid cost.",
            ephemeral=True
        )
        return

    # Make sure bid cost is valid
    if not isinstance(bid_cost, (int, float)) or bid_cost < 0:
        await interaction.response.send_message(
            "❌ The bid cost returned an invalid value.",
            ephemeral=True
        )
        return

    # =========================================================
    # CURRENT BID TOTAL
    # =========================================================

    def calculate_bid_cost(total_bids):
        """
        First bid is free.
        Every additional bid costs bid_cost.
        """
        billable_bids = max(total_bids - 1, 0)

        return billable_bids * bid_cost

    # =========================================================
    # CLEAN EXISTING BIDS
    # =========================================================

    cleaned_bids = {}

    for bid_item, bid_amount in player_bids.items():

        try:
            bid_amount = int(bid_amount)

        except (ValueError, TypeError):
            continue

        if bid_amount > 0:
            cleaned_bids[bid_item] = bid_amount

    player_entry["bids"] = cleaned_bids
    player_bids = player_entry["bids"]

    # =========================================================
    # CURRENT TOTAL
    # =========================================================

    current_total_bids = sum(
        player_bids.values()
    )

    current_total_cost = calculate_bid_cost(
        current_total_bids
    )

    # =========================================================
    # SAFETY CHECK
    # =========================================================
    #
    # If the player's current bids somehow cost more than
    # their available credits, wipe their bids.
    #

    if current_total_cost > credits:

        player_entry["bids"] = {}
        player_entry["total_bids"] = 0
        player_entry["_old_bid_total"] = 0

        # Remove the player from every lottery pool
        for loot_item in loot_items.values():

            if not isinstance(loot_item, dict):
                continue

            if isinstance(loot_item.get("bids"), list):

                loot_item["bids"] = [
                    player
                    for player in loot_item["bids"]
                    if player != username
                ]

        save_data(data)

        await interaction.response.send_message(
            "❌ Your current bid cost exceeds "
            "your available credits.\n\n"
            "All of your bids have been removed "
            "to prevent errors.",
            ephemeral=True
        )
        return

    # =========================================================
    # OLD BID AMOUNT
    # =========================================================

    old_amount = player_bids.get(
        item_name,
        0
    )

    # =========================================================
    # APPLY BID CHANGE
    # =========================================================

    if amount == 0:

        # Remove the bid entirely
        player_bids.pop(
            item_name,
            None
        )

        new_amount = 0

    else:

        # Set the bid to the requested amount
        player_bids[item_name] = amount

        new_amount = amount

    # =========================================================
    # NEW TOTAL BIDS
    # =========================================================

    total_bids = sum(
        player_bids.values()
    )

    player_entry["total_bids"] = total_bids

    # =========================================================
    # NEW TOTAL COST
    # =========================================================

    total_bid_cost = calculate_bid_cost(
        total_bids
    )

    # =========================================================
    # OLD TOTAL COST
    # =========================================================

    old_total_cost = player_entry.get(
        "_old_bid_total"
    )

    # If old cost is missing, calculate it from the old
    # total instead of assuming it is zero.
    if old_total_cost is None:

        old_total_bids = (
            current_total_bids
            - old_amount
        )

        old_total_cost = calculate_bid_cost(
            old_total_bids
        )

    try:
        old_total_cost = int(old_total_cost)

    except (ValueError, TypeError):
        old_total_cost = current_total_cost

    # =========================================================
    # COST CHANGE
    # =========================================================

    cost_change = (
        total_bid_cost
        - old_total_cost
    )

    # =========================================================
    # CHECK IF PLAYER CAN AFFORD CHANGE
    # =========================================================

    if cost_change > 0 and credits < cost_change:

        # Revert the bid change
        if old_amount <= 0:

            player_bids.pop(
                item_name,
                None
            )

        else:

            player_bids[item_name] = (
                old_amount
            )

        # Recalculate total
        player_entry["total_bids"] = sum(
            player_bids.values()
        )

        await interaction.response.send_message(
            f"❌ Not enough credits.\n\n"
            f"💰 Cost increase: **{cost_change:,}cc**\n"
            f"💳 Your credits: **{credits:,}cc**",
            ephemeral=True
        )
        return

    # =========================================================
    # APPLY CREDIT CHANGE
    # =========================================================

    player_data[3] = credits - cost_change

    # =========================================================
    # STORE CURRENT COST
    # =========================================================

    player_entry["_old_bid_total"] = (
        total_bid_cost
    )

    # =========================================================
    # GET CURRENT LOOT ITEM
    # =========================================================

    loot_item = loot_items[item_name]

    if not isinstance(loot_item, dict):
        await interaction.response.send_message(
            "❌ This loot item has invalid data.",
            ephemeral=True
        )
        return

    # =========================================================
    # REBUILD LOTTERY POOL
    # =========================================================

    loot_item["bids"] = []

    for p_name, p_data in players.items():

        if not isinstance(p_data, dict):
            continue

        p_bids = p_data.get(
            "bids",
            {}
        )

        if not isinstance(p_bids, dict):
            continue

        try:
            player_bid_amount = int(
                p_bids.get(
                    item_name,
                    0
                )
            )

        except (ValueError, TypeError):
            player_bid_amount = 0

        if player_bid_amount > 0:

            loot_item["bids"].extend(
                [p_name] * player_bid_amount
            )

    # =========================================================
    # SAVE
    # =========================================================

    save_data(data)

    # =========================================================
    # RESPONSE
    # =========================================================

    if cost_change > 0:
        cost_text = (
            f"💸 Cost: **-{cost_change:,}cc**"
        )

    elif cost_change < 0:
        cost_text = (
            f"💰 Refund: **{abs(cost_change):,}cc**"
        )

    else:
        cost_text = (
            "💰 Cost change: **0cc**"
        )

    await interaction.response.send_message(
        f"⚔️ Bid updated for **{item_name}**\n\n"
        f"📊 Item bids: **{new_amount}**\n"
        f"📦 Total bids: **{total_bids}**\n"
        f"{cost_text}\n"
        f"💳 Remaining credits: "
        f"**{player_data[3]:,}cc**\n"
        f"🎲 Lottery pool size: "
        f"**{len(loot_item['bids'])}**",
        ephemeral=True
    )

# =========================================================
# FINALIZE BIDS COMMAND (ADMIN ONLY)
# =========================================================
@client.tree.command(
    name="finalizebids",
    description="Finalize bids, distribute loot, and end the table round (admin only)"
)
async def finalizebids(interaction: discord.Interaction):

    import random

    data = load_data()

    # =========================================================
    # PERMISSION CHECK
    # =========================================================

    is_admin = interaction.user.guild_permissions.administrator

    has_dm_role = any(
        role.name.lower() == "dm"
        for role in interaction.user.roles
    )

    has_tech_role = any(
        role.name.lower() == "tech"
        for role in interaction.user.roles
    )

    if not (is_admin or has_dm_role or has_tech_role):
        await interaction.response.send_message(
            "❌ You do not have permission to use this command.",
            ephemeral=True
        )
        return

    # =========================================================
    # TABLE RESOLUTION
    # =========================================================

    table_name = get_table_from_interaction(interaction)

    if not table_name:
        await interaction.response.send_message(
            "❌ Must be used inside a valid table category.",
            ephemeral=True
        )
        return

    table = data.get("tables", {}).get(table_name)

    if not table:
        await interaction.response.send_message(
            "❌ Table does not exist.",
            ephemeral=True
        )
        return

    # =========================================================
    # GET DATA
    # =========================================================

    players = table.get("players", {})
    loot = table.get("loot", {})
    loot_items = loot.get("items", {})
    global_players = data.get("players", {})

    if not players:
        await interaction.response.send_message(
            "❌ There are no players at this table.",
            ephemeral=True
        )
        return

    # =========================================================
    # CHECK BIDDING STATUS
    # =========================================================

    if not table.get("bid active", False):
        await interaction.response.send_message(
            "❌ Bidding is not currently active.",
            ephemeral=True
        )
        return

    # =========================================================
    # TRACK ITEM DISTRIBUTION
    # =========================================================

    item_counts = {
        player: 0
        for player in players
    }

    distribution_log = {
        player: []
        for player in players
    }

    # =========================================================
    # GIVE ITEM FUNCTION
    # =========================================================

    def give_item(player, item_name, item_data):

        if player not in global_players:
            return False

        player_data = global_players[player]

        # Make sure player data has enough fields
        if not isinstance(player_data, list):
            return False

        if len(player_data) <= 5:
            return False

        # -----------------------------------------------------
        # MAGIC ITEM
        # -----------------------------------------------------

        if item_data.get("magic", False):

            magic_inventory = player_data[5]

            if not isinstance(magic_inventory, dict):
                magic_inventory = {}
                player_data[5] = magic_inventory

            if item_name in magic_inventory:

                existing = magic_inventory[item_name]

                if isinstance(existing, dict):

                    existing["amount"] = (
                        existing.get("amount", 1) + 1
                    )

                else:

                    magic_inventory[item_name] = {
                        "description": item_data.get(
                            "description",
                            ""
                        ),
                        "amount": 2
                    }

            else:

                magic_inventory[item_name] = {
                    "description": item_data.get(
                        "description",
                        ""
                    ),
                    "amount": 1
                }

        # -----------------------------------------------------
        # NORMAL ITEM
        # -----------------------------------------------------

        else:

            if not isinstance(player_data[4], list):
                player_data[4] = []

            player_data[4].append(
                item_name
            )

        distribution_log[player].append(
            item_name
        )

        return True

    # =========================================================
    # 1. DISTRIBUTE CLAIMED ITEMS FIRST
    # =========================================================

    for item_name, item in loot_items.items():

        if not isinstance(item, dict):
            continue

        claimed = item.get(
            "claimed",
            []
        )

        if not isinstance(claimed, list):
            claimed = []

        for player in claimed:

            if player not in players:
                continue

            success = give_item(
                player,
                item_name,
                item
            )

            if success:
                item_counts[player] += 1

    # =========================================================
    # 2. HANDLE BIDS + UNCLAIMED COPIES
    # =========================================================

    for item_name, item in loot_items.items():

        if not isinstance(item, dict):
            continue

        # -----------------------------------------------------
        # GET ITEM AMOUNT
        # -----------------------------------------------------

        try:
            amount = int(
                item.get(
                    "amount",
                    1
                )
            )

        except (ValueError, TypeError):
            amount = 1

        if amount < 1:
            amount = 1

        # -----------------------------------------------------
        # GET CLAIMED AMOUNT
        # -----------------------------------------------------

        claimed = item.get(
            "claimed",
            []
        )

        if not isinstance(claimed, list):
            claimed = []

        claimed_amount = len(
            claimed
        )

        remaining = max(
            amount - claimed_amount,
            0
        )

        # -----------------------------------------------------
        # GET BID POOL
        # -----------------------------------------------------

        bids = item.get(
            "bids",
            []
        )

        if not isinstance(bids, list):
            bids = []

        bids = bids.copy()

        # -----------------------------------------------------
        # DISTRIBUTE REMAINING COPIES
        # -----------------------------------------------------

        for _ in range(remaining):

            # -------------------------------------------------
            # BID WINNER
            # -------------------------------------------------

            if bids:

                # Remove invalid players from the pool
                valid_bids = [
                    player
                    for player in bids
                    if player in players
                    and player in global_players
                ]

                bids = valid_bids

            if bids:

                winner = random.choice(
                    bids
                )

                success = give_item(
                    winner,
                    item_name,
                    item
                )

                if success:

                    item_counts[winner] += 1

                    # Remove ALL bids from the winner
                    bids = [
                        player
                        for player in bids
                        if player != winner
                    ]

                else:

                    # If something went wrong, remove the
                    # player so they cannot win again
                    bids = [
                        player
                        for player in bids
                        if player != winner
                    ]

            # -------------------------------------------------
            # NO BIDS
            # -------------------------------------------------

            else:

                # Make sure there are players available
                valid_players = [
                    player
                    for player in players
                    if player in global_players
                ]

                if not valid_players:
                    continue

                # Find the lowest current item count
                lowest = min(
                    item_counts[player]
                    for player in valid_players
                )

                possible_players = [
                    player
                    for player in valid_players
                    if item_counts[player] == lowest
                ]

                winner = random.choice(
                    possible_players
                )

                success = give_item(
                    winner,
                    item_name,
                    item
                )

                if success:
                    item_counts[winner] += 1

    # =========================================================
    # 3. REFUND BID MONEY
    # =========================================================
    #
    # The /bid command removes bid money from the player's
    # credits as bids are added.
    #
    # _old_bid_total contains the amount currently paid
    # toward bids.
    #
    # That money is returned when the round is finalized.
    #

    for player, entry in players.items():

        if player not in global_players:
            continue

        if not isinstance(entry, dict):
            continue

        player_data = global_players[player]

        if not isinstance(player_data, list):
            continue

        if len(player_data) <= 3:
            continue

        refund = entry.get(
            "_old_bid_total",
            0
        )

        try:
            refund = int(refund)

        except (ValueError, TypeError):
            refund = 0

        if refund > 0:

            player_data[3] += refund

        # Reset bidding information
        entry["bids"] = {}
        entry["total_bids"] = 0
        entry["_old_bid_total"] = 0

    # =========================================================
    # 4. GIVE LOOT MONEY
    # =========================================================

    try:
        money = int(
            loot.get(
                "money",
                0
            )
        )

    except (ValueError, TypeError):
        money = 0

    if money < 0:
        money = 0

    for player in players:

        if player not in global_players:
            continue

        player_data = global_players[player]

        if not isinstance(player_data, list):
            continue

        if len(player_data) <= 3:
            continue

        player_data[3] += money

    # =========================================================
    # 5. CLEAR LOOT AND END ROUND
    # =========================================================

    table["loot"]["money"] = 0
    table["loot"]["items"] = {}

    table["bid active"] = False

    # Clear old presentation message tracking
    table["loot message ids"] = []

    table["loot message id"] = None
    table["loot channel id"] = None

    # =========================================================
    # SAVE
    # =========================================================

    save_data(data)

    # =========================================================
    # BUILD RESULTS
    # =========================================================

    result_lines = []

    for player, items in distribution_log.items():

        result_lines.append(
            f"👤 **{player}**"
        )

        if items:

            for item in items:

                result_lines.append(
                    f"  📦 {item}"
                )

        else:

            result_lines.append(
                "  No items received"
            )

        result_lines.append("")

    results = "\n".join(
        result_lines
    )

    # =========================================================
    # BUILD RESPONSE
    # =========================================================

    header = (
        f"✅ **Bids finalized for {table_name}**\n\n"
        f"📦 Items distributed\n"
        f"💰 Each player received: **{money:,}cc**\n"
        f"🧹 Loot cleared\n"
        f"🎲 Bidding closed\n\n"
        f"━━━━━━━━━━━━━━\n"
        f"🏆 **Distribution Results**\n\n"
    )

    max_message_length = 1900

    messages = []
    current_message = header

    for line in result_lines:

        line_text = line + "\n"

        if len(current_message) + len(line_text) <= max_message_length:

            current_message += line_text

        else:

            if current_message.strip():
                messages.append(
                    current_message.rstrip()
                )

            current_message = line_text

    if current_message.strip():
        messages.append(
            current_message.rstrip()
        )

    # =========================================================
    # SEND RESULTS
    # =========================================================

    try:

        await interaction.response.send_message(
            messages[0],
            ephemeral=True
        )

        for message in messages[1:]:

            await interaction.followup.send(
                message,
                ephemeral=True
            )

    except discord.HTTPException:
        # The data has already been finalized and saved.
        # Do not attempt to finalize the table again.
        pass

# =========================================================
# ADD ITEM TO SHOP COMMAND (ADMIN ONLY)
# =========================================================
@client.tree.command(
    name="additemtoshop",
    description="Add an item to the shop (admin only)"
)
@discord.app_commands.describe(
    name="Item name",
    price="Item price in credits",
    description="Item description",
    magic="Is this a magic item?",
    cyberware="Is this cyberware?",
    contains="Optional items contained inside (comma separated)"
)
async def additemtoshop(
    interaction: discord.Interaction,
    name: str,
    price: int,
    description: str,
    magic: bool = False,
    cyberware: bool = False,
    contains: str = None
):

    # =========================================================
    # ADMIN / DM ROLE CHECK
    # =========================================================
    is_admin = interaction.user.guild_permissions.administrator

    has_dm_role = any(
        role.name.lower() == "dm"
        for role in interaction.user.roles
    )

    if not is_admin and not has_dm_role:
        await interaction.response.send_message(
            "❌ You do not have permission to use this command.",
            ephemeral=True
        )
        return


    # =========================================================
    # VALIDATE PRICE
    # =========================================================
    if price <= 0:

        await interaction.response.send_message(
            "❌ Price must be greater than 0.",
            ephemeral=True
        )

        return


    # =========================================================
    # LOAD SHOP
    # =========================================================
    shop = load_shop()

    name = name.lower()



    # =========================================================
    # CHECK IF ITEM EXISTS
    # =========================================================
    if name in shop:

        await interaction.response.send_message(
            f"❌ **{name}** already exists in the shop.",
            ephemeral=True
        )

        return



    # =========================================================
    # CREATE ITEM DATA
    # =========================================================
    item_data = {
        "price": price,
        "description": description,
        "magic": magic,
        "cyberware": cyberware
    }



    # =========================================================
    # HANDLE CONTAINER ITEMS
    # =========================================================
    contained_items = []

    if contains:

        contained_items = [
            item.strip().lower()
            for item in contains.split(",")
            if item.strip()
        ]

        item_data["contains"] = contained_items



    # =========================================================
    # ADD TO SHOP
    # =========================================================
    shop[name] = item_data


    save_shop(shop)



    # =========================================================
    # RESPONSE
    # =========================================================
    message = (
        f"✅ Added **{name}** to the shop.\n\n"
        f"💰 Price: {price}cc\n"
        f"📜 Description: {description}\n"
        f"✨ Magic: {magic}\n"
        f"🦾 Cyberware: {cyberware}"
    )


    if contained_items:

        message += (
            "\n\n📦 Contains:\n"
            +
            "\n".join(
                f"• {item}"
                for item in contained_items
            )
        )


    await interaction.response.send_message(
        message,
        ephemeral=True
    )

# =========================================================
# Session 0 Toggle Command (Admin Only)
# =========================================================
@client.tree.command(
    name="setsession0",
    description="Enable or disable session 0 (admin only)"
)
async def setsession0(interaction: discord.Interaction, value: bool):

    # =========================================================
    # PERMISSION CHECK
    # =========================================================
        
    is_admin = interaction.user.guild_permissions.administrator
    
    has_dm_role = any(
        role.name.lower() == "dm"
        for role in interaction.user.roles
    )
        
    has_tech_role = any(
        role.name.lower() == "tech"
        for role in interaction.user.roles
    )
        
    if not (is_admin or has_dm_role or has_tech_role):
        await interaction.response.send_message(
            "❌ You do not have permission to use this command.",
            ephemeral=True
            )
        return

    data = load_data()

    # =========================================================
    # ENSURE KEY EXISTS
    # =========================================================
    if "session 0" not in data:
        data["session 0"] = False

    # =========================================================
    # UPDATE VALUE
    # =========================================================
    data["session 0"] = value

    save_data(data)

    # =========================================================
    # RESPONSE
    # =========================================================
    state = "ENABLED" if value else "DISABLED"

    await interaction.response.send_message(
        f"🧩 **Session 0 has been {state}.**",
        ephemeral=True
    )

# =========================================================
# Backup Data (Admin Only)
# =========================================================
@client.tree.command(
    name="backupdata",
    description="Create a backup of the current player data"
)
async def backupdata(interaction: discord.Interaction):

    # =========================================================
    # PERMISSION CHECK
    # =========================================================
        
    is_admin = interaction.user.guild_permissions.administrator
    
    has_dm_role = any(
        role.name.lower() == "dm"
        for role in interaction.user.roles
    )
        
    has_tech_role = any(
        role.name.lower() == "tech"
        for role in interaction.user.roles
    )
        
    if not (is_admin or has_dm_role or has_tech_role):
        await interaction.response.send_message(
            "❌ You do not have permission to use this command.",
            ephemeral=True
            )
        return

    # =========================================================
    # BACKUP FOLDER
    # =========================================================
    backup_folder = os.path.join(
        os.path.dirname(FILE),
        "backups"
    )

    os.makedirs(
        backup_folder,
        exist_ok=True
    )

    # =========================================================
    # CURRENT DATE
    # =========================================================
    from datetime import datetime

    current_date = datetime.now().strftime("%Y-%m-%d")

    # =========================================================
    # FIND AVAILABLE BACKUP NUMBER
    # =========================================================
    backup_number = 1

    while True:

        backup_filename = (
            f"player_data_backup_"
            f"{current_date}_"
            f"{backup_number}.json"
        )

        backup_path = os.path.join(
            backup_folder,
            backup_filename
        )

        if not os.path.exists(backup_path):
            break

        backup_number += 1

    # =========================================================
    # CREATE BACKUP
    # =========================================================
    try:

        with open(
            FILE,
            "r",
            encoding="utf-8"
        ) as original_file:

            data = json.load(original_file)

        with open(
            backup_path,
            "w",
            encoding="utf-8"
        ) as backup_file:

            json.dump(
                data,
                backup_file,
                indent=4
            )

        # =====================================================
        # SUCCESS MESSAGE
        # =====================================================
        await interaction.response.send_message(
            f"✅ Player data backup created successfully.\n\n"
            f"📁 **File:** `{backup_filename}`",
            ephemeral=True
        )

    except Exception as e:

        await interaction.response.send_message(
            "❌ Failed to create player data backup.\n"
            "Admins have been notified.",
            ephemeral=True
        )

        await item_amount_error(
            interaction.guild,
            interaction.user.name.lower(),
            "player_data.json",
            f"Backup failed: {e}"
        )

# =========================================================
# Greetings (Admin Only)
# =========================================================
@client.tree.command(
    name="greeting",
    description="Have the bot greet everyone"
)
async def greeting(interaction: discord.Interaction):

    # =========================================================
    # PERMISSION CHECK
    # =========================================================
        
    is_admin = interaction.user.guild_permissions.administrator
    
    has_dm_role = any(
        role.name.lower() == "dm"
        for role in interaction.user.roles
    )
        
    has_tech_role = any(
        role.name.lower() == "tech"
        for role in interaction.user.roles
    )
        
    if not (is_admin or has_dm_role or has_tech_role):
        await interaction.response.send_message(
            "❌ You do not have permission to use this command.",
            ephemeral=True
            )
        return

    # =========================================================
    # SEND GREETING
    # =========================================================
    await interaction.response.send_message(
        "Meowdy!! Its good to see everyone! I'm here to help!"
    )
    
# ---------------- RUN BOT ----------------
client.run('YOUR_BOT_TOKEN_HERE')