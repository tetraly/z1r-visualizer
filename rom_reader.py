from enum import IntEnum
import io
from typing import IO, List
from constants import CHAR_MAP

OVERWORLD_DATA_LOCATION = 0x18400
LEVEL_1_TO_6_DATA_LOCATION = 0x18700
LEVEL_7_TO_9_DATA_LOCATION = 0x18A00
VARIOUS_DATA_LOCATION = 0x19300
NES_HEADER_OFFSET = 0x10
ARMOS_ITEM_ADDRESS = 0x10CF5
COAST_ITEM_ADDRESS = 0x1788A
WS_ITEM_ADDRESS = 0x18607
TRIFORCE_COUNT_ADDRESS = 0x5F17


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
        
    def GetOverworldItemData(self) -> List[int]:
        return [
            self._ReadMemory(ARMOS_ITEM_ADDRESS, 0x01)[0],
            self._ReadMemory(COAST_ITEM_ADDRESS, 0x01)[0],
            self._ReadMemory(WS_ITEM_ADDRESS, 0x01)[0],
        ]

    def GetTriforceRequirement(self) -> int:
        return self._ReadMemory(TRIFORCE_COUNT_ADDRESS, 0x01)[0]
        
    def GetQuote(self, num: int) -> str:
      assert num in range(0, 38)
      low_byte = self._ReadMemory(0x4000 + 2*num, 0x01)[0]
      high_byte =  self._ReadMemory(0x4000 + 2*num + 1, 0x01)[0] - 0x40
      addr = high_byte * 0x100 + low_byte
      raw_quote = self._ReadMemory(addr, 0x40)
      out_quote = ""
      for val in raw_quote:
          char = val & 0x3F
          out_quote += CHAR_MAP[char]
          high_bits = (val >> 6) & 0x03
          if high_bits in [1, 2]:
              out_quote += " "
          if high_bits == 3:
              break
      return out_quote

    def hex_to_text(self, hex):
      tbr = ""
      for val in hex:
        tbr += CHAR_MAP[val]
      return tbr

    def GetRecorderText(self) -> str:
       raw_quote = self._ReadMemory(0xB000, 0x40)
       if raw_quote[0] != 8:
         return ""
       recorder_len = raw_quote[0]
       name_len = raw_quote[3+recorder_len]
       name_text = raw_quote[4+recorder_len:2+recorder_len + name_len]
       from_len = raw_quote[5 +recorder_len + name_len]
       from_text = raw_quote[4+recorder_len + name_len : 4+recorder_len + name_len + from_len]
       return ' '.join([self.hex_to_text(name_text), self.hex_to_text(from_text)])
