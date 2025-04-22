class User:
    def __init__(self, id, maps=[], mappers=[], items=[], pp=0, rolls_amount=0, rank=0):
        self.id = id
        self.maps = maps
        self.mappers = mappers
        self.items = items
        self.pp = pp
        self.rolls_amount = rolls_amount
        self.rank = rank
        
    def add_map(self, map):
        self.maps.append(map)
    
    def add_mapper(self, mapper):
        self.mappers.append(mapper)
    
    def add_item(self, item):
        self.items.append(item)
    
    def change_pp(self, amount):
        self.pp += amount
    
    def add_rolls(self, amount):
        self.rolls_amount += amount
    
    def change_rank(self, new_rank):
        self.rank = new_rank