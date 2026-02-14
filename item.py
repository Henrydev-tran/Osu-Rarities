class Item:
    def __init__(self, rarity, cost, name, function, id, description):
        self.rarity = rarity
        self.cost = cost
        self.name = name
        self.function = function
        self.id = id
        self.description = description
        
class Shard(Item):
    def __init__(self, rarity, cost, name, function, id, description, shardrarity):
        super().__init__(rarity, cost, name, function, id, description)
        self.shardrarity = shardrarity
        
class Mapper(Item):
    def __init__(self, rarity, cost, name, function, id, description, mapperbuff, buffamount):
        super().__init__(rarity, cost, name, function, id, description)
        self.mapperbuff = mapperbuff
        self.buffamount = buffamount

class Gear(Item):
    def __init__(self, rarity, cost, name, function, id, description, luckincrease):
        super().__init__(rarity, cost, name, function, id, description)
        self.luckincrease = luckincrease