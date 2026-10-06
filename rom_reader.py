from enum import IntEnum
import io
from typing import IO, List, Optional, Tuple
from constants import CHAR_MAP

OVERWORLD_DATA_LOCATION = 0x18400
LEVEL_1_TO_6_FIRST_QUEST_DATA_LOCATION = 0x18700
LEVEL_7_TO_9_FIRST_QUEST_DATA_LOCATION = 0x18A00
LEVEL_1_TO_6_SECOND_QUEST_DATA_LOCATION = 0x18D00
LEVEL_7_TO_9_SECOND_QUEST_DATA_LOCATION = 0x19000
OVERWORLD_POINTER_LOCATION = 0x18000
LEVEL_1_TO_6_POINTER_LOCATION = 0x18002
LEVEL_7_TO_9_POINTER_LOCATION = 0x1800E

VARIOUS_DATA_LOCATION = 0x19300
NES_HEADER_OFFSET = 0x10
ARMOS_ITEM_ADDRESS = 0x10CF5
COAST_ITEM_ADDRESS = 0x1788A
WS_ITEM_ADDRESS = 0x18607
TRIFORCE_REQUIREMENT_ADDRESS = 0x5F17
WHITE_SWORD_REQUIREMENT_ADDRESS = 0x48FD
MAGICAL_SWORD_REQUIREMENT_ADDRESS = 0x4906
DOOR_REPAIR_CHARGE_ADDRESS = 0x4890
NOTHING_CODE_ADDRESS = 0x1784F
TEXT_POINTER_TABLE_ADDRESS = 0x4000
MAX_QUOTES = 64

# ZORA's per-seed Progressive Items byte (zora-ng docs/rom-map.md, ZORA_B1_ProgressiveItems at
# CPU $BE40 in bank 1): $01 when Progressive Items is on. It is $00 when only Shop Items in the
# Item Pool is on, and $FF (unused space) in vanilla and other randomizers' ROMs.
ZORA_PROGRESSIVE_ITEMS_ADDRESS = 0x7E40

# ZORA's "Encode level data" rewrites InitMode2_Sub0's JSR to call its level decoder at $9220
# (zora-ng docs/rom-map.md). Unencoded ROMs keep PRG0's JSR $80D7 here.
LEVEL_DECODER_JSR_ADDRESS = 0x1806C
ZORA_LEVEL_DECODER_JSR = [0x20, 0x20, 0x92]


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

    def _GetLevelBlockPointer(self, addr: int) -> List[int]:
        val = self._ReadMemory(addr, 0x02)
        return val[1] * 0x100 + val[0]

    def GetLevelBlock(self, level_num: int) -> List[int]:
        if level_num == 0:
            if self._GetLevelBlockPointer(OVERWORLD_POINTER_LOCATION) == 0x8400:
                return self._ReadMemory(OVERWORLD_DATA_LOCATION, 0x300)
        if level_num in range(1, 7):
            if self._GetLevelBlockPointer(LEVEL_1_TO_6_POINTER_LOCATION) == 0x8700:
                return self._ReadMemory(LEVEL_1_TO_6_FIRST_QUEST_DATA_LOCATION, 0x300)
            elif self._GetLevelBlockPointer(LEVEL_1_TO_6_POINTER_LOCATION) == 0x8D00:
                return self._ReadMemory(LEVEL_1_TO_6_SECOND_QUEST_DATA_LOCATION, 0x300)
        if level_num in range(7, 10):
            if self._GetLevelBlockPointer(LEVEL_7_TO_9_POINTER_LOCATION) == 0x8A00:
                return self._ReadMemory(LEVEL_7_TO_9_FIRST_QUEST_DATA_LOCATION, 0x300)
            elif self._GetLevelBlockPointer(LEVEL_7_TO_9_POINTER_LOCATION) == 0x9000:
                return self._ReadMemory(LEVEL_7_TO_9_SECOND_QUEST_DATA_LOCATION, 0x300)
        return []

    def GetLevelInfo(self, level_num: int) -> List[int]:
        start = VARIOUS_DATA_LOCATION + level_num * 0xFC
        return self._ReadMemory(start, 0xFC)

    def GetOverworldItemData(self) -> List[int]:
        return [
            self._ReadMemory(ARMOS_ITEM_ADDRESS, 0x01)[0],
            self._ReadMemory(COAST_ITEM_ADDRESS, 0x01)[0],
        ]

    def GetBombUpgradeLevels(self) -> Optional[Tuple[int, int]]:
        """The two levels whose $0F dungeon person sells the bomb upgrade.

        The game compares the current level with two numbers: CMP #a / BEQ / CMP #b / BNE, at
        file offsets 0x4AEF-0x4AF5 (the levels at 0x4AF0 and 0x4AF4). Vanilla ROMs have 5 and 7;
        randomizers that move the bomb-upgrade persons rewrite them. A $0F person in any other
        level only talks. Returns None when the code there is not that comparison (a ROM that
        changed it), so callers can keep the old reading.
        """
        code = self._ReadMemory(0x4AEF - NES_HEADER_OFFSET, 0x07)
        if [code[0], code[2], code[3], code[4], code[6]] != [0xC9, 0xF0, 0x04, 0xC9, 0xD0]:
            return None
        return code[1], code[5]

    def GetRequirements(self) -> int:
        return {
            "triforce":
                self._ReadMemory(TRIFORCE_REQUIREMENT_ADDRESS, 0x01)[0],
            "white_sword":
                int(self._ReadMemory(WHITE_SWORD_REQUIREMENT_ADDRESS, 0x01)[0] / 0x10) + 1,
            "magical_sword":
                int(self._ReadMemory(MAGICAL_SWORD_REQUIREMENT_ADDRESS, 0x01)[0] / 0x10) + 1,
            "door_repair":
                self._ReadMemory(DOOR_REPAIR_CHARGE_ADDRESS, 0x01)[0],
        }

    def _GetTextPointer(self, num: int) -> int:
        low_byte, high_byte = self._ReadMemory(TEXT_POINTER_TABLE_ADDRESS + 2 * num, 0x02)
        return high_byte * 0x100 + low_byte

    def GetQuoteCount(self) -> int:
        """Counts the entries in the text pointer table.

        Vanilla has 38 texts, some Z1R seeds have 41 and ZORA has 45. The texts start right
        after the table, so the table ends where an entry would overlap the first text, or at
        the first entry that doesn't point into the text bank.
        """
        lowest_text = 0xC000
        num = 0
        while num < MAX_QUOTES and 0x8000 + 2 * num < lowest_text:
            pointer = self._GetTextPointer(num)
            if not 0x8000 <= pointer < 0xC000:
                break
            lowest_text = min(lowest_text, pointer)
            num += 1
        return num

    def GetQuote(self, num: int) -> str:
        assert num in range(0, self.GetQuoteCount())
        pointer = self._GetTextPointer(num)
        low_byte = pointer & 0xFF
        high_byte = (pointer >> 8) - 0x40
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

    def GetRecorderText(self) -> str:
        # Without a custom recorder tune, $B000 isn't recorder text (ZORA puts code there).
        if self.GetRecorderData()[0] == 0xFF:
            return ""
        raw_data = self._ReadMemory(0xB000, 0x40)
        if raw_data[0] == 0xFF:
            return ""

        words = []
        index = 0
        while index < len(raw_data):
            length = raw_data[index]
            bytes_to_process = raw_data[index + 2:index + 2 + length]
            if any(val not in CHAR_MAP for val in bytes_to_process):
                return ""
            word = "".join([CHAR_MAP[val] for val in bytes_to_process])
            if word != "RECORDER":
                words.append(word)
            index += 2 + length

        return ' '.join(words)

    def GetRecorderData(self) -> str:
        raw_data = self._ReadMemory(0x2020, 0x40)
        tbr = []

        for val in raw_data:
            tbr.append(val)
            if val == 00 or val == 0xFF:
                break
        return tbr

    def GetNothingCode(self):
        return self._ReadMemory(NOTHING_CODE_ADDRESS, 0x01)[0]

    def HasProgressiveItems(self) -> bool:
        return self._ReadMemory(ZORA_PROGRESSIVE_ITEMS_ADDRESS, 0x01)[0] == 0x01

    def HasZoraEncodedLevelData(self) -> bool:
        return self._ReadMemory(LEVEL_DECODER_JSR_ADDRESS, 0x03) == ZORA_LEVEL_DECODER_JSR
