class ItemInstance:
    def __init__(self, rarity, cost, name, function, id, description):
        self.rarity = rarity
        self.cost = cost
        self.name = name
        self.function = function
        self.id = id
        self.description = description
        
class ShardInstance(ItemInstance):
    def __init__(self, rarity, cost, name, function, id, shardrarity, description):
        super().__init__(rarity, cost, name, function, id, description)
        self.shardrarity = shardrarity

class MapperInstance(ItemInstance):
    def __init__(self, rarity, cost, name, function, id, mapperbuff, buffamount, description):
        super().__init__(rarity, cost, name, function, id, description)
        self.mapperbuff = mapperbuff
        self.buffamount = buffamount

class GearInstance(ItemInstance):
    def __init__(self, rarity, cost, name, function, id, luckincrease, description):
        super().__init__(rarity, cost, name, function, id, description)
        self.luckincrease = luckincrease

class CollectionInstance(ItemInstance):
    def __init__(self, rarity, cost, name, function, id, description):
        super().__init__(rarity, cost, name, function, id, description)
        
class Item:
    def __init__(self, template):
        self.template = template