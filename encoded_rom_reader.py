from emu import CPU, MMU
import io
from typing import IO, List


class EncodedRomReader:

    def __init__(self, rom: io.BytesIO) -> None:
        self.rom = rom

        start = 0x10 + 0x4000 * 6
        end = 0x10 + 0x4000 * 8
        # rom_banks = list(rom.getvalue()[start:end])
        rom.seek(0)
        rom_banks = list(rom.read()[start:end])

        self.mmu = MMU([(0x0, 0x630, False, []), (0x6800, 0x1000, False, []),
                        (0x8000, 0x8000, True, rom_banks)])
        self.cpu = CPU(self.mmu, 0x0)

        self.mmu.write(0x16, 2)  # CurSaveSlot = 2 (Third Slot)
        self.mmu.write(0x62F, 0)  # QuestNumber[2] = 0 (First Quest)

    def _execute_subroutine(self, addr: int) -> None:
        s_before = self.cpu.r.s
        self.cpu.JSR(addr)
        while self.cpu.r.s != s_before:
            next_instr = self.mmu.read(self.cpu.r.pc)
            self.cpu.step()

    def GetLevelBlock(self, level_num: int) -> List[int]:
        self.mmu.write(0x10, level_num)  # Set CurLevel
        self._execute_subroutine(0x8047)

        tbr: List[int] = []
        for a in range(0x687E, 0x687E + 0x300):
            tbr.append(self.mmu.read(a))
        return tbr

    def GetLevelInfo(self, level_num: int) -> List[int]:
        self.mmu.write(0x10, level_num)  # Set CurLevel
        self._execute_subroutine(0x8070)

        tbr: List[int] = []
        for a in range(0x6B7E, 0x6B7E + 0x80):
            tbr.append(self.mmu.read(a))
        return tbr
