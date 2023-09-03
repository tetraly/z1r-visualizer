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
  0x17: 'Door Repair',
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
  0x15: 'Clue',
  0x16: 'MMG',
  0x17: '-20R',
  0x18: 'Letter',
  0x19: 'Clue',
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


ITEMS = {
    0x00: "Bombs",
    0x01: "Wooden Sword",
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
    0x1F: "Blue Potion"
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
