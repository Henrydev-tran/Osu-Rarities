import os

import asyncio
import random

import discord
from discord.ext import commands

import user_handling
from user_handling import *
import loadmaps
import probabilitycalc
import jsontools
from userutils import give_rewards, SHARD_LIST, SHARD_RANK

from dotenv import load_dotenv

load_dotenv()

from raritycalculation import Calculate_Rarity, get_star_color
from jsontools import Beatmap_To_Json
from loadmaps import *
from probabilitycalc import *
from math import ceil
from collections import Counter
from userutils import xp_to_next_level, give_daily_rewards

from item import SHARDS_BY_ID, SHARD_CORE_RECIPES, ALL_RECIPES, ITEMS_BY_ID, SHOP_ITEMS, PERIPHERAL_TYPES

import datetime

client = commands.Bot(command_prefix='o!', intents=discord.Intents(message_content=True, messages=True))
client.remove_command("help")

_initialized = False
LEADERBOARD_FILE = "json/leaderboard.json"
LEADERBOARD_REFRESH_SECONDS = 300
LEADERBOARD_PAGE_SIZE = 20
LEADERBOARD_MAX_PLAYERS = 100
FAKE_USER_ID_BASE = 9_000_000_000_000_000

FAKE_NAME_PREFIXES = [
    "Hidden",
    "Solar",
    "Crimson",
    "Frozen",
    "Velvet",
    "Nova",
    "Silent",
    "Pixel",
]

FAKE_NAME_SUFFIXES = [
    "Spinner",
    "Stream",
    "Mapper",
    "Cursor",
    "Burst",
    "Slider",
    "Rhythm",
    "Starlight",
]

leaderboard_cache = []
leaderboard_details = []
leaderboard_last_refresh_at = None
leaderboard_next_refresh_at = None
leaderboard_refresh_lock = asyncio.Lock()

DEFAULT_DEV_USER_IDS = {
    718102801242259466,
    1177826548729008268,
}

DEFAULT_EXTENDED_DEV_USER_IDS = DEFAULT_DEV_USER_IDS | {
    970958596424761366,
}

DEV_IDS_FILE = "json/dev_ids.json"

DEV_USER_IDS = set(DEFAULT_DEV_USER_IDS)
EXTENDED_DEV_USER_IDS = set(DEFAULT_EXTENDED_DEV_USER_IDS)


def parse_user_id_arg(raw: str) -> int | None:
    raw = raw.strip()

    if raw.startswith("<@") and raw.endswith(">"):
        raw = raw[2:-1]
        if raw.startswith("!"):
            raw = raw[1:]

    if not raw.isdigit():
        return None

    return int(raw)


async def save_dev_ids():
    payload = {
        "dev_user_ids": sorted(DEV_USER_IDS),
        "extended_dev_user_ids": sorted(EXTENDED_DEV_USER_IDS),
    }
    await jsontools.save_to_json(DEV_IDS_FILE, payload)


async def load_dev_ids():
    global DEV_USER_IDS, EXTENDED_DEV_USER_IDS

    try:
        data = await jsontools.return_json(DEV_IDS_FILE)
    except FileNotFoundError:
        DEV_USER_IDS = set(DEFAULT_DEV_USER_IDS)
        EXTENDED_DEV_USER_IDS = set(DEFAULT_EXTENDED_DEV_USER_IDS)
        await save_dev_ids()
        return

    raw_devs = data.get("dev_user_ids", list(DEFAULT_DEV_USER_IDS))
    raw_extended = data.get("extended_dev_user_ids", list(DEFAULT_EXTENDED_DEV_USER_IDS))

    parsed_devs = {int(i) for i in raw_devs}
    parsed_extended = {int(i) for i in raw_extended}

    DEV_USER_IDS = parsed_devs or set(DEFAULT_DEV_USER_IDS)
    EXTENDED_DEV_USER_IDS = parsed_extended | DEV_USER_IDS

    # Keep file normalized and ensure core devs are always included.
    await save_dev_ids()


def calculate_inventory_rarity_total(user) -> int:
    total_rarity = 0

    for owned_map in getattr(user, "maps", []):
        for diff in getattr(owned_map, "difficulties", []):
            total_rarity += int(getattr(diff, "rarity", 0)) * int(getattr(diff, "duplicates", 0))

    return total_rarity


def format_equipped_items(user) -> str:
    peripherals = user.items.get("GearPeripheral", {})

    lines = []

    equipped_peripherals = [item for item in peripherals.values() if getattr(item, "equipped", False)]
    if equipped_peripherals:
        lines.append(
            "Peripherals: " + ", ".join(
                f"{item.peripheraltype}: {item.name}" for item in equipped_peripherals
            )
        )
    else:
        lines.append("Peripherals: None equipped")

    return "\n".join(lines)


async def get_leaderboard_rank_for_user(user) -> int | None:
    async with stored_users_lock:
        users = list(stored_users.users.values())

    ranked_users = sorted(
        users,
        key=lambda u: (
            -int(getattr(u, "level", 1)),
            -int(getattr(u, "pp", 0)),
            -calculate_inventory_rarity_total(u),
            int(u.id)
        )
    )

    for rank, candidate in enumerate(ranked_users, start=1):
        if int(candidate.id) == int(user.id):
            return rank

    return None


async def get_all_leaderboard_ranks_for_user(user):
    async with stored_users_lock:
        users = list(stored_users.users.values())

    ranks = {}

    # Level leaderboard
    ranked_users_level = sorted(
        users,
        key=lambda u: (
            -int(getattr(u, "level", 1)),
            -int(getattr(u, "pp", 0)),
            -calculate_inventory_rarity_total(u),
            int(u.id)
        )
    )
    for rank, candidate in enumerate(ranked_users_level, start=1):
        if int(candidate.id) == int(user.id):
            ranks["level"] = rank
            break

    # PP leaderboard
    ranked_users_pp = sorted(
        users,
        key=lambda u: (
            -int(getattr(u, "pp", 0)),
            -int(getattr(u, "level", 1)),
            -calculate_inventory_rarity_total(u),
            int(u.id)
        )
    )
    for rank, candidate in enumerate(ranked_users_pp, start=1):
        if int(candidate.id) == int(user.id):
            ranks["pp"] = rank
            break

    # Rarity leaderboard
    ranked_users_rarity = sorted(
        users,
        key=lambda u: (
            -calculate_inventory_rarity_total(u),
            -int(getattr(u, "level", 1)),
            -int(getattr(u, "pp", 0)),
            int(u.id)
        )
    )
    for rank, candidate in enumerate(ranked_users_rarity, start=1):
        if int(candidate.id) == int(user.id):
            ranks["rarity"] = rank
            break

    return ranks


def leaderboard_sort_key(entry):
    return (-entry["level"], -entry["pp"], -entry["inventory_rarity"], entry["id"])


LEADERBOARD_SORT_MODES = {
    "level": {
        "label": "Level",
        "description": "Sorted by level.",
        "stat_key": "level",
        "stat_label": "Level",
        "key": lambda entry: (-entry["level"], -entry["pp"], -entry["inventory_rarity"], entry["id"]),
    },
    "pp": {
        "label": "PP",
        "description": "Sorted by PP.",
        "stat_key": "pp",
        "stat_label": "PP",
        "key": lambda entry: (-entry["pp"], -entry["level"], -entry["inventory_rarity"], entry["id"]),
    },
    "rarity": {
        "label": "Map Rarity",
        "description": "Sorted by total map rarity.",
        "stat_key": "inventory_rarity",
        "stat_label": "Inventory rarity",
        "key": lambda entry: (-entry["inventory_rarity"], -entry["level"], -entry["pp"], entry["id"]),
    },
}


def sort_leaderboard_entries(entries, mode: str):
    selected_mode = LEADERBOARD_SORT_MODES.get(mode, LEADERBOARD_SORT_MODES["level"])
    return sorted(entries, key=selected_mode["key"])


def get_leaderboard_pages(mode: str = "level"):
    if not leaderboard_details:
        return []

    sorted_entries = sort_leaderboard_entries(leaderboard_details, mode)[:LEADERBOARD_MAX_PLAYERS]
    return chunk_list(sorted_entries, LEADERBOARD_PAGE_SIZE)


def build_leaderboard_embed(mode: str = "level", page_index: int = 0):
    pages = get_leaderboard_pages(mode)
    if not pages:
        return None

    selected_mode = LEADERBOARD_SORT_MODES.get(mode, LEADERBOARD_SORT_MODES["level"])
    page_index = max(0, min(page_index, len(pages) - 1))
    page_entries = pages[page_index]

    lines = []
    start_rank = page_index * LEADERBOARD_PAGE_SIZE
    for offset, entry in enumerate(page_entries, start=1):
        stat_value = format_number(entry[selected_mode["stat_key"]])
        lines.append(
            f"**#{start_rank + offset}** {entry['name']} • {selected_mode['stat_label']} {stat_value}"
        )

    embed = discord.Embed(
        title=f"Player Leaderboard — {selected_mode['label']}",
        description="\n".join(lines),
        color=discord.Color.gold(),
        timestamp=datetime.datetime.now()
    )

    embed.add_field(
        name="Current Sort",
        value=selected_mode["description"],
        inline=False
    )

    if leaderboard_next_refresh_at is not None:
        next_refresh_unix = int(leaderboard_next_refresh_at.timestamp())
        embed.add_field(
            name="Next Refresh",
            value=f"<t:{next_refresh_unix}:R> (<t:{next_refresh_unix}:T>)",
            inline=False
        )

    embed.set_footer(text=f"Page {page_index + 1}/{len(pages)} • Showing top {sum(len(page) for page in pages)} players")

    return embed


async def resolve_leaderboard_name(user_id: int) -> str:
    cached_user = client.get_user(user_id)
    if cached_user is not None:
        return getattr(cached_user, "display_name", None) or getattr(cached_user, "global_name", None) or cached_user.name

    try:
        fetched_user = await client.fetch_user(user_id)
    except (discord.NotFound, discord.Forbidden, discord.HTTPException):
        return str(user_id)

    return getattr(fetched_user, "display_name", None) or getattr(fetched_user, "global_name", None) or fetched_user.name

async def refresh_leaderboard():
    global leaderboard_cache, leaderboard_details, leaderboard_last_refresh_at, leaderboard_next_refresh_at

    async with leaderboard_refresh_lock:
        async with stored_users_lock:
            users = list(stored_users.users.values())

        ranked_users = []
        for user in users:
            ranked_users.append({
                "id": int(user.id),
                "level": int(getattr(user, "level", 1)),
                "pp": int(getattr(user, "pp", 0)),
                "inventory_rarity": calculate_inventory_rarity_total(user),
                "display_name": getattr(user, "display_name", None),
            })

        ranked_users.sort(key=leaderboard_sort_key)
        ranked_users = ranked_users[:LEADERBOARD_MAX_PLAYERS]

        cached_names = {entry_id: entry_name for entry_name, entry_id in leaderboard_cache}
        refreshed_details = []
        saved_entries = []

        for entry in ranked_users:
            name = entry.get("display_name") or cached_names.get(entry["id"]) or await resolve_leaderboard_name(entry["id"])
            refreshed_details.append({
                **entry,
                "name": name,
            })
            saved_entries.append((name, entry["id"]))

        await jsontools.save_to_json(LEADERBOARD_FILE, saved_entries)

        now = datetime.datetime.now(datetime.timezone.utc)
        leaderboard_details = refreshed_details
        leaderboard_cache = saved_entries
        leaderboard_last_refresh_at = now
        leaderboard_next_refresh_at = now + datetime.timedelta(seconds=LEADERBOARD_REFRESH_SECONDS)


def generate_fake_user_name() -> str:
    return f"{random.choice(FAKE_NAME_PREFIXES)} {random.choice(FAKE_NAME_SUFFIXES)} {random.randint(1000, 9999)}"


def get_next_fake_user_id() -> int:
    used_ids = {int(user_id) for user_id in stored_users.users.keys()}
    next_id = FAKE_USER_ID_BASE

    while next_id in used_ids:
        next_id += 1

    return next_id


async def build_fake_user(user_id: int):
    fake_name = generate_fake_user_name()
    level = random.randint(1, 250)
    xp_needed = max(1, xp_to_next_level(level))
    fake_user = User(
        user_id,
        maps=[],
        items={},
        pp=random.randint(0, 5_000_000),
        xp=random.randint(0, max(0, xp_needed - 1)),
        level=level,
        dev_luck_base=1,
        display_name=fake_name,
        is_fake=True,
    )

    map_count = random.randint(10, 80)
    available_maps = getattr(probabilitycalc, "maps", None) or []
    if not available_maps:
        return fake_user

    for _ in range(map_count):
        map_data = random.choice(available_maps)
        map_result = await Dict_to_BeatmapDiff(map_data)
        duplicates = random.randint(1, 3)
        owned_map = User_BMD_Object(
            map_result.sr,
            map_result.parent_id,
            map_result.id,
            map_result.title,
            map_result.artist,
            map_result.difficulty_name,
            duplicates,
        )
        await fake_user.add_map(owned_map)

    return fake_user


async def clear_fake_users_from_store() -> int:
    async with stored_users_lock:
        fake_ids = [user_id for user_id, user in stored_users.users.items() if getattr(user, "is_fake", False)]

        for user_id in fake_ids:
            stored_users.users.pop(user_id, None)
            stored_users.users_json.pop(user_id, None)

    return len(fake_ids)


async def heartbeat():
    while True:
        await asyncio.sleep(LEADERBOARD_REFRESH_SECONDS)

        try:
            await write_stored_variable()
            await refresh_leaderboard()
        except Exception as error:
            print(f"Heartbeat failed: {error}")

# Loads all the necessary data for the bot to function
@client.event
async def on_ready():
    global _initialized
    if _initialized:
        return
    _initialized = True

    await load_dev_ids()

    # Run module initialization concurrently
    print("starting user_handling")
    await user_handling.init_user_handling()
    print("done user_handling")

    print("starting loadmaps")
    await loadmaps.init_loadmaps()
    print("done loadmaps")

    print("starting probabilitycalc")
    await probabilitycalc.init_probabilitycalc()
    print("done probabilitycalc")

    await refresh_leaderboard()

    asyncio.create_task(heartbeat())

    print(f"Bot ready as {client.user}")
    
"""@client.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        await ctx.message.reply("Command not found. Use o!help(WIP) to check available commands.")
    else:
        await ctx.message.reply("An error occurred while processing the command.")
        print(f"Error in command '{ctx.command}': {error}")"""

active_views = {}

########################## UTILS ##########################

# Maps the star rating into color emojis
emoji_map = {
    1: "<:1_:1415986345670606949>",
    2: "<:2_:1415986479062057020>",
    3: "<:3_:1415986584498606130>",
    4: "<:4_:1415986680267014144>",
    5: "<:5_:1415986831907885147>",
    6: "<:6_:1415986916394012806>",
    7: "<:7_:1415987059868434462>", 
    8: "<:8_:1415987148124979240>", 
    9: "<:9_:1415987239909064816>", 
    10: "<:10:1415987332552720426>", 
    11: "<:11:1415987398994558996>", 
    12: "<:12:1415987514371473488>", 
    13: "<:13:1415987587029667931>", 
    14: "<:14:1415987664330424320>", 
    15: "<:15:1415987720001552416>"
}

# Returns an emoji id from a given star rating
def get_star_emoji(star_rating: float) -> str:
    star = round(star_rating)
    if star < 1: star = 1
    if star > 15: star = 15
    return emoji_map.get(star, "<:15:345678901234567890>")

# Split a list into chunks of given size
def chunk_list(lst, size):
    return [lst[i:i + size] for i in range(0, len(lst), size)]

# Format a number with commas for thousands and above
def format_number(n: int) -> str:
    return format(n, ",")

# Return an xp bar using emojis
async def xp_bar(current_xp, xp_needed, length=10):
    progress = current_xp / xp_needed
    filled = int(progress * length)

    return "🟩" * filled + "⬛" * (length - filled)

# Flattens a dict of item categories into a single list of items for pagination
async def flatten_items(items_dict):
    """
    Turns:
    {"Shards": {"Common": Shard, "Uncommon": Shard}}
    into:
    [Shard, Shard]
    """
    items = []

    for category, category_items in items_dict.items():
        for item in category_items.values():
            items.append(item)

    return items

# Like flatten_items but for a specific category, returns list of items in that category or empty list if category not found
def flatten_category(items_dict, category: str):
    """
    {"Shards": {"Common": Shard, "Uncommon": Shard}}
    → [Shard, Shard]
    """
    category_items = items_dict.get(category, {})
    return list(category_items.values())

# Flattens a dict of item categories each containing lists of items into a single list of items for pagination
def flatten_item_lists(items_dict):
    """
    {"Peripherals": ListOfItems, "Consumables": ListOfItems}
    into
    [Item, Item, Item, Item]
    """
    itemlists = []
    items = []
    for category_items in items_dict.values():
        itemlists.append(category_items)
        
    for i in itemlists:
        for y in i:
            items.append(y)
            
    return items

# Returns the index of a shard rarity for sorting purposes, higher means rarer
def shard_rarity_index(rarity: str) -> int:
    return SHARD_RANK.get(rarity, 0)

# Class displays maps in a paging system and sorting
class MapPaginator(discord.ui.View):
    def __init__(self, maps, username, author: discord.User, per_page=6):
        super().__init__(timeout=120)
        self.original_maps = maps  # keep a reference to the unsorted maps
        self.maps = maps[:]        # working copy (can be sorted)
        self.author_id = author.id
        self.pages = chunk_list(self.maps, per_page) 
        self.index = 0
        self.username = username

        # add dropdown menu into the view
        self.add_item(self.SortDropdown(self))

    def update_pages(self):
        """Re-split maps into pages after sorting"""
        self.pages = chunk_list(self.maps, len(self.pages[0]))
        self.index = 0  # reset to first page

    def make_embed(self):        
        if len(self.pages) == 0:
            embed = discord.Embed(
                title=f"{self.username}'s Maps",
                color=discord.Color.blurple()
            )
            
            embed.add_field(
                name=f"You currently have no maps.",
                value="Use o!roll to roll for maps!",
                inline=False
            )
            
            return embed
        
        embed = discord.Embed(
            title=f"{self.username}'s Maps",
            color=discord.Color.blurple()
        )

        for m in self.pages[self.index]:
            difficulties = "\n".join(
                f"{get_star_emoji(d['star_rating'])} "
                f"- {d['difficulty_name']} ⭐ {d['star_rating']} (rarity 1 in {format_number(d['rarity'])}) -- ID: {d['id']} -- # {d['duplicates']}"
                for d in m["difficulties"]
            )

            embed.add_field(
                name=f"{m['title']} — {m['artist']} (by {m['mapper']}) -- ID: {m['id']}",
                value=difficulties,
                inline=False
            )

        embed.set_footer(text=f"Page {self.index+1}/{len(self.pages)}")
        return embed

    @discord.ui.button(label="◀️", style=discord.ButtonStyle.secondary)
    async def previous(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.index > 0:
            self.index -= 1
            await interaction.response.edit_message(embed=self.make_embed(), view=self)

    @discord.ui.button(label="▶️", style=discord.ButtonStyle.secondary)
    async def next(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.index < len(self.pages) - 1:
            self.index += 1
            await interaction.response.edit_message(embed=self.make_embed(), view=self)
            
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.author_id:
            await interaction.response.send_message(
                "❌ This menu isn’t yours.",
                ephemeral=True
            )
            return False
        return True

    class SortDropdown(discord.ui.Select):
        def __init__(self, paginator):
            self.paginator = paginator
            options = [
                discord.SelectOption(label="Default order", value="default"),
                discord.SelectOption(label="Rarity ↑ (low → high)", value="asc"),
                discord.SelectOption(label="Rarity ↓ (high → low)", value="desc"),
            ]
            super().__init__(placeholder="Sort maps by...", min_values=1, max_values=1, options=options)

        async def callback(self, interaction: discord.Interaction):            
            if self.values[0] == "asc":
                self.paginator.maps = sorted(self.paginator.original_maps, key=lambda m: min(d['rarity'] for d in m['difficulties']))
            elif self.values[0] == "desc":
                self.paginator.maps = sorted(self.paginator.original_maps, key=lambda m: max(d['rarity'] for d in m['difficulties']), reverse=True)
            else:
                self.paginator.maps = self.paginator.original_maps[:]  # reset

            self.paginator.update_pages()
            await interaction.response.edit_message(embed=self.paginator.make_embed(), view=self.paginator)


class LeaderboardView(discord.ui.View):
    def __init__(self, author: discord.User, initial_mode: str = "level"):
        super().__init__(timeout=120)
        self.author_id = author.id
        self.mode = initial_mode
        self.page_index = 0
        self.add_item(self.SortDropdown(self))
        self.update_buttons()

    def update_buttons(self):
        pages = get_leaderboard_pages(self.mode)
        total_pages = len(pages)
        self.previous.disabled = self.page_index <= 0
        self.next.disabled = total_pages <= 1 or self.page_index >= total_pages - 1

    async def refresh_message(self, interaction: discord.Interaction):
        embed = build_leaderboard_embed(self.mode, self.page_index)
        if embed is None:
            await interaction.response.edit_message(content="No players are on the leaderboard yet.", embed=None, view=None)
            return

        self.update_buttons()
        await interaction.response.edit_message(embed=embed, view=self)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.author_id:
            await interaction.response.send_message(
                "❌ This menu isn’t yours.",
                ephemeral=True
            )
            return False
        return True

    @discord.ui.button(label="◀️", style=discord.ButtonStyle.secondary)
    async def previous(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.page_index > 0:
            self.page_index -= 1
        await self.refresh_message(interaction)

    @discord.ui.button(label="▶️", style=discord.ButtonStyle.secondary)
    async def next(self, interaction: discord.Interaction, button: discord.ui.Button):
        pages = get_leaderboard_pages(self.mode)
        if self.page_index < len(pages) - 1:
            self.page_index += 1
        await self.refresh_message(interaction)

    class SortDropdown(discord.ui.Select):
        def __init__(self, leaderboard_view):
            self.leaderboard_view = leaderboard_view
            options = [
                discord.SelectOption(label="Level", value="level", default=leaderboard_view.mode == "level"),
                discord.SelectOption(label="PP", value="pp", default=leaderboard_view.mode == "pp"),
                discord.SelectOption(label="Map Rarity", value="rarity", default=leaderboard_view.mode == "rarity"),
            ]
            super().__init__(placeholder="Sort leaderboard by...", min_values=1, max_values=1, options=options)

        async def callback(self, interaction: discord.Interaction):
            self.leaderboard_view.mode = self.values[0]
            self.leaderboard_view.page_index = 0

            for option in self.options:
                option.default = option.value == self.leaderboard_view.mode

            await self.leaderboard_view.refresh_message(interaction)

# Dropdown for selecting item categories in inventory views
class ItemCategorySelect(discord.ui.Select):
    def __init__(self, user_items, paginator):
        self.user_items = user_items
        self.paginator = paginator

        options = [
            discord.SelectOption(
                label=category,
                value=category
            )
            for category in user_items.keys()
        ]

        super().__init__(
            placeholder="Select item type...",
            options=options,
            min_values=1,
            max_values=1
        )

    async def callback(self, interaction: discord.Interaction):
        category = self.values[0]

        items = flatten_category(self.user_items, category)

        # Sort shards by rarity order
        if category == "Shards":
            items.sort(key=lambda item: SHARD_RANK.get(item.shardrarity, 0))

        # Reset paginator
        self.paginator.items = items
        self.paginator.pages = chunk_list(items, self.paginator.per_page)
        self.paginator.index = 0
        self.paginator.current_category = category

        await interaction.response.edit_message(
            embed=self.paginator.make_embed(),
            view=self.paginator
        )    

class ShopModal(discord.ui.Modal):
    def __init__(self, view):
        super().__init__(title="Choose a shop item (1–5)")
        self.view = view
        
        self.number = discord.ui.TextInput(
            label="Enter a number from 1 to 5",
            placeholder="1-5",
            min_length=1,
            max_length=1
        )
        
        self.add_item(self.number)

    async def on_submit(self, interaction: discord.Interaction):
        value = self.number.value

        if value not in ["1", "2", "3", "4", "5"]:
            await interaction.response.send_message(
                "❌ Invalid number. Choose 1–5.", ephemeral=True
            )
            self.view.disable_view()
            return
        
        await interaction.response.defer()
        
        await self.view.process_buy_interaction(interaction, int(value))

# Class displays shop items in a paging system (WIP)
class ShopView(discord.ui.View):
    def __init__(self, user, author: discord.User, per_page=5):
        super().__init__(timeout=120)
        self.user = user
        self.author_id = author.id
        self.items = SHOP_ITEMS
        self.selectedcategory = "Peripherals"
        self.per_page = per_page
        self.pages = chunk_list(self.items[self.selectedcategory], self.per_page)
        self.index = 0
        
        self.add_item(self.ShopCategorySelect(self))
        
    def disable_view(self):
        for item in self.children:
            item.disabled = True
        self.stop()
        
    async def make_embed(self):
        embed = discord.Embed(
            title="Shop",
            color=discord.Color.purple()
        )

        for index, item in enumerate(self.pages[self.index]):
            description = (
                f"{item.description}\n"
                f"*{item.function}*\n"
                f"**ID:** {item.id}"
            )
            
            name = f"🔹 - {index + 1} - {item.name} - {item.value} PP"
            
            if getattr(item, 'type', None) == 'GearPeripheral':
                if self.user.find_item_by_id(getattr(item, 'id', None)):
                    name = f"❌ {item.name} - Owned"
                    description = "*You already own this item and cannot purchase it again.*"
                    
            if self.user.pp < item.value:
                name = f"❌ ~~{item.name} - {item.value} PP~~"
                description = (
                f"~~{item.description}~~\n"
                f"~~*{item.function}*~~\n"
                "*You don't have enough PP to buy this item.*"
                )
            
            embed.add_field(
                name=name,
                value=description,
                inline=False
            )

        embed.set_footer(text=f"Page {self.index + 1}/{len(self.pages)}")
        return embed
    
    async def update_buttons(self):
        pass
    
    @discord.ui.button(label="Buy", style=discord.ButtonStyle.success)
    async def buy(self, interaction, button):
        await interaction.response.send_modal(ShopModal(self))
        
    async def process_buy_interaction(self, interaction, number):
        if number is None:
            await interaction.message.reply(
                "❌ No item selected.", mention_author=False
            )
            return
        
        index = number - 1
        if index < 0 or index >= len(self.pages[self.index]):
            await interaction.message.reply(
                "❌ Invalid item number.", mention_author=False
            )
            return
        
        item = self.pages[self.index][index]
        
        if getattr(item, 'type', None) in ['Gear', 'GearPeripheral'] and self.user.find_item_by_id(getattr(item, 'id', None)):
            await interaction.message.reply(
                "❌ You already own this item and cannot purchase it again.", mention_author=False
            )
            return
        
        if self.user.pp < item.value:
            await interaction.message.reply(
                "❌ You don't have enough PP to buy this item.", mention_author=False
            )
            return
        
        await self.user.change_pp(-item.value)
        self.user.add_item(item, item.type)
        
        await update_user(self.user)
        
        await interaction.message.reply(f"You bought {item.name} for {item.value} PP!")
    
    @discord.ui.button(label="◀️", style=discord.ButtonStyle.secondary)
    async def previous(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.index > 0:
            self.index -= 1
            await interaction.response.edit_message(embed=await self.make_embed(), view=self)
            
        else:
            await interaction.response.edit_message(embed=await self.make_embed(), view=self)
            
    @discord.ui.button(label="▶️", style=discord.ButtonStyle.secondary)
    async def next(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.index < len(self.pages) - 1:
            self.index += 1
            await interaction.response.edit_message(embed=await self.make_embed(), view=self)
            
        else:
            await interaction.response.edit_message(embed=await self.make_embed(), view=self)
 
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.author_id:
            await interaction.response.send_message(
                "❌ This shop menu isn’t yours.",
                ephemeral=True
            )
            return False
        return True
    
    class ShopCategorySelect(discord.ui.Select):
        def __init__(self, view):
            self.shopview = view
            options = [
                discord.SelectOption(label=category, value=category)
                for category in SHOP_ITEMS.keys()
            ]
            super().__init__(placeholder="Select category...", options=options)
        
        async def callback(self, interaction):
            category = self.values[0]
            self.shopview.selectedcategory = category
            self.shopview.items = SHOP_ITEMS.get(category, [])
            self.shopview.pages = chunk_list(self.shopview.items, self.shopview.per_page)
            self.shopview.index = 0
            
            await interaction.response.edit_message(embed=await self.shopview.make_embed(), view=self.shopview)

# View for equipment menu (WIP)
class EquipmentView(discord.ui.View):
    def __init__(self, user, author: discord.User):
        super().__init__(timeout=120)
        self.user = user
        self.author_id = author.id
        self.equipped_items = {peripheral_type: None for peripheral_type in PERIPHERAL_TYPES}
        self.selected_peripheral = None
        
        self.add_item(self.PeripheralSelect(self))
        
    async def update_equipped_items(self):
        for peripheral_type in PERIPHERAL_TYPES:
            equipped = None
            for item in self.user.items.get("GearPeripheral", {}).values():
                if getattr(item, 'peripheraltype', None) == peripheral_type and getattr(item, 'equipped', False):
                    equipped = item
                    break
            self.equipped_items[peripheral_type] = equipped
        
    async def make_embed(self):
        await self.update_equipped_items()
        
        embed = discord.Embed(
            title="Equipment",
            color=discord.Color.red()
        )

        for peripheral_type in PERIPHERAL_TYPES:
            equipped = self.equipped_items.get(peripheral_type)
            if equipped:
                name = f"✅ {peripheral_type}: {equipped.name}"
                description = equipped.description
            else:
                name = f"❌ {peripheral_type}: None"
                description = "No item equipped in this slot."

            embed.add_field(
                name=name,
                value=description,
                inline=False
            )
            
        for item in self.children:
            if isinstance(item, discord.ui.Select):
                self.remove_item(item)
        
        self.add_item(self.PeripheralSelect(self))

        return embed
    
    async def show_available_equipment(self, interaction, peripheral_type):
        available = [
            item for item in self.user.items.get("GearPeripheral", {}).values()
            if getattr(item, 'peripheraltype', None) == peripheral_type
        ]

        if not available:
            await interaction.response.send_message(
                f"You have no {peripheral_type} peripherals to equip.",
                ephemeral=True
            )
            return
        
        embed = discord.Embed(
            title=f"Available {peripheral_type} Peripherals",
            color=discord.Color.orange()
        )
        
        for item in available:
            name = f"{item.name} (Luck +{item.luckincrease}, ×{item.luckmultiplier})"
            description = f"{item.description}\n**ID:** {item.id}"
            embed.add_field(name=name, value=description, inline=False)
            
        for item in self.children:
            if isinstance(item, discord.ui.Select):
                self.remove_item(item)
        
        self.add_item(self.PeripheralCategorySelect(self, available))
        self.add_item(self.PeripheralSelect(self))
            
        await interaction.response.edit_message(embed=embed, view=self)
        
    class PeripheralCategorySelect(discord.ui.Select):
        def __init__(self, view, available):
            self.equipmentview = view
            options = [
                discord.SelectOption(label=item.name, value=item.name)
                for item in available
            ]
            super().__init__(placeholder="Select item to equip.", options=options)
            
        async def callback(self, interaction):
            equipped_name = self.values[0]
            for item in self.equipmentview.user.items.get("GearPeripheral", {}).values():
                if item.peripheraltype != self.equipmentview.selected_peripheral:
                    continue
                
                item.equipped = False
                
                if item.name == equipped_name:
                    item.equipped = True
                    break
                
            await update_user(self.equipmentview.user)
            await self.equipmentview.update_equipped_items()
            
            await interaction.response.edit_message(embed=await self.equipmentview.make_embed(), view=self.equipmentview)
        
    class PeripheralSelect(discord.ui.Select):
        def __init__(self, view):
            self.equipmentview = view
            options = [
                discord.SelectOption(label=peripheral_type, value=peripheral_type)
                for peripheral_type in PERIPHERAL_TYPES
            ]
            super().__init__(placeholder="Select peripheral type to modify.", options=options)
            
        async def callback(self, interaction):
            peripheral_type = self.values[0]
            
            self.equipmentview.selected_peripheral = peripheral_type
            await self.equipmentview.show_available_equipment(interaction, peripheral_type)
            
# Dropdown for selecting crafting recipes in recipe menu
class CraftRecipeSelect(discord.ui.Select):
    def __init__(self, recipes, selected_recipe_id: str | None):
        options = []

        for recipe in recipes:
            options.append(
                discord.SelectOption(
                    label=recipe.name,
                    description=recipe.description[:50],
                    value=recipe.id,
                    default=(recipe.id == selected_recipe_id)  # ⭐ key line
                )
            )

        super().__init__(
            placeholder="Select recipe",
            options=options
        )

    async def callback(self, interaction):
        view: CraftingView = self.view
        view.selected_recipe_id = self.values[0]
        view.craft_amount = 1  # reset amount on change
        view.selected_map_ids = []

        view.refresh_components()

        await interaction.response.edit_message(
            embed=view.make_embed(),
            view=view
        )

# Dropdown for selecting crafting categories in recipe menu
class CraftCategorySelect(discord.ui.Select):
    def __init__(self, current_category: str):
        options = []

        for label, value in [
            ("Shard Cores", "ShardCores"),
            ("Beatmap Charms", "BeatmapCharms"),
            ("Tools", "Tools"),
            ("Essences", "Essences")
        ]:
            options.append(
                discord.SelectOption(
                    label=label,
                    value=value,
                    default=(value == current_category)
                )
            )

        super().__init__(
            placeholder="Select crafting category",
            options=options
        )

    async def callback(self, interaction):
        view: CraftingView = self.view
        view.set_category(self.values[0])

        await interaction.response.edit_message(
            embed=view.make_embed(),
            view=view
        )     
        
class CraftAmountModal(discord.ui.Modal):
    def __init__(self, recipe, view):
        super().__init__(title="Enter craft amount")
        self.view = view
        self.recipe = recipe
        
        self.amount = discord.ui.TextInput(
            label="Amount to craft",
            placeholder="Enter a number",
            min_length=1,
            max_length=5
        )
        
        self.add_item(self.amount)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            value = int(self.amount.value)
            if value < 1:
                raise ValueError
        except ValueError:
            await interaction.response.send_message(
                "❌ Invalid amount. Please enter a positive integer.", ephemeral=True
            )
            return
        
        view: CraftingView = self.view
        recipe = self.recipe
        
        if recipe is None:
            await interaction.response.send_message(
                "❌ No recipe selected.", ephemeral=True
            )
            return
        
        max_craftable = recipe.max_craftable(view.user)
        
        if value > max_craftable:
            await interaction.response.send_message(
                f"❌ You can only craft up to {max_craftable} of this item.", ephemeral=True
            )
            return
        
        view.craft_amount = value
        view.selected_map_ids = []
        view.refresh_components()
        
        await interaction.response.edit_message(
            embed=view.make_embed(),
            view=view
        )


class CraftMapSelectionView(discord.ui.View):
    def __init__(self, parent_view, recipe, required_count: int, author_id: int, parent_message, per_page: int = 5):
        super().__init__(timeout=120)
        self.parent_view = parent_view
        self.recipe = recipe
        self.required_count = max(0, required_count)
        self.author_id = author_id
        self.parent_message = parent_message
        self.per_page = per_page
        self.index = 0

        eligible_lookup = self.parent_view.get_eligible_map_lookup_for_recipe(recipe)
        eligible_diffs = list(eligible_lookup.values())
        eligible_diffs.sort(key=lambda d: d.sr, reverse=True)

        self.units = []
        for diff in eligible_diffs:
            copies = max(0, int(getattr(diff, "duplicates", 0)))
            for copy_index in range(copies):
                self.units.append({
                    "unit_key": f"{diff.id}:{copy_index + 1}",
                    "diff_id": diff.id,
                    "title": diff.title,
                    "difficulty_name": diff.difficulty_name,
                    "sr": diff.sr,
                    "copy_index": copy_index + 1,
                    "total_copies": copies,
                })

        self.pages = chunk_list(self.units, self.per_page) if self.units else [[]]
        self.selected_unit_keys = set()
        self._preselect_from_parent()
        self._update_slot_buttons()

    def _preselect_from_parent(self):
        if not self.parent_view.selected_map_ids:
            return

        desired_counts = Counter(self.parent_view.selected_map_ids)
        for unit in self.units:
            diff_id = unit["diff_id"]
            if len(self.selected_unit_keys) >= self.required_count:
                break
            if desired_counts.get(diff_id, 0) > 0:
                self.selected_unit_keys.add(unit["unit_key"])
                desired_counts[diff_id] -= 1

    def selected_count(self) -> int:
        return len(self.selected_unit_keys)

    def selected_map_ids(self):
        result = []
        for unit in self.units:
            if unit["unit_key"] in self.selected_unit_keys:
                result.append(unit["diff_id"])
        return result

    def _update_slot_buttons(self):
        current_page = self.pages[self.index]
        slot_buttons = [self.sm1, self.sm2, self.sm3, self.sm4, self.sm5]

        for i, button in enumerate(slot_buttons):
            if i < len(current_page):
                unit = current_page[i]
                button.disabled = False
                button.style = discord.ButtonStyle.success if unit["unit_key"] in self.selected_unit_keys else discord.ButtonStyle.primary
            else:
                button.disabled = True
                button.style = discord.ButtonStyle.secondary

        self.previous.disabled = self.index == 0
        self.next.disabled = self.index >= len(self.pages) - 1
        self.confirm.disabled = self.selected_count() != self.required_count

    def make_embed(self):
        embed = discord.Embed(
            title=f"Map Selection - {self.recipe.name}",
            color=discord.Color.blurple()
        )

        map_req = getattr(self.recipe, "map_requirement", None)
        req_text = map_req.format_requirement() if map_req is not None else "No map requirement"
        embed.description = (
            f"Select exactly **{self.required_count}** map(s).\n"
            f"Requirement: **{req_text}**\n"
            f"Selected: **{self.selected_count()}/{self.required_count}**"
        )

        current_page = self.pages[self.index]
        if not current_page:
            lines = ["No eligible maps in your inventory."]
        else:
            lines = []
            for i, unit in enumerate(current_page, start=1):
                marker = "✅" if unit["unit_key"] in self.selected_unit_keys else "▫️"
                copy_text = ""
                if unit["total_copies"] > 1:
                    copy_text = f" | Copy {unit['copy_index']}/{unit['total_copies']}"

                lines.append(
                    f"{marker} {i}. {unit['title']} [{unit['difficulty_name']}] | ⭐ {unit['sr']} | ID: {unit['diff_id']}{copy_text}"
                )

        embed.add_field(name="Maps", value="\n".join(lines), inline=False)
        embed.set_footer(text=f"Page {self.index + 1}/{len(self.pages)}")
        return embed

    async def _toggle_slot(self, interaction: discord.Interaction, slot_index: int):
        current_page = self.pages[self.index]
        if slot_index >= len(current_page):
            self._update_slot_buttons()
            await interaction.response.edit_message(embed=self.make_embed(), view=self)
            return

        unit = current_page[slot_index]
        unit_key = unit["unit_key"]

        if unit_key in self.selected_unit_keys:
            self.selected_unit_keys.remove(unit_key)
        else:
            if self.selected_count() >= self.required_count:
                await interaction.response.send_message(
                    f"You can only select {self.required_count} map(s).",
                    ephemeral=True
                )
                return

            self.selected_unit_keys.add(unit_key)

        self._update_slot_buttons()
        await interaction.response.edit_message(embed=self.make_embed(), view=self)

    @discord.ui.button(label="1️⃣", style=discord.ButtonStyle.primary)
    async def sm1(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._toggle_slot(interaction, 0)

    @discord.ui.button(label="2️⃣", style=discord.ButtonStyle.primary)
    async def sm2(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._toggle_slot(interaction, 1)

    @discord.ui.button(label="3️⃣", style=discord.ButtonStyle.primary)
    async def sm3(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._toggle_slot(interaction, 2)

    @discord.ui.button(label="4️⃣", style=discord.ButtonStyle.primary)
    async def sm4(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._toggle_slot(interaction, 3)

    @discord.ui.button(label="5️⃣", style=discord.ButtonStyle.primary)
    async def sm5(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._toggle_slot(interaction, 4)

    @discord.ui.button(label="◀️", style=discord.ButtonStyle.secondary)
    async def previous(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.index > 0:
            self.index -= 1
        self._update_slot_buttons()
        await interaction.response.edit_message(embed=self.make_embed(), view=self)

    @discord.ui.button(label="▶️", style=discord.ButtonStyle.secondary)
    async def next(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.index < len(self.pages) - 1:
            self.index += 1
        self._update_slot_buttons()
        await interaction.response.edit_message(embed=self.make_embed(), view=self)

    @discord.ui.button(label="Clear", style=discord.ButtonStyle.danger)
    async def clear(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.selected_unit_keys.clear()
        self._update_slot_buttons()
        await interaction.response.edit_message(embed=self.make_embed(), view=self)

    @discord.ui.button(label="Confirm", style=discord.ButtonStyle.success)
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        selected_ids = self.selected_map_ids()
        ok, message = self.parent_view.validate_selected_maps(self.recipe, selected_ids)
        if not ok:
            await interaction.response.send_message(message, ephemeral=True)
            return

        self.parent_view.selected_map_ids = selected_ids
        self.parent_view.refresh_components()

        try:
            await self.parent_message.edit(embed=self.parent_view.make_embed(), view=self.parent_view)
        except Exception:
            pass

        try:
            await interaction.response.defer()
            await interaction.delete_original_response()
        except Exception:
            try:
                await interaction.message.delete()
            except Exception:
                pass

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.author_id:
            await interaction.response.send_message(
                "❌ This map selection menu isn’t yours.",
                ephemeral=True
            )
            return False
        return True

# Class for crafting menu, includes category and recipe dropdowns and crafting buttons
# When I built this, I was barely awake on like 2 hours of sleep and I have no recollection of ever writing it. 
# Realistically this code is never getting touched again by me
# I won't even try to optimize it.
class CraftingView(discord.ui.View):
    def __init__(self, user, author: discord.User):
        super().__init__(timeout=120)
        self.user = user
        self.author_id = author.id
        self.category = "ShardCores"
        self.craft_amount = 1
        self.selected_recipe_id = None
        self.selected_map_ids = []

        self.refresh_components()  
        
    def set_category(self, category: str):
        self.category = category
        self.selected_recipe_id = None
        self.craft_amount = 1
        self.selected_map_ids = []
        self.refresh_components()
        
    def refresh_components(self):
        self.clear_items()

        # category dropdown
        self.add_item(CraftCategorySelect(self.category))

        # recipe dropdown (depends on category)
        recipes = self.get_recipes_for_category()
        if recipes:
            self.add_item(
                CraftRecipeSelect(
                    recipes,
                    self.selected_recipe_id
                )
            )

        # buttons
        # determine if selected recipe is Gear (Beatmap Charm)
        recipe = self.get_selected_recipe()
        is_single = False
        if recipe is not None:
            is_single = getattr(recipe.result, 'type', None) in ('Gear', 'GearPeripheral', 'Tool')

        # enforce single-quantity for gear
        if is_single:
            self.craft_amount = 1

        # disable +/- when crafting gear since only 1 is allowed
        self.decrease.disabled = is_single
        self.increase.disabled = is_single

        self.add_item(self.decrease)
        self.add_item(self.increase)
        self.add_item(self.select_amount)
        self.select_maps.disabled = recipe is None or getattr(recipe, "map_requirement", None) is None
        self.add_item(self.select_maps)
        self.add_item(self.craft)
        self.add_item(self.craft_max)

    def get_eligible_map_lookup_for_recipe(self, recipe):
        map_req = getattr(recipe, "map_requirement", None)
        if map_req is None:
            return {}

        return self.user.get_eligible_map_lookup(
            min_star=map_req.min_star,
            max_star=map_req.max_star,
            include_min=map_req.include_min,
            include_max=map_req.include_max,
        )

    def validate_selected_maps(self, recipe, selected_ids):
        map_req = getattr(recipe, "map_requirement", None)
        if map_req is None:
            return True, ""

        eligible_lookup = self.get_eligible_map_lookup_for_recipe(recipe)
        counts = Counter(selected_ids)

        for map_id, amount in counts.items():
            diff = eligible_lookup.get(map_id)
            if diff is None:
                return False, f"Map ID {map_id} does not meet the recipe requirements or is not in your inventory."

            if amount > getattr(diff, "duplicates", 0):
                return False, f"Map ID {map_id} only has {getattr(diff, 'duplicates', 0)} copies in your inventory."

        return True, ""

    def disable_all_components(self):
        """Disable all interactive components in the view (used after crafting)."""
        for child in self.children:
            try:
                child.disabled = True
            except Exception:
                pass
            
    def get_recipes_for_category(self):
        # Filter available recipes by craftability and prevent showing Gear (charms)
        # recipes the user already owns.
        # Do not show recipes that have item requirements the user does not meet (e.g. previous charm tier)
        results = []
        for r in ALL_RECIPES.get(self.category, []):
            # check item requirement
            if getattr(r, 'item_requirement', None) is not None:
                if self.user.count_item_by_id(r.item_requirement) == 0:
                    continue

            res = getattr(r, 'result', None)
            if res is not None and getattr(res, 'type', None) in ('Gear', 'GearPeripheral', 'Tool'):
                # if user already has this gear, skip the recipe
                if self.user.count_item_by_id(getattr(res, 'id', None)) > 0:
                    continue

            results.append(r)

        return results
        
    def get_selected_recipe(self):
        if self.selected_recipe_id is None:
            return None

        for recipe in ALL_RECIPES.get(self.category, []):
            if recipe.id == self.selected_recipe_id:
                return recipe

        return None
        
    def make_embed(self):
        recipe = self.get_selected_recipe()

        # dynamic title: use recipe name if selected, otherwise derive from category
        if recipe is None:
            if self.category == "ShardCores":
                title_text = "🛠 Shard Core Crafting"
            elif self.category == "BeatmapCharms":
                title_text = "🛠 Beatmap Charm Crafting"
            else:
                title_text = "🛠 Crafting"
        else:
            title_text = f"🛠 {recipe.name}"

        embed = discord.Embed(
            title=title_text,
            color=discord.Color.gold()
        )
        
        if recipe is None:
            embed.description = "Select a crafting category and recipe from the dropdowns below."

            embed.add_field(
                name="How crafting works",
                value=(
                    "• Choose a category\n"
                    "• Select a recipe\n"
                    "• Adjust amount\n"
                    "• Craft!"
                ),
                inline=False
            )

            embed.set_footer(text="Waiting for recipe selection")
            return embed
        
        embed.description = recipe.description

        requirement_lines = []
        for item_id, amt in recipe.requirements.items():
            requirement_lines.append(
                f"🔹 **{amt}× {ITEMS_BY_ID.get(item_id).name if ITEMS_BY_ID.get(item_id) else item_id}** | You Have: {self.user.count_item_by_id(item_id)}"
            )

        map_req = getattr(recipe, "map_requirement", None)
        if map_req is not None:
            eligible_count = self.user.count_eligible_maps(
                min_star=map_req.min_star,
                max_star=map_req.max_star,
                include_min=map_req.include_min,
                include_max=map_req.include_max,
            )
            requirement_lines.append(
                f"🗺️ **{map_req.format_requirement()}** | Eligible in Inventory: {eligible_count}"
            )

        if not requirement_lines:
            requirement_lines.append("No item requirements.")

        embed.add_field(
            name="Requirements",
                value="\n".join(requirement_lines),
            inline=False
        )

        if map_req is not None:
            eligible_lookup = self.get_eligible_map_lookup_for_recipe(recipe)
            eligible_maps = list(eligible_lookup.values())
            eligible_maps.sort(key=lambda d: d.sr, reverse=True)

            if eligible_maps:
                preview = "\n".join(
                    f"• {d.title} [{d.difficulty_name}] | ⭐ {d.sr} | ID: {d.id} | x{d.duplicates}"
                    for d in eligible_maps[:10]
                )
                if len(eligible_maps) > 10:
                    preview += f"\n... and {len(eligible_maps) - 10} more"
            else:
                preview = "No eligible maps in your inventory."

            embed.add_field(
                name="Eligible Maps",
                value=preview,
                inline=False,
            )

            needed = map_req.amount * self.craft_amount
            selected = len(self.selected_map_ids)
            embed.add_field(
                name="Selected Maps",
                value=f"{selected}/{needed} selected",
                inline=False,
            )

        embed.add_field(
            name="Result",
            value=(f"✨ {recipe.result.name}\n"
                   f"**ID:** {recipe.result.id}"
            ),
            inline=False
        )
        
        embed.add_field(
            name="Amount",
            value=f"×{self.craft_amount}",
            inline=True
        )

        # Show max craftable. For Gear recipes this is always 1 (if available).
        if getattr(recipe.result, 'type', None) == 'Gear':
            can_craft_max = 1
        else:
            can_craft_max = recipe.max_craftable(self.user)

        embed.add_field(
            name="You Can Craft",
            value=f"{can_craft_max} max",
            inline=True
        )

        return embed      
    
    async def craft(self, interaction, amount: int):
        recipe = self.get_selected_recipe()

        if not recipe.can_craft(self.user, amount):
            await interaction.response.send_message(
                "Not enough materials.",
                ephemeral=True
            )
            return

        recipe.consume(self.user, amount)
        recipe.give_result(self.user, amount)

        await interaction.response.edit_message(
            embed=self.make_embed(),
            view=self
        )   
        
    @discord.ui.button(label="➖", style=discord.ButtonStyle.secondary)
    async def decrease(self, interaction, button):
        # no-op if selected recipe is Gear (only 1 allowed)
        recipe = self.get_selected_recipe()
        if recipe is not None and getattr(recipe.result, 'type', None) == 'Gear':
            await interaction.response.edit_message(embed=self.make_embed(), view=self)
            return

        if self.craft_amount > 1:
            self.craft_amount -= 1
            self.selected_map_ids = []

        await interaction.response.edit_message(
            embed=self.make_embed(),
            view=self
        )
        
    @discord.ui.button(label="➕", style=discord.ButtonStyle.secondary)
    async def increase(self, interaction, button):
        recipe = self.get_selected_recipe()
        if not recipe:
            return

        # no-op if Gear
        if getattr(recipe.result, 'type', None) == 'Gear':
            await interaction.response.edit_message(embed=self.make_embed(), view=self)
            return

        max_amount = recipe.max_craftable(self.user)
        if self.craft_amount < max_amount:
            self.craft_amount += 1
            self.selected_map_ids = []

        await interaction.response.edit_message(
            embed=self.make_embed(),
            view=self
        )
        
    @discord.ui.button(label="Select Amount", style=discord.ButtonStyle.secondary)  
    async def select_amount(self, interaction, button):
        recipe = self.get_selected_recipe()
        if not recipe:
            return

        # For Gear recipes, crafting amount is always 1, so no need to show modal
        if getattr(recipe.result, 'type', None) == 'Gear':
            await interaction.response.edit_message(embed=self.make_embed(), view=self)
            return

        modal = CraftAmountModal(recipe, self)
        await interaction.response.send_modal(modal)

    @discord.ui.button(label="Select Maps", style=discord.ButtonStyle.primary)
    async def select_maps(self, interaction, button):
        recipe = self.get_selected_recipe()
        if recipe is None:
            return

        if getattr(recipe, "map_requirement", None) is None:
            await interaction.response.send_message(
                "This recipe does not require maps.",
                ephemeral=True,
            )
            return

        required_count = recipe.map_requirement.amount * self.craft_amount
        picker_view = CraftMapSelectionView(
            parent_view=self,
            recipe=recipe,
            required_count=required_count,
            author_id=self.author_id,
            parent_message=interaction.message,
            per_page=5,
        )

        await interaction.response.send_message(
            embed=picker_view.make_embed(),
            view=picker_view,
            ephemeral=True,
        )
        
    @discord.ui.button(label="Craft", style=discord.ButtonStyle.success)
    async def craft(self, interaction, button):
        recipe = self.get_selected_recipe()
        if not recipe:
            return

        print(getattr(recipe.result, 'type', None))
        print(self.user.count_item_by_id(getattr(recipe.result, 'id', None)))

        # Prevent crafting limited items the user already owns
        if getattr(recipe.result, 'type', None) in ('Gear', 'GearPeripheral', 'Tool') and self.user.count_item_by_id(getattr(recipe.result, 'id', None)) > 0:
            return await interaction.response.send_message(
                "You already own this item and cannot craft another.",
                ephemeral=True
            )

        # Enforce single quantity for limited items
        if getattr(recipe.result, 'type', None) in ('Gear', 'GearPeripheral', 'Tool'):
            amount_to_craft = 1
        else:
            amount_to_craft = self.craft_amount

        if amount_to_craft > recipe.max_craftable(self.user):
            return await interaction.response.send_message(
                "Not enough materials.",
                ephemeral=True
            )

        selected_map_ids = None
        map_req = getattr(recipe, "map_requirement", None)
        if map_req is not None:
            needed = map_req.amount * amount_to_craft
            if len(self.selected_map_ids) < needed:
                return await interaction.response.send_message(
                    f"Select {needed} eligible map ID(s) first using the Select Maps button.",
                    ephemeral=True,
                )

            ok, message = self.validate_selected_maps(recipe, self.selected_map_ids)
            if not ok:
                return await interaction.response.send_message(
                    message,
                    ephemeral=True,
                )

            selected_map_ids = self.selected_map_ids[:needed]

        recipe.consume(self.user, amount_to_craft, selected_map_ids=selected_map_ids)
        recipe.give_result(self.user, amount_to_craft)
        
        await interaction.message.reply(
                f"Crafted {self.craft_amount}x {recipe.name}"
            )

        self.craft_amount = 1  # reset after craft
        self.selected_map_ids = []
        
        await update_user(self.user)
        # Disable the view so the user cannot craft again from the same menu
        self.disable_all_components()

        await interaction.response.edit_message(
            embed=self.make_embed(),
            view=self
        )
        
    @discord.ui.button(label="Craft Max", style=discord.ButtonStyle.primary)
    async def craft_max(self, interaction, button):
        recipe = self.get_selected_recipe()
        if not recipe:
            return

        # Prevent crafting Gear (charms) the user already owns
        if getattr(recipe.result, 'type', None) in ('Gear', 'GearPeripheral', 'Tool') and self.user.count_item_by_id(getattr(recipe.result, 'id', None)) > 0:
            return await interaction.response.send_message(
                "You already own this item and cannot craft another.",
                ephemeral=True
            )

        # For Gear recipes, craft exactly 1. Otherwise craft max.
        if getattr(recipe.result, 'type', None) in ('Gear', 'GearPeripheral', 'Tool'):
            amount = 1
        else:
            amount = recipe.max_craftable(self.user)

        selected_map_ids = None
        map_req = getattr(recipe, "map_requirement", None)
        if map_req is not None:
            if len(self.selected_map_ids) == 0:
                return await interaction.response.send_message(
                    "Select at least one eligible map ID using the Select Maps button.",
                    ephemeral=True,
                )

            ok, message = self.validate_selected_maps(recipe, self.selected_map_ids)
            if not ok:
                return await interaction.response.send_message(
                    message,
                    ephemeral=True,
                )

            selected_limited = len(self.selected_map_ids) // map_req.amount
            amount = min(amount, selected_limited)
            selected_map_ids = self.selected_map_ids[: amount * map_req.amount]

        if amount == 0:
            return await interaction.response.send_message(
                "No valid craft amount available with the selected maps.",
                ephemeral=True,
            )

        recipe.consume(self.user, amount, selected_map_ids=selected_map_ids)
        recipe.give_result(self.user, amount)
        
        await update_user(self.user)

        self.craft_amount = 1
        self.selected_map_ids = []

        # Disable the view after crafting to prevent further interaction
        self.disable_all_components()

        await interaction.response.edit_message(
            embed=self.make_embed(),
            view=self
        )

        await interaction.message.reply(
                f"Crafted {amount}x {recipe.name}"
            )

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.author_id:
            await interaction.response.send_message(
                "❌ This crafting menu isn’t yours.",
                ephemeral=True
            )
            return False
        return True

# Displays a user's inventory in a paginated embed with category selection
class ItemPaginator(discord.ui.View):
    def __init__(self, user_items, username, author: discord.User, per_page=8):
        super().__init__(timeout=120)
        self.user_items = user_items
        self.username = username
        self.author_id = author.id
        self.per_page = per_page
        self.index = 0
        self.current_category = "Shards"

        # Initial load
        self.items = flatten_category(self.user_items, "Shards")
        self.items.sort(key=lambda i: SHARD_RANK.get(i.shardrarity, 0))
        self.pages = chunk_list(self.items, per_page)

        self.add_item(ItemCategorySelect(self.user_items, self))

    def make_embed(self):
        embed = discord.Embed(
            title=f"{self.username}'s {self.current_category}",
            color=discord.Color.green()
        )

        if not self.pages:
            embed.description = "No items in this category."
            return embed

        for item in self.pages[self.index]:
            if not item.type in ("Tool"):
                embed.add_field(
                    name=f"🔹 {item.name} ×{item.duplicates}",
                    value=(
                        f"{item.function}\n"
                        f"**ID**: {item.id}"
                    )
                )
                
            else:
                embed.add_field(
                    name=f"🔹 {item.name}",
                    value=(
                        f"{item.description}\n"
                        f"**ID**: {item.id}"
                    )
                )

        embed.set_footer(text=f"Page {self.index + 1}/{len(self.pages)}")
        return embed

    @discord.ui.button(label="◀️", style=discord.ButtonStyle.secondary)
    async def previous(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.index > 0:
            self.index -= 1
            await interaction.response.edit_message(embed=self.make_embed(), view=self)

    @discord.ui.button(label="▶️", style=discord.ButtonStyle.secondary)
    async def next(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.index < len(self.pages) - 1:
            self.index += 1
            await interaction.response.edit_message(embed=self.make_embed(), view=self)
            
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.author_id:
            await interaction.response.send_message(
                "❌ This menu isn’t yours.",
                ephemeral=True
            )
            return False
        return True


# Class displays maps in a paging system and sorting to sell
class SellingPaginator(discord.ui.View):
    def __init__(self, user, maps, username, author: discord.User, per_page=5):
        super().__init__(timeout=120)
        self.original_maps = maps  # keep a reference to the unsorted maps  
        self.undividedmaps = []  
        self.author_id = author.id
        def divide_maps(maps):
            result = []
            
            for i in maps:
                for y in i.difficulties:
                    new = User_BM_Object(i.id, i.title, i.artist, i.mapper, i.status, [y])
                    result.append(new)
            
            return result
        
        self.maps = divide_maps(user.maps)
        
        for i in self.maps:
            self.undividedmaps.append(UBMO_To_Dict_nonsync(i))
        
        self.pages = chunk_list(self.undividedmaps, per_page)
        self.mapsinqueue = []
        self.index = 0
        self.username = username
        self.user = user

        # add dropdown menu into the view
        self.add_item(self.SortDropdown(self))

    def update_pages(self):
        """Re-split maps into pages after sorting"""
        self.pages = chunk_list(self.maps, len(self.pages[0]))
        self.index = 0  # reset to first page

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.author_id:
            await interaction.response.send_message(
                "❌ This crafting menu isn’t yours.",
                ephemeral=True
            )
            return False
        return True
    
    def make_embed(self):
        if len(self.pages) == 0:
            embed = discord.Embed(
                title=f"Selling Maps",
                color=discord.Color.blurple()
            )
            
            embed.add_field(
                name=f"You currently have no maps.",
                value="Use o!roll to roll for maps!",
                inline=False
            )
            
            return embed
        
        embed = discord.Embed(
            title="Selling Maps",
            color=discord.Color.blurple()
        )

        for m in self.pages[self.index]:
            difficulties = "\n".join(
                f"{get_star_emoji(d['star_rating'])} "
                f"- {d['difficulty_name']} ⭐ {d['star_rating']} (rarity 1 in {format_number(d['rarity'])}) -- ID: {d['id']} -- # {d['duplicates']}"
                for d in m["difficulties"]
            )

            embed.add_field(
                name=f"{m['title']} — {m['artist']} (by {m['mapper']}) -- ID: {m['id']}",
                value=difficulties,
                inline=False
            )

        embed.set_footer(text=f"Page {self.index+1}/{len(self.pages)}")
        return embed
    
    async def checkmaps_updatebuttons(self):
        if len(self.pages[self.index])>0:
            if self.pages[self.index][0]["difficulties"][0] in self.mapsinqueue:
                self.sm1.style = discord.ButtonStyle.success
            else:
                self.sm1.style = discord.ButtonStyle.primary
        else:        
            self.sm1.style = discord.ButtonStyle.primary
        
        if len(self.pages[self.index])>1:
            if self.pages[self.index][1]["difficulties"][0] in self.mapsinqueue:
                self.sm2.style = discord.ButtonStyle.success
            else:
                self.sm2.style = discord.ButtonStyle.primary
        else:        
            self.sm2.style = discord.ButtonStyle.primary
            
        if len(self.pages[self.index])>2:
            if self.pages[self.index][2]["difficulties"][0] in self.mapsinqueue:
                self.sm3.style = discord.ButtonStyle.success
            else:
                self.sm3.style = discord.ButtonStyle.primary
        else:        
            self.sm3.style = discord.ButtonStyle.primary
            
        if len(self.pages[self.index])>3:
            if self.pages[self.index][3]["difficulties"][0] in self.mapsinqueue:
                self.sm4.style = discord.ButtonStyle.success
            else:
                self.sm4.style = discord.ButtonStyle.primary
        else:        
            self.sm4.style = discord.ButtonStyle.primary
            
        if len(self.pages[self.index])>4:
            if self.pages[self.index][4]["difficulties"][0] in self.mapsinqueue:
                self.sm5.style = discord.ButtonStyle.success
            else:
                self.sm5.style = discord.ButtonStyle.primary
        else:        
            self.sm5.style = discord.ButtonStyle.primary 

            
    @discord.ui.button(label="1️⃣", style=discord.ButtonStyle.primary)
    async def sm1(self, interaction: discord.Interaction, button: discord.ui.Button):
        selectedmap = self.pages[self.index][0]["difficulties"][0]
        
        if selectedmap in self.mapsinqueue:
            self.mapsinqueue.remove(selectedmap)
            await self.checkmaps_updatebuttons()
            await interaction.response.edit_message(view=self)
            
            return
        
        self.mapsinqueue.append(selectedmap)
        await self.checkmaps_updatebuttons()
        await interaction.response.edit_message(view=self)
    
    @discord.ui.button(label="2️⃣", style=discord.ButtonStyle.primary)
    async def sm2(self, interaction: discord.Interaction, button: discord.ui.Button):    
        if not len(self.pages[self.index])>1:
            await interaction.message.reply("Map selection failed")
            await interaction.response.edit_message(view=self)
            return
            
        selectedmap = self.pages[self.index][1]["difficulties"][0]
        
        if selectedmap in self.mapsinqueue:
            self.mapsinqueue.remove(selectedmap)
            await self.checkmaps_updatebuttons()
            await interaction.response.edit_message(view=self)
            
            return
        
        self.mapsinqueue.append(selectedmap)
        await self.checkmaps_updatebuttons()
        await interaction.response.edit_message(view=self)
        
    @discord.ui.button(label="3️⃣", style=discord.ButtonStyle.primary)
    async def sm3(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not len(self.pages[self.index])>2:
            await interaction.message.reply("Map selection failed")
            await interaction.response.edit_message(view=self)
            return
        
        selectedmap = self.pages[self.index][2]["difficulties"][0]
        
        if selectedmap in self.mapsinqueue:
            self.mapsinqueue.remove(selectedmap)
            await self.checkmaps_updatebuttons()
            await interaction.response.edit_message(view=self)
            
            return
        
        self.mapsinqueue.append(selectedmap)
        await self.checkmaps_updatebuttons()
        await interaction.response.edit_message(view=self)
        
    @discord.ui.button(label="4️⃣", style=discord.ButtonStyle.primary)
    async def sm4(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not len(self.pages[self.index])>3:
            await interaction.message.reply("Map selection failed")
            await interaction.response.edit_message(view=self)
            return
        
        selectedmap = self.pages[self.index][3]["difficulties"][0]
        
        if selectedmap in self.mapsinqueue:
            self.mapsinqueue.remove(selectedmap)
            await self.checkmaps_updatebuttons()
            await interaction.response.edit_message(view=self)
            
            return
        
        self.mapsinqueue.append(selectedmap)
        await self.checkmaps_updatebuttons()
        await interaction.response.edit_message(view=self)
        
    @discord.ui.button(label="5️⃣", style=discord.ButtonStyle.primary)
    async def sm5(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not len(self.pages[self.index])>4:
            await interaction.message.reply("Map selection failed")
            await interaction.response.edit_message(view=self)
            return
        
        selectedmap = self.pages[self.index][4]["difficulties"][0]
        
        if selectedmap in self.mapsinqueue:
            self.mapsinqueue.remove(selectedmap)
            await self.checkmaps_updatebuttons()
            await interaction.response.edit_message(view=self)
            
            return
        
        self.mapsinqueue.append(selectedmap)
        await self.checkmaps_updatebuttons()
        await interaction.response.edit_message(view=self)
        
    
    @discord.ui.button(label="◀️", style=discord.ButtonStyle.secondary)
    async def previous(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.index > 0:
            self.index -= 1
            await self.checkmaps_updatebuttons()
            await interaction.response.edit_message(embed=self.make_embed(), view=self)

    @discord.ui.button(label="▶️", style=discord.ButtonStyle.secondary)
    async def next(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.index < len(self.pages) - 1:
            self.index += 1
            await self.checkmaps_updatebuttons()
            await interaction.response.edit_message(embed=self.make_embed(), view=self)
            
    @discord.ui.button(label="All", style=discord.ButtonStyle.danger)
    async def all(self, interaction: discord.Interaction, button: discord.ui.Button):
        for i in range(len(self.pages[self.index])):
            selectedmap = self.pages[self.index][i]["difficulties"][0]
            if selectedmap in self.mapsinqueue:
                self.mapsinqueue.remove(selectedmap)
            self.mapsinqueue.append(selectedmap)
            
        await self.checkmaps_updatebuttons()
        
        await interaction.response.edit_message(view=self)
    
    @discord.ui.button(label="Sell", style=discord.ButtonStyle.success)
    async def sell(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.message.reply("Calculating rewards...")
        
        ids_to_remove = {d["id"] for d in self.mapsinqueue}

        removed_difficulties = []
        kept_maps = []

        for m in self.user.maps:
            kept_diffs = []

            for diff in m.difficulties:
                if diff.id in ids_to_remove:
                    removed_difficulties.append(diff)
                else:
                    kept_diffs.append(diff)

            if kept_diffs:
                m.difficulties = kept_diffs
                kept_maps.append(m)

        self.user.maps = kept_maps

        if getattr(self.user, 'equipped_map_id', None) is not None and self.user.get_equipped_map() is None:
            self.user.equipped_map_id = None
        
        rewards = await give_rewards(removed_difficulties)
        
        mapssold = 0
        
        for i in removed_difficulties:
            mapssold += i.duplicates
        
        await interaction.message.reply(f"{format_number(mapssold)} map(s) sold.")
        
        message = (
            f"{format_number(rewards.pp)} PP gained. \n"
            + "\n".join(f"{k}: {format_number(v.duplicates)}" for k, v in rewards.shards.items())
        )
        
        for y in rewards.shards.values():
            self.user.add_item(y, "Shard")
            
        if not rewards.staresc == None:
            self.user.add_item(rewards.staresc, "Special")
            message += f"\nStar Essence: {rewards.staresc.duplicates}"
            
        await self.user.change_pp(rewards.pp)
        
        await interaction.message.reply(message)
        
        for child in self.children:
            if isinstance(child, discord.ui.Button):
                child.disabled = True
                
        await update_user(self.user)
        await interaction.response.edit_message(embed=self.make_embed(), view=self)

    class SortDropdown(discord.ui.Select):
        def __init__(self, paginator):
            self.paginator = paginator
            options = [
                discord.SelectOption(label="Default order", value="default"),
                discord.SelectOption(label="Rarity ↑ (low → high)", value="asc"),
                discord.SelectOption(label="Rarity ↓ (high → low)", value="desc"),
            ]
            super().__init__(placeholder="Sort maps by...", min_values=1, max_values=1, options=options)

        async def callback(self, interaction: discord.Interaction):
            if self.values[0] == "asc":
                self.paginator.maps = sorted(self.paginator.original_maps, key=lambda m: min(d['rarity'] for d in m['difficulties']))
            elif self.values[0] == "desc":
                self.paginator.maps = sorted(self.paginator.original_maps, key=lambda m: max(d['rarity'] for d in m['difficulties']), reverse=True)
            else:
                self.paginator.maps = self.paginator.original_maps[:]  # reset

            self.paginator.update_pages()
            await interaction.response.edit_message(embed=self.paginator.make_embed(), view=self.paginator)


class EquipMapView(discord.ui.View):
    def __init__(self, user, maps, username, author: discord.User, per_page=5):
        super().__init__(timeout=120)
        self.user = user
        self.author_id = author.id
        self.username = username
        self.per_page = per_page
        self.index = 0
        self.selected_map_id = getattr(user, "equipped_map_id", None)
        self.maps = self._flatten_maps(maps)
        self.pages = chunk_list(self.maps, per_page)
        self._update_buttons()

    def _flatten_maps(self, maps):
        result = []

        for ubmo in maps:
            for diff in getattr(ubmo, "difficulties", []):
                result.append({
                    "id": diff.id,
                    "parent_id": diff.parent_id,
                    "title": diff.title,
                    "artist": diff.artist,
                    "difficulty_name": diff.difficulty_name,
                    "star_rating": getattr(diff, "sr", 0),
                    "rarity": getattr(diff, "rarity", 0),
                    "duplicates": getattr(diff, "duplicates", 0)
                })

        # Sort by rarity descending (rarest first)
        result.sort(key=lambda x: x["rarity"], reverse=True)

        return result

    def _get_selected_text(self):
        if self.selected_map_id is None:
            return "None"

        selected = next((item for item in self.maps if item["id"] == self.selected_map_id), None)
        if selected is None:
            return "None"

        return f"{selected['title']} [{selected['difficulty_name']}] • ⭐ {selected['star_rating']}"

    def _update_buttons(self):
        for button in (self.sm1, self.sm2, self.sm3, self.sm4, self.sm5):
            button.style = discord.ButtonStyle.secondary
            button.disabled = True

        current_page = self.pages[self.index] if self.pages else []

        for index, button in enumerate((self.sm1, self.sm2, self.sm3, self.sm4, self.sm5), start=1):
            if index <= len(current_page):
                button.disabled = False
                item = current_page[index - 1]
                button.style = discord.ButtonStyle.success if item["id"] == self.selected_map_id else discord.ButtonStyle.primary

        self.previous.disabled = self.index == 0
        self.next.disabled = self.index >= len(self.pages) - 1

    def make_embed(self):
        embed = discord.Embed(
            title=f"{self.username}'s Equip Map Menu",
            color=discord.Color.blurple()
        )

        if not self.pages or not self.pages[self.index]:
            embed.add_field(
                name="No maps available",
                value="Use o!roll to get maps first.",
                inline=False
            )
            return embed

        lines = []
        for index, item in enumerate(self.pages[self.index], start=1):
            prefix = "✅ " if item["id"] == self.selected_map_id else ""
            lines.append(
                f"{get_star_emoji(item['star_rating'])} {prefix}**{index}.** {item['title']} — {item['artist']} [{item['difficulty_name']}] "
                f"• ⭐ {item['star_rating']} (rarity 1 in {format_number(item['rarity'])}) x{item['duplicates']}"
            )

        embed.description = "\n".join(lines)
        embed.add_field(name="Selected Map", value=self._get_selected_text(), inline=False)
        embed.set_footer(text=f"Page {self.index + 1}/{max(1, len(self.pages))}")
        return embed

    @discord.ui.button(label="1️⃣", style=discord.ButtonStyle.primary)
    async def sm1(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._select_slot(interaction, 0)

    @discord.ui.button(label="2️⃣", style=discord.ButtonStyle.primary)
    async def sm2(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._select_slot(interaction, 1)

    @discord.ui.button(label="3️⃣", style=discord.ButtonStyle.primary)
    async def sm3(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._select_slot(interaction, 2)

    @discord.ui.button(label="4️⃣", style=discord.ButtonStyle.primary)
    async def sm4(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._select_slot(interaction, 3)

    @discord.ui.button(label="5️⃣", style=discord.ButtonStyle.primary)
    async def sm5(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._select_slot(interaction, 4)

    async def _select_slot(self, interaction: discord.Interaction, slot_index: int):
        current_page = self.pages[self.index] if self.pages else []
        if slot_index >= len(current_page):
            await interaction.response.edit_message(embed=self.make_embed(), view=self)
            return

        self.selected_map_id = current_page[slot_index]["id"]
        self._update_buttons()
        await interaction.response.edit_message(embed=self.make_embed(), view=self)

    @discord.ui.button(label="◀️", style=discord.ButtonStyle.secondary)
    async def previous(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.index > 0:
            self.index -= 1
        self._update_buttons()
        await interaction.response.edit_message(embed=self.make_embed(), view=self)

    @discord.ui.button(label="▶️", style=discord.ButtonStyle.secondary)
    async def next(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.index < len(self.pages) - 1:
            self.index += 1
        self._update_buttons()
        await interaction.response.edit_message(embed=self.make_embed(), view=self)

    @discord.ui.button(label="Confirm", style=discord.ButtonStyle.success)
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.selected_map_id is None:
            await interaction.response.send_message(
                "Please select a map to equip first.",
                ephemeral=True
            )
            return

        self.user.equipped_map_id = self.selected_map_id
        await update_user(self.user)

        for child in self.children:
            if isinstance(child, discord.ui.Button):
                child.disabled = True

        self._update_buttons()
        await interaction.response.edit_message(embed=self.make_embed(), view=self)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.author_id:
            await interaction.response.send_message(
                "❌ This menu isn’t yours.",
                ephemeral=True
            )
            return False
        return True


###########################################################

rolling_disabled = False

# Check if bot is online/working properly
@client.command('ping')
async def ping(ctx):
    await login(ctx.author.id)
    
    await ctx.message.reply("hi")

# Calculate the rarity of a given star rating
@client.command("calculaterarity")
async def calcrare(ctx, sr):
    await login(ctx.author.id)
    
    await ctx.message.reply(f"The given star rating of {sr} has a rarity of 1 in {format_number(round(Calculate_Rarity(sr)))}")

# Load the beatmapset of a given ID and outputs it
@client.command("load_beatmapset")
async def loadbms(ctx, bms):
    await login(ctx.author.id)
    
    await ctx.message.reply(await load_beatmapset(bms))

# Load a beatmapset of a given ID and saves it into database (dev only)
@client.command("loadbms_intodatabase")
async def loadbmsintodatabase(ctx, msid):
    if ctx.author.id in DEV_USER_IDS:
        bms = None
        
        json_object = await return_json("json/maps.json")
        
        try:
            bms = json_object[str(msid)]
        except:
            json_object[str(msid)] = await load_beatmapset(msid)
            await save_to_json("json/maps.json", json_object)
            
            bms = json_object[str(msid)]
            
            
            await ctx.message.reply(f"Beatmap {bms['title']} of ID {bms['id']} has been loaded into the database.")
        else:
            bms = json_object[str(msid)]
            
            await ctx.message.reply(f"Beatmap {bms['title']} of ID {bms['id']} has already been loaded.")
            return
        
        return
    
    await ctx.message.reply("You do not have the permission to use this command.")  
    
# Basically the function above without the discord context
async def loadbms(msid):
    bms = None
    
    json_object = await return_json("json/maps.json")
    
    try:
        bms = json_object[str(msid)]
    except:
        try:
            json_object[str(msid)] = await load_beatmapset(msid)
        except:
            return 1
        await save_to_json("json/maps.json", json_object)
    else:
        return 1
    
    return 0

# Load the next page of beatmapsets (dev only)
@client.command("load_next")
async def loadnext_page(ctx):
    if ctx.author.id in DEV_USER_IDS:
        await loadnpage()
        
        await ctx.message.reply("Loaded 50 new beatmaps into the database")
        
        return
    
    await ctx.message.reply("You do not have the permission to use this command.")  
    
# Load the next given amount of pages (dev only)
@client.command("load_multipages")
async def loadmanypages(ctx, num):
    if ctx.author.id in DEV_USER_IDS:
        amount_maps = 0
        
        for i in range(int(num)):
            await loadnpage()
            amount_maps += 50
        
        await ctx.message.reply(f"{amount_maps} maps has been loaded!")
        
        return
    
    await ctx.message.reply("You do not have the permission to use this command.")  

@client.command("setpp")
async def setpp(ctx, pp):
    if ctx.author.id in DEV_USER_IDS:
        userdata = await login(ctx.author.id)
        await userdata.edit_pp(int(pp))
        await update_user(userdata)
        
        await ctx.message.reply(f"PP set to {pp}.")
        
        return
    
    await ctx.message.reply("You do not have the permission to use this command.")

# Sell a map from user's inventory
@client.command("sellmaps")
async def sellmaps(ctx, id = None):
    userid = ctx.author.id
    
    if userid in active_views:
        msg, view = active_views.pop(userid)

        for child in view.children:
            if isinstance(child, discord.ui.Button):
                child.disabled = True

        try:
            await msg.edit(view=view)
        except discord.NotFound:
            pass
        
        await ctx.reply("Your previous menu was disabled.", mention_author=False)
    
    await login(userid)
    
    userdata = None
    username = None
    
    if id == None:
        userdata = await login(userid)
        username = ctx.author.display_name
    else:
        userdata = await login(id)
        user = await client.fetch_user(id)
        username = user.name
        
    
    user_json = await User_To_Dict(userdata)
    
    maps = user_json["maps"]
    
    view = SellingPaginator(userdata, maps, username, per_page=5, author=ctx.author)
    msg = await ctx.send(embed=view.make_embed(), view=view)
    
    active_views[userid] = (msg, view)

# Check PP balance of user
@client.command("balance")
async def balance(ctx):
    userdata = await login(ctx.author.id)
    
    await ctx.message.reply(f"You currently have {format_number(userdata.pp)} PP.")

# Check user's items
@client.command("inventory")
async def inventory(ctx):
    username = ctx.author.display_name
    userdata = await login(ctx.author.id)
    raw_items = userdata.items 

    if not raw_items or not raw_items.get("Shards"):
        await ctx.message.reply("You have no items.")
        return

    view = ItemPaginator(raw_items, username, per_page=6, author=ctx.author)
    await ctx.send(embed=view.make_embed(), view=view)


# Check the amount of maps loaded in the database
@client.command("mapsloaded")
async def loadedamount(ctx):
    await login(ctx.author.id)
    
    json_object = await return_json("json/maps.json")
    
    await ctx.message.reply(f"This bot has loaded {len(json_object)} maps into its database.")

# Reset the internal page count (dev only)
@client.command("reset_page_count")
async def rpc(ctx):
    if ctx.author.id in DEV_USER_IDS:
        await reset_page_count()
        await ctx.message.reply("Done.")
        print("Reseted page back to 0.")
        
        return
    
    await ctx.message.reply("You do not have the permission to use this command.") 
    
# set the internal page count (dev only)
@client.command("spc")
async def spc(ctx, page):
    if ctx.author.id in DEV_USER_IDS:
        await set_page_count(page)
        await ctx.message.reply("Done.")
        print(f"Set page to {page}.")
        
        return
    
    await ctx.message.reply("You do not have the permission to use this command.") 
    
# Change query of bot search
@client.command("change_year")
async def bot_change_year(ctx, year):
    if ctx.author.id in DEV_USER_IDS:
        await change_year(year)
        await set_query_year(await get_year())
        await ctx.message.reply(f"Done, changed the query date to {str(year)}")
        print(f"Done, changed the query date to {str(year)}")
        
        return
        
    await ctx.message.reply("You do not have the permission to use this command.") 
    
# Turn rolling on/off for all users (dev only)
@client.command("toggle_rolling")
async def disable_rolling(ctx):
    global rolling_disabled
    
    if ctx.author.id in DEV_USER_IDS:
        if rolling_disabled:
            await ctx.message.reply("Rolling Enabled.")
        if not rolling_disabled:
            await ctx.message.reply("Rolling disabled.")
            
        rolling_disabled = not rolling_disabled
            
        return
    
    await ctx.message.reply("You do not have the permission to use this command.") 

# Add an extended developer (core dev only)
@client.command("add_extended_dev")
async def add_extended_dev(ctx, target: str):
    if ctx.author.id not in DEV_USER_IDS:
        await ctx.message.reply("You do not have the permission to use this command.")
        return

    user_id = parse_user_id_arg(target)
    if user_id is None:
        await ctx.message.reply("Invalid user. Use a mention like @user or a numeric user ID.")
        return

    user_mention = f"<@{user_id}>"

    if user_id in EXTENDED_DEV_USER_IDS:
        await ctx.message.reply(f"{user_mention} is already an extended developer.")
        return

    EXTENDED_DEV_USER_IDS.add(user_id)
    await save_dev_ids()
    await ctx.message.reply(f"{user_mention} has been added as an extended developer.")

# Remove an extended developer (core dev only)
@client.command("remove_extended_dev")
async def remove_extended_dev(ctx, target: str):
    if ctx.author.id not in DEV_USER_IDS:
        await ctx.message.reply("You do not have the permission to use this command.")
        return

    user_id = parse_user_id_arg(target)
    if user_id is None:
        await ctx.message.reply("Invalid user. Use a mention like @user or a numeric user ID.")
        return

    user_mention = f"<@{user_id}>"

    if user_id in DEV_USER_IDS:
        await ctx.message.reply(f"{user_mention} is a core developer and cannot be removed from extended developer access.")
        return

    if user_id not in EXTENDED_DEV_USER_IDS:
        await ctx.message.reply(f"{user_mention} is not an extended developer.")
        return

    EXTENDED_DEV_USER_IDS.remove(user_id)
    await save_dev_ids()
    await ctx.message.reply(f"{user_mention} has been removed from extended developers.")

# Show current core/extended developer lists (core dev only)
@client.command("show_devs")
async def show_devs(ctx):
    if ctx.author.id not in DEV_USER_IDS:
        await ctx.message.reply("You do not have the permission to use this command.")
        return

    core_sorted = sorted(DEV_USER_IDS)
    extended_sorted = sorted(EXTENDED_DEV_USER_IDS)

    core_lines = [f"<@{user_id}> ({user_id})" for user_id in core_sorted]
    extended_lines = [f"<@{user_id}> ({user_id})" for user_id in extended_sorted]

    embed = discord.Embed(
        title="Developer Access Lists",
        color=discord.Color.red()
    )
    embed.add_field(name="Core Developers", value="\n".join(core_lines) if core_lines else "None", inline=False)
    embed.add_field(name="Extended Developers", value="\n".join(extended_lines) if extended_lines else "None", inline=False)

    await ctx.message.reply(embed=embed, mention_author=False)


@client.command("add_fake_users")
async def add_fake_users(ctx, amount: int = 10):
    if ctx.author.id not in DEV_USER_IDS:
        await ctx.message.reply("You do not have the permission to use this command.")
        return

    if amount < 1:
        await ctx.message.reply("Amount must be at least 1.")
        return

    if amount > 500:
        await ctx.message.reply("Amount is too high. Max is 500 per command.")
        return

    created_users = []
    next_id = get_next_fake_user_id()

    for _ in range(amount):
        fake_user = await build_fake_user(next_id)
        await update_user(fake_user)
        created_users.append(fake_user)
        next_id += 1

    await write_stored_variable()
    await refresh_leaderboard()

    preview_names = ", ".join(user.display_name for user in created_users[:5])
    if len(created_users) > 5:
        preview_names += ", ..."

    await ctx.message.reply(
        f"Created {format_number(len(created_users))} fake user(s). {preview_names}"
    )


@client.command("clear_fake_users")
async def clear_fake_users(ctx):
    if ctx.author.id not in DEV_USER_IDS:
        await ctx.message.reply("You do not have the permission to use this command.")
        return

    removed_count = await clear_fake_users_from_store()
    await write_stored_variable()
    await refresh_leaderboard()

    await ctx.message.reply(f"Removed {format_number(removed_count)} fake user(s).")
        
# Add all difficulties to sorted file for sorting (dev only). Step 1
@client.command("load_diffs_sorted")
async def load_diffs_sorted(ctx):
    if ctx.author.id in DEV_USER_IDS:
        await add_diffs_to_sorted_file()
        
        await ctx.message.reply("Done.")
        
        return  
    
    await ctx.message.reply("You do not have the permission to use this command.")  
    
# Acumulate all ranges in file (dev only). Step 2
"""@client.command("load_cumulative_diffs")
async def load_nmz_diffs(ctx):
    if ctx.author.id in DEV_USER_IDS:
        await add_cumulative_diffs_to_sorted_file()
        
        await ctx.message.reply("Done.")
        
        return
    
    await ctx.message.reply("You do not have the permission to use this command.")
    
# Calculate the ranges of rarities for sorted beatmaps (dev only). Step 3
@client.command("calculate_ranges")
async def calc_ranges(ctx):
    if ctx.author.id in DEV_USER_IDS:
        await add_ranges_to_file()
        
        await ctx.message.reply("Done.")
        
        return  
    
    await ctx.message.reply("You do not have the permission to use this command.") """

# Get a specific beatmap and add it to user's inventory (dev only)
@client.command("getmap")
async def getmap(ctx, id, bmid, amount=1):
    if ctx.author.id in EXTENDED_DEV_USER_IDS:
        userdata = await login(ctx.author.id)
        res = await load_beatmapset(id)
        
        result = None
        
        for i in res["difficulties"]:
            if i["id"] == int(bmid):
                result = i
        
        relative_rarity = result['rarity'] / userdata.luck_mult
        embed = discord.Embed(title=f"You rolled {result['title']}[{result['difficulty_name']}]! (1 in {format_number(result['rarity'])})", description=f"Star Rating: {result['star_rating']} ⭐\n*Relative Rarity: 1 in {format_number(relative_rarity)}*", color=await get_star_color(result['star_rating']), timestamp=datetime.datetime.now())
        embed.set_image(url=f"https://assets.ppy.sh/beatmaps/{res['id']}/covers/cover.jpg")
        embed.set_thumbnail(url=f"https://b.ppy.sh/thumb/{res['id']}l.jpg")
        
        map_result = await Dict_to_BeatmapDiff(result)
        ubmd = User_BMD_Object(map_result.sr, map_result.parent_id, map_result.id, map_result.title, map_result.artist, map_result.difficulty_name, amount)
        
        parent = await find_ubmo(map_result.parent_id)
        
        embed.add_field(name="Artist", value=parent.artist)
        embed.add_field(name="Mapper", value=parent.mapper)
        embed.add_field(name="BeatmapsetID", value=parent.id)
        embed.add_field(name="BeatmapID", value=result["id"])
        embed.add_field(name="Status", value=await get_status(parent.status))
        embed.add_field(name="Duplicates", value=amount)
        
        await userdata.add_map(ubmd)
        
        await update_user(userdata)
        
        await ctx.message.reply(embed=embed)
        
        return
    
    await ctx.message.reply("You do not have the permission to use this command.") 

# Set the luck multiplier of the user (dev only)
@client.command("setluck")
async def setluck(ctx, luck):
    if ctx.author.id not in EXTENDED_DEV_USER_IDS:
        await ctx.message.reply("You do not have the permission to use this command.")
        return
    
    if int(luck) > 999_999_999_999:
        await ctx.message.reply("Luck multiplier demanded is too high, max is 999,999,999,999 (999 billion)")
        
        return
    
    userdata = await login(ctx.author.id)
    userdata.dev_luck_base = int(luck)
    userdata.recalculate_luck()
    
    await update_user(userdata)
    await ctx.message.reply(f"Set base luck to {format_number(int(luck))}x. Gear multipliers now apply on top of this value.")
    
# Roll a beatmap
@client.command("roll")
async def roll_random(ctx):
    if not rolling_disabled:
        userdata = await login(ctx.author.id)
        can_roll, retry_after, reason = await userdata.can_roll()

        if not can_roll:
            if reason == "cooldown":
                await ctx.message.reply(
                    f"You are on roll cooldown. Try again in {retry_after:.2f}s."
                )
                return

            if reason == "roll_limit":
                await ctx.message.reply(
                    (
                        f"You reached your rolling cap ({userdata.roll_max} rolls per "
                        f"{userdata.roll_window_seconds} seconds). "
                        f"Try again in {retry_after:.2f}s."
                    )
                )
                return

        luck_mult = userdata.luck_mult
        print(luck_mult)
        
        result = await get_random_map(luck_mult)
        
        relative_rarity = result['rarity'] / luck_mult
        embed = discord.Embed(title=f"You rolled {result['title']}[{result['difficulty_name']}]! (1 in {format_number(result['rarity'])})", description=f"Star Rating: {result['star_rating']} ⭐\n*Relative Rarity: 1 in {format_number(relative_rarity)}*", color=await get_star_color(result['star_rating']), timestamp=datetime.datetime.now())
        embed.set_image(url=f"https://assets.ppy.sh/beatmaps/{result['id']}/covers/cover.jpg")
        embed.set_thumbnail(url=f"https://b.ppy.sh/thumb/{result['id']}l.jpg")
        
        map_result = await Dict_to_BeatmapDiff(result)
        ubmd = User_BMD_Object(map_result.sr, map_result.parent_id, map_result.id, map_result.title, map_result.artist, map_result.difficulty_name)
        
        parent = await find_ubmo(map_result.parent_id)
        
        embed.add_field(name="Artist", value=parent.artist)
        embed.add_field(name="Mapper", value=parent.mapper)
        embed.add_field(name="BeatmapsetID", value=parent.id)
        embed.add_field(name="BeatmapID", value=result["id"])
        embed.add_field(name="Status", value=await get_status(parent.status))
        
        old_level = userdata.level
        level_up = await userdata.add_xp(result["rarity"])
        await userdata.register_roll()
        
        await userdata.add_map(ubmd)

        is_new_rarest = result["rarity"] > getattr(userdata, "rarest_rolled_rarity", 0)
        if is_new_rarest:
            userdata.rarest_rolled_rarity = result["rarity"]

        await update_user(userdata)
        
        await ctx.message.reply(embed=embed)
        
        if is_new_rarest:
            await ctx.message.reply(
                f"You have rolled a new rarest map with a rarity of 1 in {format_number(result['rarity'])}!"
            )
        
        xp_needed = xp_to_next_level(userdata.level)
        bar = await xp_bar(userdata.xp, xp_needed)
        
        if level_up:
            await ctx.message.reply((
                f"You leveled up! Level {format_number(old_level)} -> {format_number(userdata.level)}\n"
                f"Level {format_number(userdata.level)} - {bar} - {format_number(userdata.level+1)}\n"
                f"{format_number(userdata.xp)}/{format_number(xp_needed)} XP"
            ))
        
        return
        
    await ctx.message.reply("Rolling had been temporarily disabled by the developer.")

# Check user's level, XP and XP progress bar
@client.command("level")
async def level(ctx):
    userdata = await login(ctx.author.id)
    
    xp_needed = xp_to_next_level(userdata.level)
    bar = await xp_bar(userdata.xp, xp_needed)
        
    await ctx.message.reply((
        f"Level {format_number(userdata.level)} - {bar} - {format_number(userdata.level+1)}\n"
        f"{format_number(userdata.xp)}/{format_number(xp_needed)} XP"
    ))


@client.command("profile")
async def profile(ctx, target: discord.User = None):
    target = target or ctx.author
    userdata = await login(target.id)
    userdata.recalculate_luck()

    xp_needed = xp_to_next_level(userdata.level)
    bar = await xp_bar(userdata.xp, xp_needed)
    inventory_rarity = calculate_inventory_rarity_total(userdata)

    diff_count = sum(len(ubmo.difficulties) for ubmo in getattr(userdata, "maps", []))
    total_copies = sum(
        int(getattr(diff, "duplicates", 0))
        for ubmo in getattr(userdata, "maps", [])
        for diff in getattr(ubmo, "difficulties", [])
    )

    rank = await get_leaderboard_rank_for_user(userdata)
    rank_text = f"#{rank}" if rank is not None else "Not ranked"

    ranks = await get_all_leaderboard_ranks_for_user(userdata)
    
    if ctx.message.author.avatar == None:
        url = "https://osu.ppy.sh/images/layout/avatar-guest.png"
    else:
        url = ctx.message.author.avatar.url

    embed = discord.Embed(
        title=f"{target.display_name if getattr(target, 'display_name', None) else target.name}'s Profile",
        color=await get_star_color(0),
        timestamp=datetime.datetime.now()
    )
    
    embed.set_thumbnail(url=url)

    embed.add_field(name="Level Rank", value=f"#{ranks.get('level', 'Not ranked')}", inline=True)
    embed.add_field(name="PP Rank", value=f"#{ranks.get('pp', 'Not ranked')}", inline=True)
    embed.add_field(name="Rarity Rank", value=f"#{ranks.get('rarity', 'Not ranked')}", inline=True)
    embed.add_field(name="Level", value=f"{format_number(userdata.level)}", inline=True)
    embed.add_field(name="PP", value=f"{format_number(userdata.pp)}", inline=True)
    embed.add_field(name="Luck Multiplier", value=f"{format_number(userdata.luck_mult)}x", inline=True)
    embed.add_field(name="XP", value=f"{format_number(userdata.xp)}/{format_number(xp_needed)}", inline=True)
    embed.add_field(name="XP Progress", value=bar, inline=False)
    embed.add_field(name="Inventory Rarity", value=f"1 in {format_number(inventory_rarity)}", inline=True)
    embed.add_field(name="Maps", value=f"{format_number(diff_count)} difficulty(s) / {format_number(total_copies)} total copies", inline=True)
    embed.add_field(name="Daily Streak", value=f"{format_number(userdata.daily_streak)} day(s)", inline=True)

    embed.add_field(
        name="Rarest Rolled Map Rarity",
        value=(f"1 in {format_number(userdata.rarest_rolled_rarity)}" if userdata.rarest_rolled_rarity else "None yet"),
        inline=True
    )
    embed.add_field(name="Equipped Items", value=format_equipped_items(userdata), inline=False)

    equipped_map = userdata.get_equipped_map()
    if equipped_map is not None:
        embed.set_image(url=f"https://assets.ppy.sh/beatmaps/{equipped_map.parent_id}/covers/cover.jpg")
        embed.add_field(
            name="Equipped Map",
            value=(
                f"{equipped_map.title} [{equipped_map.difficulty_name}] • ⭐ {equipped_map.sr} "
                f"(rarity 1 in {format_number(getattr(equipped_map, 'rarity', 0))})"
            ),
            inline=False
        )
        
        embed.color = await get_star_color(equipped_map.sr)
    else:
        embed.add_field(name="Equipped Map", value="None", inline=False)

    await ctx.message.reply(embed=embed, mention_author=False)


@client.command("equip_map")
async def equip_map(ctx):
    userid = ctx.author.id

    if userid in active_views:
        msg, view = active_views.pop(userid)

        for child in view.children:
            if isinstance(child, discord.ui.Button):
                child.disabled = True

        try:
            await msg.edit(view=view)
        except discord.NotFound:
            pass

        await ctx.reply("Your previous menu was disabled.", mention_author=False)

    await login(userid)
    userdata = await login(userid)

    if not getattr(userdata, 'maps', []):
        await ctx.message.reply("You have no maps to equip. Roll some maps first.")
        return

    view = EquipMapView(userdata, userdata.maps, ctx.author.display_name, ctx.author)
    msg = await ctx.send(embed=view.make_embed(), view=view)
    active_views[userid] = (msg, view)


@client.command("leaderboard")
async def leaderboard(ctx):
    await login(ctx.author.id)

    if leaderboard_next_refresh_at is None:
        await refresh_leaderboard()

    embed = build_leaderboard_embed("level")
    if embed is None:
        await ctx.message.reply("No players are on the leaderboard yet.")
        return

    leaderboard_view = LeaderboardView(ctx.author, initial_mode="level")
    await ctx.message.reply(embed=embed, view=leaderboard_view)

# Clear userdata of a specific user (dev only, risky)
@client.command("clear_userdata")
async def clear_userdata_cmd(ctx, id):
    if ctx.author.id in DEV_USER_IDS:    
        await clear_userdata(id)
        
        await ctx.message.reply("Done.")
        
        return
    
    await ctx.message.reply("You do not have the permission to use this command.")
    
# Clear ALL userdata in the database (dev only, risky)
@client.command("clear_all_userdata")
async def clear_all_userdata_cmd(ctx):
    if ctx.author.id in DEV_USER_IDS:
        json_object = await return_json("json/users.json")
        
        await ctx.message.reply(f"This is a big decision. Are you sure about this? You have 20 seconds to turn off the bot before {format_number(len(json_object))} users gets cleared")
        print(f"This is a big decision. Are you sure about this? You have 20 seconds to turn off the bot before {format_number(len(json_object))} users gets cleared")
        
        await asyncio.sleep(20)
        
        await clear_userdata_all()
        
        await ctx.message.reply("All users have been cleared.")
        
        return
    
    await ctx.message.reply("You do not have the permission to use this command.")

# Clear ALL maps in the database (dev only, risky)
@client.command("clear_all_maps")
async def clear_maps_cmd(ctx):
    if ctx.author.id in DEV_USER_IDS:
        json_object = await return_json("json/maps.json")
        
        await ctx.message.reply(f"This is a big decision. Are you sure about this? You have 20 seconds to turn off the bot before {format_number(len(json_object))} maps gets cleared")
        print(f"This is a big decision. Are you sure about this? You have 20 seconds to turn off the bot before {format_number(len(json_object))} maps gets cleared")
        
        await asyncio.sleep(20)
        
        async with aiofiles.open("json/maps.json", "w") as file:
            await file.write("{}")
        
        async with aiofiles.open("json/bmpage.count", "w") as file:
            await file.write("0")
        
        await ctx.message.reply("All maps have been cleared.")
        
        return
    
    await ctx.message.reply("You do not have the permission to use this command.")

# Check user's current luck multiplier (soon this will be displayed in a profile page instead of a command)
@client.command("luckmult")
async def luckmult(ctx):
    userdata = await login(ctx.author.id)
    
    await ctx.message.reply(f"Your current luck multiplier is {userdata.luck_mult}")

# Clear ALL sorted and ranges maps in the database (dev only, risky)
@client.command("clear_sorted_diffs")
async def clear_sorted_diffs_cmd(ctx):
    if ctx.author.id in DEV_USER_IDS:
        json_object = await return_json("json/sorteddiffs.json")
        
        await ctx.message.reply(f"This is a big decision. Are you sure about this? You have 20 seconds to turn off the bot before {format_number(len(json_object))} difficulties gets cleared")
        print(f"This is a big decision. Are you sure about this? You have 20 seconds to turn off the bot before {format_number(len(json_object))} difficulties gets cleared")
        
        await asyncio.sleep(20)
        
        async with aiofiles.open("json/sorteddiffs.json", "w") as file:
            await file.write("[]")
        
        async with aiofiles.open("json/ranges.json", "w") as file:
            await file.write("[]")
        
        await ctx.message.reply("All difficulties have been cleared.")
        
        return
    
    await ctx.message.reply("You do not have the permission to use this command.")
    
# Update optimization variables in case range or maps file change (dev only)
@client.command("uov")
async def uov(ctx):
    if ctx.author.id in DEV_USER_IDS:
        await update_optimization_variables()
        await load_gmaps_variable()
        await write_stored_variable()
        await ctx.message.reply("Done.")
        
        return
        
    await ctx.message.reply("You do not have the permission to use this command.")
    
# Check available commands
@client.command("help")
async def help(ctx):
    await login(ctx.author.id)

    embed = discord.Embed(
        title="osu! Rarities — Command List",
        description="Prefix: `o!`  •  Arguments in `<angle brackets>` are required, `[square brackets]` are optional.",
        color=discord.Color.blurple()
    )

    embed.add_field(
        name="🎲 Rolling & Maps",
        value=(
            "`o!roll` — Roll a random beatmap based on your luck multiplier.\n"
            "`o!maps [user_id]` — Browse your beatmap collection (paginated).\n"
            "`o!sellmaps [user_id]` — Sell maps from your collection for PP.\n"
            "`o!lookup <beatmap_id>` — Look up a beatmap and see which difficulties you own.\n"
            "`o!mapsloaded` — Check how many beatmaps are in the database."
        ),
        inline=False
    )

    embed.add_field(
        name="💰 Economy & Progression",
        value=(
            "`o!balance` — Check your current PP balance.\n"
            "`o!level` — View your level, XP, and progress toward the next level.\n"
            "`o!profile [@user]` — View your profile or another player's profile.\n"
            "`o!equip_map` — Equip one of your maps as your favourite.\n"
            "`o!leaderboard` — View the ranked player leaderboard and next refresh time.\n"
            "`o!luckmult` — Check your current luck multiplier."
        ),
        inline=False
    )

    embed.add_field(
        name="🎒 Items & Equipment",
        value=(
            "`o!inventory` — View items and shards in your inventory.\n"
            "`o!item <item_id>` — View detailed info about a specific item.\n"
            "`o!shop` — Browse the shop and buy items.\n"
            "`o!equipment` — View and manage your equipped gear.\n"
            "`o!craft` — Open the crafting menu to craft new items."
        ),
        inline=False
    )

    embed.add_field(
        name="🔧 Utility",
        value=(
            "`o!calculaterarity <star_rating>` — Calculate the rarity of a given star rating.\n"
            "`o!ping` — Check if the bot is online.\n"
            "`o!help` — Show this message."
        ),
        inline=False
    )

    embed.set_footer(text="Developer-only commands are not listed here.")

    await ctx.send(embed=embed)

# Shop command
# WIP, pending implementation of shop system and items
@client.command("shop")
async def shop(ctx):
    userdata = await login(ctx.author.id)
    
    if ctx.author.id in active_views:
        msg, view = active_views.pop(ctx.author.id)

        for child in view.children:
            if isinstance(child, discord.ui.Button):
                child.disabled = True

        try:
            await msg.edit(view=view)
        except discord.NotFound:
            pass
        
        await ctx.reply("Your previous menu was disabled.", mention_author=False)
    
    shopView = ShopView(
        user=userdata,
        author=ctx.author
    )
    msg = await ctx.send(embed=await shopView.make_embed(), view=shopView)
    
    active_views[ctx.author.id] = (msg, shopView)
    
@client.command("equipment")
async def equipment(ctx):
    userdata = await login(ctx.author.id)
    
    if ctx.author.id in active_views:
        msg, view = active_views.pop(ctx.author.id)

        for child in view.children:
            if isinstance(child, discord.ui.Button):
                child.disabled = True

        try:
            await msg.edit(view=view)
        except discord.NotFound:
            pass
        
        await ctx.reply("Your previous menu was disabled.", mention_author=False)
    
    equipmentView = EquipmentView(
        user=userdata,
        author=ctx.author
    )
    msg = await ctx.send(embed=await equipmentView.make_embed(), view=equipmentView)
    
    active_views[ctx.author.id] = (msg, equipmentView)

# Crafting command
# More items soon
@client.command("craft")
async def craft(ctx):
    userdata = await login(ctx.author.id)
    
    if ctx.author.id in active_views:
        msg, view = active_views.pop(ctx.author.id)

        for child in view.children:
            if isinstance(child, discord.ui.Button):
                child.disabled = True

        try:
            await msg.edit(view=view)
        except discord.NotFound:
            pass
        
        await ctx.reply("Your previous menu was disabled.", mention_author=False)
    
    view = CraftingView(
        user=userdata,
        author=ctx.author
    )

    msg = await ctx.send(embed=view.make_embed(), view=view)
    
    active_views[ctx.author.id] = (msg, view)

# Lookup command to check beatmap info and if user has it in inventory
@client.command("lookup")
async def lookup(ctx, beatmapid):
    userdata = await login(ctx.author.id)
    
    map = await find_beatmap(beatmapid)
    
    embed = discord.Embed(title=f"{map.title} - ID: {beatmapid}", color=discord.Color.blurple())
    embed.add_field(name="Artist", value=map.artist)
    embed.add_field(name="Mapper", value=map.mapper)
    embed.add_field(name="Status", value=await get_status(map.status))
    
    owned = []
    owned_var1 = False
    
    ids = [beatmap.id for beatmap in userdata.maps]
    
    if int(beatmapid) in ids:       
        for i in map.difficulties:
            owned_var2 = False
            
            for y in userdata.maps[ids.index(int(beatmapid))].difficulties:
                if i.id == y.id:
                    owned.append(y.duplicates)
                    owned_var2 = True
            
            if owned_var2:
                continue
                    
            owned.append(0)    
        
        owned_var1 = True
        
    if not owned_var1:
        for i in map.difficulties:
            owned.append(0)
    
    difficulties = "\n".join(
        f"{get_star_emoji(d.sr)} "
        f"- {d.difficulty_name} ⭐ {d.sr} (rarity 1 in {format_number(d.rarity)}) -- ID: {d.id} -- Owned: {owned[map.difficulties.index(d)]}"
        for d in map.difficulties
    )

    embed.add_field(
        name=f"Difficulties",
        value=difficulties,
        inline=False
    )
    
    embed.set_image(url=f"https://assets.ppy.sh/beatmaps/{map.id}/covers/cover.jpg")
    embed.set_thumbnail(url=f"https://b.ppy.sh/thumb/{map.id}l.jpg")
    
    await ctx.message.reply(embed=embed)
    
@client.command("item")
async def item(ctx, itemid):
    userdata = await login(ctx.author.id)
    
    try:
        item = ITEMS_BY_ID[itemid]
    except:
        item = None
    
    if item == None:
        await ctx.message.reply("Item not found. You can find item IDs in the shop/crafting menu/inventory.")
        return
    
    embed = discord.Embed(title=f"{item.name} - ID: {itemid}", color=discord.Color.blurple())
    embed.add_field(name="Type", value=item.type)
    
    if item.type == "Shard":
        embed.add_field(name="Shard Rarity", value=item.shardrarity)
    else:
        embed.add_field(name="Rarity", value=item.rarity)
        
    embed.add_field(name="Function", value=item.function)
    embed.add_field(name="Value", value=item.value)
    
    if item.type in ("Gear", "GearPeripheral"):
        embed.add_field(name="Luck Increase", value=item.luckincrease)
        embed.add_field(name="Luck Multiplier", value=item.luckmultiplier)
        
    if item.type == "GearPeripheral":
        embed.add_field(name="Equipped", value=f"{'Yes' if item.equipped else 'No'}")
    
    owned = userdata.count_item_by_id(itemid)
    
    embed.add_field(name="Owned", value=owned)
    
    embed.add_field(name="Description", value=item.description, inline=False)
    
    await ctx.message.reply(embed=embed)

# I forgot what this does
# I think it was for testing adding and removing items from inventory, pending removal or update
@client.command("test1")
async def t1(ctx, id, amount):
    userdata = await login(ctx.author.id)
    
    await userdata.remove_item_by_id(id, int(amount))
    
    await update_user(userdata)
    
    await ctx.message.reply("Done.")

# Why do i keep adding random commands
# Removal soon
@client.command("test2")
async def t1(ctx, id):
    userdata = await login(ctx.author.id)
    
    await ctx.message.reply(await userdata.count_item_by_id(id))
    
@client.command("daily")
async def daily(ctx):
    userdata = await login(ctx.author.id)
    
    can_claim, retry_after = await userdata.can_claim_daily()
    
    def format_duration(seconds):
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        secs = seconds % 60

        return f"{int(hours)} hours, {int(minutes)} minutes, {int(secs)} seconds"
    
    if can_claim:
        reward, streak_reset, streak_reset_days = await give_daily_rewards(userdata)
        await update_user(userdata)
        await ctx.message.reply(f"You claimed your daily reward: {reward} PP | Streak: {userdata.daily_streak} days")
        
        if streak_reset:
            await ctx.message.reply(f"You haven't claimed your daily reward in {streak_reset_days} days. Your daily streak has been lowered by {streak_reset} day(s). Your current streak is now {userdata.daily_streak} days.")
        
    else:
        await ctx.message.reply(f"You cannot claim your daily reward yet. You can claim your daily reward in {format_duration(retry_after)}.")

# Inventory command to check user's maps
@client.command("maps")
async def maps(ctx, id = None):
    userid = ctx.author.id
    
    if userid in active_views:
        msg, view = active_views.pop(userid)

        for child in view.children:
            if isinstance(child, discord.ui.Button):
                child.disabled = True

        try:
            await msg.edit(view=view)
        except discord.NotFound:
            pass
        
        await ctx.reply("Your previous menu was disabled.", mention_author=False)
    
    await login(userid)
    
    userdata = None
    username = None
    
    if id == None:
        userdata = await login(userid)
        username = ctx.author.display_name
    else:
        userdata = await login(id)
        user = await client.fetch_user(id)
        username = user.name
        
    
    user_json = await User_To_Dict(userdata)
    
    maps = user_json["maps"]
    
    view = MapPaginator(maps, username, per_page=10, author=ctx.author)
    msg = await ctx.send(embed=view.make_embed(), view=view)
    
    active_views[userid] = (msg, view)
    
# Recalculate rarities of maps in the database in case of formula change (dev only)
@client.command("recalculate_rarities")
async def recalculate_rarities(ctx):
    if ctx.author.id in DEV_USER_IDS:
        json_object = await return_json("json/maps.json")
        
        for i in json_object:
            for y in json_object[i]["difficulties"]:
                y["rarity"] = Calculate_Rarity(y["star_rating"])
                
        await save_to_json("json/maps.json", json_object)
                
        await ctx.message.reply("Done.")
        
        return
        
    await ctx.message.reply("You do not have the permission to use this command.")

# Developer command to give a specific item to themselves
@client.command("give_dev")
async def give_dev(ctx, itemid, amount):
    if ctx.author.id in EXTENDED_DEV_USER_IDS:
        userdata = await login(ctx.author.id)
        
        # If user inputs an array of items, add all items in the array to inventory. Example: o!give_dev [item1,item2,item3] 1
        if itemid.startswith("[") and itemid.endswith("]"):
            itemids = itemid[1:-1].split(",")
            for id in itemids:
                item = copy.deepcopy(ITEMS_BY_ID.get(id.strip()))
                
                if not item:
                    await ctx.message.reply(f"Item with ID {id.strip()} not found. Check item IDs in the shop/crafting menu/inventory.")
                    continue
                
                item.duplicates = int(amount)
                
                userdata.add_item(item, item.type)
            
            await update_user(userdata)
            
            await ctx.message.reply(f"Gave {format_number(int(amount))}x of each item: {', '.join(id.strip() for id in itemids)}.")
            
            return
        
        item = copy.deepcopy(ITEMS_BY_ID.get(itemid))
        
        if not item:
            await ctx.message.reply("Item not found. Check item IDs in the shop/crafting menu/inventory.")
            return
        
        item.duplicates = int(amount)
        
        userdata.add_item(item, item.type)
        
        await update_user(userdata)
        
        await ctx.message.reply(f"Gave {format_number(int(amount))}x {item.name}.")
        
        return
    
    await ctx.message.reply("You do not have the permission to use this command.")

# Test the embed function (temporary, to be removed soon)
@client.command("test_embed")
async def test_embed(ctx):
    await login(ctx.author.id)
    
    embed = discord.Embed(title="You rolled Parallel Universe Shifter[Quantum Field Disruption]! (1 in 126,900)", description="Star Rating: 8.54 ⭐", color=0x0362fc)
    embed.add_field(name="Field1", value="test embed", inline=False)
    embed.add_field(name="Field2", value="Open the gates to the parallel universes.", inline=False)
    embed.add_field(name="lmao", value="test embed", inline=False)
    embed.set_image(url="https://assets.ppy.sh/beatmaps/2062263/covers/cover.jpg")
    embed.set_footer(text="Time: hh:mm dd/mm/yyyy")
    embed.set_thumbnail(url="https://b.ppy.sh/thumb/2062263l.jpg")
    
    await ctx.message.reply(embed=embed)

# Simulation command to test performance of get_random_map and give_rewards functions with concurrent users (dev only)
@client.command("simulate")
async def simulate(ctx, users: int = 50, actions: int = 10, mode: str = "roll"):
    """Dev-only: simulate `users` concurrent users each performing `actions` get_random_map calls.
    mode: 'roll' (default) only calls `get_random_map`; 'sell' will simulate rolling then selling each user's collected maps.
    """
    # only allow developers
    if ctx.author.id not in DEV_USER_IDS:
        await ctx.message.reply("You do not have the permission to use this command.")
        return

    await ctx.message.reply(f"Starting simulation: {users} users × {actions} actions... mode={mode}")

    import time

    async def simulate_user(uid: int):
        # if mode is sell, collect rolled difficulties per user
        collected = {}
        for _ in range(actions):
            # call get_random_map (async, uses luck tables)
            result = await probabilitycalc.get_random_map(1.0)
            if mode == "sell":
                # result is a dict with "star_rating"
                sr = result.get("star_rating") or result.get("star_rating")
                # aggregate duplicates by star rating
                collected[sr] = collected.get(sr, 0) + 1
        return collected

    start = time.perf_counter()

    tasks = [asyncio.create_task(simulate_user(i)) for i in range(users)]

    results = await asyncio.gather(*tasks)

    elapsed = time.perf_counter() - start

    if mode != "sell":
        await ctx.message.reply(f"Simulation completed in {elapsed:.3f}s ({users * actions} total calls)")
        return

    # mode == 'sell' -> process selling for each simulated user
    class SimDiff:
        def __init__(self, sr, duplicates):
            self.sr = sr
            self.duplicates = duplicates

    sell_start = time.perf_counter()
    total_shards = 0
    total_pp = 0

    for collected in results:
        # build list of SimDiff objects
        diffs = [SimDiff(float(sr), cnt) for sr, cnt in collected.items()]

        rewards = await give_rewards(diffs)
        # accumulate totals
        total_pp += rewards.pp
        for sh in rewards.shards.values():
            total_shards += sh.duplicates

    sell_elapsed = time.perf_counter() - sell_start

    await ctx.message.reply((
        f"Simulation completed. roll_time={elapsed:.3f}s sell_time={sell_elapsed:.3f}s "
        f"(total calls={users * actions}, total_pp={format_number(total_pp)}, total_shards={format_number(total_shards)})"
    ))

# Show dev-only commands    
@client.command("devhelp")
async def devhelp(ctx):
    if ctx.author.id in DEV_USER_IDS:
        embed = discord.Embed(
            title="osu! Rarities — Developer Command List",
            description="Prefix: `o!`  •  Arguments in `<angle brackets>` are required, `[square brackets]` are optional.",
            color=discord.Color.red()
        )

        embed.add_field(
            name="Map & User Management",
            value=(
                "`o!loadmaps` — Load beatmaps into the database from the osu! API (50 maps per call).\n"
                "`o!recalculate_rarities` — Recalculate rarities of all maps in the database (use if formula changes).\n"
                "`o!clear_userdata <user_id>` — Clear inventory and progress of a specific user.\n"
                "`o!clear_all_userdata` — Clear inventory and progress of all users (use with caution!).\n"
                "`o!clear_all_maps` — Clear all beatmaps from the database (use with caution!).\n"
                "`o!clear_sorted_diffs` — Clear sorted difficulties and ranges data (use with caution!).\n"
                "`o!uov` — Update optimization variables after changing maps or ranges data."
            ),
            inline=False
        )

        embed.add_field(
            name="Bot Configuration",
            value=(
                "`o!setpp <amount>` — Set your PP balance to a specific amount.\n"
                "`o!setluck <multiplier>` — Set your base luck multiplier (gear multipliers apply on top of this).\n"
                "`o!add_extended_dev <@user>` — Grant extended developer permissions to a user (core devs only).\n"
                "`o!remove_extended_dev <@user>` — Remove extended developer permissions from a user (core devs only).\n"
                "`o!show_devs` — Show current core and extended developer lists.\n"
                "`o!add_fake_users [amount]` — Add fake users with random stats and maps for leaderboard testing.\n"
                "`o!clear_fake_users` — Remove all fake users from the database.\n"
                "`o!give_dev <item_id or [item_id1,item_id2,...]> <amount>` — Give yourself a specific item or multiple items for testing (check item IDs in shop/crafting menu/inventory).\n"
                "`o!change_year <year>` — Change the query year for beatmap loading (e.g. to load only maps ranked before a certain year).\n"
                "`o!toggle_rolling` — Enable or disable rolling for all users."
            ),
            inline=False
        )

        embed.add_field(
            name="Testing & Simulation",
            value=(
                "`o!getmap <beatmapset_id> <beatmap_id> [amount]` — Add a specific beatmap difficulty to your inventory for testing purposes.\n"
                "`o!test_embed` — Send a test embed to preview formatting.\n"
                "`o!simulate [users] [actions] [mode]` — Simulate concurrent users performing actions to test performance (mode: 'roll' or 'sell')."
            ),
            inline=False
        )
    
        await ctx.send(embed=embed)
    else:
        await ctx.message.reply("You do not have the permission to use this command.")

client.run(os.getenv("tester_token"))
