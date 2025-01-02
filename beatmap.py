from raritycalculation import Calculate_Rarity

class Beatmap:
    def __init__(self, id, title, artist, difficulties, mapper) -> None:
        self.id = id
        self.title = title
        self.artist = artist
        self.difficulties = difficulties
        self.mapper = mapper


class Beatmap_Difficulty:
    def __init__(self, sr, parent_id, id) -> None:
        self.id = id
        self.sr = sr
        self.rarity = Calculate_Rarity(self.sr)
        self.parent_id = parent_id