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
        
class Mapper(Item):
    def __init__(self, rarity, cost, name, value, function, id, description, duplicates, mapperbuff, type, buffamount):
        super().__init__(rarity, cost, name, value, function, id, description, duplicates, type)
        self.mapperbuff = mapperbuff
        self.buffamount = buffamount

class Gear(Item):
    def __init__(self, rarity, cost, name, value, function, id, description, duplicates, type, luckincrease):
        super().__init__(rarity, cost, name, value, function, id, description, duplicates, type)
        self.luckincrease = luckincrease
        
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