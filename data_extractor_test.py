import io
import os
import unittest
from data_extractor import DataExtractor, GarbledLevelDataError


class Bar():
    pass


class Foo(object):

    def getvalue(self):
        return Bar()


class DataExtractorTest(unittest.TestCase):

    def test_open_vanilla_rom(self):
        with open('testdata/z1.nes', 'rb') as f:
            de = DataExtractor(f)
            self.assertFalse(de.is_z1r)
            level_1_start_room = de.data[1][0x73]
            self.assertEqual('yellow', level_1_start_room['north.color'])
            self.assertEqual('black', level_1_start_room['south.color'])

    def test_open_randomized_rom(self):
        with open('testdata/z1-prg0-12345-no-rr-354.nes', 'rb') as f:
            de = DataExtractor(f)
            self.assertTrue(de.is_z1r)
            level_1_test_room = de.data[1][70]
            self.assertEqual('orange', level_1_test_room['north.color'])
            self.assertEqual('orange', level_1_test_room['south.color'])

    def test_open_randomized_encoded_rom(self):
        with open('testdata/z1-prg0-12345-with-rr-354.nes', 'rb') as f:
            de = DataExtractor(f)
            self.assertTrue(de.is_z1r)
            level_1_test_room = de.data[1][12]
            self.assertEqual('black', level_1_test_room['south.color'])
            self.assertEqual('black', level_1_test_room['west.color'])

    @unittest.skipUnless(os.path.exists('testdata/zora-playtest-seed42.nes'), 'playtest ROM not present')
    def test_plain_rom_passes_validation(self):
        with open('testdata/zora-playtest-seed42.nes', 'rb') as f:
            de = DataExtractor(f)
            de.Parse()
            self.assertEqual(14, len(de.data[1]))
            self.assertTrue(all(len(de.data[level]) <= 64 for level in range(1, 10)))

    @unittest.skipUnless(os.path.exists('testdata/zora-playtest-seed42-encoded.nes'), 'playtest ROM not present')
    def test_encoded_rom_is_rejected(self):
        with open('testdata/zora-playtest-seed42-encoded.nes', 'rb') as f:
            de = DataExtractor(f)
            with self.assertRaises(GarbledLevelDataError):
                de.Parse()


def _ParsedZoraRom(name):
    with open('testdata/%s' % name, 'rb') as f:
        de = DataExtractor(io.BytesIO(f.read()))
    de.Parse()
    return de


def _HasTestRom(name):
    return os.path.exists('testdata/%s' % name)


# ZORA ROMs generated with zora.api.generate_rom from the Consternation preset without level
# encoding ('8hq4BeR1JXo89BJ2!TFpTP02u8UJ3A'), or the same preset with B09 off for Progressive
# Items ('8hq4BeR1JXo7yjOOHjbxryVQW!UJ3A'). The file names give the ZORA option and the seed.
class ZoraRomTest(unittest.TestCase):

    @unittest.skipUnless(_HasTestRom('zora-sword-seed1.nes'), 'ZORA ROM not present')
    def test_magical_sword_in_level_room(self):
        # Randomize Magical Sword (ZORA flags 1.D) makes $0E the nothing code, so $03 is the sword.
        de = _ParsedZoraRom('zora-sword-seed1.nes')
        self.assertEqual(0x0E, de.nothing_code)
        self.assertEqual('D Magical Sword', de.data[4][0x0A]['item_info'])

    @unittest.skipUnless(_HasTestRom('zora-sword-seed3.nes'), 'ZORA ROM not present')
    def test_magical_sword_in_item_cellar(self):
        de = _ParsedZoraRom('zora-sword-seed3.nes')
        self.assertEqual('Magical Sword', de.data[8][0x69]['stair_info'])

    @unittest.skipUnless(_HasTestRom('zora-sword-seed100.nes'), 'ZORA ROM not present')
    def test_magical_sword_at_armos(self):
        de = _ParsedZoraRom('zora-sword-seed100.nes')
        self.assertEqual(['Magical Sword', 'Heart Container'], de.GetOverworldItems())

    @unittest.skipUnless(_HasTestRom('zora-sword-seed1.nes'), 'ZORA ROM not present')
    def test_nothing_code_rooms_stay_empty_except_ganon(self):
        de = _ParsedZoraRom('zora-sword-seed1.nes')
        items = [room['item_info'] for level in range(1, 10) for room in de.data[level].values()]
        self.assertNotIn('No Item', items)
        self.assertEqual(1, items.count('Triforce of Power'))

    @unittest.skipUnless(_HasTestRom('zora-progressive-seed1.nes'), 'ZORA ROM not present')
    def test_progressive_items_shown_by_line(self):
        de = _ParsedZoraRom('zora-progressive-seed1.nes')
        self.assertTrue(de.has_progressive_items)
        self.assertEqual('Sword Upgrade', de.data[7][0x25]['stair_info'])  # a White Sword byte
        self.assertEqual('Sword Upgrade', de.GetItemName(de.shop_data[0x10][1]))  # Wood Sword cave
        self.assertEqual('Ring Upgrade', de.GetItemName(0x12))
        self.assertEqual('Bow', de.GetItemName(0x0A))

    @unittest.skipUnless(_HasTestRom('zora-sword-seed1.nes'), 'ZORA ROM not present')
    def test_progressive_items_off(self):
        de = _ParsedZoraRom('zora-sword-seed1.nes')
        self.assertFalse(de.has_progressive_items)
        self.assertEqual('Magical Sword', de.GetItemName(0x03))
        self.assertEqual('Blue Ring', de.GetItemName(0x12))

    @unittest.skipUnless(_HasTestRom('zora-sword-seed1.nes'), 'ZORA ROM not present')
    def test_all_hint_texts(self):
        de = _ParsedZoraRom('zora-sword-seed1.nes')
        self.assertEqual(45, de.GetQuoteCount())
        self.assertEqual('MASTER USING IT AND YOU CAN HAVE THE HEART CONTAINER', de.GetQuote(1))
        self.assertEqual('THIS COULD BE YOU!', de.GetQuote(44))

    @unittest.skipUnless(_HasTestRom('zora-sword-seed1.nes'), 'ZORA ROM not present')
    def test_recorder_text_without_custom_tune(self):
        # ZORA has code where a custom recorder tune's text would be.
        de = _ParsedZoraRom('zora-sword-seed1.nes')
        self.assertEqual('', de.GetRecorderText())

    @unittest.skipUnless(_HasTestRom('zora-encoded-seed1.nes'), 'ZORA ROM not present')
    def test_encoded_rom_refused_by_marker(self):
        with open('testdata/zora-encoded-seed1.nes', 'rb') as f:
            de = DataExtractor(io.BytesIO(f.read()))
        self.assertTrue(de.rom_reader.HasZoraEncodedLevelData())
        with self.assertRaisesRegex(GarbledLevelDataError, "ZORA's level decoder"):
            de.Parse()
        self.assertFalse(_ParsedZoraRom('zora-sword-seed1.nes').rom_reader.HasZoraEncodedLevelData())


class ShopItemTest(unittest.TestCase):

    # A Zelda Randomizer seed whose Shop 2 sells a fairy ($23) for 50 rupees.
    @unittest.skipUnless(_HasTestRom('z1r-fairy-shop.nes'), 'Z1R ROM not present')
    def test_fairy_in_shop(self):
        de = _ParsedZoraRom('z1r-fairy-shop.nes')
        self.assertEqual(0x23, de.shop_data[0x1E][0])
        self.assertEqual('Fairy', de.GetItemName(de.shop_data[0x1E][0]))

    @unittest.skipUnless(_HasTestRom('zora-sword-seed1.nes'), 'ZORA ROM not present')
    def test_item_names_never_raise(self):
        de = _ParsedZoraRom('zora-sword-seed1.nes')
        self.assertEqual('Clock', de.GetItemName(0x21))
        self.assertEqual('Unknown Item 30', de.GetItemName(0x30))


if __name__ == '__main__':
    unittest.main()
