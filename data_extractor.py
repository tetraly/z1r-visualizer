from rom_reader import RomReader
import io
from typing import IO, List
import math
from typing import Any, Dict, List, Optional
from constants import Direction, WallType, ROOM_TYPES, ENEMY_TYPES, ITEM_TYPES
from constants import ENTRANCE_DIRECTION_MAP, PALETTE_COLORS, CAVE_NAME_SHORT, CAVE_NAME
from constants import OVERWORLD_BLOCK_TYPES

PALETTE_OFFSET = 0xB
START_ROOM_OFFSET = 0x2F
STAIRWAY_LIST_OFFSET = 0x34
DISPLAY_OFFSET_OFFSET = 0x2D

class DataExtractor(object):
    def __init__(self, rom: io.BytesIO, allow_decoding_roms: bool=False) -> None:
        self.rom_reader = RomReader(rom)
        self.is_z1r = True
        self.level_info: List[List[int]] = []
        self.data: Dict[int, Dict[int, Any]] = {}
        self.shop_data = {}
   
        for level_num in range(0, 10):
            level_info = self.rom_reader.GetLevelInfo(level_num)
            self.level_info.append(level_info)
            vals = level_info[0x34:0x3E]
            if vals[-1] in range(0, 5):
                continue
            self.is_z1r = False

        self.level_blocks: List[List[int]] = []
        for level_num in [0,1,7]:
            self.level_blocks.append(self.rom_reader.GetLevelBlock(level_num))
        
        self.ProcessOverworld()
        for level_num in range(1, 10):
            self.ProcessLevel(level_num)        

    def GetRoomData(self, level_num: int, byte_num: int) -> int:
        foo = -1
        if level_num == 0:
            foo = 0
        elif level_num in range(1, 7):
            foo = 1
        elif level_num in range(7, 10):
            foo = 2
        return self.level_blocks[foo][byte_num]
      
    def GetLevelEntranceDirection(self, level_num: int) -> Direction:
        if not self.is_z1r:
            return Direction.SOUTH
        return ENTRANCE_DIRECTION_MAP[self._GetRawLevelStairwayRoomNumberList(
            level_num)[-1]]

    def GetLevelStartRoomNumber(self, level_num: int) -> int:
        return self.level_info[level_num][START_ROOM_OFFSET]

    def GetLevelStairwayRoomNumberList(self, level_num: int) -> List[int]:
        stairway_list = self._GetRawLevelStairwayRoomNumberList(level_num)
        # In randomized roms, the last item in the stairway list is the entrance dir.
        if self.is_z1r:
            stairway_list.pop(-1)
        return stairway_list

    def _GetRawLevelStairwayRoomNumberList(self, level_num: int) -> List[int]:
        vals = self.level_info[level_num][
            STAIRWAY_LIST_OFFSET:STAIRWAY_LIST_OFFSET + 10]
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
        for shop_type in range (0x10, 0x24):
            base_index = 4*0x80 + 3*(shop_type-0x10)
            price_index = 4*0x80 + 3*(shop_type-0x10) + 0x14*3
            self.shop_data[shop_type] = []
            self.shop_data[shop_type].append(self.level_blocks[0][base_index] & 0x3F)
            self.shop_data[shop_type].append(self.level_blocks[0][base_index + 1] & 0x3F)
            self.shop_data[shop_type].append(self.level_blocks[0][base_index + 2] & 0x3F)
            self.shop_data[shop_type].append(self.level_blocks[0][price_index])
            self.shop_data[shop_type].append(self.level_blocks[0][price_index + 1])
            self.shop_data[shop_type].append(self.level_blocks[0][price_index + 2])
            
        self.data[0] = {}
        for screen_num in range(0, 0x80):
            # Skip any screens that aren't "Secret in 1st Quest"
            if (self.GetRoomData(0, screen_num + 5*0x80) & 0x80) > 0:
                continue
            # Cave destination is upper 6 bits of table 1
            destination = self.GetRoomData(0, screen_num + 1*0x80) >> 2
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
 
    def ProcessLevel(self, level_num: int) -> None:
        self.data[level_num] = {}
        rooms_to_visit = [(self.GetLevelStartRoomNumber(level_num), 
                           self.GetLevelEntranceDirection(level_num))]
        while True:
            room_num, direction = rooms_to_visit.pop()
            new_rooms = self._VisitRoom(level_num, room_num, direction)
            if new_rooms:
                rooms_to_visit.extend(new_rooms)
            if not rooms_to_visit:
                break
        stairway_num = 1
        for stairway_room_num in self.GetLevelStairwayRoomNumberList(level_num):
            left_exit = self.GetRoomData(level_num, stairway_room_num) % 0x80
            right_exit = self.GetRoomData(level_num, stairway_room_num + 0x80) % 0x80

            # Ignore any rooms in the stairway room list that don't connect to the current level.
            if not (left_exit in self.data[level_num] and right_exit in self.data[level_num]):
                print("WARNING: This seed has a phantom stairway room %x in level %d" %
                      (stairway_room_num, level_num))
                continue

            if left_exit == right_exit:  # Item stairway
              item_type = int(self.GetRoomData(level_num, stairway_room_num + (4 * 0x80)) % 0x1F)
              self.data[level_num][left_exit]['stair_info'] = '%s' % ITEM_TYPES[item_type]
              self.data[level_num][left_exit]['stair_tooltip'] = '%s' % ITEM_TYPES[item_type]
            else:  # Transport stairway
              self.data[level_num][left_exit]['stair_info'] = 'Stair #%d' % stairway_num
              self.data[level_num][right_exit]['stair_info'] = 'Stair #%d' % stairway_num
              self.data[level_num][left_exit]['stair_tooltip'] = 'Stairway #%d' % stairway_num
              self.data[level_num][right_exit]['stair_tooltip'] = 'Stairway #%d' % stairway_num
              stairway_num += 1
            
    def GetLevelDisplayOffset(self, level_num: int) -> int:
        return self.level_info[level_num][DISPLAY_OFFSET_OFFSET] - 3


    def _VisitRoom(self,
                   level_num: int,
                   room_num: int,
                   from_dir: Direction) -> None:
        if room_num in self.data[level_num]:
            return
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
            if (room_num + int(direction)) in self.data[level_num]:
              self.data[level_num][room_num]['%s.color' % direction_text[direction]] = "red"

            self.data[level_num][room_num]['%s.wall.x' % direction_text[direction]] = x + direction_x[direction]
            self.data[level_num][room_num]['%s.wall.y' % direction_text[direction]] = y + direction_y[direction]
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
            self.data[level_num][room_num]['%s.x' % direction_text[direction]] = x + direction_x[direction]
            self.data[level_num][room_num]['%s.y' % direction_text[direction]] = y + direction_y[direction]
            self.data[level_num][room_num]['%s.color' % direction_text[direction]] = color[wall_type]  
        
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
                break
            elif left_exit == room_num and right_exit != room_num:
                tbr.append((right_exit, direction.NO_DIRECTION))
                # Stop looking for additional staircases after finding one
                break
            elif right_exit == room_num and left_exit != room_num:
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
        room_type_code = self.GetRoomData(level_num, room_num + 3*0x80) & 0x3F

        # Spiral Stair, Narrow Stair, and Diamond Stair rooms always have a stairway
        if room_type_code in [0x1A, 0x1B, 0x1C]:
            return True

        # Check if there are any shutter doors in this room. If so, they'll open when a middle
        # row pushblock is pushed instead of a stairway appearing
        for direction in [Direction.NORTH, Direction.EAST, Direction.SOUTH, Direction.WEST]:
            if self._GetWallType(level_num, room_num, direction) == WallType.SHUTTER_DOOR:
                return False

        # Check if "Movable block" bit is set in a room_type that has a middle row pushblock
        if room_type_code in [0x01, 0x07, 0x08, 0x09, 0x10, 0x0A, 0x0C, 0x0D, 0x11, 0x1F, 0x22]:
            if ((self.GetRoomData(level_num, room_num + 3*0x80) >> 6) & 0x01) > 0:
                return True
        return False

    def _GetRoomType(self, level_num: int, room_num: int) -> str:
        code = self.GetRoomData(level_num, room_num + 3*0x80)
        while code >= 0x40:
            code -= 0x40             
        if code in ROOM_TYPES:
            return ROOM_TYPES[code]
        return 'ERROR CODE %X' % code

    def _GetEnemyNum(self, level_num: int, room_num: int) -> int:
        code = math.floor(self.GetRoomData(level_num, room_num + 2*0x80) / 64)
        if code == 0:
          return 3
        elif code == 1:
          return 5
        elif code == 2:
          return 6
        elif code == 3:
          return 8
        return -1

    def _GetEnemyText(self, level_num: int, room_num: int) -> str:
      code = self.GetRoomData(level_num, room_num + 2*0x80)
      while code >= 0x40:
          code -= 0x40
      if self.GetRoomData(level_num, room_num + 3*0x80) >= 0x80:
          code += 0x40

      num_text = ''
      if (code <= 0x30 or code >= 0x62) and code != 0x00:
          num_text = '%s ' % self._GetEnemyNum(level_num, room_num)
      if code in ENEMY_TYPES:
          return num_text + ENEMY_TYPES[code]
      return 'ERROR CODE %X' % code

    def _GetEnemyType(self, level_num: int, room_num: int) -> int:
        code = self.GetRoomData(level_num, room_num + 2*0x80)
        while code >= 0x40:
            code -= 0x40
        if self.GetRoomData(level_num, room_num + 3*0x80) >= 0x80:
            code += 0x40
        if code in ENEMY_TYPES:
            return ENEMY_TYPES[code]
        return 'E %X' % code

    def _GetItemText(self, level_num: int, room_num: int) -> int:
       code =  self.GetRoomData(level_num, room_num + 4*0x80)
       while code >= 0x20:
           code -= 0x20
       if code == 0x03:
           return ''
       is_drop = math.floor(self.GetRoomData(level_num, room_num + 5*0x80) / 4) % 0x02 == 1
       return "%s%s" % ('D ' if is_drop else '', ITEM_TYPES[code])

    def GetLevelColorPalette(self, level_num: int) -> List[str]:
        vals = self.level_info[level_num][PALETTE_OFFSET:PALETTE_OFFSET + 8]
        rgbs: List[str] = []
        for val in vals:
            rgbs.append(PALETTE_COLORS[val])
        return rgbs
        
    def GetOverworldItems(self) -> List[str]:
         tbr = []
         for item in self.rom_reader.GetOverworldItemData():
             tbr.append(ITEM_TYPES[item])
         return tbr
         
    def GetTriforceRequirement(self) -> int:
      return self.rom_reader.GetTriforceRequirement()

    def GetQuote(self, quote_num:int) -> str:
        return self.rom_reader.GetQuote(quote_num)

    def GetRecorderText(self) -> str:
        return self.rom_reader.GetRecorderText()

