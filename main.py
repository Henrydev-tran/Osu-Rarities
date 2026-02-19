import os

import asyncio

import discord
from discord.ext import commands

from user_handling import *
from userutils import give_rewards, SHARD_LIST, SHARD_RANK

from dotenv import load_dotenv

load_dotenv()

from raritycalculation import Calculate_Rarity, get_star_color
from jsontools import Beatmap_To_Json
from loadmaps import *
from probabilitycalc import *
from math import ceil
from userutils import xp_to_next_level

from item import SHARDS_BY_ID, SHARD_CORE_RECIPES, ALL_RECIPES

import datetime

client = commands.Bot(command_prefix='o!', intents=discord.Intents(messages=True, guilds=True, message_content=True))
client.remove_command("help")

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

def format_number(n: int) -> str:
    return format(n, ",")

# Return an xp bar using emojis
async def xp_bar(current_xp, xp_needed, length=10):
    progress = current_xp / xp_needed
    filled = int(progress * length)

    return "🟩" * filled + "⬛" * (length - filled)

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
                f"- {d['difficulty_name']} ⭐ {d['star_rating']} (rarity 1 in {format_number(d['rarity'])}) -- ID: {d['id']} -- # {d["duplicates"]}"
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
                "❌ This crafting menu isn’t yours.",
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

        view.refresh_components()

        await interaction.response.edit_message(
            embed=view.make_embed(),
            view=view
        )
  
class CraftCategorySelect(discord.ui.Select):
    def __init__(self, current_category: str):
        options = []

        for label, value in [
            ("Shard Cores", "ShardCores")
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
            
class CraftingView(discord.ui.View):
    def __init__(self, user, author: discord.User):
        super().__init__(timeout=120)
        self.user = user
        self.author_id = author.id
        self.category = "ShardCores"
        self.craft_amount = 1
        self.selected_recipe_id = None

        self.refresh_components()  
        
    def set_category(self, category: str):
        self.category = category
        self.selected_recipe_id = None
        self.craft_amount = 1
        self.refresh_components()
        
    def refresh_components(self):
        self.clear_items()

        # category dropdown
        self.add_item(CraftCategorySelect(self.category))

        # recipe dropdown (depends on category)
        recipes = ALL_RECIPES.get(self.category, [])
        if recipes:
            self.add_item(
                CraftRecipeSelect(
                    recipes,
                    self.selected_recipe_id
                )
            )

        # buttons
        self.add_item(self.decrease)
        self.add_item(self.increase)
        self.add_item(self.craft)
        self.add_item(self.craft_max)
            
    def get_recipes_for_category(self):
        return [
            r for r in ALL_RECIPES[self.category]
            if r.can_craft(self.user)
        ]
        
    def get_selected_recipe(self):
        if self.selected_recipe_id is None:
            return None

        for recipe in ALL_RECIPES[self.category]:
            if recipe.id == self.selected_recipe_id:
                return recipe

        return None
        
    def make_embed(self):
        recipe = self.get_selected_recipe()

        embed = discord.Embed(
            title="🛠 Shard Core Crafting",
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

        embed.add_field(
            name="Requirements",
            value="\n".join(
                f"🔹 {amt}× {SHARDS_BY_ID[item_id].name}"
                for item_id, amt in recipe.requirements.items()
            ),
            inline=False
        )

        embed.add_field(
            name="Result",
            value=f"✨ {recipe.result.name}",
            inline=False
        )
        
        embed.add_field(
            name="Amount",
            value=f"×{self.craft_amount}",
            inline=True
        )

        embed.add_field(
            name="You Can Craft",
            value=f"{recipe.max_craftable(self.user)} max",
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
        if self.craft_amount > 1:
            self.craft_amount -= 1

        await interaction.response.edit_message(
            embed=self.make_embed(),
            view=self
        )
        
    @discord.ui.button(label="➕", style=discord.ButtonStyle.secondary)
    async def increase(self, interaction, button):
        recipe = self.get_selected_recipe()
        if not recipe:
            return

        max_amount = recipe.max_craftable(self.user)
        if self.craft_amount < max_amount:
            self.craft_amount += 1

        await interaction.response.edit_message(
            embed=self.make_embed(),
            view=self
        )
        
    @discord.ui.button(label="Craft", style=discord.ButtonStyle.success)
    async def craft(self, interaction, button):
        recipe = self.get_selected_recipe()
        if not recipe:
            return

        if self.craft_amount > recipe.max_craftable(self.user):
            return await interaction.response.send_message(
                "Not enough materials.",
                ephemeral=True
            )

        recipe.consume(self.user, self.craft_amount)
        recipe.give_result(self.user, self.craft_amount)
        
        await interaction.message.reply(
                f"Crafted {self.craft_amount}x {recipe.name}"
            )

        self.craft_amount = 1  # reset after craft
        
        await update_user(self.user)

        await interaction.response.edit_message(
            embed=self.make_embed(),
            view=self
        )
        
    @discord.ui.button(label="Craft Max", style=discord.ButtonStyle.primary)
    async def craft_max(self, interaction, button):
        recipe = self.get_selected_recipe()
        if not recipe:
            return

        amount = recipe.max_craftable(self.user)
        if amount == 0:
            return
        
        recipe.consume(self.user, amount)
        recipe.give_result(self.user, amount)
        
        await update_user(self.user)

        self.craft_amount = 1

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

def flatten_category(items_dict, category: str):
    """
    {"Shards": {"Common": Shard, "Uncommon": Shard}}
    → [Shard, Shard]
    """
    category_items = items_dict.get(category, {})
    return list(category_items.values())

def shard_rarity_index(rarity: str) -> int:
    return SHARD_RANK.get(rarity, 0)

class ItemPaginator(discord.ui.View):
    def __init__(self, user_items, username, author: discord.User, per_page=8):
        super().__init__(timeout=120)
        self.user_items = items
        self.username = username
        self.author_id = author.id
        self.per_page = per_page
        self.index = 0
        self.current_category = "Shards"

        # Initial load
        self.items = flatten_category(user_items, "Shards")
        self.items.sort(key=lambda i: SHARD_RANK.get(i.shardrarity, 0))
        self.pages = chunk_list(self.items, per_page)

        self.add_item(ItemCategorySelect(user_items, self))

    def make_embed(self):
        embed = discord.Embed(
            title=f"{self.username}'s {self.current_category}",
            color=discord.Color.green()
        )

        if not self.pages:
            embed.description = "No items in this category."
            return embed

        for item in self.pages[self.index]:
            if isinstance(item, Shard):
                embed.add_field(
                    name=f"🔹 {item.name} ×{item.duplicates}",
                    value=(
                        f"**Shard Rarity:** {item.shardrarity}\n"
                        f"{item.function}\n"
                        f"**Value:** {item.value}\n"
                        f"**Effect:** {item.description}"
                    ),
                    inline=False
                )

            else:
                embed.add_field(
                    name=f"{item.name} ×{item.duplicates}",
                    value=(
                        f"**Rarity:** {item.rarity}\n"
                        f"{item.function}\n"
                        f"**Value:** {item.value}\n"
                        f"**Description:** {item.description}"
                    ),
                    inline=False
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
                "❌ This crafting menu isn’t yours.",
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
                f"- {d['difficulty_name']} ⭐ {d['star_rating']} (rarity 1 in {format_number(d['rarity'])}) -- ID: {d['id']} -- # {d["duplicates"]}"
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
    if ctx.author.id == 718102801242259466 or ctx.author.id == 1177826548729008268:
        bms = None
        
        json_object = await return_json("json/maps.json")
        
        try:
            bms = json_object[str(msid)]
        except:
            json_object[str(msid)] = await load_beatmapset(msid)
            await save_to_json("json/maps.json", json_object)
            
            bms = json_object[str(msid)]
            
            
            await ctx.message.reply(f"Beatmap {bms["title"]} of ID {bms["id"]} has been loaded into the database.")
        else:
            bms = json_object[str(msid)]
            
            await ctx.message.reply(f"Beatmap {bms["title"]} of ID {bms["id"]} has already been loaded.")
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
    if ctx.author.id == 718102801242259466 or ctx.author.id == 1177826548729008268:
        await loadnpage()
        
        await ctx.message.reply("Loaded 50 new beatmaps into the database")
        
        return
    
    await ctx.message.reply("You do not have the permission to use this command.")  
    
# Load the next given amount of pages (dev only)
@client.command("load_multipages")
async def loadmanypages(ctx, num):
    if ctx.author.id == 718102801242259466 or ctx.author.id == 1177826548729008268:
        amount_maps = 0
        
        for i in range(int(num)):
            await loadnpage()
            amount_maps += 50
        
        await ctx.message.reply(f"{amount_maps} maps has been loaded!")
        
        return
    
    await ctx.message.reply("You do not have the permission to use this command.")  
    
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

@client.command("balance")
async def balance(ctx):
    userdata = await login(ctx.author.id)
    
    await ctx.message.reply(f"You currently have {format_number(userdata.pp)} PP.")
    
@client.command("items")
async def items(ctx):
    username = ctx.author.display_name
    userdata = await login(ctx.author.id)
    raw_items = userdata.items 

    if not raw_items or not raw_items.get("Shards"):
        await ctx.message.reply("You have no items.")
        return

    view = ItemPaginator(raw_items, username, per_page=5, author=ctx.author)
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
    if ctx.author.id == 718102801242259466 or ctx.author.id == 1177826548729008268:
        await reset_page_count()
        await ctx.message.reply("Done.")
        print("Reseted page back to 0.")
        
        return
    
    await ctx.message.reply("You do not have the permission to use this command.") 
    
# set the internal page count (dev only)
@client.command("spc")
async def spc(ctx, page):
    if ctx.author.id == 718102801242259466 or ctx.author.id == 1177826548729008268:
        await set_page_count(page)
        await ctx.message.reply("Done.")
        print(f"Set page to {page}.")
        
        return
    
    await ctx.message.reply("You do not have the permission to use this command.") 
    
# Change query of bot search
@client.command("change_year")
async def bot_change_year(ctx, year):
    if ctx.author.id == 718102801242259466 or ctx.author.id == 1177826548729008268:
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
    
    if ctx.author.id == 718102801242259466 or ctx.author.id == 1177826548729008268:
        if rolling_disabled:
            await ctx.message.reply("Rolling Enabled.")
        if not rolling_disabled:
            await ctx.message.reply("Rolling disabled.")
            
        rolling_disabled = not rolling_disabled
            
        return
    
    await ctx.message.reply("You do not have the permission to use this command.") 
        
# Add all difficulties to sorted file for sorting (dev only). Step 1
@client.command("load_diffs_sorted")
async def load_diffs_sorted(ctx):
    if ctx.author.id == 718102801242259466 or ctx.author.id == 1177826548729008268:
        await add_diffs_to_sorted_file()
        
        await ctx.message.reply("Done.")
        
        return  
    
    await ctx.message.reply("You do not have the permission to use this command.")  
    
# Acumulate all ranges in file (dev only). Step 2
"""@client.command("load_cumulative_diffs")
async def load_nmz_diffs(ctx):
    if ctx.author.id == 718102801242259466 or ctx.author.id == 1177826548729008268:
        await add_cumulative_diffs_to_sorted_file()
        
        await ctx.message.reply("Done.")
        
        return
    
    await ctx.message.reply("You do not have the permission to use this command.")
    
# Calculate the ranges of rarities for sorted beatmaps (dev only). Step 3
@client.command("calculate_ranges")
async def calc_ranges(ctx):
    if ctx.author.id == 718102801242259466 or ctx.author.id == 1177826548729008268:
        await add_ranges_to_file()
        
        await ctx.message.reply("Done.")
        
        return  
    
    await ctx.message.reply("You do not have the permission to use this command.") """
    
@client.command("getmap")
async def getmap(ctx, id, bmid, amount=1):
    if ctx.author.id == 718102801242259466 or ctx.author.id == 1177826548729008268 or ctx.author.id == 970958596424761366:
        userdata = await login(ctx.author.id)
        res = await load_beatmapset(id)
        
        result = None
        
        for i in res["difficulties"]:
            if i["id"] == int(bmid):
                result = i
        
        embed = discord.Embed(title=f"You rolled {result["title"]}[{result["difficulty_name"]}]! (1 in {format_number(result["rarity"])})", description=f"Star Rating: {result["star_rating"]} ⭐", color=await get_star_color(result["star_rating"]), timestamp=datetime.datetime.now())
        embed.set_image(url=f"https://assets.ppy.sh/beatmaps/{res["id"]}/covers/cover.jpg")
        embed.set_thumbnail(url=f"https://b.ppy.sh/thumb/{res["id"]}l.jpg")
        
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
    
@client.command("setluck")
async def setluck(ctx, luck):
    if int(luck) > 999_999_999_999:
        await ctx.message.reply("Luck multiplier demanded is too high, max is 999,999,999,999 (999 billion)")
        
        return
    
    userdata = await login(ctx.author.id)
    userdata.luck_mult = int(luck)
    
    await update_user(userdata)
    await ctx.message.reply(f"Set luck to {format_number(int(luck))}x.")
    
# Roll a beatmap
@client.command("roll")
async def roll_random(ctx):
    if not rolling_disabled:
        userdata = await login(ctx.author.id)
        luck_mult = userdata.luck_mult
        print(luck_mult)
        
        result = await get_random_map(luck_mult)
        
        embed = discord.Embed(title=f"You rolled {result["title"]}[{result["difficulty_name"]}]! (1 in {format_number(result["rarity"])})", description=f"Star Rating: {result["star_rating"]} ⭐", color=await get_star_color(result["star_rating"]), timestamp=datetime.datetime.now())
        embed.set_image(url=f"https://assets.ppy.sh/beatmaps/{result["id"]}/covers/cover.jpg")
        embed.set_thumbnail(url=f"https://b.ppy.sh/thumb/{result["id"]}l.jpg")
        
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
        
        await userdata.add_map(ubmd)
        
        await update_user(userdata)
        
        await ctx.message.reply(embed=embed)
        
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
    
@client.command("level")
async def level(ctx):
    userdata = await login(ctx.author.id)
    
    xp_needed = xp_to_next_level(userdata.level)
    bar = await xp_bar(userdata.xp, xp_needed)
        
    await ctx.message.reply((
        f"Level {format_number(userdata.level)} - {bar} - {format_number(userdata.level+1)}\n"
        f"{format_number(userdata.xp)}/{format_number(xp_needed)} XP"
    ))
    
@client.command("clear_userdata")
async def clear_userdata_cmd(ctx, id):
    if ctx.author.id == 718102801242259466 or ctx.author.id == 1177826548729008268:    
        await clear_userdata(id)
        
        await ctx.message.reply("Done.")
        
        return
    
    await ctx.message.reply("You do not have the permission to use this command.")
    
# Clear ALL userdata in the database (dev only, risky)
@client.command("clear_all_userdata")
async def clear_all_userdata_cmd(ctx):
    if ctx.author.id == 718102801242259466 or ctx.author.id == 1177826548729008268:
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
    if ctx.author.id == 718102801242259466 or ctx.author.id == 1177826548729008268:
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
        
# Clear ALL sorted and ranges maps in the database (dev only, risky)
@client.command("clear_sorted_diffs")
async def clear_sorted_diffs_cmd(ctx):
    if ctx.author.id == 718102801242259466 or ctx.author.id == 1177826548729008268:
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
    if ctx.author.id == 718102801242259466 or ctx.author.id == 1177826548729008268:
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
    
    await ctx.message.reply("Check DMs.")
    
    await ctx.author.send("""Prefix - o!
ping - Check status of Bot. example: o!ping.
calculaterarity - Calculate rarity of a given star rating. Arguments: <sr>. example: o!calculaterarity 7.86.
load_beatmapset - Returns json data of a beatmapset with a given bms id. Arguments: <bms_id>. example: o!load_beatmapset 2288709.
mapsloaded - Check how many maps has been loaded into the database. example: o!mapsloaded.
help - Shows this message.
7 more dev-only commands.""")
    
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

@client.command("test1")
async def t1(ctx, id, amount):
    userdata = await login(ctx.author.id)
    
    await userdata.remove_item_by_id(id, int(amount))
    
    await update_user(userdata)
    
    await ctx.message.reply("Done.")
    
@client.command("test2")
async def t1(ctx, id):
    userdata = await login(ctx.author.id)
    
    await ctx.message.reply(await userdata.count_item_by_id(id))
        
@client.command("inventory")
async def inventory(ctx, id = None):
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
    
    
@client.command("recalculate_rarities")
async def recalculate_rarities(ctx):
    if ctx.author.id == 718102801242259466 or ctx.author.id == 1177826548729008268:
        json_object = await return_json("json/maps.json")
        
        for i in json_object:
            for y in json_object[i]["difficulties"]:
                y["rarity"] = Calculate_Rarity(y["star_rating"])
                
        await save_to_json("json/maps.json", json_object)
                
        await ctx.message.reply("Done.")
        
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

client.run(os.getenv("token"))