from rom_reader import RomReader
import io
from typing import IO, List
import math
from typing import Any, Dict, List, Optional
from constants import Direction, WallType
from constants import ENTRANCE_DIRECTION_MAP, ITEMS, PALETTE_COLORS, CAVE_NAME_SHORT, CAVE_NAME

PALETTE_OFFSET = 0xB
START_ROOM_OFFSET = 0x2F
STAIRWAY_LIST_OFFSET = 0x34
DISPLAY_OFFSET_OFFSET = 0x2D

class DataExtractor(object):
    def __init__(self, rom: io.BytesIO) -> None:
        self.rom_reader = RomReader(rom)
        self.is_z1r = True
        self.level_info: List[List[int]] = []
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
        
        self.data: Dict[int, Dict[int, Any]] = {}
        
        for level_num in range(1, 10):
          self.ProcessLevel(level_num)
          
        self.ProcessOverworld()

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
        self.data[0] = {}
        for screen_num in range(0, 0x80):
            print("Screen %x val is %x" % (screen_num, self.GetRoomData(0, screen_num + 5*0x80)))
            if (self.GetRoomData(0, screen_num + 5*0x80) & 0x80) > 0:
                continue
            print("Screen %x" % screen_num)
            foo = self.GetRoomData(0, screen_num + 1*0x80)
            print("Found 0x%x" % foo)
            bar = foo >> 2
            print("Now 0x%x" % bar)
            if bar == 0:
              continue
            x = screen_num % 0x10 
            y = 8 - (math.floor(screen_num / 0x10))
            self.data[0][screen_num] = {
                'screen_num': '%x' % screen_num,
                'col': x,
                'x_coord': x + .5,
                'row': y,
                'y_coord': y - .5,
                'cave': '%x' % bar
              }
            if bar in CAVE_NAME:
              self.data[0][screen_num]['cave_name'] = CAVE_NAME[bar]
            if bar in CAVE_NAME_SHORT:
              self.data[0][screen_num]['cave_name_short'] = CAVE_NAME_SHORT[bar]
 
    def ProcessLevel(self, level_num: int) -> None:
        #room_level_nums = [0] * 0x80
        self.data[level_num] = {}
        self._VisitRoom(level_num,
                        self.GetLevelStartRoomNumber(level_num),
                        # room_level_nums,
                        from_dir=self.GetLevelEntranceDirection(level_num))
        stairway_num = 1
        for stairway_room_num in self.GetLevelStairwayRoomNumberList(level_num):
            print('Visiting level %d Stairway room 0x%x' % (level_num, stairway_room_num))
            left_exit = self.GetRoomData(level_num, stairway_room_num) % 0x80
            right_exit = self.GetRoomData(level_num, stairway_room_num + 0x80) % 0x80
            self._VisitRoom(level_num, left_exit) #, room_level_nums)
            self._VisitRoom(level_num, right_exit) #, room_level_nums)
            if left_exit == right_exit:
              print("Found an item!")
              item_type = int(self.GetRoomData(level_num, stairway_room_num + (4 * 0x80)) % 0x1F)
              self.data[level_num][left_exit]['stairway_info'] = '%s' % ITEMS[item_type]
              print("Found item %x" % item_type)       
            else:
              self.data[level_num][left_exit]['stairway_info'] = 'Stairway #%d' % stairway_num
              self.data[level_num][right_exit]['stairway_info'] = 'Stairway #%d' % stairway_num
              print("Setting stairway for %x and %x" % (left_exit, right_exit))       
              stairway_num += 1
            
        for i in range(0, 0x80):
          if i % 0x10 == 0:
            print('')
          print('-' if i not in self.data[level_num] else '*', end='')
        print('')

    def GetLevelDisplayOffset(self, level_num: int) -> int:
        return self.level_info[level_num][DISPLAY_OFFSET_OFFSET] - 3


    def _VisitRoom(self,
                   level_num: int,
                   room_num: int,
                   #room_level_nums: List[int],
                   from_dir: Optional[Direction] = None) -> None:

        if room_num in self.data[level_num]:
            return
        x = (room_num + self.GetLevelDisplayOffset(level_num)) % 0x10 
        y = 8 - (math.floor(room_num / 0x10))
        self.data[level_num][room_num] = {'col': x, 'x_coord': x - .5, 'row': y, 'y_coord': y - .5, 'stairway_info': ''}
        
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
              WallType.LOCKED_DOOR_1: 'yellow',
              WallType.LOCKED_DOOR_2: 'yellow',
              WallType.WALK_THROUGH_WALL_1: 'purple',
              WallType.WALK_THROUGH_WALL_2: 'purple',
              WallType.SHUTTER_DOOR: 'orange',
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
            self._VisitRoom(level_num,
                            room_num + direction,
                            # room_level_nums,
                            from_dir=direction.inverse())

    def _GetWallType(self, level_num: int, room_num: int, direction: Direction) -> int:
        offset = 0x80 if direction in [Direction.EAST, Direction.WEST] else 0x00
        bits_to_shift = 32 if direction in [Direction.NORTH, Direction.WEST
                                           ] else 4

        wall_type = math.floor(
            self.GetRoomData(level_num, room_num + offset) / bits_to_shift) % 0x08
        return wall_type

    def GetLevelColorPalette(self, level_num: int) -> List[str]:
        vals = self.level_info[level_num][PALETTE_OFFSET:PALETTE_OFFSET + 8]
        rgbs: List[str] = []
        for val in vals:
            #print("%02x " % val, end="")
            rgbs.append(PALETTE_COLORS[val])
        return rgbs

if __name__ == '__main__':
  f = open('z1.nes', 'rb')
  de = DataExtractor(f)
  print('is_z1r: %s' % de.is_z1r)

  for i in range(0, 0xFC):
    if i % 0x10 == 0:
      print('')
    if i % 0x80 == 0:
      print('')
    print('%02x ' % de.level_info[1][i], end='')
  print('')
  de.ProcessLevel(7)