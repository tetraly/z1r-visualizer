from enum import IntEnum
import io
from typing import IO, List

OVERWORLD_DATA_LOCATION = 0x18400
LEVEL_1_TO_6_DATA_LOCATION = 0x18700
LEVEL_7_TO_9_DATA_LOCATION = 0x18A00
VARIOUS_DATA_LOCATION = 0x19300
NES_HEADER_OFFSET = 0x10


class RomReader:
  
    def __init__(self, rom: io.BytesIO) -> None:
        self.rom = rom

    def _ReadMemory(self, address: int, num_bytes: int = 1) -> List[int]:
        assert num_bytes > 0, "num_bytes shouldn't be negative"
        self.rom.seek(NES_HEADER_OFFSET + address)
        data = []  # type: List[int]
        for raw_byte in self.rom.read(num_bytes):
            data.append(int(raw_byte))
        return data
    
    def GetLevelBlock(self, level_num: int) -> List[int]:
        if level_num == 0:
            return self._ReadMemory(OVERWORLD_DATA_LOCATION, 0x300)
        if level_num in range(1, 7):
            return self._ReadMemory(LEVEL_1_TO_6_DATA_LOCATION, 0x300)
        if level_num in range(7, 10):
            return self._ReadMemory(LEVEL_7_TO_9_DATA_LOCATION, 0x300)
        return []

    def GetLevelInfo(self, level_num: int) -> List[int]:
        start = VARIOUS_DATA_LOCATION + level_num * 0xFC
        return self._ReadMemory(start, 0xFC)

if __name__ == '__main__':
  f = open('z1.nes', 'rb')
  r = RomReader(f)
  #d = r.GetRoomGridRawData(0)
  d = r.GetLevelInfo(1)

  for i in range(0, 0xFC):
    if i % 0x10 == 0:
      print('')
    if i % 0x80 == 0:
      print('')
    print('%02x ' % d[i], end='')
  print('')