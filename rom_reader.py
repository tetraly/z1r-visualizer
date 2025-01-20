from enum import IntEnum
import io
from typing import IO, List

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
