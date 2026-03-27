from enum import Enum


class MapRequirement:
    def __init__(self, amount: int = 1, min_star: float | None = None, max_star: float | None = None, include_min: bool = True, include_max: bool = True):
        self.amount = amount
        self.min_star = min_star
        self.max_star = max_star
        self.include_min = include_min
        self.include_max = include_max

    def matches(self, map_diff) -> bool:
        star = getattr(map_diff, "sr", None)
        if star is None:
            return False

        if self.min_star is not None:
            if self.include_min:
                if star < self.min_star:
                    return False
            else:
                if star <= self.min_star:
                    return False

        if self.max_star is not None:
            if self.include_max:
                if star > self.max_star:
                    return False
            else:
                if star >= self.max_star:
                    return False

        return True

    def format_requirement(self) -> str:
        if self.min_star is not None and self.max_star is None:
            op = ">=" if self.include_min else ">"
            return f"{self.amount} map(s) with star rating {op} {self.min_star}"

        if self.max_star is not None and self.min_star is None:
            op = "<=" if self.include_max else "<"
            return f"{self.amount} map(s) with star rating {op} {self.max_star}"

        if self.min_star is not None and self.max_star is not None:
            left = ">=" if self.include_min else ">"
            right = "<=" if self.include_max else "<"
            return f"{self.amount} map(s) with {self.min_star} {left} SR {right} {self.max_star}"

        return f"{self.amount} map(s)"

class Item:
    def __init__(self, rarity, cost, name, value, function, id, description, duplicates, type):
        self.rarity = rarity
        self.cost = cost
        self.value = value
        self.name = name
        self.function = function
        self.id = id
        self.description = description
        self.duplicates = duplicates
        self.type = type
        
class Tool:
    def __init__(self, rarity, name, function, id, description, type):
        self.rarity = rarity
        self.name = name
        self.function = function
        self.id = id
        self.description = description
        self.type = type
        
class Shard(Item):
    def __init__(self, rarity, cost, name, value, function, id, description, duplicates, type, shardrarity):
        super().__init__(rarity, cost, name, value, function, id, description, duplicates, type)
        self.shardrarity = shardrarity
        
class Special(Item):
    def __init__(self, rarity, cost, name, value, function, id, description, duplicates, type):
        super().__init__(rarity, cost, name, value, function, id, description, duplicates, type)
        
class ShardCore(Item):
    def __init__(self, rarity, cost, name, value, function, id, description, duplicates, type, corerarity):
        super().__init__(rarity, cost, name, value, function, id, description, duplicates, type)
        self.corerarity = corerarity
        
class Mapper(Item):
    def __init__(self, rarity, cost, name, value, function, id, description, duplicates, mapperbuff, type, buffamount):
        super().__init__(rarity, cost, name, value, function, id, description, duplicates, type)
        self.mapperbuff = mapperbuff
        self.buffamount = buffamount

class Gear(Item):
    def __init__(self, rarity, cost, name, value, function, id, description, duplicates, type, luckincrease, luckmultiplier):
        super().__init__(rarity, cost, name, value, function, id, description, duplicates, type)
        self.luckincrease = luckincrease
        self.luckmultiplier = luckmultiplier
        
class Gear_Peripheral(Gear):
    def __init__(self, rarity, cost, name, value, function, id, description, duplicates, type, luckincrease, luckmultiplier, peripheraltype, equipped=False):
        super().__init__(rarity, cost, name, value, function, id, description, duplicates, type, luckincrease, luckmultiplier)
        self.peripheraltype = peripheraltype
        self.equipped = equipped
        
class CraftingRecipe:
    def __init__(self, id, name, result, requirements, description, item_requirement=None, map_requirement: MapRequirement | None = None):
        self.id = id
        self.name = name
        self.result = result            
        self.requirements = requirements  
        self.description = description

        # This recipe wont show up on the crafting screen unless the user has this item in their inventory (used for gating recipes behind tools)
        self.item_requirement = item_requirement
        self.map_requirement = map_requirement
        
    def max_craftable(self, user) -> int:
        """
        Returns the maximum number of times this recipe can be crafted
        based on user's inventory.
        """
        item_max = float("inf")
        if self.requirements:
            item_max = min(
                user.count_item_by_id(item_id) // amount
                for item_id, amount in self.requirements.items()
            )

        map_max = float("inf")
        if self.map_requirement is not None:
            eligible_count = user.count_eligible_maps(
                min_star=self.map_requirement.min_star,
                max_star=self.map_requirement.max_star,
                include_min=self.map_requirement.include_min,
                include_max=self.map_requirement.include_max,
            )
            map_max = eligible_count // self.map_requirement.amount

        result = min(item_max, map_max)

        if result == float("inf"):
            return 0

        return int(result)

    def can_craft(self, user, amount: int = 1) -> bool:
        return self.max_craftable(user) >= amount

    def consume(self, user, amount: int, selected_map_ids: list[int] | None = None):
        for item_id, req_amount in self.requirements.items():
            user.remove_item_by_id(item_id, req_amount * amount)

        if self.map_requirement is not None:
            needed = self.map_requirement.amount * amount
            if selected_map_ids is None or len(selected_map_ids) < needed:
                raise ValueError("Not enough selected maps to satisfy this recipe.")

            user.remove_maps_by_id_list(selected_map_ids[:needed])

    def give_result(self, user, amount: int):
        self.result.duplicates = amount
        user.add_item(self.result, self.result.type)
        
SHARDS = {
    "Common": Shard(
        rarity="Common",
        cost=False,
        value=5, # in PP
        name="Common Shard",
        function="Used for crafting. Can be sold.",
        id="SHARD_COMMON",
        description="Common Shard Description",
        duplicates=1,
        type="Shard",
        shardrarity="Common"
    ),
    "Uncommon": Shard(
        rarity="Uncommon",
        cost=False,
        value=15, # in PP
        name="Uncommon Shard",
        function="Used for crafting. Can be sold.",
        id="SHARD_UNCOMMON",
        description="Uncommon Shard Description",
        duplicates=1,
        type="Shard",
        shardrarity="Uncommon"
    ),
    "Rare": Shard(
        rarity="Rare",
        cost=False,
        value=50, # in PP
        name="Rare Shard",
        function="Used for crafting. Can be sold.",
        id="SHARD_RARE",
        description="Rare Shard Description",
        duplicates=1,
        type="Shard",
        shardrarity="Rare"
    ),
    "Epic": Shard(
        rarity="Epic",
        cost=False,
        value=200, # in PP
        name="Epic Shard",
        function="Used for crafting. Can be sold.",
        id="SHARD_EPIC",
        description="Epic Shard Description",
        duplicates=1,
        type="Shard",
        shardrarity="Epic"
    ),
    "Mythic": Shard(
        rarity="Mythic",
        cost=False,
        value=1000, # in PP
        name="Mythic Shard",
        function="Used for crafting. Can be sold.",
        id="SHARD_MYTHIC",
        description="Mythic Shard Description",
        duplicates=1,
        type="Shard",
        shardrarity="Mythic"
    ),
    "Legendary": Shard(
        rarity="Legendary",
        cost=False,
        value=10000, # in PP
        name="Legendary Shard",
        function="Used for crafting. Can be sold.",
        id="SHARD_LEGENDARY",
        description="Legendary Shard Description",
        duplicates=1,
        type="Shard",
        shardrarity="Legendary"
    ),
    "Chromatic": Shard(
        rarity="Chromatic",
        cost=False,
        value=75000, # in PP
        name="Chromatic Shard",
        function="Used for crafting. Can be sold.",
        id="SHARD_CHROMATIC",
        description="Chromatic Shard Description",
        duplicates=1,
        type="Shard",
        shardrarity="Chromatic"
    ),
    "Ultra": Shard(
        rarity="Ultra",
        cost=False,
        value=500000, # in PP
        name="Ultra Shard",
        function="Used for crafting. Can be sold.",
        id="SHARD_ULTRA",
        description="Ultra Shard Description",
        duplicates=1,
        type="Shard",
        shardrarity="Ultra"
    ),
} 

BEATMAP_CHARMS = {
    "Common": Gear(
        rarity="Common",
        cost=False,
        value=100, # in PP
        name="Common Beatmap Charm",
        function="Increases luck when playing beatmaps.",
        id="CHARM_COMMON",
        description="A charm that increases your luck when playing beatmaps. Common quality.",
        duplicates=1,
        type="Gear",
        luckincrease=0,
        luckmultiplier=2
    ),
    "Uncommon": Gear(
        rarity="Uncommon",
        cost=False,
        value=300, # in PP
        name="Uncommon Beatmap Charm",
        function="Increases luck when playing beatmaps.",
        id="CHARM_UNCOMMON",
        description="A charm that increases your luck when playing beatmaps. Uncommon quality.",
        duplicates=1,
        type="Gear",
        luckincrease=0,
        luckmultiplier=4
    ),
    "Rare": Gear(
        rarity="Rare",
        cost=False,
        value=1000, # in PP
        name="Rare Beatmap Charm",
        function="Increases luck when playing beatmaps.",
        id="CHARM_RARE",
        description="A charm that increases your luck when playing beatmaps. Rare quality.",
        duplicates=1,
        type="Gear",
        luckincrease=0,
        luckmultiplier=8
    ),
    "Epic": Gear(
        rarity="Epic",
        cost=False,
        value=4000, # in PP
        name="Epic Beatmap Charm",
        function="Increases luck when playing beatmaps.",
        id="CHARM_EPIC",
        description="A charm that increases your luck when playing beatmaps. Epic quality.",
        duplicates=1,
        type="Gear",
        luckincrease=0,
        luckmultiplier=16
    ),
    "Mythic": Gear(
        rarity="Mythic",
        cost=False,
        value=20000, # in PP
        name="Mythic Beatmap Charm",
        function="Increases luck when playing beatmaps.",
        id="CHARM_MYTHIC",
        description="A charm that increases your luck when playing beatmaps. Mythic quality.",
        duplicates=1,
        type="Gear",
        luckincrease=0,
        luckmultiplier=32
    ),
    "Legendary": Gear(
        rarity="Legendary",
        cost=False,
        value=100000, # in PP
        name="Legendary Beatmap Charm",
        function="Increases luck when playing beatmaps.",
        id="CHARM_LEGENDARY",
        description="A charm that increases your luck when playing beatmaps. Legendary quality.",
        duplicates=1,
        type="Gear",
        luckincrease=0,
        luckmultiplier=64
    ),
    "Chromatic": Gear(
        rarity="Chromatic",
        cost=False,
        value=750000, # in PP
        name="Chromatic Beatmap Charm",
        function="Increases luck when playing beatmaps.",
        id="CHARM_CHROMATIC",
        description="A charm that increases your luck when playing beatmaps. Chromatic quality.",
        duplicates=1,
        type="Gear",
        luckincrease=0,
        luckmultiplier=128
    ),
    "Ultra": Gear(
        rarity="Ultra",
        cost=False,
        value=5000000, # in PP
        name="Ultra Beatmap Charm",
        function="Increases luck when playing beatmaps.",
        id="CHARM_ULTRA",
        description="A charm that increases your luck when playing beatmaps. Ultra quality.",
        duplicates=1,
        type="Gear",
        luckincrease=0,
        luckmultiplier=256
    )
}

PERIPHERAL_TYPES = ["Tracking", "Keyboard", "System", "Display", "Audio"]

# SHOP ITEMS #
OFFICE_MOUSE = Gear_Peripheral(
    rarity="Common",
    cost=1000, # in PP
    value=500, # in PP
    name="Office Mouse",
    function="Increases luck when playing beatmaps.",
    id="OFFICE_MOUSE",
    description="A trusty office mouse.",
    duplicates=1,
    type="GearPeripheral",
    luckincrease=1,
    luckmultiplier=1,
    peripheraltype="Tracking"
)
OFFICE_KEYBOARD = Gear_Peripheral(
    rarity="Common",
    cost=1000, # in PP
    value=500, # in PP
    name="Office Keyboard",
    function="Increases luck when playing beatmaps.",
    id="OFFICE_KEYBOARD",
    description="A trusty office keyboard.",
    duplicates=1,
    type="GearPeripheral",
    luckincrease=1,
    luckmultiplier=1,
    peripheraltype="Keyboard"
)
GAMING_MOUSE = Gear_Peripheral(
    rarity="Rare",
    cost=25000, # in PP
    value=12500, # in PP
    name="Gaming Mouse",
    function="Increases luck when playing beatmaps.",
    id="GAMING_MOUSE",
    description="A high-end gaming mouse.",
    duplicates=1,
    type="GearPeripheral",
    luckincrease=5,
    luckmultiplier=1,
    peripheraltype="Tracking"
)
GAMING_KEYBOARD = Gear_Peripheral(
    rarity="Rare",
    cost=50000, # in PP
    value=25000, # in PP
    name="Gaming Keyboard",
    function="Increases luck when playing beatmaps.",
    id="GAMING_KEYBOARD",
    description="A high-end gaming keyboard.",
    duplicates=1,
    type="GearPeripheral",
    luckincrease=10,
    luckmultiplier=1,
    peripheraltype="Keyboard"
)
DRAWING_TABLET = Gear_Peripheral(
    rarity="Epic",
    cost=750000, # in PP
    value=375000, # in PP
    name="Drawing Tablet",
    function="Increases luck when playing beatmaps.",
    id="DRAWING_TABLET",
    description="A professional drawing tablet.",
    duplicates=1,
    type="GearPeripheral",
    luckincrease=50,
    luckmultiplier=1,
    peripheraltype="Tracking"
)
WOOTING_KEYBOARD = Gear_Peripheral(
    rarity="Legendary",
    cost=5000000, # in PP
    value=2500000, # in PP
    name="Wooting Keyboard",
    function="Increases luck when playing beatmaps.",
    id="WOOTING_KEYBOARD",
    description="A Wooting keyboard with Hall effect input.",
    duplicates=1,
    type="GearPeripheral",
    luckincrease=100,
    luckmultiplier=1,
    peripheraltype="Keyboard"
)
OLD_PC = Gear_Peripheral(
    rarity="Common",
    cost=2500, # in PP
    value=1250, # in PP
    name="Old PC",
    function="Increases luck when playing beatmaps.",
    id="OLD_PC",
    description="An old, barely functional PC from your grandpa.",
    duplicates=1,
    type="GearPeripheral",
    luckincrease=2,
    luckmultiplier=1,
    peripheraltype="System"
)
OFFICE_PC = Gear_Peripheral(
    rarity="Uncommon",
    cost=100000, # in PP
    value=50000, # in PP
    name="Office PC",
    function="Increases luck when playing beatmaps.",
    id="OFFICE_PC",
    description="A standard office PC.",
    duplicates=1,
    type="GearPeripheral",
    luckincrease=25,
    luckmultiplier=1,
    peripheraltype="System"
)
GAMING_PC = Gear_Peripheral(
    rarity="Epic",
    cost=1000000, # in PP
    value=500000, # in PP
    name="Gaming PC",
    function="Increases luck when playing beatmaps.",
    id="GAMING_PC",
    description="A high-end gaming PC.",
    duplicates=1,
    type="GearPeripheral",
    luckincrease=75,
    luckmultiplier=1,
    peripheraltype="System"
)
BROKEN_MONITOR = Gear_Peripheral(
    rarity="Common",
    cost=1000, # in PP
    value=500, # in PP
    name="Broken Monitor",
    function="Increases luck when playing beatmaps.",
    id="BROKEN_MONITOR",
    description="A broken monitor with a cracked screen.",
    duplicates=1,
    type="GearPeripheral",
    luckincrease=1,
    luckmultiplier=1,
    peripheraltype="Display"
)
OLD_MONITOR = Gear_Peripheral(
    rarity="Uncommon",
    cost=5000, # in PP
    value=2500, # in PP
    name="Old Monitor",
    function="Increases luck when playing beatmaps.",
    id="OLD_MONITOR",
    description="An old monitor from the early 2000s with a refresh rate of 45hz.",
    duplicates=1,
    type="GearPeripheral",
    luckincrease=4,
    luckmultiplier=1,
    peripheraltype="Display"
)
OFFICE_MONITOR = Gear_Peripheral(
    rarity="Uncommon",
    cost=25000, # in PP
    value=12500, # in PP
    name="Office Monitor",
    function="Increases luck when playing beatmaps.",
    id="OFFICE_MONITOR",
    description="A standard office monitor with a refresh rate of 60hz.",
    duplicates=1,
    type="GearPeripheral",
    luckincrease=7,
    luckmultiplier=1,
    peripheraltype="Display"
)
GAMING_MONITOR = Gear_Peripheral(
    rarity="Rare",
    cost=100000, # in PP
    value=50000, # in PP
    name="Gaming Monitor",
    function="Increases luck when playing beatmaps.",
    id="GAMING_MONITOR",
    description="A high-end gaming monitor with a refresh rate of 144hz.",
    duplicates=1,
    type="GearPeripheral",
    luckincrease=25,
    luckmultiplier=1,
    peripheraltype="Display"
)
PRO_MONITOR = Gear_Peripheral(
    rarity="Epic",
    cost=500000, # in PP
    value=250000, # in PP
    name="Pro Monitor",
    function="Increases luck when playing beatmaps.",
    id="PRO_MONITOR",
    description="A professional monitor with a refresh rate of 360hz.",
    duplicates=1,
    type="GearPeripheral",
    luckincrease=50,
    luckmultiplier=1,
    peripheraltype="Display"
)
BROKEN_SPEAKERS = Gear_Peripheral(
    rarity="Common",
    cost=1000, # in PP
    value=500, # in PP
    name="Broken Speakers",
    function="Increases luck when playing beatmaps.",
    id="BROKEN_SPEAKERS",
    description="A pair of broken speakers with distorted sound.",
    duplicates=1,
    type="GearPeripheral",
    luckincrease=1,
    luckmultiplier=1,
    peripheraltype="Audio"
)
OLD_SPEAKERS = Gear_Peripheral(
    rarity="Uncommon",
    cost=5000, # in PP
    value=2500, # in PP
    name="Old Speakers",
    function="Increases luck when playing beatmaps.",
    id="OLD_SPEAKERS",
    description="A pair of old speakers from the early 2000s with poor sound quality.",
    duplicates=1,
    type="GearPeripheral",
    luckincrease=3,
    luckmultiplier=1,
    peripheraltype="Audio"
)
OFFICE_HEADPHONES = Gear_Peripheral(
    rarity="Uncommon",
    cost=25000, # in PP
    value=12500, # in PP
    name="Office Headphones",
    function="Increases luck when playing beatmaps.",
    id="OFFICE_HEADPHONES",
    description="A pair of standard office headphones with decent sound quality.",
    duplicates=1,
    type="GearPeripheral",
    luckincrease=5,
    luckmultiplier=1,
    peripheraltype="Audio"
)
GAMING_HEADPHONES = Gear_Peripheral(
    rarity="Rare",
    cost=100000, # in PP
    value=50000, # in PP
    name="Gaming Headphones",
    function="Increases luck when playing beatmaps.",
    id="GAMING_HEADPHONES",
    description="A pair of high-end gaming headphones with surround sound.",
    duplicates=1,
    type="GearPeripheral",
    luckincrease=20,
    luckmultiplier=1,
    peripheraltype="Audio"
)
PRO_HEADPHONES = Gear_Peripheral(
    rarity="Epic",
    cost=500000, # in PP
    value=250000, # in PP
    name="Pro Headphones",
    function="Increases luck when playing beatmaps.",
    id="PRO_HEADPHONES",
    description="A pair of professional headphones with crystal clear sound.",
    duplicates=1,
    type="GearPeripheral",
    luckincrease=40,
    luckmultiplier=1,
    peripheraltype="Audio"
)

PERIPHERALS = [
    OFFICE_MOUSE,
    OFFICE_KEYBOARD,
    GAMING_MOUSE,
    GAMING_KEYBOARD,
    DRAWING_TABLET,
    WOOTING_KEYBOARD,
    OLD_PC,
    OFFICE_PC,
    GAMING_PC,
    BROKEN_MONITOR,
    OLD_MONITOR,
    OFFICE_MONITOR,
    GAMING_MONITOR,
    PRO_MONITOR,
    BROKEN_SPEAKERS,
    OLD_SPEAKERS,
    OFFICE_HEADPHONES,
    GAMING_HEADPHONES,
    PRO_HEADPHONES
]

SHOP_ITEMS = {
    "Peripherals": PERIPHERALS
}

MAP_REFINER_MKI = Tool(
    rarity="Rare",
    name="Map Refiner MKI",
    function="Used for refining beatmaps. Unlocks Map Essence crafting.",
    id="MAP_REFINER_MKI",
    description="A tool used for refining beatmaps into Map Essences.",
    type="Tool"
)

MAP_REFINER_MKII = Tool(
    rarity="Mythic",
    name="Map Refiner MKII",
    function="Used for refining beatmaps. Unlocks Condensed Map Essence crafting.",
    id="MAP_REFINER_MKII",
    description="A tool used for refining beatmaps into Condensed Map Essences.",
    type="Tool"
)

STAR_HARVESTER = Tool(
    rarity="Legendary",
    name="Star Harvester",
    function="Used for harvesting star essence from dying stars. Unlocks Condensed Star Essence crafting.",
    id="STAR_HARVESTER",
    description="A tool used for harvesting star essence from dying stars and turning them into Condensed Star Essences.",
    type="Tool"
)

STARESSENCE = Special(
    rarity="Special",
    cost=False,
    name="Star Essence",
    value=500,
    function="Used for crafting.",
    id="STAR_ESSENCE",
    description="Star essence fragments collected from dying stars.",
    duplicates=1,
    type="Special"
)

MAP_ESSENCE = Special(
    rarity="Special",
    cost=False,
    name="Map Essence",
    value=120,
    function="Used for crafting.",
    id="MAP_ESSENCE",
    description="Essence extracted from beatmaps using the Map Refiner.",
    duplicates=1,
    type="Special"
)

CONDENSED_MAP_ESSENCE = Special(
    rarity="Special",
    cost=False,
    name="Condensed Map Essence",
    value=1000,
    function="Used for crafting.",
    id="CONDENSED_MAP_ESSENCE",
    description="A condensed form of Map Essence that can be used for advanced crafting.",
    duplicates=1,
    type="Special"
)

CONDENSED_STAR_ESSENCE = Special(
    rarity="Special",
    cost=False,
    name="Condensed Star Essence",
    value=10000,
    function="Used for crafting.",
    id="CONDENSED_STAR_ESSENCE",
    description="A condensed form of Star Essence that can be used for advanced crafting.",
    duplicates=1,
    type="Special"
)

##############

# Crafting recipes for Beatmap Charms
BEATMAP_CHARM_RECIPES = []

# Create recipes so that:
# {rarity} Beatmap Charm = {rarity} Shards x 25 + 1 Beatmap Charm of lower rarity
# Common charms only need 25 shards (no lower charm prerequisite)
shard_rarity_order = list(SHARDS.keys())

for idx, rarity in enumerate(shard_rarity_order):
    charm = BEATMAP_CHARMS.get(rarity)
    if not charm:
        continue

    requirements = {SHARDS[rarity].id: 25}

    # for non-common rarities, require one lower-rarity charm
    if idx > 0:
        lower = shard_rarity_order[idx - 1]
        lower_charm = BEATMAP_CHARMS.get(lower)
        if lower_charm:
            requirements[lower_charm.id] = 1

    recipe = CraftingRecipe(
        id=f"CRAFT_CHARM_{rarity.upper()}",
        name=f"{rarity} Beatmap Charm",
        result=charm,
        requirements=requirements,
        description=f"Craft a {rarity} Beatmap Charm using 25 {rarity} shards" + (f" + 1 {lower} Beatmap Charm" if idx > 0 else ""),
        # Requires the previous charm as an item requirement to show up in the crafting screen (except for common)
        item_requirement=lower_charm.id if idx > 0 else None
    )

    BEATMAP_CHARM_RECIPES.append(recipe)

SHARDS_BY_ID = {
    shard.id: shard
    for shard in SHARDS.values()
}

SHARD_CORES = {
    rarity: ShardCore(
        rarity=rarity,
        cost=False,
        value=SHARDS[rarity].value * 8,
        name=f"{rarity} Shard Core",
        function="Used for advanced crafting.",
        id=f"CORE_{rarity.upper()}",
        description=f"A condensed core made from {rarity.lower()} shards.",
        duplicates=1,
        type="ShardCore",
        corerarity=rarity
    )
    for rarity in SHARDS
}

SHARD_CORE_RECIPES = []

for rarity, shard in SHARDS.items():
    recipe = CraftingRecipe(
        id=f"CRAFT_CORE_{rarity.upper()}",
        name=f"{rarity} Shard Core",
        result=SHARD_CORES[rarity],
        requirements={
            shard.id: 10
        },
        description=f"Combine 10 {rarity} shards into a {rarity} shard core."
    )

    SHARD_CORE_RECIPES.append(recipe)
    
MAP_REFINER_MKI_RECIPE = CraftingRecipe(
    id="CRAFT_MAP_REFINER_MKI",
    name="Map Refiner MKI",
    result=MAP_REFINER_MKI,
    requirements={
        SHARDS["Common"].id: 120,
        SHARDS["Uncommon"].id: 50,   
        SHARDS["Rare"].id: 25,
        SHARDS["Epic"].id: 5,
        SHARD_CORES["Common"].id: 10,
        SHARD_CORES["Uncommon"].id: 2,
        SHARD_CORES["Rare"].id: 1
    },
    description="Craft the Map Refiner MKI to unlock Map Essence crafting."
)

MAP_REFINER_MKII_RECIPE = CraftingRecipe(
    id="CRAFT_MAP_REFINER_MKII",
    name="Map Refiner MKII",
    result=MAP_REFINER_MKII,
    requirements={
        SHARDS["Uncommon"].id: 100,
        SHARDS["Mythic"].id: 10,
        SHARD_CORES["Uncommon"].id: 50,
        SHARD_CORES["Rare"].id: 10,
        SHARD_CORES["Epic"].id: 5
    },
    description="Craft the Map Refiner MKII to unlock Condensed Map Essence crafting.",
    item_requirement=MAP_REFINER_MKI.id
)

STAR_HARVESTER_RECIPE = CraftingRecipe(
    id="CRAFT_STAR_HARVESTER",
    name="Star Harvester",
    result=STAR_HARVESTER,
    requirements={
        MAP_ESSENCE.id: 100,
        STARESSENCE.id: 250,
        CONDENSED_MAP_ESSENCE.id: 5,
        SHARD_CORES["Mythic"].id: 50,
    },
    description="Craft the Star Harvester to unlock Condensed Star Essence crafting.",
    item_requirement=MAP_REFINER_MKII.id
)

MAP_ESSENCE_RECIPE = CraftingRecipe(
    id="CRAFT_MAP_ESSENCE",
    name="Map Essence",
    result=MAP_ESSENCE,
    requirements={},
    description="Refine 1 map with star rating higher than 5 into Map Essence.",
    item_requirement=MAP_REFINER_MKI.id,
    map_requirement=MapRequirement(
        amount=1,
        min_star=5.0,
        include_min=False,
    )
)

CONDENSED_MAP_ESSENCE_RECIPE = CraftingRecipe(
    id="CRAFT_CONDENSED_MAP_ESSENCE",
    name="Condensed Map Essence",
    result=CONDENSED_MAP_ESSENCE,
    requirements={
        MAP_ESSENCE.id: 25,
    },
    description="Refine 25 Map Essence and 1 map with star rating higher than 6 into Condensed Map Essence.",
    item_requirement=MAP_REFINER_MKII.id,
    map_requirement=MapRequirement(
        amount=1,
        min_star=6.0,
        include_min=False,
    )
)
    
ALL_RECIPES = {
    "ShardCores": SHARD_CORE_RECIPES,
    "BeatmapCharms": BEATMAP_CHARM_RECIPES,
    "Tools": [MAP_REFINER_MKI_RECIPE, MAP_REFINER_MKII_RECIPE, STAR_HARVESTER_RECIPE],
    "Essences": [MAP_ESSENCE_RECIPE, CONDENSED_MAP_ESSENCE_RECIPE],
}

RECIPES_BY_ID = {
    recipe.id: recipe
    for recipes in ALL_RECIPES.values()
    for recipe in recipes
}

# A lookup of all items by their `id` for convenience
ITEMS_BY_ID = {}
for shard in SHARDS.values():
    ITEMS_BY_ID[shard.id] = shard

for core in SHARD_CORES.values():
    ITEMS_BY_ID[core.id] = core

for charm in BEATMAP_CHARMS.values():
    ITEMS_BY_ID[charm.id] = charm

ITEMS_BY_ID[STARESSENCE.id] = STARESSENCE
ITEMS_BY_ID[MAP_ESSENCE.id] = MAP_ESSENCE
ITEMS_BY_ID[CONDENSED_MAP_ESSENCE.id] = CONDENSED_MAP_ESSENCE
ITEMS_BY_ID[CONDENSED_STAR_ESSENCE.id] = CONDENSED_STAR_ESSENCE

for peripheral in PERIPHERALS:
    ITEMS_BY_ID[peripheral.id] = peripheral