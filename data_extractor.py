from rom_reader import RomReader
import io
from typing import IO, List
import math
from typing import Any, Dict, List, Optional, Tuple
from constants import Direction, WallType, ROOM_TYPES, ENEMY_TYPES, ITEM_TYPES
from constants import ENTRANCE_DIRECTION_MAP, PALETTE_COLORS, CAVE_NAME_SHORT, CAVE_NAME
from constants import OVERWORLD_BLOCK_TYPES, DOOR_TYPES
from constants import BOMB_UPGRADE_PERSON, TALKING_PERSON

PALETTE_OFFSET = 0xB
START_ROOM_OFFSET = 0x2F
STAIRWAY_LIST_OFFSET = 0x34
DISPLAY_OFFSET_OFFSET = 0x2D

MAGICAL_SWORD_CODE = 0x03

# With ZORA's Progressive Items on, an item in one of these lines gives the next level of
# that line the player lacks (zora-ng docs/progressive-patches.md).
PROGRESSIVE_LINES = {
    0x01: "Sword Upgrade",
    0x02: "Sword Upgrade",
    0x03: "Sword Upgrade",
    0x06: "Candle Upgrade",
    0x07: "Candle Upgrade",
    0x08: "Arrow Upgrade",
    0x09: "Arrow Upgrade",
    0x12: "Ring Upgrade",
    0x13: "Ring Upgrade",
    0x1D: "Boomerang Upgrade",
    0x1E: "Boomerang Upgrade",
}


class GarbledLevelDataError(Exception):
    """Raised when a level's room data can't be a real dungeon, e.g. a Race ROM with encoded data."""


class DataExtractor(object):

    def __init__(self, rom: io.BytesIO, allow_decoding_roms: bool = False) -> None:
        self.rom_reader = RomReader(rom)
        self.is_z1r = True
        self.level_info: List[List[int]] = []
        self.data: Dict[int, Dict[int, Any]] = {}
        self.shop_data = {}
        self.nothing_code = self.rom_reader.GetNothingCode()
        self.has_progressive_items = self.rom_reader.HasProgressiveItems()

        for level_num in range(0, 10):
            level_info = self.rom_reader.GetLevelInfo(level_num)
            self.level_info.append(level_info)
            vals = level_info[0x34:0x3E]
            if vals[-1] in range(0, 5):
                continue
            self.is_z1r = False

        self.level_blocks: List[List[int]] = []
        for level_num in [0, 1, 7]:
            self.level_blocks.append(self.rom_reader.GetLevelBlock(level_num))

    def Parse(self) -> None:
        if self.rom_reader.HasZoraEncodedLevelData():
            raise GarbledLevelDataError("ZORA's level decoder is installed")
        self.ProcessOverworld()
        for level_num in range(1, 10):
            self.ProcessLevel(level_num)
        self._ValidateLevelData()

    def _ValidateLevelData(self) -> None:
        """Checks that the walked levels look like real dungeons.

        Encoded (Race ROM) level data parses without errors but the room walk leaks across
        the whole 128-room block. Two geometric facts hold for any playable dungeon and fail
        on garbage: a level fits on the 8x8 map, and levels that share a data block (1-6 and
        7-9) never claim the same room.
        """
        for level_num in range(1, 10):
            rooms = self.data[level_num]
            if len(rooms) > 64:
                raise GarbledLevelDataError("Level %d has %d rooms; a level can't have more than 64" %
                                            (level_num, len(rooms)))
            for room_num, room in rooms.items():
                if not 1 <= room['col'] <= 8:
                    raise GarbledLevelDataError("Level %d room 0x%02X falls outside the 8-column map" %
                                                (level_num, room_num))
        for block_levels in (range(1, 7), range(7, 10)):
            claimed = {}  # type: Dict[int, int]
            for level_num in block_levels:
                for room_num in self.data[level_num]:
                    if room_num in claimed:
                        raise GarbledLevelDataError("Room 0x%02X is claimed by both level %d and level %d" %
                                                    (room_num, claimed[room_num], level_num))
                    claimed[room_num] = level_num

    def GetItemName(self, code: int, by_line: bool = True) -> str:
        """Names an item code as the game hands it out: caves, shops, the Armos and the coast.

        $03 is the Magical Sword here. Only level rooms and item cellars treat it as "no item",
        and only in ROMs that keep $03 as their nothing code (see GetRoomItemName). With
        by_line, a ROM with Progressive Items names line items by their line ("Sword Upgrade").
        """
        if by_line and self.has_progressive_items and code in PROGRESSIVE_LINES:
            return PROGRESSIVE_LINES[code]
        if code == MAGICAL_SWORD_CODE:
            return "Magical Sword"
        return ITEM_TYPES.get(code, "Unknown Item %02X" % code)

    def GetRoomItemName(self, code: int, by_line: bool = True) -> str:
        """Names a level room's or item cellar's item code (the low five bits)."""
        if code == self.nothing_code:
            return ITEM_TYPES[MAGICAL_SWORD_CODE]  # "No Item"
        return self.GetItemName(code, by_line)

    def GetRoomItem(self, level_num: int, room_num: int) -> Optional[Tuple[str, bool]]:
        """A room's item as (name, dropped by its enemies), or None; as _GetItemText, but
        named by the item itself even with Progressive Items."""
        code = self.GetRoomData(level_num, room_num + 4 * 0x80) % 0x20
        if code == self.nothing_code:
            # Ganon's room holds the Triforce of Power ($0E), which is also ZORA's nothing code.
            if self._GetEnemyType(level_num, room_num) != ENEMY_TYPES[0x3E]:
                return None
            name = ITEM_TYPES[code]
        else:
            name = self.GetRoomItemName(code, by_line=False)
        if name == ITEM_TYPES[MAGICAL_SWORD_CODE]:  # "No Item"
            return None
        is_drop = math.floor(self.GetRoomData(level_num, room_num + 5 * 0x80) / 4) % 0x02 == 1
        return name, is_drop

    def GetRoomEnemies(self, level_num: int, room_num: int) -> Optional[Tuple[str, Optional[int]]]:
        """A room's enemies as (name, how many), or None. The count is None where the game's
        group size doesn't apply (bosses and other single foes), as _GetEnemyText shows them."""
        name = self._GetEnemyType(level_num, room_num)
        if name == ENEMY_TYPES[0x00]:
            return None
        text = self._GetEnemyText(level_num, room_num)
        if text.startswith('ERROR CODE'):
            return text, None
        count = self._GetEnemyNum(level_num, room_num)
        return name, (count if text == '%d %s' % (count, name) else None)

    def GetRoomData(self, level_num: int, byte_num: int) -> int:
        foo = -1
        if level_num == 0:
            level_block_num = 0
        elif level_num in range(1, 7):
            level_block_num = 1
        elif level_num in range(7, 10):
            level_block_num = 2
        return self.level_blocks[level_block_num][byte_num]

    def GetLevelEntranceDirection(self, level_num: int) -> Direction:
        if not self.is_z1r:
            return Direction.SOUTH
        return ENTRANCE_DIRECTION_MAP[self._GetRawLevelStairwayRoomNumberList(level_num)[-1]]

    def GetLevelStartRoomNumber(self, level_num: int) -> int:
        return self.level_info[level_num][START_ROOM_OFFSET]

    def GetLevelStairwayRoomNumberList(self, level_num: int) -> List[int]:
        stairway_list = self._GetRawLevelStairwayRoomNumberList(level_num)
        # In randomized roms, the last item in the stairway list is the entrance dir.
        if self.is_z1r:
            stairway_list.pop(-1)
        return stairway_list

    def _GetRawLevelStairwayRoomNumberList(self, level_num: int) -> List[int]:
        vals = self.level_info[level_num][STAIRWAY_LIST_OFFSET:STAIRWAY_LIST_OFFSET + 10]
        stairway_list = []  # type: List[int]
        for val in vals:
            if val != 0xFF:
                stairway_list.append(val)

        # This is a hack needed in order to make vanilla L3 work.  For some reason,
        # the vanilla ROM's data for level 3 doesn't include a stairway room even
        # though there obviously is one in vanilla level 3.
        #
        # See http://www.romhacking.net/forum/index.php?topic=18750.msg271821#msg271821
        # for more information about why this is the case and why this hack
        # is needed.
        if level_num == 3 and not stairway_list:
            stairway_list.append(0x0F)
        return stairway_list

    def ProcessOverworld(self) -> None:
        self.data[0] = {}
        for screen_num in range(0, 0x80):
            # Skip any screens that aren't "Secret in 1st Quest"
            if (self.GetRoomData(0, screen_num + 5 * 0x80) & 0x80) > 0:
                continue
            # Cave destination is upper 6 bits of table 1
            destination = self.GetRoomData(0, screen_num + 1 * 0x80) >> 2
            if destination == 0:
                continue
            x = screen_num % 0x10
            y = 8 - (math.floor(screen_num / 0x10))

            block_type = 'Tell Tetra what block type this is'
            try:
                block_type = OVERWORLD_BLOCK_TYPES[screen_num]
            except KeyError:
                continue
            self.data[0][screen_num] = {
                'screen_num': '%x' % screen_num,
                'col': x,
                'x_coord': x + .5,
                'row': y,
                'y_coord': y - .5,
                'cave': '%x' % destination,
                'block_type': block_type,
            }
            if destination in CAVE_NAME:
                self.data[0][screen_num]['cave_name'] = CAVE_NAME[destination]
            if destination in CAVE_NAME_SHORT:
                self.data[0][screen_num]['cave_name_short'] = CAVE_NAME_SHORT[destination]

        for shop_type in range(0x10, 0x24):
            base_index = 4 * 0x80 + 3 * (shop_type - 0x10)
            price_index = 4 * 0x80 + 3 * (shop_type - 0x10) + 0x14 * 3
            self.shop_data[shop_type] = []
            self.shop_data[shop_type].append(self.level_blocks[0][base_index] & 0x3F)
            self.shop_data[shop_type].append(self.level_blocks[0][base_index + 1] & 0x3F)
            self.shop_data[shop_type].append(self.level_blocks[0][base_index + 2] & 0x3F)
            self.shop_data[shop_type].append(self.level_blocks[0][price_index])
            self.shop_data[shop_type].append(self.level_blocks[0][price_index + 1])
            self.shop_data[shop_type].append(self.level_blocks[0][price_index + 2])

    def ProcessLevel(self, level_num: int) -> None:
        self.data[level_num] = {}
        rooms_to_visit = [(self.GetLevelStartRoomNumber(level_num),
                           self.GetLevelEntranceDirection(level_num))]
        transport_staircase_room_nums = set()
        while True:
            room_num, direction = rooms_to_visit.pop()
            for new_room in self._VisitRoom(level_num, room_num, direction):
                if new_room[1] == Direction.STAIRCASE:
                    transport_staircase_room_nums.add(new_room[0])
                else:
                    rooms_to_visit.append(new_room)
            if not rooms_to_visit:
                break

        self._MarkVisibleSolidWalls(level_num)

        # Add stair info/tooltips for each room that leads to a transport stairway
        stairway_num = 1
        for stairway_room_num in transport_staircase_room_nums:
            left_exit = self.GetRoomData(level_num, stairway_room_num) % 0x80
            right_exit = self.GetRoomData(level_num, stairway_room_num + 0x80) % 0x80
            self.data[level_num][left_exit]['stair_info'] = 'Stair #%d' % stairway_num
            self.data[level_num][right_exit]['stair_info'] = 'Stair #%d' % stairway_num
            self.data[level_num][left_exit]['stair_tooltip'] = 'Stairway #%d' % stairway_num
            self.data[level_num][right_exit]['stair_tooltip'] = 'Stairway #%d' % stairway_num
            self.data[level_num][left_exit]['stair_partner'] = right_exit
            self.data[level_num][right_exit]['stair_partner'] = left_exit
            stairway_num += 1

    def _MarkVisibleSolidWalls(self, level_num: int) -> None:
        """Marks solid walls that sit between two rooms of the level so they get drawn.

        Walls on the outer edge of the level (nothing on the other side) are left
        unmarked so they don't clutter the map.  This runs after every room has been
        visited so the result doesn't depend on the order rooms were discovered in.
        """
        rooms = self.data[level_num]
        direction_text = {
            Direction.NORTH: "north",
            Direction.SOUTH: "south",
            Direction.WEST: "west",
            Direction.EAST: "east"
        }
        for room_num, room in rooms.items():
            for direction, text in direction_text.items():
                if room.get('%s.wall_type' % text) != DOOR_TYPES[WallType.SOLID_WALL]:
                    continue
                neighbor = room_num + int(direction)
                if neighbor not in rooms:
                    continue
                # East/west neighbors must be on the same row; otherwise room 0x0F's
                # "east" neighbor would be 0x10, the first room of the next row.
                if direction in (Direction.EAST, Direction.WEST) and neighbor // 0x10 != room_num // 0x10:
                    continue
                room['%s.color' % text] = "red"

    def GetLevelDisplayOffset(self, level_num: int) -> int:
        return self.level_info[level_num][DISPLAY_OFFSET_OFFSET] - 3

    def _VisitRoom(self, level_num: int, room_num: int, from_dir: Direction) -> None:
        if room_num in self.data[level_num]:
            return []
        if room_num not in range(0, 0x80):
            return []
        tbr = []
        x = (room_num + self.GetLevelDisplayOffset(level_num)) % 0x10
        y = 8 - (math.floor(room_num / 0x10))

        enemy_num = self._GetEnemyNum(level_num, room_num)
        enemy_type = self._GetEnemyType(level_num, room_num)
        self.data[level_num][room_num] = {
            'col': x,
            'x_coord': x - .5,
            'row': y,
            'y_coord': y - .5,
            'room_num': '%X' % room_num,
            'stair_info': '',
            'stair_tooltip': 'None',
            'room_type': self._GetRoomType(level_num, room_num),
            'enemy_num_tooltip': '%x' % enemy_num,
            'enemy_type_tooltip': enemy_type,
            'enemy_info': self._GetEnemyText(level_num, room_num),
            'item_info': self._GetItemText(level_num, room_num),
        }

        for direction in [Direction.NORTH, Direction.EAST, Direction.SOUTH, Direction.WEST]:
            wall_type = self._GetWallType(level_num, room_num, direction)
            if wall_type == WallType.SOLID_WALL:
                direction_text = {
                    Direction.NORTH: "north",
                    Direction.SOUTH: "south",
                    Direction.WEST: "west",
                    Direction.EAST: "east"
                }
                direction_x = {
                    Direction.NORTH: -.5,
                    Direction.SOUTH: -.5,
                    Direction.WEST: -1,
                    Direction.EAST: 0
                }
                direction_y = {
                    Direction.NORTH: 0,
                    Direction.SOUTH: -1,
                    Direction.WEST: -.5,
                    Direction.EAST: -.5
                }
                self.data[level_num][room_num][
                    '%s.wall.x' % direction_text[direction]] = x + direction_x[direction]
                self.data[level_num][room_num][
                    '%s.wall.y' % direction_text[direction]] = y + direction_y[direction]
                self.data[level_num][room_num]['%s.wall_type' %
                                               direction_text[direction]] = DOOR_TYPES[wall_type]
            if wall_type != WallType.SOLID_WALL:
                direction_text = {
                    Direction.NORTH: "north",
                    Direction.SOUTH: "south",
                    Direction.WEST: "west",
                    Direction.EAST: "east"
                }
                direction_x = {
                    Direction.NORTH: -.5,
                    Direction.SOUTH: -.5,
                    Direction.WEST: -.95,
                    Direction.EAST: -.05
                }
                direction_y = {
                    Direction.NORTH: -.05,
                    Direction.SOUTH: -.95,
                    Direction.WEST: -.5,
                    Direction.EAST: -.5
                }
                color = {
                    WallType.BOMB_HOLE: 'blue',
                    WallType.LOCKED_DOOR_1: 'orange',
                    WallType.LOCKED_DOOR_2: 'orange',
                    WallType.WALK_THROUGH_WALL_1: 'purple',
                    WallType.WALK_THROUGH_WALL_2: 'purple',
                    WallType.SHUTTER_DOOR: 'brown',
                    WallType.DOOR: 'black'
                }
                self.data[level_num][room_num][
                    '%s.x' % direction_text[direction]] = x + direction_x[direction]
                self.data[level_num][room_num][
                    '%s.y' % direction_text[direction]] = y + direction_y[direction]
                self.data[level_num][room_num]['%s.color' %
                                               direction_text[direction]] = color[wall_type]
            self.data[level_num][room_num]['%s.wall_type' %
                                           direction_text[direction]] = DOOR_TYPES[wall_type]

        for direction in [Direction.NORTH, Direction.EAST, Direction.SOUTH, Direction.WEST]:
            if from_dir and direction == from_dir:
                continue
            if self._GetWallType(level_num, room_num, direction) == WallType.SOLID_WALL:
                continue
            tbr.append((room_num + direction, direction.inverse()))

        # Only check for stairways if this room is configured to have a stairway entrance
        if not self._HasStairway(level_num, room_num):
            return tbr
        for stairway_room_num in self.GetLevelStairwayRoomNumberList(level_num):
            left_exit = self.GetRoomData(level_num, stairway_room_num) % 0x80
            right_exit = self.GetRoomData(level_num, stairway_room_num + 0x80) % 0x80

            if left_exit == room_num and right_exit == room_num:
                # This is an item staircase, not a transport staircase
                item_type = int(self.GetRoomData(level_num, stairway_room_num + (4 * 0x80)) % 0x20)
                item_name = self.GetRoomItemName(item_type)
                self.data[level_num][left_exit]['stair_item_code'] = item_type
                self.data[level_num][left_exit]['stair_info'] = item_name
                self.data[level_num][left_exit]['stair_tooltip'] = item_name
                break
            elif left_exit == room_num and right_exit != room_num:
                tbr.append((stairway_room_num, direction.STAIRCASE))
                tbr.append((right_exit, direction.NO_DIRECTION))
                # Stop looking for additional staircases after finding one
                break
            elif right_exit == room_num and left_exit != room_num:
                tbr.append((stairway_room_num, direction.STAIRCASE))
                tbr.append((left_exit, direction.NO_DIRECTION))
                # Stop looking for additional staircases after finding one
                break
        return tbr

    def _GetWallType(self, level_num: int, room_num: int, direction: Direction) -> int:
        offset = 0x80 if direction in [Direction.EAST, Direction.WEST] else 0x00
        bits_to_shift = 32 if direction in [Direction.NORTH, Direction.WEST] else 4

        wall_type = math.floor(
            self.GetRoomData(level_num, room_num + offset) / bits_to_shift) % 0x08
        return wall_type

    def _HasStairway(self, level_num: int, room_num: int) -> str:
        room_type_code = self.GetRoomData(level_num, room_num + 3 * 0x80) & 0x3F

        # Spiral Stair, Narrow Stair, and Diamond Stair rooms always have a stairway
        if room_type_code in [0x1A, 0x1B, 0x1C]:
            return True

        # Check if there are any shutter doors in this room. If so, they'll open when a middle
        # row pushblock is pushed instead of a stairway appearing
        for direction in [Direction.NORTH, Direction.EAST, Direction.SOUTH, Direction.WEST]:
            if self._GetWallType(level_num, room_num, direction) == WallType.SHUTTER_DOOR:
                return False

        # Check if "Movable block" bit is set in a room_type that has a middle row pushblock
        if room_type_code in [
                0x01, 0x06, 0x07, 0x08, 0x09, 0x10, 0x0A, 0x0C, 0x0D, 0x11, 0x1F, 0x22
        ]:
            if ((self.GetRoomData(level_num, room_num + 3 * 0x80) >> 6) & 0x01) > 0:
                return True
        return False

    def _GetRoomType(self, level_num: int, room_num: int) -> str:
        code = self.GetRoomData(level_num, room_num + 3 * 0x80)
        while code >= 0x40:
            code -= 0x40
        if code in ROOM_TYPES:
            return ROOM_TYPES[code]
        return 'ERROR CODE %X' % code

    def _GetEnemyNum(self, level_num: int, room_num: int) -> int:
        code = math.floor(self.GetRoomData(level_num, room_num + 2 * 0x80) / 64)
        if code == 0:
            return 3
        elif code == 1:
            return 5
        elif code == 2:
            return 6
        elif code == 3:
            return 8
        return -1

    def _EnemyName(self, level_num: int, code: int) -> str:
        """Names a room's enemy code. A $0F person ($4F here) sells the bomb upgrade only in the
        two levels the ROM names (RomReader.GetBombUpgradeLevels); elsewhere it only talks."""
        if code == BOMB_UPGRADE_PERSON:
            levels = self.rom_reader.GetBombUpgradeLevels()
            if levels is not None and level_num not in levels:
                return TALKING_PERSON
        return ENEMY_TYPES[code]

    def _GetEnemyText(self, level_num: int, room_num: int) -> str:
        code = self.GetRoomData(level_num, room_num + 2 * 0x80)
        while code >= 0x40:
            code -= 0x40
        if self.GetRoomData(level_num, room_num + 3 * 0x80) >= 0x80:
            code += 0x40

        num_text = ''
        if (code <= 0x30 or code >= 0x62) and code != 0x00:
            num_text = '%s ' % self._GetEnemyNum(level_num, room_num)
        if code in ENEMY_TYPES:
            return num_text + self._EnemyName(level_num, code)
        return 'ERROR CODE %X' % code

    def _GetEnemyType(self, level_num: int, room_num: int) -> int:
        code = self.GetRoomData(level_num, room_num + 2 * 0x80)
        while code >= 0x40:
            code -= 0x40
        if self.GetRoomData(level_num, room_num + 3 * 0x80) >= 0x80:
            code += 0x40
        if code in ENEMY_TYPES:
            return self._EnemyName(level_num, code)
        return 'E %X' % code

    def _GetItemText(self, level_num: int, room_num: int) -> int:
        code = self.GetRoomData(level_num, room_num + 4 * 0x80)
        while code >= 0x20:
            code -= 0x20
        if code == self.nothing_code:
            # Ganon's room holds the Triforce of Power ($0E), which is also ZORA's nothing code.
            if self._GetEnemyType(level_num, room_num) != ENEMY_TYPES[0x3E]:
                return ''
            item_name = ITEM_TYPES[code]
        else:
            item_name = self.GetRoomItemName(code)
        is_drop = math.floor(self.GetRoomData(level_num, room_num + 5 * 0x80) / 4) % 0x02 == 1
        return "%s%s" % ('D ' if is_drop else '', item_name)

    def GetLevelColorPalette(self, level_num: int) -> List[str]:
        vals = self.level_info[level_num][PALETTE_OFFSET:PALETTE_OFFSET + 8]
        rgbs: List[str] = []
        for val in vals:
            rgbs.append(PALETTE_COLORS[val])
        return rgbs

    def GetOverworldItems(self) -> List[str]:
        tbr = []
        for item in self.rom_reader.GetOverworldItemData():
            tbr.append(self.GetItemName(item))
        return tbr

    def GetRequirements(self) -> int:
        return self.rom_reader.GetRequirements()

    def GetQuoteCount(self) -> int:
        return self.rom_reader.GetQuoteCount()

    def GetQuote(self, quote_num: int) -> str:
        return self.rom_reader.GetQuote(quote_num)

    def GetRecorderText(self) -> str:
        return self.rom_reader.GetRecorderText()

    def GetRecorderData(self) -> str:
        return self.rom_reader.GetRecorderData()

    def GetRecorderPatchData(self) -> str:
        patch_data = [0x50, 0x41, 0x54, 0x43, 0x48]  # PATCH

        # rom.seek(0x1AFE) was 0x1B00
        # rom.write(bytes([0x20, 0x00, 0xA0]))
        patch_data.extend([0x00, 0x1A, 0xFE, 0x00, 0x03, 0x20, 0x00, 0xA0])

        # rom.seek(0x1B12) was 0x1B14
        # rom.write(bytes([0x20, 0x10, 0xA0]))
        patch_data.extend([0x00, 0x1B, 0x12, 0x00, 0x03, 0x20, 0x10, 0xA0])

        # rom.seek(0x1B3D) was 0x183F
        # rom.write(bytes([0x20, 0x10, 0xA0]))
        patch_data.extend([0x00, 0x1B, 0x3D, 0x00, 0x03, 0x20, 0x10, 0xA0])

        # rom.seek(0x2010)
        # rom.write(bytes([0xAD, 0x07, 0x06, 0xC9, 0x10, 0xD0, 0x03, 0xA9,
        #                  0x00, 0x60, 0xB9, 0x54, 0x9A, 0x60]))
        patch_data.extend([0x00, 0x20, 0x10, 0x00, 0x0E])
        patch_data.extend(
            [0xAD, 0x07, 0x06, 0xC9, 0x10, 0xD0, 0x03, 0xA9, 0x00, 0x60, 0xB9, 0x54, 0x9A, 0x60])

        # rom.seek(0x2020)
        # rom.write(bytes([0xAD, 0x07, 0x06, 0xC9, 0x10, 0xD0, 0x04, 0xB9,
        #                  0x20, 0xA0, 0x60, 0xB9, 0x55, 0x9A, 0x60]))
        patch_data.extend([0x00, 0x20, 0x20, 0x00, 0x0F])
        patch_data.extend([
            0xAD, 0x07, 0x06, 0xC9, 0x10, 0xD0, 0x04, 0xB9, 0x20, 0xA0, 0x60, 0xB9, 0x55, 0x9A, 0x60
        ])

        # For the actual recorder tune
        rec_data = self.rom_reader.GetRecorderData()
        patch_data.extend([0x00, 0x20, 0x30, 0x00, len(rec_data)])
        patch_data.extend(rec_data)

        # For testing: Put the recorder in the wood sword cave
        # rom.seek(0x18611)
        # rom.write(bytes([0x05]))
        #patch_data.extend([0x01, 0x86, 0x11, 0x00, 0x01, 0x05])

        # EOF to close it out
        patch_data.extend([0x45, 0x4F, 0x46])
        return patch_data
