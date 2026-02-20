import copy

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
        
class CraftingRecipe:
    def __init__(self, id, name, result, requirements, description):
        self.id = id
        self.name = name
        self.result = result            
        self.requirements = requirements  
        self.description = description
        
    def max_craftable(self, user) -> int:
        """
        Returns the maximum number of times this recipe can be crafted
        based on user's inventory.
        """
        return min(
            user.count_item_by_id(item_id) // amount
            for item_id, amount in self.requirements.items()
        )

    def can_craft(self, user, amount: int = 1) -> bool:
        return self.max_craftable(user) >= amount

    def consume(self, user, amount: int):
        for item_id, req_amount in self.requirements.items():
            user.remove_item_by_id(item_id, req_amount * amount)

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
        id="0001",
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
        id="0002",
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
        id="0003",
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
        id="0004",
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
        id="0005",
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
        id="0005",
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
        id="0006",
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
        id="0007",
        description="Ultra Shard Description",
        duplicates=1,
        type="Shard",
        shardrarity="Ultra"
    ),
} 

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
    
ALL_RECIPES = {
    "ShardCores": SHARD_CORE_RECIPES
}

RECIPES_BY_ID = {
    recipe.id: recipe
    for recipes in ALL_RECIPES.values()
    for recipe in recipes
}