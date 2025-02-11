from enum import IntEnum
from typing import Dict

class Direction(IntEnum):
  NORTH = -0x10
  WEST = -0x1
  NO_DIRECTION = 0
  EAST = 0x1
  SOUTH = 0x10
  
  @classmethod
  def inverse(self) -> "Direction":
    if self == Direction.NORTH:
      return Direction.SOUTH
    elif self == Direction.SOUTH:
      return Direction.NORTH
    elif self == Direction.WEST:
      return Direction.EAST
    elif self == Direction.EAST:
      return Direction.WEST
    return Direction.NO_DIRECTION

ENTRANCE_DIRECTION_MAP: Dict[int, Direction] = {
  1: Direction.NORTH,
  2: Direction.SOUTH,
  3: Direction.WEST,
  4: Direction.EAST
}

DOOR_TYPES = {
    0: "Door",
    1: "Wall",
    2: "Walk-Through Wall",
    3: "Walk-Through Wall",
    4: "Bomb Hole",
    5: "Locked Door",
    6: "Locked Door",
    7: "Shutter Door",
}

class WallType(IntEnum):
  DOOR = 0
  SOLID_WALL = 1
  WALK_THROUGH_WALL_1 = 2
  WALK_THROUGH_WALL_2 = 3
  BOMB_HOLE = 4
  LOCKED_DOOR_1 = 5
  LOCKED_DOOR_2 = 6
  SHUTTER_DOOR = 7


class TileType(IntEnum):
  FLOOR = 0
  BLOCK = 1
  WATER = 2
  STATUE = 3
  STAIRWAY = 4
  BLACK = 5
  BOMB_HOLE = 6
  KEY_DOOR = 7
  SHUTTER_DOOR = 8
  WALK_THROUGH_WALL = 9
  OLD_MAN = 10


WALL_TYPE_CHAR = {
    0: (" ", " "),
    1: ("-", "|"),
    2: ("=", "!"),
    3: ("=", "!"),
    4: ("B", "B"),
    5: ("K", "K"),
    6: ("K", "K"),
    7: ("S", "S"),
}

CAVE_NAME = {
  0x01: 'Level 1',
  0x02: 'Level 2',
  0x03: 'Level 3',
  0x04: 'Level 4',
  0x05: 'Level 5',
  0x06: 'Level 6',
  0x07: 'Level 7',
  0x08: 'Level 8',
  0x09: 'Level 9',
  0x10: 'Wood Sword Cave',
  0x11: 'Take Any',
  0x12: 'White Sword Cave',
  0x13: 'Magical Sword Cave',
  0x14: 'Any Road',
  0x15: 'White Sword Clue',
  0x16: 'Money Making Game',
  0x17: 'Door Repair',
  0x18: 'Letter Cave',
  0x19: 'Magical Sword Clue',
  0x1A: 'Potion Shop',
  0x1B: 'Hint Shop 1',
  0x1C: 'Hint Shop 2',
  0x1D: 'Shop 1',
  0x1E: 'Shop 2',
  0x1F: 'Shop 3',
  0x20: 'Shop 4',
  0x21: 'Medium Secret',
  0x22: 'Large Secret',
  0x23: 'Small Secret'
}

CAVE_NAME_SHORT = {
  0x01: 'L1',
  0x02: 'L2',
  0x03: 'L3',
  0x04: 'L4',
  0x05: 'L5',
  0x06: 'L6',
  0x07: 'L7',
  0x08: 'L8',
  0x09: 'L9',
  0x10: 'Wood',
  0x11: 'Take Any',
  0x12: 'White',
  0x13: 'Mags',
  0x14: 'Any Rd.',
  0x15: 'WS Clue',
  0x16: 'MMG',
  0x17: '-20R',
  0x18: 'Letter',
  0x19: 'MS Clue',
  0x1A: 'Potion',
  0x1B: 'Hints 1',
  0x1C: 'Hints 2',
  0x1D: 'Shop 1',
  0x1E: 'Shop 2',
  0x1F: 'Shop 3',
  0x20: 'Shop 4',
  0x21: '30R',
  0x22: '100R',
  0x23: '10R'
}

ITEM_TYPES = {
    0x00: "Bombs",
    0x01: "Wood Sword",
    0x02: "White Sword",
    0x03: "No Item",
    0x04: "Bait",
    0x05: "Recorder",
    0x06: "Blue Candle",
    0x07: "Red Candle",
    0x08: "Wooden Arrow",
    0x09: "Silver Arrow",
    0x0A: "Bow",
    0x0B: "Magical Key",
    0x0C: "Raft",
    0x0D: "Ladder",
    0x0E: "Triforce",  # Big L9 triforce, not small tringle
    0x0F: "5 Rupees",
    0x10: "Wand",
    0x11: "Book",
    0x12: "Blue Ring",
    0x13: "Red Ring",
    0x14: "Power Bracelet",
    0x15: "Letter",
    0x16: "Compass",
    0x17: "Map",
    0x18: "1 Rupee",
    0x19: "Key",
    0x1A: "Heart Container",
    0x1B: "Triforce",
    0x1C: "Shield",
    0x1D: "Boomerang",
    0x1E: "Magical Boomerang",
    0x1F: "Blue Potion",
    0x20: "Red Potion",
    0x22: "Heart",
    0x3F: "Nothing",
}

ROOM_TYPES = {
  0x00: "Plain",
  0x01: "Spike Trap",
  0x02: "Four Short",
  0x03: "Four Tall",
  0x04: "Aqua Room",
  0x05: "Gleeok Room",
  0x06: "Gohma Room",
  0x07: "Three Rows",
  0x08: "Reverse C",
  0x09: "Circle Wall",
  0x0A: "Double Block",
  0x0B: "Is this a lava moat room?",
  0x0C: "Maze Room",
  0x0D: "Grid Room",
  0x0E: "Vert. Chute",
  0x0F: "Horiz. Chute",
  0x10: "Vertical Rows",
  0x11: "Zigzag",
  0x12: "T Room",
  0x13: "Vert. Moat",
  0x14: "Circle Moat",
  0x15: "Pointless Moat",
  0x16: "Chevy",
  0x17: "NSU",
  0x18: "Horiz. Moat",
  0x19: "Double Moat",
  0x1A: "Diamond Stair",
  0x1B: "Narrow Stair",
  0x1C: "Spiral Stair",  
  0x1D: "Double Six",
  0x1E: "Single Six",
  0x1F: "Five Pair",
  0x20: "Turnstile",
  0x21: "Entrance Room",
  0x22: "Single Block",
  0x23: "Two Fireball",
  0x24: "Four Fireball",
  0x25: "Desert Room",
  0x26: "Black Room",
  0x27: "Zelda Room",
  0x28: "Gannon Room",
  0x29: "Triforce Room",
}

ENEMY_TYPES = {
    0x00: "",
    0x01: "Blue Lynel",
    0x02: "Red Lynel",
    0x03: "Blue Moblin",
    0x04: "Red Moblin",
    0x05: "Blue Goriya",
    0x06: "Red Goriya",
    0x07: "Red Octorok",
    0x08: "Red Octorok",
    0x09: "Blue Octorok",
    0x0A: "Blue Octorok",
    0x0B: "Red Darknut",
    0x0C: "Blue Darknut",
    0x0D: "Blue Tektite",
    0x0E: "Red Tektite",
    0x0F: "Blue Lever",
    0x10: "Red Lever",
    0x12: "Vire", 
    0x13: "Zol",
    0x14: "Gel",
    0x15: "Gel",
    0x16: "Pols Voice",
    0x17: "Like Like",
    0x1A: "Peahat",
    0x1B: "Blue Keese",
    0x1C: "Red Keese",
    0x1D: "Black Keese",
    0x1E: "Armos",
    0x1F: "Falling Rocks",
    0x20: "Falling Rock",
    0x21: "Ghini",
    0x22: "Ghini",
    0x23: "Blue Wizzrobe",
    0x24: "Red Wizzrobe",
    0x27: "Wallmaster",
    0x28: "Rope",
    0x2A: "Stalfos",
    0x2B: "Bubble",
    0x2C: "Blue Bubble",
    0x2D: "Red Bubble",
    0x30: "Gibdo",
    0x31: "3 Dodongos",
    0x32: "1 Dodongo",
    0x33: "Blue Gohma",
    0x34: "Red Gohma",
    0x35: "Rupee Boss",
    0x36: "Hungry Enemy",
    0x37: "The Kidnapped",
    0x38: "Digdogger (3)",
    0x39: "Digdogger (1)",
    0x3A: "Red Lanmola",
    0x3B: "Blue Lanmola",
    0x3C: "Manhandala",
    0x3D: "Aquamentus",
    0x3E: "The Beast",
    0x41: "Moldorm",
    0x42: "1 Head Gleeok",
    0x43: "2 Head Gleeok",
    0x44: "3 Head Gleeok",
    0x45: "4 Head Gleeok",
    0x46: "Gleeok Head",
    0x47: "Patra (Ellipse)",
    0x48: "Patra (Circle)",
    0x49: "Horiz. Traps",
    0x4A: "Corner Traps",
    0x4B: "Hint #1",
    0x4C: "Hint #2",
    0x4D: "Hint #3",
    0x4E: "Hint #4",
    0x4F: "Bomb Upgrade",
    0x50: "Hint #6",
    0x51: "Mugger",
    0x52: "Hint #5",
    0x62: "Enemy Mix A",
    0x63: "Enemy Mix B",
    0x64: "Enemy Mix C",
    0x65: "Enemy Mix D",
    0x66: "Enemy Mix E",
    0x67: "Enemy Mix F",
    0x68: "Enemy Mix G",
    0x69: "Enemy Mix H",
    0x6A: "Enemy Mix I",
    0x6B: "Enemy Mix J",
    0x6C: "Enemy Mix K",
    0x6D: "Enemy Mix L",
    0x6E: "Enemy Mix M",
    0x6F: "Enemy Mix N",
    0x70: "Enemy Mix O",
    0x71: "Enemy Mix P",
    0x72: "Enemy Mix Q",
    0x73: "Enemy Mix R",
    0x74: "Enemy Mix S",
    0x75: "Enemy Mix T",
    0x76: "Enemy Mix U",
    0x77: "Enemy Mix V",
    0x78: "Enemy Mix W",
    0x79: "Enemy Mix X",
    0x7A: "Enemy Mix Y",
    0x7B: "Enemy Mix Z",
    0x7C: "Enemy Mix AA",
    0x7D: "Enemy Mix BB",
    0x7E: "Enemy Mix CC",
    0x7F: "Enemy Mix DD",
}
OVERWORLD_BLOCK_TYPES = {
  0x00: "Bomb",  # 2nd quest level 9
  0x01: "Bomb",
  0x02: "Bomb", #2nd quest only
  0x03: "Bomb",
  0x04: "Open",
  0x05: "Bomb", # 1st quest level 9
  0x06: "Recorder", #2nd quest only
  0x07: "Bomb", 
  0x09: "Power Bracelet", #2nd quest only
  0x0A: "Open",
  0x0B: "Open",
  0x0C: "Open",
  0x0D: "Bomb",
  0x0E: "Open",
  0x0F: "Open",  # 1st quest 100 secret
  0x10: "Bomb",  
  0x11: "Power Bracelet", # 2nd quest letter cave
  0x12: "Bomb", 
  0x13: "Bomb",
  0x14: "Bomb",
  0x15: "Bomb", # 2nd quest only
  0x16: "Bomb", 
  0x18: "Ladder+Bomb", #  quest only
  0x19: "Ladder+Bomb", # 2nd quest only
  0x1A: "Open",
  0x1B: "Power Bracelet", # 2nd quest only
  0x1C: "Open",
  0x1D: "Power Bracelet",
  0x1E: "Bomb",
  0x1F: "Open",
  0x20: "Open",  # 2nd quest Grave block
  0x21: "Open", # 1st quest Grave block
  0x22: "Open", # 1Q6
  0x23: "Power Bracelet",
  0x24: "Open",
  0x25: "Open",
  0x26: "Bomb", # forgotten spot
  0x27: "Bomb", # 1st quest only
  0x28: "Candle",
  0x29: "Recorder", #2nd quest only
  0x2B: "Recorder", #2nd quest only
  0x2C: "Bomb",  # 1st quest only
  0x2D: "Bomb",
  0x2F: "Raft",
  0x30: "Recorder",  # 2nd quest level 6
  0x33: "Bomb",
  0x34: "Open",
  0x37: "Open", 
  0x3A: "Recorder",  # 2nd quest only
  0x3C: "Recorder",  # 2nd quest level 3
  0x3D: "Open",
  0x42: "Recorder", # 1st quest level 7
  0x44: "Open",
  0x45: "Raft", # 1st quest level 4
  0x46: "Candle", 
  0x47: "Candle",  # 1st quest only 
  0x48: "Candle", 
  0x49: "Power Bracelet", 
  0x4A: "Open",
  0x4B: "Candle",
  0x4D: "Candle",
  0x4E: "Open",
  0x51: "Candle",
  0x53: "Candle",  # 2nd quest only
  0x56: "Candle", 
  0x58: "Recorder",  # 2nd quest only
  0x5B: "Candle",
  0x5E: "Open",
  0x60: "Recorder",  # 2nd quest onlye
  0x62: "Candle", # 1st quest only
  0x63: "Candle",
  0x64: "Open",
  0x66: "Open", 
  0x67: "Bomb",  # 1st quest only 
  0x68: "Candle", 
  0x6A: "Candle",
  0x6B: "Candle",  # 1st quest only
  0x6C: "Candle",  # 2nd quest only
  0x6D: "Candle",  # 1st quest only
  0x6E: "Recorder",  # 2nd quest only
  0x6F: "Open", 
  0x70: "Open", 
  0x71: "Bomb",  # 1st quest only
  0x72: "Recorder", #2nd quest only
  0x74: "Open",
  0x75: "Open",
  0x76: "Bomb",
  0x77: "Open", 
  0x78: "Candle", 
  0x79: "Power Bracelet",
  0x7B: "Bomb",  # 1st quest only
  0x7C: "Bomb",
  0x7D: "Bomb",
}

CHAR_MAP = {
  0x00: "0",
  0x01: "1",
  0x02: "2",
  0x03: "3",
  0x04: "4",
  0x05: "5",
  0x06: "6",
  0x07: "7",
  0x08: "8",
  0x09: "9",
  0x0A: "A",
  0x0B: "B",
  0x0C: "C",
  0x0D: "D",
  0x0E: "E",
  0x0F: "F",
  0x10: "G",
  0x11: "H",
  0x12: "I",
  0x13: "J",
  0x14: "K",
  0x15: "L",
  0x16: "M",
  0x17: "N",
  0x18: "O",
  0x19: "P",
  0x1A: "Q",
  0x1B: "R",
  0x1C: "S",
  0x1D: "T",
  0x1E: "U",
  0x1F: "V",
  0x20: "W",
  0x21: "X",
  0x22: "Y",
  0x23: "Z",
  0x24: " ",
  0x25: "",
  0x28: ",",
  0x29: "!",
  0x2A: "'",
  0x2B: "&",
  0x2C: '.',
  0x2D: "\"",
  0x2E: "?",
  0x2F: "-",
  0x3F: " ",
  0xFF: " ",
}

PALETTE_COLORS = [
"#7C7C7C",
"#0000FC",
"#0000BC",
"#4428BC",
"#940084",
"#A80020",
"#A81000",
"#881400",
"#503000",
"#007800",
"#006800",
"#005800",
"#004058",
"#000000",
"#000000",
"#000000",
"#BCBCBC",
"#0078F8",
"#0058F8",
"#6844FC",
"#D800CC",
"#E40058",
"#F83800",
"#E45C10",
"#AC7C00",
"#00B800",
"#00A800",
"#00A844",
"#008888",
"#000000",
"#000000",
"#000000",
"#F8F8F8",
"#3CBCFC",
"#6888FC",
"#9878F8",
"#F878F8",
"#F85898",
"#F87858",
"#FCA044",
"#F8B800",
"#B8F818",
"#58D854",
"#58F898",
"#00E8D8",
"#787878",
"#000000",
"#000000",
"#FCFCFC",
"#A4E4FC",
"#B8B8F8",
"#D8B8F8",
"#F8B8F8",
"#F8A4C0",
"#F0D0B0",
"#FCE0A8",
"#F8D878",
"#D8F878",
"#B8F8B8",
"#B8F8D8",
"#00FCFC",
"#F8D8F8",
"#000000",
"#000000"
]
