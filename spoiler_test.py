import json
import os
import unittest
from spoiler import Export


def _Export(name):
    with open('testdata/%s' % name, 'rb') as f:
        return Export(f.read())


def _HasTestRom(name):
    return os.path.exists('testdata/%s' % name)


class ExportTest(unittest.TestCase):

    @unittest.skipUnless(_HasTestRom('zora-sword-seed1.nes'), 'ZORA ROM not present')
    def test_parsed_rom(self):
        data = _Export('zora-sword-seed1.nes')
        self.assertEqual('ok', data['status'])
        self.assertEqual([str(level) for level in range(1, 10)], list(data['levels']))
        self.assertEqual(45, len(data['texts']))
        self.assertIn({'Item': 'Magical Sword', 'Screen': 'A', 'Location': 'Drop'},
                      data['itemSummary']['levels']['4'])
        self.assertIn({'Cave': 'Magical Sword Cave', 'Item': 'Heart Container'}, data['itemSummary']['caves'])
        self.assertEqual(json.loads(json.dumps(data)), data)  # plain JSON, nothing lost

    @unittest.skipUnless(_HasTestRom('zora-encoded-seed1.nes'), 'ZORA ROM not present')
    def test_encoded_rom_gives_no_seed_data(self):
        data = _Export('zora-encoded-seed1.nes')
        self.assertEqual('encoded', data['status'])
        self.assertIn("ZORA's level decoder", data['message'])
        self.assertEqual({'status', 'message', 'recorder'}, set(data))

    def test_not_a_rom(self):
        data = Export(b'not a rom')
        self.assertEqual('unsupported', data['status'])
        self.assertEqual({'status', 'message', 'recorder'}, set(data))


if __name__ == '__main__':
    unittest.main()
