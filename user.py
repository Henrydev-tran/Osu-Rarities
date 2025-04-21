class User:
    def __init__(self, id):
        self.id = id
        self.maps = []
        self.mappers = []
        self.items = []
        self.pp = []
        self.rolls_amount = 0
        self.rank = 0
        
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