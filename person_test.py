"""Dungeon persons with code $0F: a bomb upgrade only in the two levels the ROM names."""
import io
import os
import unittest

from constants import TALKING_PERSON
from data_extractor import DataExtractor


def _Parsed(name):
    with open('testdata/%s' % name, 'rb') as f:
        de = DataExtractor(io.BytesIO(f.read()))
    de.Parse()
    return de


def _HasTestRom(name):
    return os.path.exists('testdata/%s' % name)


def _Persons(de):
    """{(level, room): name} for every $0F person, as the views name them."""
    return {(level, room): data['enemy_type_tooltip'] for level in range(1, 10) for room, data in de.data[level].items()
            if data['enemy_type_tooltip'] in ('Bomb Upgrade', TALKING_PERSON)}


class BombUpgradeTest(unittest.TestCase):

    @unittest.skipUnless(_HasTestRom('prg0.nes'), 'PRG0 ROM not present')
    def test_vanilla(self):
        # Levels 5 and 7 sell the upgrade; level 8 has a $0F person who only talks.
        de = _Parsed('prg0.nes')
        self.assertEqual((5, 7), de.rom_reader.GetBombUpgradeLevels())
        self.assertEqual({(5, 0x17): 'Bomb Upgrade', (7, 0x48): 'Bomb Upgrade', (8, 0x3D): TALKING_PERSON},
                         _Persons(de))
        self.assertEqual(TALKING_PERSON, de.data[8][0x3D]['enemy_info'])

    @unittest.skipUnless(_HasTestRom('zora-sword-seed1.nes'), 'ZORA ROM not present')
    def test_moved_bomb_upgrades(self):
        # ZORA's bomb-upgrade shuffle names levels 8 and 2; the $0F person in level 4 only talks.
        de = _Parsed('zora-sword-seed1.nes')
        self.assertEqual((8, 2), de.rom_reader.GetBombUpgradeLevels())
        self.assertEqual({(2, 0x05): 'Bomb Upgrade', (4, 0x1A): TALKING_PERSON, (8, 0x27): 'Bomb Upgrade'},
                         _Persons(de))

    @unittest.skipUnless(_HasTestRom('zora-sword-seed1.nes'), 'ZORA ROM not present')
    def test_unrecognised_code_keeps_the_old_reading(self):
        # A ROM whose code there is not the comparison: every $0F person stays a bomb upgrade.
        with open('testdata/zora-sword-seed1.nes', 'rb') as f:
            rom = bytearray(f.read())
        rom[0x4AF1] = 0xEA  # the BEQ becomes a NOP
        de = DataExtractor(io.BytesIO(bytes(rom)))
        de.Parse()
        self.assertIsNone(de.rom_reader.GetBombUpgradeLevels())
        self.assertEqual({'Bomb Upgrade'}, set(_Persons(de).values()))


if __name__ == '__main__':
    unittest.main()
