import unittest
from data_extractor import DataExtractor


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


if __name__ == '__main__':
    unittest.main()
